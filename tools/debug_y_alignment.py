"""Inspect the actual pixel content of punctuation rows in the HQ sheet."""
import cv2
import numpy as np
import json
from pathlib import Path

root = Path(__file__).resolve().parent.parent
cfg = json.loads((root / "configs" / "ethernium.json").read_text(encoding="utf-8"))

sheet_path = root / cfg["sheet"]
img = cv2.imread(str(sheet_path))
ref_h = cfg["reference_height"]
factor = img.shape[0] / ref_h
pixel_scale = max(img.shape[1] / cfg.get("reference_width", 1024), img.shape[0] / ref_h)
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

print(f"Sheet: {img.shape[1]}x{img.shape[0]}, pixel_scale={pixel_scale:.2f}, factor={factor:.2f}")

# Scan the Y axis to find where ink actually is
# Focus on the punctuation region (config y_start 370 to y_end 503)
scan_start = int(350 * factor)
scan_end = min(img.shape[0], int(520 * factor))

print(f"\nScanning Y={scan_start} to Y={scan_end} for ink content...")

# Threshold
from font_forge.core import prepare_binary
thresh = prepare_binary(gray, cfg["pipeline"].get("threshold", 30), sharpen=cfg["pipeline"].get("sharpen", True))

# Project ink onto Y axis
proj_y = np.sum(thresh[scan_start:scan_end, :] > 0, axis=1)

# Find bands of ink
in_band = False
bands = []
for y_off, val in enumerate(proj_y):
    y_abs = scan_start + y_off
    if val > 50:  # significant ink
        if not in_band:
            band_start = y_abs
            in_band = True
    else:
        if in_band:
            bands.append((band_start, y_abs))
            in_band = False
if in_band:
    bands.append((band_start, scan_start + len(proj_y)))

print(f"\nFound {len(bands)} ink bands:")
for i, (b_start, b_end) in enumerate(bands):
    ref_start = b_start / factor
    ref_end = b_end / factor
    height = b_end - b_start
    print(f"  Band {i}: Y={b_start}-{b_end} (ref: {ref_start:.1f}-{ref_end:.1f}), height={height}px")

# Now for each row, check alignment
print("\n--- Checking row alignment ---")
for row in cfg["rows"]:
    name = row["name"]
    if name not in ("Basic Punc", "Extended Punc", "Special Symbols"):
        continue
    
    y1 = int(round(row["y_start"] * factor))
    y2 = int(round(row["y_end"] * factor))
    baseline = int(round(row["baseline"] * factor))
    
    # Find actual ink in this Y range
    crop = thresh[y1:y2, :]
    ink_rows = np.where(np.sum(crop > 0, axis=1) > 10)[0]
    
    if len(ink_rows) > 0:
        actual_top = y1 + ink_rows[0]
        actual_bottom = y1 + ink_rows[-1]
        actual_height = actual_bottom - actual_top
        center = (actual_top + actual_bottom) // 2
        print(f"\n  {name}:")
        print(f"    Config range: y={y1}-{y2} (height={y2-y1})")
        print(f"    Baseline: {baseline}")
        print(f"    Actual ink: y={actual_top}-{actual_bottom} (height={actual_height})")
        print(f"    Ink center: {center}")
        print(f"    Top margin: {actual_top - y1}px")
        print(f"    Bottom margin: {y2 - actual_bottom}px")
        print(f"    Baseline offset from bottom ink: {baseline - actual_bottom}px")
    else:
        print(f"\n  {name}: NO INK FOUND in range y={y1}-{y2}")

# Also check what the pad_y does
print("\n--- Effect of pad_y ---")
pad_y = max(0, int(4 * pixel_scale))
print(f"pad_y = {pad_y}px")
for row in cfg["rows"]:
    name = row["name"]
    if name not in ("Basic Punc", "Extended Punc", "Special Symbols"):
        continue
    y1 = int(round(row["y_start"] * factor))
    y2 = int(round(row["y_end"] * factor))
    y1p = max(0, y1 - pad_y)
    y2p = min(thresh.shape[0], y2 + pad_y)
    
    # Check if there's unwanted ink in the padded zone
    top_pad = thresh[y1p:y1, :]
    bot_pad = thresh[y2:y2p, :]
    top_ink = np.sum(top_pad > 0)
    bot_ink = np.sum(bot_pad > 0)
    print(f"  {name}: pad zone top [{y1p}-{y1}] ink={top_ink}, bot [{y2}-{y2p}] ink={bot_ink}")
