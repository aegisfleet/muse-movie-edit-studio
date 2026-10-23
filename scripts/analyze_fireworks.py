"""
Fireworks Scene Analyzer & Auto-Framing with YOLO (scripts/analyze_fireworks.py)
Detects fireworks, computes burst intensity & grandeur score,
finds optimal 9:16 vertical crop position (crop_x), and selects best scenes.
"""

import sys
import os
import json
import glob
from pathlib import Path
import cv2
import numpy as np
from ultralytics import YOLO, YOLOWorld

if sys.stdout:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

def analyze_frames_dir(video_id: str, frames_dir: str, video_path: str, model_world=None):
    frame_files = sorted(glob.glob(os.path.join(frames_dir, "*.jpg")))
    records = []
    
    print(f"[{video_id}] Analyzing {len(frame_files)} frames from {video_path}...")
    
    prev_gray = None
    
    for idx, fpath in enumerate(frame_files):
        img = cv2.imread(fpath)
        if img is None:
            continue
        
        h, w = img.shape[:2]
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        
        # 1. Intensity & Color Metrics
        mean_val = float(np.mean(gray))
        max_val = int(np.max(gray))
        
        # Bright firework pixels (above threshold)
        bright_mask = gray > 140
        very_bright_mask = gray > 200
        bright_count = int(np.sum(bright_mask))
        very_bright_count = int(np.sum(very_bright_mask))
        
        # Saturated color firework pixels
        sat_mask = (gray > 90) & (hsv[:, :, 1] > 60)
        sat_count = int(np.sum(sat_mask))
        
        # Motion / explosion burst dynamic
        burst_motion = 0.0
        if prev_gray is not None:
            diff = cv2.absdiff(gray, prev_gray)
            burst_motion = float(np.mean(diff[diff > 30])) if np.any(diff > 30) else 0.0
        prev_gray = gray
        
        # 2. Firework Center of Mass (for auto crop_x)
        # Weight by brightness^2 to focus on bright burst center
        y_indices, x_indices = np.where(bright_mask)
        if len(x_indices) > 50:
            weights = gray[bright_mask].astype(float) ** 2
            center_x = float(np.sum(x_indices * weights) / np.sum(weights)) / float(w)
            center_y = float(np.sum(y_indices * weights) / np.sum(weights)) / float(h)
            firework_present = True
        else:
            center_x = 0.5
            center_y = 0.5
            firework_present = False
            
        # 3. YOLO detection for bounding boxes & confirmation
        yolo_boxes = []
        if firework_present and model_world is not None:
            # Predict with low threshold for fireworks/light/sparks
            res = model_world.predict(img, conf=0.008, verbose=False)
            boxes = res[0].boxes
            for b in boxes:
                c_id = int(b.cls[0])
                c_name = res[0].names[c_id]
                c_conf = float(b.conf[0])
                xyxy = [float(val) for val in b.xyxy[0].tolist()]
                # normalize box
                n_xyxy = [xyxy[0]/w, xyxy[1]/h, xyxy[2]/w, xyxy[3]/h]
                box_w = n_xyxy[2] - n_xyxy[0]
                box_h = n_xyxy[3] - n_xyxy[1]
                if box_w * box_h > 0.005:  # filter tiny artifacts
                    yolo_boxes.append({
                        "name": c_name,
                        "conf": round(c_conf, 3),
                        "box": [round(v, 3) for v in n_xyxy]
                    })
                    
        # If YOLO detected fireworks, refine center_x
        if len(yolo_boxes) > 0:
            fw_boxes = [b for b in yolo_boxes if b["name"] in ["fireworks", "firework", "explosion"]]
            if fw_boxes:
                # pick largest
                largest = max(fw_boxes, key=lambda b: (b["box"][2]-b["box"][0])*(b["box"][3]-b["box"][1]))
                yolo_cx = (largest["box"][0] + largest["box"][2]) / 2.0
                center_x = 0.7 * center_x + 0.3 * yolo_cx

        # 4. Composite Grandeur Score (0 - 100)
        # Factors: bright pixel area, colorful saturation, mean brightness, explosion dynamic
        area_score = min(50.0, (bright_count / (w * h)) * 800.0)
        color_score = min(25.0, (sat_count / (w * h)) * 500.0)
        brightness_score = min(15.0, (mean_val / 60.0) * 15.0)
        motion_score = min(10.0, (burst_motion / 50.0) * 10.0)
        
        grandeur_score = round(area_score + color_score + brightness_score + motion_score, 2)
        
        # Optimal crop_x for 9:16 (clamp between 0.2 and 0.8)
        # Note: 9:16 aspect ratio occupies roughly 31.6% of a 16:9 frame.
        # So crop window width ratio is 0.316.
        # Center of window is crop_x. Valid crop_x range for standard ffmpeg crop is [0.0, 1.0].
        crop_x = round(float(np.clip(center_x, 0.2, 0.8)), 3)
        
        sec = idx * 1.0  # 1fps
        
        records.append({
            "video_id": video_id,
            "video_path": video_path,
            "sec": sec,
            "frame_idx": idx,
            "grandeur_score": grandeur_score,
            "bright_count": bright_count,
            "sat_count": sat_count,
            "mean_val": round(mean_val, 1),
            "max_val": max_val,
            "center_x": round(center_x, 3),
            "center_y": round(center_y, 3),
            "crop_x": crop_x,
            "yolo_count": len(yolo_boxes),
            "yolo_boxes": yolo_boxes[:3]
        })
        
    return records

def main():
    print("=== Loading YOLO-World for Fireworks Analysis ===")
    model = YOLOWorld("yolov8s-worldv2.pt")
    model.set_classes(["fireworks", "firework", "explosion", "spark", "light flash"])
    
    videos = [
        ("v1", "scratch/v1", "inputs/PXL_20261002_110253075.mp4"),
        ("v2", "scratch/v2", "inputs/PXL_20261002_110602248.mp4"),
        ("v3", "scratch/v3", "inputs/PXL_20261002_111358696.mp4")
    ]
    
    all_records = []
    for vid, fdir, vpath in videos:
        recs = analyze_frames_dir(vid, fdir, vpath, model)
        all_records.extend(recs)
        
    out_file = Path("scratch/fireworks_analysis.json")
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(all_records, f, ensure_ascii=False, indent=2)
        
    print(f"\nAnalysis completed! Total analyzed seconds: {len(all_records)}")
    print(f"Results saved to {out_file}")
    
    # Show Top 15 Most Spectacular Fireworks Moments
    top_bursts = sorted(all_records, key=lambda x: x["grandeur_score"], reverse=True)[:20]
    print("\n=== TOP 20 MOST SPECTACULAR FIREWORKS MOMENTS ===")
    for rank, b in enumerate(top_bursts, 1):
        print(f"#{rank:2d}: [{b['video_id']}] @ {b['sec']:5.1f}s | Score: {b['grandeur_score']:5.1f} | Bright: {b['bright_count']:5d} | Crop_X: {b['crop_x']} | YOLO: {b['yolo_count']} | Video: {Path(b['video_path']).name}")

if __name__ == "__main__":
    main()
