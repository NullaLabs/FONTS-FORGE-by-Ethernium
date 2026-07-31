import cv2
import numpy as np

def analyze_sheet(name):
    img = cv2.imread(name, cv2.IMREAD_GRAYSCALE)
    if img is None:
        print(f"Could not read {name}")
        return
    h, w = img.shape
    _, thresh = cv2.threshold(cv2.medianBlur(img, 3), 30, 255, cv2.THRESH_BINARY)
    proj = np.sum(thresh > 0, axis=1)
    
    # find continuous active rows
    active = proj > (proj.max() * 0.05)
    bands = []
    start = None
    for i, val in enumerate(active):
        if val and start is None:
            start = i
        elif not val and start is not None:
            if i - start >= 5:
                bands.append((start, i))
            start = None
    if start is not None:
        bands.append((start, h))
        
    print(f"\nSheet {name} ({w}x{h}):")
    for idx, (y1, y2) in enumerate(bands):
        ref_y1 = int(round(y1 * 682 / h))
        ref_y2 = int(round(y2 * 682 / h))
        print(f"  Band {idx+1:2d}: pixels {y1:4d} - {y2:4d} (ref {ref_y1:3d} - {ref_y2:3d}, height={y2-y1})")

analyze_sheet("ethernium_sheet.png")
analyze_sheet("ethernium_sheet_hq.png")
