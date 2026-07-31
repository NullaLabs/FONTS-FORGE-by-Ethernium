import cv2
import numpy as np

img = cv2.imread("tools/hq_punc_inspect.png", cv2.IMREAD_GRAYSCALE)
if img is not None:
    _, thresh = cv2.threshold(img, 30, 255, cv2.THRESH_BINARY)
    proj = np.sum(thresh > 0, axis=1)
    
    # find all active y ranges (using a small absolute pixel threshold like 10 pixels to detect tiny punctuation dots)
    active = proj > 5
    bands = []
    start = None
    for i, val in enumerate(active):
        if val and start is None:
            start = i
        elif not val and start is not None:
            if i - start >= 3:
                bands.append((start, i))
            start = None
    if start is not None:
        bands.append((start, len(active)))
        
    print("Ink bands detected in hq_punc_inspect.png (relative to y=1650):")
    for idx, (y1, y2) in enumerate(bands):
        abs_y1 = 1650 + y1
        abs_y2 = 1650 + y2
        ref_y1 = int(round(abs_y1 * 682 / 3264))
        ref_y2 = int(round(abs_y2 * 682 / 3264))
        print(f"  Band {idx:2d}: abs y={abs_y1:4d} to {abs_y2:4d} (ref {ref_y1:3d} to {ref_y2:3d}, height={y2-y1} px)")
