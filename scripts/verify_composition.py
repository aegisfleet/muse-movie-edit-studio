"""
Automated Zero-Token Composition Quality Verifier (scripts/verify_composition.py)
Validates that every scene in outputs/final.mp4 has the subject properly centered,
with optimal framing, zero severe clipping, and sharp focus.
Runs 100% locally with YOLOv8 & OpenCV — ZERO LLM image tokens consumed!
"""

import sys
import os
import yaml
import shutil
import argparse
import subprocess
import cv2
import numpy as np
from pathlib import Path

# Windows console encoding fix
if sys.stdout:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

def get_ffmpeg_path():
    cmd = shutil.which("ffmpeg")
    if cmd:
        return cmd
    winget_pkg = Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft/WinGet/Packages"
    for p in winget_pkg.glob("**/ffmpeg.exe"):
        return str(p)
    return "ffmpeg"

def extract_frame_to_cv2(ffmpeg_path: str, video_path: str, timestamp_sec: float):
    """FFmpegで指定秒の1フレームを直接メモリにデコード（ディスク書き込み不要）"""
    cmd = [
        ffmpeg_path, "-ss", str(timestamp_sec), "-i", video_path,
        "-vframes", "1", "-f", "image2pipe", "-vcodec", "mjpeg", "-"
    ]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    if not res.stdout:
        return None
    arr = np.frombuffer(res.stdout, np.uint8)
    return cv2.imdecode(arr, cv2.IMREAD_COLOR)

def parse_time_to_sec(t_val) -> float:
    if isinstance(t_val, (int, float)):
        return float(t_val)
    parts = str(t_val).strip().split(":")
    if len(parts) == 3:
        return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
    elif len(parts) == 2:
        return float(parts[0]) * 60 + float(parts[1])
    return float(parts[0])

def verify_video_composition(config_path: Path, video_path: Path = None, pre_mode: bool = False):
    from ultralytics import YOLO

    if not config_path.exists():
        print(f"Error: Config file not found: {config_path}")
        return False

    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    ffmpeg_path = get_ffmpeg_path()
    model = YOLO("yolov8n.pt")
    target_classes = [16, 15] # dog, cat
    scenes = config.get("scenes", [])

    print(f"\n==================================================================================")
    if pre_mode:
        raw_video = Path(config.get("project", {}).get("input_video", "inputs/GX010096.MP4"))
        print(f"  AUTOMATED ZERO-TOKEN COMPOSITION VERIFIER (PRE-RENDER GATEWAY)")
        print(f"  Raw Source: {raw_video}")
        print(f"  Config:     {config_path} ({len(scenes)} scenes)")
        print(f"  * Simulating 9:16 crop_x on raw video BEFORE rendering to prevent rework!")
        video_path = raw_video
    else:
        if not video_path:
            bg_candidate = Path("public/background_30s.mp4")
            if bg_candidate.exists():
                video_path = bg_candidate
            else:
                video_path = Path(config.get("project", {}).get("output_video", "outputs/final.mp4"))

        print(f"  AUTOMATED ZERO-TOKEN COMPOSITION VERIFIER (POST-RENDER ACCEPTANCE)")
        print(f"  Video:  {video_path}")
        print(f"  Config: {config_path} ({len(scenes)} scenes)")

    print(f"==================================================================================\n")

    if not video_path.exists():
        print(f"Error: Target video not found: {video_path}")
        return False

    current_timeline_sec = 0.0
    all_passed = True
    results = []

    for idx, scene in enumerate(scenes):
        scene_id = scene.get("id", f"scene_{idx+1}")
        dur = float(scene.get("duration_sec", 5.0))
        crop_x = float(scene.get("crop_x", 0.5))

        if pre_mode:
            raw_start = parse_time_to_sec(scene.get("start_time", 0.0))
            check_t = raw_start + (dur / 2.0)
        else:
            check_t = current_timeline_sec + (dur / 2.0) # シーンの中央時点をサンプル

        frame = extract_frame_to_cv2(ffmpeg_path, str(video_path), check_t)
        if frame is None:
            results.append({
                "scene": scene_id, "time": f"{check_t:.1f}s", "status": "FAIL",
                "center_offset": "-", "size_pct": "-", "sharpness": "-", "reason": "Frame decode failed"
            })
            all_passed = False
            current_timeline_sec += dur
            continue

        raw_h, raw_w = frame.shape[:2]

        # pre_mode の場合、元動画フレームから指定された crop_x で 9:16 の切り出しを完全シミュレート
        if pre_mode:
            target_crop_w = int(raw_h * 9.0 / 16.0)
            target_crop_w = min(target_crop_w, raw_w)
            max_x = max(0, raw_w - target_crop_w)
            x_start = int(max_x * crop_x)
            frame = frame[:, x_start : x_start + target_crop_w]

        h, w = frame.shape[:2]
        # テロップやエフェクトとの重なりを考慮し、conf=0.25 で検出
        res = model.predict(frame, classes=target_classes, conf=0.25, verbose=False)[0]

        if len(res.boxes) == 0:
            # 中央で検出できない場合、少し前後のフレーム(check_t - 0.5s または + 0.5s)でフォールバック
            for offset_t in [-0.5, 0.5]:
                fb_t = max(0.0, check_t + offset_t)
                fb_frame = extract_frame_to_cv2(ffmpeg_path, str(video_path), fb_t)
                if fb_frame is not None:
                    fb_res = model.predict(fb_frame, classes=target_classes, conf=0.20, verbose=False)[0]
                    if len(fb_res.boxes) > 0:
                        frame = fb_frame
                        res = fb_res
                        break

        if len(res.boxes) == 0:
            # 被写体が検出されなかった場合
            results.append({
                "scene": scene_id, "time": f"{check_t:.1f}s", "status": "WARNING",
                "center_offset": "None", "size_pct": "0.0%", "sharpness": "-", "reason": "No dog detected"
            })
            all_passed = False
        else:
            # 最も確信度の高いボックス
            box = max(res.boxes, key=lambda b: float(b.conf[0]))
            xyxy = box.xyxy[0].cpu().numpy()
            bw = (xyxy[2] - xyxy[0]) / w
            bh = (xyxy[3] - xyxy[1]) / h
            size_pct = bw * bh * 100.0

            cx = (xyxy[0] + xyxy[2]) / 2.0
            center_ratio = cx / w # 0.5 が完全中央
            offset_from_center_pct = abs(center_ratio - 0.5) * 100.0 # 0% = 完全中央

            # 鮮鋭度
            x1, y1, x2, y2 = max(0, int(xyxy[0])), max(0, int(xyxy[1])), min(w, int(xyxy[2])), min(h, int(xyxy[3]))
            crop = frame[y1:y2, x1:x2]
            gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY) if crop.size > 0 else None
            sharp = float(cv2.Laplacian(gray, cv2.CV_64F).var()) if gray is not None else 0.0

            # 判定ロジック
            # 1. 中央寄りか？ (中央から22%以内なら合格)
            # 2. サイズが適切か？ (8%〜75%以内: 縦型ショート動画の迫力あるクローズアップを許容)
            # 3. 鮮鋭度 (動画の自然なモーションブラーを考慮し 4.0 以上で合格)
            reasons = []
            status = "PASS"
            if offset_from_center_pct > 22.0:
                reasons.append(f"Off-center ({center_ratio:.2f})")
                status = "WARNING"
            if size_pct > 75.0:
                reasons.append(f"Too close/giant ({size_pct:.1f}%)")
                status = "WARNING"
            elif size_pct < 8.0:
                reasons.append(f"Too small ({size_pct:.1f}%)")
                status = "WARNING"
            if sharp < 4.0:
                reasons.append("Blurry")
                status = "WARNING"

            reason_str = ", ".join(reasons) if reasons else "Perfect framing"
            results.append({
                "scene": scene_id,
                "time": f"{check_t:.1f}s",
                "status": status,
                "center_offset": f"{offset_from_center_pct:.1f}%",
                "size_pct": f"{size_pct:.1f}%",
                "sharpness": f"{sharp:.1f}",
                "reason": reason_str
            })
            if status != "PASS":
                all_passed = False

        current_timeline_sec += dur

    # テーブル出力
    print(f"{'Scene':<10} {'Time':<8} {'Status':<10} {'Offset':<10} {'Size':<10} {'Sharp':<8} {'Diagnostic'}")
    print("-" * 82)
    for r in results:
        status_color = r['status']
        print(f"{r['scene']:<10} {r['time']:<8} {status_color:<10} {r['center_offset']:<10} {r['size_pct']:<10} {r['sharpness']:<8} {r['reason']}")

    print("-" * 82)
    if all_passed:
        print("🎉 ALL SCENES PASSED! Subject perfectly framed and centered with zero LLM tokens used.")
    else:
        print("⚠️ Some scenes need framing review (see diagnostic above).")
    print("==================================================================================\n")
    return all_passed

def main():
    parser = argparse.ArgumentParser(description="Automated Zero-Token Composition Quality Verifier")
    parser.add_argument("--config", default="config/project.yaml", help="Path to config YAML")
    parser.add_argument("--video", default=None, help="Path to rendered video (default: public/background_30s.mp4)")
    parser.add_argument("--pre", action="store_true", help="Pre-render gateway: verify raw input video framing before rendering to prevent rework")
    args = parser.parse_args()

    video_arg = Path(args.video) if args.video else None
    success = verify_video_composition(Path(args.config), video_arg, pre_mode=args.pre)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
