import sys
sys.path.append('.')
import cv2
import numpy as np
import json
from pathlib import Path
from font_forge.config import scale_rows

ROOT = Path(".")
config_path = ROOT / "configs" / "ethernium.json"
config = json.loads(config_path.read_text(encoding="utf-8"))

# Load sheet
img = cv2.imread("ethernium_sheet_hq.png", cv2.IMREAD_GRAYSCALE)
h, w = img.shape
ref_h = config["reference_height"]
pixel_scale = w / config["reference_width"]

# Get Uppercase row
row = config["rows"][0]
rows_scaled = scale_rows([row], h, ref_h)[0]
y1 = rows_scaled["y_start"]
y2 = rows_scaled["y_end"]

pad_y = max(0, int(4 * pixel_scale))
y1p = max(0, y1 - pad_y)
y2p = min(img.shape[0], y2 + pad_y)
crop = img[y1p:y2p, :]

# Grid extraction
from font_forge.core import extract_glyphs_grid
merged = extract_glyphs_grid(crop, len(row["chars"]), pixel_scale)

print(f"Uppercase row y1p={y1p}, y2p={y2p}")
for idx, (gx, gy, gw, gh) in enumerate(merged):
    char = row["chars"][idx]
    if char not in "LMNOP":
        continue
    
    margin = max(2, int(3 * pixel_scale))
    cx1, cy1 = max(0, gx - margin), max(0, gy - margin)
    cx2 = min(crop.shape[1], gx + gw + margin)
    cy2 = min(crop.shape[0], gy + gh + margin)
    
    glyph_crop = crop[cy1:cy2, cx1:cx2].copy()
    contours, _ = cv2.findContours(glyph_crop, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # Calculate bounding box of all contours combined relative to gx
    all_pts = []
    for c in contours:
        for pt in c.reshape(-1, 2):
            abs_x = cx1 + pt[0]
            rel_x = abs_x - gx
            all_pts.append(rel_x)
            
    if all_pts:
        min_rel_x = min(all_pts)
        max_rel_x = max(all_pts)
        print(f"Char {char}: gx={gx}, gw={gw} | crop_w={cx2-cx1} | rel_x range: {min_rel_x} to {max_rel_x} (span={max_rel_x - min_rel_x})")
    else:
        print(f"Char {char}: gx={gx}, gw={gw} | crop_w={cx2-cx1} | No contours found!")
