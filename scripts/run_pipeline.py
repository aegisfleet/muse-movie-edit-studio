"""
End-to-End Movie Editing Pipeline Orchestrator (Generalized Framework)
GoPro Raw -> Fast GPU HLG Tonemap & Adaptive Grading -> Smooth Dynamic xfade -> Remotion Synthesis -> final.mp4
Any config YAML, any video source, any cut length!
"""

import os
import sys
import json
import yaml
import shutil
import argparse
import subprocess
from pathlib import Path

# Windows console encoding fix
if sys.stdout:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

def parse_time_str(t_str: str) -> float:
    """HH:MM:SS or MM:SS or seconds string -> float seconds"""
    parts = str(t_str).strip().split(":")
    if len(parts) == 3:
        return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
    elif len(parts) == 2:
        return float(parts[0]) * 60 + float(parts[1])
    else:
        return float(parts[0])

def format_time_str(seconds: float) -> str:
    """float seconds -> HH:MM:SS.mmm"""
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = seconds % 60
    return f"{hrs:02d}:{mins:02d}:{secs:06.3f}"

def get_ffmpeg_path():
    """FFmpegの実行可能ファイルパスを取得"""
    ffmpeg_cmd = shutil.which("ffmpeg")
    if ffmpeg_cmd:
        return ffmpeg_cmd
    winget_pkg = Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft/WinGet/Packages"
    for p in winget_pkg.glob("**/ffmpeg.exe"):
        return str(p)
    return "ffmpeg"

def select_video_encoder() -> list:
    """
    映像エンコーダを選択する。
    - 環境変数 VIDEO_ENCODER=nvenc|x264 で明示指定が可能。
    - 既定では NVIDIA GPU デバイス (nvidia-smi または /dev/nvidia0) が
      実際に存在する場合のみ h264_nvenc を使い、それ以外は libx264 に
      フォールバックする。エンコーダがビルドに含まれていても GPU が
      無い環境 (Muse VM や一般的な CI) では NVENC は実行時に失敗するため。
    """
    choice = os.environ.get("VIDEO_ENCODER", "auto").lower()
    has_gpu = bool(shutil.which("nvidia-smi")) or Path("/dev/nvidia0").exists()
    if choice == "nvenc" or (choice == "auto" and has_gpu):
        return ["-c:v", "h264_nvenc", "-preset", "p4", "-b:v", "12M"]
    return ["-c:v", "libx264", "-preset", "medium", "-b:v", "12M", "-pix_fmt", "yuv420p"]


def export_project_json(config: dict, output_json_path: Path):
    """
    YAML設定からRemotionが直接参照可能な project_config.json を出力
    各シーンの絶対開始フレーム、終了フレーム等を自動計算
    """
    fps = config.get("project", {}).get("target_fps", 30)
    current_frame = 0
    scenes_data = []

    for scene in config.get("scenes", []):
        duration_sec = float(scene.get("duration_sec", 5.0))
        duration_frames = int(round(duration_sec * fps))
        start_frame = current_frame
        end_frame = current_frame + duration_frames

        scene_item = {
            **scene,
            "start_frame": start_frame,
            "end_frame": end_frame,
            "duration_frames": duration_frames,
        }
        scenes_data.append(scene_item)
        current_frame = end_frame

    full_config = {
        **config,
        "total_frames": current_frame,
        "total_duration_sec": current_frame / fps,
        "scenes": scenes_data,
    }

    output_json_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_json_path, "w", encoding="utf-8") as f:
        json.dump(full_config, f, ensure_ascii=False, indent=2)

    print(f"[Config] Exported calculated timeline to: {output_json_path} (Total frames: {current_frame}, {current_frame / fps:.1f}s)")
    return full_config

def step_1_cut_and_grade_background(config: dict, ffmpeg_path: str):
    """
    設定ファイルに基づき、カット切り出し・カラーグレーディング・動的xfadeトランジションを
    GPU NVENCで超高速処理
    """
    print("\n[Step 1/3] Processing raw video (Fast GPU Grading & Dynamic Transitions)...")
    input_video = config["project"]["input_video"]
    output_bg = Path("public/background_30s.mp4")
    output_bg.parent.mkdir(parents=True, exist_ok=True)

    scenes = config.get("scenes", [])
    n_scenes = len(scenes)
    if n_scenes == 0:
        raise ValueError("No scenes found in config!")

    xfade_duration = 0.4
    fps = config["project"].get("target_fps", 30)
    default_profile = "curves=master='0/0 0.15/0.25 0.4/0.52 0.75/0.82 1/1',eq=contrast=1.05:saturation=1.26"

    inputs = []
    filter_chains = []
    audio_chains = []
    offsets = []
    accumulated_time = 0.0

    for idx, sc in enumerate(scenes):
        start_sec = parse_time_str(sc["start_time"])
        dur_sec = float(sc.get("duration_sec", 5.0))
        sc_video = sc.get("video") or input_video

        # トランジションの重なり計算
        # 先頭シーン: 後ろに + xfade_duration/2 (0.2s)
        # 中間シーン: 前後に + xfade_duration/2 (計 +0.4s)
        # 末尾シーン: 前に + xfade_duration/2 (0.2s)
        if idx == 0:
            cut_start = start_sec
            cut_len = dur_sec + (xfade_duration / 2.0 if n_scenes > 1 else 0.0)
            offset = dur_sec - (xfade_duration / 2.0)
        elif idx == n_scenes - 1:
            cut_start = max(0.0, start_sec - (xfade_duration / 2.0))
            cut_len = dur_sec + (xfade_duration / 2.0)
            offset = None
        else:
            cut_start = max(0.0, start_sec - (xfade_duration / 2.0))
            cut_len = dur_sec + xfade_duration
            offset = None

        cut_start_str = format_time_str(cut_start)
        cut_to_str = format_time_str(cut_start + cut_len)
        grade_opt = sc.get("profile", default_profile)

        inputs.extend(["-ss", cut_start_str, "-to", cut_to_str, "-i", sc_video])

        # クロップ位置（被写体の位置に合わせて左右パン可能）
        crop_x_val = sc.get("crop_x", 0.5)
        if crop_x_val == "left":
            crop_x_ratio = 0.15
        elif crop_x_val == "right":
            crop_x_ratio = 0.85
        elif crop_x_val == "center":
            crop_x_ratio = 0.5
        else:
            crop_x_ratio = float(crop_x_val)

        # 色変換チェーンは入力の転送特性で分岐する。
        # HLG / PQ の HDR 入力のみトーンマッピングし、SDR (bt709) や
        # メタデータ無しの一般動画はそのままグレーディングする。
        # SDR を HLG チェーンに通すと zscale が "no path between colorspaces"
        # で失敗するため、アップロード素材全般ではこの分岐が必須になる。
        source_transfer = str(config.get("color_grading", {}).get("source_transfer", "arib-std-b67")).lower()
        tonemap_algo = config.get("color_grading", {}).get("tonemap_algorithm", "hable")
        if source_transfer in ("arib-std-b67", "hlg", "smpte2084", "pq"):
            tin = "arib-std-b67" if source_transfer in ("arib-std-b67", "hlg") else "smpte2084"
            color_chain = (
                f"zscale=tin={tin}:pin=bt2020:min=bt2020nc:t=linear:npl=100,"
                f"format=gbrpf32le,zscale=p=bt709,tonemap=tonemap={tonemap_algo}:desat=0,zscale=t=bt709:m=bt709:r=tv,"
                f"format=yuv420p,"
            )
        else:
            color_chain = "format=yuv420p,"

        chain = (
            f"[{idx}:v]fps={fps},"
            f"{color_chain}"
            f"{grade_opt},"
            f"scale=1080:1920:force_original_aspect_ratio=increase,"
            f"crop=1080:1920:(in_w-out_w)*{crop_x_ratio}:(in_h-out_h)/2,setsar=1[v{idx}]"
        )
        filter_chains.append(chain)

    # 動的xfadeチェーンの構築
    # offset_i = (直前までの合計実表示秒数) - xfade_duration/2
    if n_scenes == 1:
        full_filter = filter_chains[0] + ";[v0]null[vout]"
    else:
        xfade_parts = []
        cur_offset = float(scenes[0]["duration_sec"]) - (xfade_duration / 2.0)
        
        # 最初のxfade: [v0][v1] -> [x1]
        xfade_parts.append(f"[v0][v1]xfade=transition=fade:duration={xfade_duration}:offset={cur_offset:.3f}[x1]")
        
        for k in range(1, n_scenes - 1):
            cur_offset += float(scenes[k]["duration_sec"])
            prev_tag = f"[x{k}]"
            next_tag = f"[v{k+1}]"
            out_tag = f"[x{k+1}]" if k + 1 < n_scenes - 1 else "[vout]"
            xfade_parts.append(f"{prev_tag}{next_tag}xfade=transition=fade:duration={xfade_duration}:offset={cur_offset:.3f}{out_tag}")
            
        if n_scenes == 2:
            xfade_parts[0] = f"[v0][v1]xfade=transition=fade:duration={xfade_duration}:offset={cur_offset:.3f}[vout]"

        xfade_chain = ";".join(xfade_parts)
        full_filter = ";".join(filter_chains) + ";" + xfade_chain

    total_duration = sum(float(sc["duration_sec"]) for sc in scenes)

    cmd = [
        ffmpeg_path, "-y",
        *inputs,
        "-filter_complex", full_filter,
        "-map", "[vout]",
        *select_video_encoder(),
        "-r", str(fps), "-t", f"{total_duration:.3f}",
        str(output_bg)
    ]

    print(f"Running background render -> {output_bg} (Scenes: {n_scenes}, Total target: {total_duration:.1f}s)")
    subprocess.run(cmd, check=True)
    print(f"Background video ready: {output_bg} ({output_bg.stat().st_size // (1024*1024)} MB)")

    # ライブオーディオ（花火の生音）の切り出し・結合・強力DSPブースト処理
    live_audio_out = Path("public/audio/live_audio.wav")
    live_audio_out.parent.mkdir(parents=True, exist_ok=True)
    audio_inputs = []
    audio_filter_parts = []
    
    for idx, sc in enumerate(scenes):
        start_sec = parse_time_str(sc["start_time"])
        dur_sec = float(sc.get("duration_sec", 5.0))
        sc_video = sc.get("video") or input_video
        audio_inputs.extend(["-ss", format_time_str(start_sec), "-t", str(dur_sec), "-i", sc_video])
        audio_filter_parts.append(f"[{idx}:a]aresample=48000,aformat=channel_layouts=stereo[a{idx}]")
        
    audio_boost_db = config.get("theme", {}).get("audio_boost_db", 18.0)
    audio_dsp = f"bass=g=4:f=75:w=0.5,volume={audio_boost_db}dB,alimiter=limit=-1.0dB:attack=5:release=50"
    concat_filter = "".join(f"[a{i}]" for i in range(n_scenes)) + f"concat=n={n_scenes}:v=0:a=1,{audio_dsp}[aout]"
    full_audio_filter = ";".join(audio_filter_parts) + ";" + concat_filter
    
    audio_cmd = [
        ffmpeg_path, "-y",
        *audio_inputs,
        "-filter_complex", full_audio_filter,
        "-map", "[aout]",
        "-c:a", "pcm_s16le",
        str(live_audio_out)
    ]
    try:
        print(f"Extracting synchronized live audio (Boost: +{audio_boost_db}dB + Bass DSP) -> {live_audio_out}")
        subprocess.run(audio_cmd, check=True, stderr=subprocess.PIPE)
        print(f"Live audio ready: {live_audio_out}")
    except Exception as e:
        print(f"[Warning] Live audio extraction skipped or failed: {e}")

def step_2_render_remotion_composition(output_video_path: Path):
    """RemotionでJIZURA風エフェクトと字幕を合成してfinal.mp4を出力"""
    print("\n[Step 2/3] Rendering Remotion Composition (JIZURA-style Effects & Typography)...")
    output_video_path.parent.mkdir(parents=True, exist_ok=True)

    concurrency = os.environ.get("REMOTION_CONCURRENCY") or str(max(1, min(4, (os.cpu_count() or 2) // 2 or 1)))
    gl_backend = os.environ.get("REMOTION_GL") or ("angle" if os.name == "nt" else "swiftshader")
    cmd = [
        "npx.cmd" if os.name == "nt" else "npx",
        "remotion", "render",
        "src/index.tsx", "ShortVideo",
        str(output_video_path),
        f"--concurrency={concurrency}",
        f"--gl={gl_backend}"
    ]
    print(f"Running Remotion CLI -> {output_video_path}")
    subprocess.run(cmd, check=True)
    print(f"\n[Step 3/3] Video editing complete! Final video output: {output_video_path}")

def main():
    parser = argparse.ArgumentParser(description="Generalized SNS Movie Editing Pipeline")
    parser.add_argument("--config", default="config/project.yaml", help="Path to config YAML")
    parser.add_argument("--input", default=None, help="Override input raw video path")
    parser.add_argument("--output", default=None, help="Override final output video path")
    parser.add_argument("--step", choices=["all", "1", "2"], default="all", help="Pipeline step to run")
    args = parser.parse_args()

    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Config not found: {config_path}")
        sys.exit(1)

    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    if args.input:
        config["project"]["input_video"] = args.input
    if args.output:
        config["project"]["output_video"] = args.output

    # Remotion用設定JSONのエクスポート (public/project_config.json)
    output_json = Path("public/project_config.json")
    full_config = export_project_json(config, output_json)

    ffmpeg_path = get_ffmpeg_path()
    print(f"Using FFmpeg: {ffmpeg_path}")

    out_final = Path(config["project"].get("output_video", "outputs/final.mp4"))

    if args.step in ["all", "1"]:
        step_1_cut_and_grade_background(full_config, ffmpeg_path)

    if args.step in ["all", "2"]:
        step_2_render_remotion_composition(out_final)

if __name__ == "__main__":
    main()
