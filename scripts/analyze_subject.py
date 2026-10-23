"""
AI Subject Analyzer & Auto-Framing Assistant (scripts/analyze_subject.py)
Uses Ultralytics YOLOv8 to automatically track subjects (dog, cat, person, etc.),
compute exact bounding boxes, determine optimal 9:16 vertical crop positions,
and score highlight candidates without manual frame-by-frame inspection.

Proxy workflow (--proxy): decoding the original (e.g. 4K HEVC) frame by frame
dominates analysis time on small machines. With --proxy, a low-resolution
proxy video is generated once (cached under scratch/proxy/) and analyzed
instead. Bounding boxes and crop positions are normalized coordinates, and
timestamps are unchanged, so every result applies to the original video
as-is. The final render always reads the original full-resolution source;
the proxy is only a fast stand-in for analysis and framing decisions.
"""

import sys
import os
import json
import argparse
import shutil
import subprocess
from pathlib import Path
import cv2
import numpy as np

# Windows console encoding fix
if sys.stdout:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

def get_class_filter(target: str):
    """
    target string -> list of COCO class IDs
    """
    target = target.lower()
    if target in ["dog", "犬", "いぬ"]:
        return [16, 15] # 16=dog, 15=cat (small dogs often detected as cat)
    elif target in ["cat", "猫", "ねこ"]:
        return [15, 16]
    elif target in ["pet", "ペット", "animal", "動物"]:
        return [15, 16, 17, 18, 19, 20, 21, 22, 23] # horse, sheep, cow, elephant, bear, zebra, giraffe
    elif target in ["person", "人", "human"]:
        return [0]
    elif target == "all":
        return None
    else:
        return [16, 15]

def ensure_proxy(video_path: str, width: int = 854) -> str:
    """
    Build (or reuse) a low-resolution proxy of the source video for analysis.

    The proxy lives at scratch/proxy/<stem>_w<width>.mp4 next to the current
    working directory and is regenerated only when the source is newer.
    Returns the proxy path. Falls back to the source path if ffmpeg is
    unavailable or proxy generation fails.
    """
    src = Path(video_path)
    proxy_dir = Path("scratch/proxy")
    proxy_dir.mkdir(parents=True, exist_ok=True)
    proxy_path = proxy_dir / f"{src.stem}_w{width}.mp4"

    if proxy_path.exists() and proxy_path.stat().st_mtime >= src.stat().st_mtime:
        print(f"[Proxy] Reusing cached proxy: {proxy_path}")
        return str(proxy_path)

    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        print("[Proxy] ffmpeg not found; analyzing the original video")
        return video_path

    print(f"[Proxy] Generating {width}px-wide proxy -> {proxy_path} (one-time cost)")
    cmd = [
        ffmpeg, "-y", "-v", "error",
        "-i", str(src),
        "-vf", f"scale={width}:-2",
        "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "28",
        str(proxy_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0 or not proxy_path.exists():
        print(f"[Proxy] Generation failed ({result.stderr.strip()[:200]}); analyzing the original video")
        return video_path
    size_mb = proxy_path.stat().st_size / (1024 * 1024)
    print(f"[Proxy] Ready: {proxy_path} ({size_mb:.1f} MB)")
    return str(proxy_path)


def analyze_video(
    video_path: str,
    target: str = "dog",
    sample_interval_sec: float = 0.5,
    min_conf: float = 0.35,
    model_name: str = "yolov8n.pt"
):
    from ultralytics import YOLO

    print(f"Loading YOLO model: {model_name}...")
    model = YOLO(model_name)
    target_classes = get_class_filter(target)

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"Error: Could not open video file {video_path}")
        return []

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration_sec = total_frames / fps
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    print(f"Video Info: {video_path}")
    print(f"   Resolution: {width}x{height}, FPS: {fps:.2f}, Duration: {duration_sec:.2f}s ({total_frames} frames)")
    print(f"   Target: {target} (COCO classes: {target_classes})")
    print(f"   Sampling every: {sample_interval_sec}s\n")

    # 9:16 crop geometry calculation
    # scaled_w = width * (1920 / height)
    # out_w = 1080
    # max_shift = scaled_w - out_w
    scaled_w = width * (1920.0 / height)
    out_w = 1080.0
    max_shift = max(1.0, scaled_w - out_w)

    step_frames = max(1, int(fps * sample_interval_sec))
    records = []

    current_frame = 0
    while current_frame < total_frames:
        cap.set(cv2.CAP_PROP_POS_FRAMES, current_frame)
        ret, frame = cap.read()
        if not ret:
            break

        timestamp_sec = current_frame / fps

        # YOLO inference
        results = model.predict(frame, classes=target_classes, conf=min_conf, verbose=False)
        boxes = results[0].boxes

        if len(boxes) > 0:
            # Pick highest confidence or largest box
            best_box = None
            best_score = -1.0
            for box in boxes:
                conf = float(box.conf[0])
                xyxy = box.xyxy[0].cpu().numpy()
                bw = xyxy[2] - xyxy[0]
                bh = xyxy[3] - xyxy[1]
                area_ratio = (bw * bh) / (width * height)
                score = conf * 0.6 + area_ratio * 0.4
                if score > best_score:
                    best_score = score
                    best_box = (box, xyxy, conf, area_ratio)

            box, xyxy, conf, area_ratio = best_box
            cls_id = int(box.cls[0])
            cls_name = model.names.get(cls_id, str(cls_id))

            # Bounding box width and height relative to image
            norm_w = (xyxy[2] - xyxy[0]) / width
            norm_h = (xyxy[3] - xyxy[1]) / height
            area_pct = float(round(area_ratio * 100, 1))

            # Bounding box center
            cx_orig = (xyxy[0] + xyxy[2]) / 2.0
            cy_orig = (xyxy[1] + xyxy[3]) / 2.0

            # Scale to 1920 height
            cx_scaled = cx_orig * (1920.0 / height)
            cy_scaled = cy_orig * (1920.0 / height)

            # Compute ideal crop_x (0.0=left, 1.0=right) so that target center aligns with 1080 center (540)
            ideal_shift = cx_scaled - (out_w / 2.0)
            crop_x = float(np.clip(ideal_shift / max_shift, 0.0, 1.0))

            # 1. 鮮鋭度（ピンぼけ判定）: 被写体バウンディングボックス内のラプラシアン分散
            x1, y1, x2, y2 = max(0, int(xyxy[0])), max(0, int(xyxy[1])), min(width, int(xyxy[2])), min(height, int(xyxy[3]))
            crop_bgr = frame[y1:y2, x1:x2]
            if crop_bgr.size > 0:
                crop_gray = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2GRAY)
                sharpness = float(cv2.Laplacian(crop_gray, cv2.CV_64F).var())
            else:
                sharpness = 0.0

            # 2. 構図・占有率スコア (0.0 〜 1.0)
            # 理想: 12% 〜 38% (全身〜バストアップが綺麗に収まる)
            # ペナルティ: 45%超（カメラ衝突・お尻ドアップ）、8%未満（遠すぎる）
            if 14.0 <= area_pct <= 38.0:
                size_score = 1.0
            elif 8.0 <= area_pct < 14.0:
                size_score = 0.6 + 0.4 * ((area_pct - 8.0) / 6.0)
            elif 38.0 < area_pct <= 46.0:
                size_score = 1.0 - 0.7 * ((area_pct - 38.0) / 8.0)
            else:
                size_score = 0.1 # 極端なドアップや遠景は大幅除外

            # 3. 画面端見切れペナルティ
            # 上下または左右両方が画面端に張り付いている場合は体の一部しか映っていない
            touch_top = (xyxy[1] / height) < 0.02
            touch_bottom = (xyxy[3] / height) > 0.98
            touch_left = (xyxy[0] / width) < 0.02
            touch_right = (xyxy[2] / width) > 0.98
            boundary_penalty = 1.0
            if touch_top and touch_bottom:
                boundary_penalty *= 0.35 # 上下見切れ（レンズ衝突）
            if touch_left and touch_right:
                boundary_penalty *= 0.35 # 左右見切れ

            # 4. 9:16 縦型収まりやすさ（横幅が縦型動画の幅 0.5625 以内に収まるか）
            fit_916_score = 1.0 if norm_w <= 0.50 else max(0.2, 1.0 - (norm_w - 0.50) * 2.0)

            # 総合フレーム品質スコア (0〜100点)
            quality_score = round(
                (conf * 0.35 + size_score * 0.35 + fit_916_score * 0.15 + min(1.0, sharpness / 60.0) * 0.15)
                * boundary_penalty * 100.0,
                1
            )

            records.append({
                "time_sec": float(round(timestamp_sec, 2)),
                "time_str": f"{int(timestamp_sec//60):02d}:{timestamp_sec%60:05.2f}",
                "detected": True,
                "class": str(cls_name),
                "conf": float(round(conf, 2)),
                "area_pct": area_pct,
                "sharpness": round(sharpness, 1),
                "quality_score": quality_score,
                "box_norm": [float(round(xyxy[0]/width, 3)), float(round(xyxy[1]/height, 3)), float(round(xyxy[2]/width, 3)), float(round(xyxy[3]/height, 3))],
                "recommended_crop_x": float(round(crop_x, 2))
            })
        else:
            records.append({
                "time_sec": float(round(timestamp_sec, 2)),
                "time_str": f"{int(timestamp_sec//60):02d}:{timestamp_sec%60:05.2f}",
                "detected": False,
                "class": None,
                "conf": 0.0,
                "area_pct": 0.0,
                "sharpness": 0.0,
                "quality_score": 0.0,
                "box_norm": None,
                "recommended_crop_x": 0.5
            })

        current_frame += step_frames

    cap.release()
    return records

def find_highlight_segments(records: list, min_duration_sec: float = 3.0):
    """
    高品質スコア（quality_score >= 45）が持続する神カット区間を抽出
    """
    segments = []
    current_seg = []

    for r in records:
        # 検出されており、かつ品質スコアが十分高いもの
        if r["detected"] and r.get("quality_score", 0.0) >= 45.0:
            current_seg.append(r)
        else:
            if current_seg:
                seg_dur = current_seg[-1]["time_sec"] - current_seg[0]["time_sec"]
                if seg_dur >= min_duration_sec:
                    segments.append(current_seg)
                current_seg = []

    if current_seg:
        seg_dur = current_seg[-1]["time_sec"] - current_seg[0]["time_sec"]
        if seg_dur >= min_duration_sec:
            segments.append(current_seg)

    summary = []
    for seg in segments:
        start_t = seg[0]["time_sec"]
        end_t = seg[-1]["time_sec"]
        dur = end_t - start_t
        avg_crop_x = np.mean([r["recommended_crop_x"] for r in seg])
        avg_conf = np.mean([r["conf"] for r in seg])
        avg_area = np.mean([r["area_pct"] for r in seg])
        avg_sharp = np.mean([r.get("sharpness", 0.0) for r in seg])
        avg_quality = np.mean([r.get("quality_score", 0.0) for r in seg])
        crop_std = float(np.std([r["recommended_crop_x"] for r in seg])) # 位置の安定度

        summary.append({
            "start_time": f"{int(start_t//60):02d}:{start_t%60:05.2f}",
            "start_sec": float(round(start_t, 2)),
            "end_time": f"{int(end_t//60):02d}:{end_t%60:05.2f}",
            "end_sec": float(round(end_t, 2)),
            "duration_sec": float(round(dur, 2)),
            "recommended_crop_x": float(round(float(avg_crop_x), 2)),
            "crop_stability": float(round(crop_std, 3)), # 小さいほど位置が安定
            "avg_quality_score": float(round(float(avg_quality), 1)),
            "avg_conf": float(round(float(avg_conf), 2)),
            "avg_size_pct": float(round(float(avg_area), 1)),
            "avg_sharpness": float(round(float(avg_sharp), 1))
        })

    # 総合品質スコアと尺でソート（お尻ドアップは自動的に低スコアで除外される）
    summary.sort(key=lambda s: s["avg_quality_score"] * min(6.0, s["duration_sec"]), reverse=True)
    return summary

def main():
    parser = argparse.ArgumentParser(description="AI Subject Analyzer & Auto-Framing Assistant")
    parser.add_argument("--video", "-v", required=True, help="Input video file path")
    parser.add_argument("--target", "-t", default="dog", help="Target subject (dog, cat, person, pet)")
    parser.add_argument("--interval", "-i", type=float, default=0.5, help="Sampling interval in seconds (default: 0.5s)")
    parser.add_argument("--out", "-o", default=None, help="Output JSON path (optional)")
    parser.add_argument("--proxy", action="store_true", help="Analyze a low-resolution proxy instead of the original (results are normalized and apply to the original; recommended for 4K sources)")
    parser.add_argument("--proxy-width", type=int, default=854, help="Proxy width in pixels (default: 854)")
    args = parser.parse_args()

    video_for_analysis = ensure_proxy(args.video, width=args.proxy_width) if args.proxy else args.video
    if video_for_analysis != args.video:
        print(f"[Proxy] Analyzing proxy in place of: {args.video} (timestamps and normalized coordinates are identical)")

    records = analyze_video(video_for_analysis, target=args.target, sample_interval_sec=args.interval)
    if not records:
        return

    highlights = find_highlight_segments(records)

    print("=" * 82)
    print("TOP RECOMMENDED HIGHLIGHT SCENES (Auto-Scored: Aesthetics + Framing + Sharpness)")
    print("=" * 82)
    print(f"{'No.':<4} {'Start Time':<12} {'End Time':<12} {'Duration':<10} {'Crop X':<10} {'Quality':<10} {'Size':<8} {'Conf'}")
    print("-" * 82)
    for i, h in enumerate(highlights[:10], 1):
        dur_str = f"{h['duration_sec']:.1f}s"
        size_str = f"{h['avg_size_pct']:.1f}%"
        print(f"#{i:<3} {h['start_time']:<12} {h['end_time']:<12} {dur_str:<10} {h['recommended_crop_x']:<10.2f} {h['avg_quality_score']:<10.1f} {size_str:<8} {h['avg_conf']:.2f}")

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        # Convert any remaining numpy types to native python types
        def sanitize_obj(obj):
            if isinstance(obj, dict):
                return {k: sanitize_obj(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [sanitize_obj(v) for v in obj]
            elif hasattr(obj, "item"):
                return obj.item()
            return obj

        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(sanitize_obj({"records": records, "highlights": highlights}), f, ensure_ascii=False, indent=2)
        print(f"\nSaved analysis results to: {out_path}")

if __name__ == "__main__":
    main()
