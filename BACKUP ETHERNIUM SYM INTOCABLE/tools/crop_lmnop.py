import cv2
import numpy as np

img = cv2.imread("ethernium_sheet_hq.png")
if img is not None:
    # Let's crop the region around L, M, N, O, P
    # L is around x=2142, P is around x=2832
    # y is around 890 to 1050
    crop = img[880:1060, 2100:3000]
    cv2.imwrite("tools/lmnop_sheet.png", crop)
    print("Saved tools/lmnop_sheet.png")
