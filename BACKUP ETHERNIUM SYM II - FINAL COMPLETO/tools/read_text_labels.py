import cv2
import numpy as np

img = cv2.imread("ethernium_sheet_hq.png", cv2.IMREAD_GRAYSCALE)
if img is not None:
    # y=830 to 865, x=2270 to 2650
    sub = img[825:865, 2270:2650]
    _, thresh = cv2.threshold(sub, 30, 255, cv2.THRESH_BINARY)
    
    print("Visual representation of label region:")
    # print every 2nd row and every 2nd column
    for y_idx in range(0, sub.shape[0], 2):
        row_pixels = thresh[y_idx, :]
        line = "".join(["#" if p > 0 else "." for p in row_pixels[::4]])
        print(f"{825+y_idx:3d}: {line}")
