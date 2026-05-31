"""Debug punctuation/symbol extraction - shows exact contour boxes and merged results."""
import cv2
import numpy as np
import json
from pathlib import Path
import sys

root = Path(__file__).resolve().parent.parent
cfg = json.loads((root / "configs" / "ethernium.json").read_text(encoding="utf-8"))

sheet_path = root / cfg["sheet"]
img = cv2.imread(str(sheet_path))
if img is None:
    print(f"Cannot read sheet: {sheet_path}")
    sys.exit(1)

ref_h = cfg["reference_height"]
factor = img.shape[0] / ref_h
pixel_scale = max(img.shape[1] / cfg.get("reference_width", 1024), img.shape[0] / ref_h)

gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
from font_forge.core import prepare_binary, merge_boxes
thresh = prepare_binary(gray, cfg["pipeline"].get("threshold", 30), sharpen=cfg["pipeline"].get("sharpen", True))

print(f"Sheet: {img.shape[1]}x{img.shape[0]}, pixel_scale={pixel_scale:.2f}, factor={factor:.2f}")
print()

# Analyze each punctuation/symbol row
for row in cfg["rows"]:
    name = row["name"]
    if name not in ("Basic Punc", "Extended Punc", "Special Symbols"):
        continue
    
    char_list = row["chars"]
    y1 = int(round(row["y_start"] * factor))
    y2 = int(round(row["y_end"] * factor))
    baseline = int(round(row["baseline"] * factor))
    
    pad_y = max(0, int(4 * pixel_scale))
    y1p = max(0, y1 - pad_y)
    y2p = min(thresh.shape[0], y2 + pad_y)
    crop = thresh[y1p:y2p, :]
    
    print(f"=== {name} ===")
    print(f"  Config: y_start={row['y_start']}, y_end={row['y_end']}, baseline={row['baseline']}")
    print(f"  Scaled: y1={y1}, y2={y2}, baseline={baseline}")
    print(f"  With pad: y1p={y1p}, y2p={y2p}, crop_height={y2p-y1p}")
    print(f"  Expected chars: {len(char_list)} -> {repr(char_list)}")
    
    # Find contours
    min_w = max(2, int(2 * pixel_scale))
    min_h = max(2, int(2 * pixel_scale))
    min_area = max(8, int(8 * pixel_scale * pixel_scale))
    max_w = int(200 * pixel_scale)
    merge_gap = max(3, int(4 * pixel_scale))
    
    row_gap = row.get("merge_gap")
    gap = max(2, int(row_gap * pixel_scale)) if row_gap else merge_gap
    max_merge_w = row.get("max_merge_width")
    max_merge_w = int(max_merge_w * pixel_scale) if max_merge_w else int(55 * pixel_scale)
    
    contours, _ = cv2.findContours(crop, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    print(f"  Raw contours found: {len(contours)}")
    print(f"  Filters: min_w={min_w}, min_h={min_h}, min_area={min_area}, max_w={max_w}")
    print(f"  Merge: gap={gap}, max_merge_w={max_merge_w}")
    
    boxes = []
    rejected = []
    for c in contours:
        x, y, w, h = cv2.boundingRect(c)
        if w > max_w:
            rejected.append((x, y, w, h, "too_wide"))
        elif h < min_h:
            rejected.append((x, y, w, h, "too_short"))
        elif w < min_w:
            rejected.append((x, y, w, h, "too_narrow"))
        elif w * h < min_area:
            rejected.append((x, y, w, h, "too_small_area"))
        else:
            boxes.append((x, y, w, h))
    
    print(f"  Accepted boxes: {len(boxes)}")
    if rejected:
        print(f"  Rejected boxes ({len(rejected)}):")
        for r in sorted(rejected, key=lambda b: b[0]):
            print(f"    x={r[0]:4d}, y={r[1]:3d}, w={r[2]:3d}, h={r[3]:3d} -> {r[4]}")
    
    x_max = row.get("x_max")
    if x_max is not None:
        x_lim = int(x_max * pixel_scale)
        boxes = [b for b in boxes if b[0] <= x_lim]
        print(f"  After x_max filter: {len(boxes)}")
    
    merged = merge_boxes(boxes, gap, max_merge_width=max_merge_w)
    
    print(f"  Merged boxes: {len(merged)}")
    for i, (x, y, w, h) in enumerate(merged):
        char = char_list[i] if i < len(char_list) else "???"
        print(f"    [{i:2d}] '{char}' (U+{ord(char) if i < len(char_list) else 0:04X}): "
              f"x={x:4d}, y={y:3d}, w={w:3d}, h={h:3d}")
    
    if len(merged) != len(char_list):
        print(f"  *** MISMATCH: got {len(merged)}, expected {len(char_list)} ***")
    
    # Save debug crop image
    debug_img = cv2.cvtColor(crop, cv2.COLOR_GRAY2BGR)
    for x, y, w, h in merged:
        cv2.rectangle(debug_img, (x, y), (x+w, y+h), (0, 255, 0), 1)
    for r in rejected:
        cv2.rectangle(debug_img, (r[0], r[1]), (r[0]+r[2], r[1]+r[3]), (0, 0, 255), 1)
    
    out_path = root / "tools" / f"debug_{name.lower().replace(' ', '_')}.png"
    cv2.imwrite(str(out_path), debug_img)
    print(f"  Debug image: {out_path.name}")
    print()
