"""Debug the underscore and backslash specifically."""
import cv2
import numpy as np
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

root = Path(__file__).resolve().parent.parent
cfg = json.loads((root / "configs" / "ethernium.json").read_text(encoding="utf-8"))

sheet_path = root / cfg["sheet"]
img = cv2.imread(str(sheet_path))
ref_h = cfg["reference_height"]
factor = img.shape[0] / ref_h
pixel_scale = max(img.shape[1] / cfg.get("reference_width", 1024), img.shape[0] / ref_h)

gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
from font_forge.core import prepare_binary, merge_boxes
thresh = prepare_binary(gray, cfg["pipeline"].get("threshold", 30), sharpen=cfg["pipeline"].get("sharpen", True))

# Basic Punc row
row = [r for r in cfg["rows"] if r["name"] == "Basic Punc"][0]
y1 = int(round(row["y_start"] * factor))
y2 = int(round(row["y_end"] * factor))
baseline = int(round(row["baseline"] * factor))

pad_y = max(0, int(4 * pixel_scale))
y1p = max(0, y1 - pad_y)
y2p = min(thresh.shape[0], y2 + pad_y)
crop = thresh[y1p:y2p, :]

print(f"Basic Punc: y1={y1}, y2={y2}, y1p={y1p}, y2p={y2p}")
print(f"Crop height: {y2p-y1p}")
print(f"Baseline: {baseline}")

# Find all contours in crop  
contours, _ = cv2.findContours(crop, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

min_w = max(2, int(2 * pixel_scale))
min_h = max(2, int(2 * pixel_scale))
min_area = max(8, int(8 * pixel_scale * pixel_scale))
max_w = int(200 * pixel_scale)

boxes = []
for c in contours:
    x, y, w, h = cv2.boundingRect(c)
    if w > max_w or h < min_h or w < min_w or w * h < min_area:
        continue
    boxes.append((x, y, w, h))

merge_gap = max(3, int(4 * pixel_scale))
max_merge_w = int(55 * pixel_scale)
merged = merge_boxes(boxes, merge_gap, max_merge_width=max_merge_w)

char_list = row["chars"]
print(f"\nMerged: {len(merged)} boxes, expected: {len(char_list)} chars")
for i, (x, y, w, h) in enumerate(merged):
    if i < len(char_list):
        char = char_list[i]
        # Convert y-position to font coords to see what baseline offset does
        abs_y_top = y1p + y
        abs_y_bot = y1p + y + h
        fy_top = int((baseline - abs_y_top) * (20 / pixel_scale))
        fy_bot = int((baseline - abs_y_bot) * (20 / pixel_scale))
        print(f"  [{i}] '{char}': x={x}, y={y}, w={w}, h={h}")
        print(f"       abs_y: {abs_y_top}-{abs_y_bot}, font_y: {fy_top} to {fy_bot}")

# Now do the same WITHOUT padding
print(f"\n\n=== Without pad_y ===")
crop_nopad = thresh[y1:y2, :]
contours2, _ = cv2.findContours(crop_nopad, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
boxes2 = []
for c in contours2:
    x, y, w, h = cv2.boundingRect(c)
    if w > max_w or h < min_h or w < min_w or w * h < min_area:
        continue
    boxes2.append((x, y, w, h))
merged2 = merge_boxes(boxes2, merge_gap, max_merge_width=max_merge_w)
print(f"Merged (no pad): {len(merged2)} boxes")
for i, (x, y, w, h) in enumerate(merged2):
    if i < len(char_list):
        char = char_list[i]
        abs_y_top = y1 + y
        abs_y_bot = y1 + y + h
        fy_top = int((baseline - abs_y_top) * (20 / pixel_scale))
        fy_bot = int((baseline - abs_y_bot) * (20 / pixel_scale))
        print(f"  [{i}] '{char}': x={x}, y={y}, w={w}, h={h}")
        print(f"       abs_y: {abs_y_top}-{abs_y_bot}, font_y: {fy_top} to {fy_bot}")

# Save debug images
debug1 = cv2.cvtColor(crop, cv2.COLOR_GRAY2BGR)
for x, y, w, h in merged:
    cv2.rectangle(debug1, (x, y), (x+w, y+h), (0, 255, 0), 2)
cv2.imwrite(str(root / "tools" / "debug_basicpunc_padded.png"), debug1)

debug2 = cv2.cvtColor(crop_nopad, cv2.COLOR_GRAY2BGR)
for x, y, w, h in merged2:
    cv2.rectangle(debug2, (x, y), (x+w, y+h), (0, 255, 0), 2)
cv2.imwrite(str(root / "tools" / "debug_basicpunc_nopad.png"), debug2)
print("\nSaved debug images")
