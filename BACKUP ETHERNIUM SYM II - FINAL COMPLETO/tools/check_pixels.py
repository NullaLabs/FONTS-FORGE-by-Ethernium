import cv2
import numpy as np

img = cv2.imread("ethernium_sheet_hq.png", cv2.IMREAD_GRAYSCALE)
if img is not None:
    # Column of M: x = 2384 to 2486
    # Let's check y from 830 to 900
    sub = img[830:900, 2384:2486]
    _, thresh = cv2.threshold(sub, 30, 255, cv2.THRESH_BINARY)
    
    print("Active pixels in column of M (y=830 to 900):")
    for y_idx in range(sub.shape[0]):
        row_pixels = thresh[y_idx, :]
        active_count = np.sum(row_pixels > 0)
        if active_count > 0:
            # print a line representation
            line = "".join(["#" if p > 0 else "." for p in row_pixels[::4]])
            print(f"y={830+y_idx}: {line} ({active_count} px)")
