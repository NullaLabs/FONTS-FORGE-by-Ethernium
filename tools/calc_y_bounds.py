"""Calculate exact Y boundaries needed for each punctuation row."""
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
from font_forge.core import prepare_binary
thresh = prepare_binary(gray, cfg["pipeline"].get("threshold", 30), sharpen=cfg["pipeline"].get("sharpen", True))

print(f"factor={factor:.4f}, pixel_scale={pixel_scale:.2f}")

# For each row, find the exact Y range where the glyph ink exists
# We need to be precise: scan column by column in the glyph region, ignoring labels
for row in cfg["rows"]:
    name = row["name"]
    if name not in ("Basic Punc", "Extended Punc", "Special Symbols"):
        continue
    
    y1_cfg = row["y_start"]
    y2_cfg = row["y_end"]
    
    # Scan a wider range to find all ink
    scan_start = int((y1_cfg - 15) * factor)
    scan_end = int((y2_cfg + 15) * factor)
    scan_start = max(0, scan_start)
    scan_end = min(thresh.shape[0], scan_end)
    
    crop = thresh[scan_start:scan_end, :]
    
    # Find ink projection per row
    proj_y = np.sum(crop > 0, axis=1)
    
    # The glyphs are the main ink band - look for contiguous ink
    # But we need to distinguish between glyph ink and label/separator ink
    # Labels are thin horizontal bands (height ~35px at this scale)
    # Glyphs are taller (80-140px)
    
    # Find the main ink band (largest contiguous region with high ink)
    in_ink = proj_y > 100  # significant ink
    bands = []
    start = None
    for i, val in enumerate(in_ink):
        if val and start is None:
            start = i
        elif not val and start is not None:
            bands.append((start, i, i - start))
            start = None
    if start is not None:
        bands.append((start, len(in_ink), len(in_ink) - start))
    
    # The glyph band is the tallest one
    if bands:
        glyph_band = max(bands, key=lambda b: b[2])
        glyph_y_start = scan_start + glyph_band[0]
        glyph_y_end = scan_start + glyph_band[1]
        
        # Convert back to reference coords
        ref_y_start = glyph_y_start / factor
        ref_y_end = glyph_y_end / factor
        
        print(f"\n{name}:")
        print(f"  Current config: y_start={y1_cfg}, y_end={y2_cfg}")
        print(f"  All bands: {[(scan_start+b[0], scan_start+b[1], b[2]) for b in bands]}")
        print(f"  Glyph band (abs): y={glyph_y_start}-{glyph_y_end} (h={glyph_y_end-glyph_y_start})")
        print(f"  Glyph band (ref): y={ref_y_start:.1f}-{ref_y_end:.1f}")
        print(f"  Recommended: y_start={int(ref_y_start - 0.5)}, y_end={int(ref_y_end + 0.5)}")
        
        # Where should baseline be?
        # For uppercase, baseline is at the bottom of the tallest chars
        # For punct, it should align with the uppercase baseline 
        # The underscore sits ON the baseline, most glyphs hang from above
        
        # Find the underscore position if in this row
        if name == "Basic Punc":
            # Underscore is char 9 (0-indexed) in ".,:;!?'\"-_/\\"
            # Let's find actual bottom of longest chars
            print(f"  Current baseline (ref): {row['baseline']}")
            # Bottom of ink = glyph_y_end
            ref_baseline = ref_y_end - 1
            print(f"  Suggested baseline (bottom of ink): {ref_baseline:.1f}")
            
            # But looking at the data, the baseline should be where the bottom
            # of the period/comma sits, which is at the bottom of the glyph band
            # The top of the band is where the apostrophe/! starts
