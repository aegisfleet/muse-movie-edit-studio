"""
Narration Generator (muse-movie-edit-studio)

YAML設定の scenes[].narration を読み込み、シーンごとのナレーション音声を
一括生成する。生成先は narration.audio_file (public/ からの相対パス)。

バックエンド (自動選択):
  1. muse  : Muse 環境の /opt/hatch/bin/tts (Meta AI ボイス)。
             Muse 環境で実行した場合はこちらが使われる。
  2. edge  : Microsoft Edge TTS (pip: edge-tts)。Muse 環境外での汎用経路。
             日本語ボイスの既定は ja-JP-NanamiNeural。

尺ガードレール:
  生成音声がシーン尺 (duration_sec - start_offset) を超える場合、ffmpeg の
  atempo で自動圧縮し、末尾に 0.1 秒のフェードアウトを付けて、次シーンへの
  被りと末尾の途切れを防ぐ (元実装 generate_irodori_girl_dog.py の設計を継承)。

使い方:
  python scripts/generate_narration.py --config config/my_video.yaml
  python scripts/generate_narration.py --config config/my_video.yaml --backend edge --voice ja-JP-KeitaNeural
"""

import argparse
import asyncio
import json
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

if sys.stdout:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

MUSE_TTS = "/opt/hatch/bin/tts"
DEFAULT_MUSE_VOICE = "avocado_v2:MAI_03"  # Meta AI voice (Helio)
DEFAULT_EDGE_VOICE = "ja-JP-NanamiNeural"


def get_duration(ffprobe: str, path: Path) -> float:
    res = subprocess.run(
        [ffprobe, "-v", "quiet", "-print_format", "json", "-show_format", str(path)],
        capture_output=True, text=True,
    )
    try:
        return float(json.loads(res.stdout).get("format", {}).get("duration", 0.0))
    except Exception:
        return 0.0


def fit_to_duration(ffmpeg: str, ffprobe: str, path: Path, max_dur: float) -> None:
    """無音トリム + atempo ガードレールで音声を max_dur 秒以内に収める。"""
    if max_dur <= 0:
        return
    dur = get_duration(ffprobe, path)
    if dur <= 0:
        return
    tmp = path.parent / f"temp_{path.name}"
    subprocess.run(
        [ffmpeg, "-y", "-i", str(path), "-af",
         "silenceremove=start_periods=1:start_duration=0.03:start_threshold=-40dB:detection=peak",
         str(tmp)],
        capture_output=True,
    )
    if tmp.exists():
        cleaned = get_duration(ffprobe, tmp)
        if cleaned > 0:
            shutil.move(str(tmp), str(path))
            dur = cleaned
    if dur > max_dur:
        speed = min(2.0, max(1.0, dur / max_dur))
        out = path.parent / f"stretch_{path.name}"
        subprocess.run(
            [ffmpeg, "-y", "-i", str(path), "-filter:a",
             f"atempo={speed:.4f},afade=t=out:st={max(0.0, max_dur - 0.1):.2f}:d=0.1",
             str(out)],
            capture_output=True, check=True,
        )
        if out.exists():
            shutil.move(str(out), str(path))
            print(f"    [guardrail] {dur:.2f}s -> {get_duration(ffprobe, path):.2f}s (atempo {speed:.2f}x)")


def synth_muse(text: str, raw_out: Path, voice: str, language: str) -> None:
    cmd = [MUSE_TTS, "speak", "--output", str(raw_out), "--language", language,
           "--voice", voice, "--text-stdin"]
    res = subprocess.run(cmd, input=text, capture_output=True, text=True)
    if res.returncode != 0 or not raw_out.exists():
        raise RuntimeError(f"Muse TTS failed: {res.stdout} {res.stderr}")


async def _edge_save(text: str, raw_out: Path, voice: str) -> None:
    import edge_tts
    await edge_tts.Communicate(text, voice).save(str(raw_out))


def synth_edge(text: str, raw_out: Path, voice: str) -> None:
    asyncio.run(_edge_save(text, raw_out, voice))


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate narration audio from YAML config")
    parser.add_argument("--config", default="config/project.yaml")
    parser.add_argument("--backend", choices=["auto", "muse", "edge"], default="auto")
    parser.add_argument("--voice", default=None, help="muse: voice ID / edge: voice name")
    parser.add_argument("--language", default="ja")
    args = parser.parse_args()

    backend = args.backend
    if backend == "auto":
        backend = "muse" if Path(MUSE_TTS).exists() else "edge"
    voice = args.voice or (DEFAULT_MUSE_VOICE if backend == "muse" else DEFAULT_EDGE_VOICE)
    print(f"[Narration] backend={backend} voice={voice} language={args.language}")

    ffmpeg = shutil.which("ffmpeg") or "ffmpeg"
    ffprobe = shutil.which("ffprobe") or "ffprobe"

    with open(args.config, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    fps = float(config.get("project", {}).get("target_fps", 30))

    made = 0
    for scene in config.get("scenes", []):
        narration = scene.get("narration") or {}
        text = narration.get("text")
        audio_file = narration.get("audio_file")
        if not text or not audio_file:
            continue
        out_path = Path("public") / audio_file
        out_path.parent.mkdir(parents=True, exist_ok=True)
        print(f"  [{scene.get('id', '?')}] {text[:40]}... -> {out_path}")

        raw = out_path.parent / f"raw_{out_path.stem}.mp3"
        if backend == "muse":
            synth_muse(text, raw, voice, args.language)
        else:
            synth_edge(text, raw, voice)
        # 拡張子に合わせて変換 (wav 指定なら pcm_s16le に揃える)
        conv = [ffmpeg, "-y", "-i", str(raw)]
        if out_path.suffix.lower() == ".wav":
            conv += ["-c:a", "pcm_s16le"]
        conv += [str(out_path)]
        subprocess.run(conv, capture_output=True, check=True)
        raw.unlink(missing_ok=True)

        offset_sec = float(narration.get("start_offset_frame", 0)) / fps
        max_dur = float(scene.get("duration_sec", 5.0)) - offset_sec - 0.05
        fit_to_duration(ffmpeg, ffprobe, out_path, max_dur)
        made += 1

    print(f"[Narration] done: {made} scene(s)")


if __name__ == "__main__":
    main()
