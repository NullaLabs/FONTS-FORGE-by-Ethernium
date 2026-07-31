import cv2
import numpy as np

img = cv2.imread("ethernium_sheet_hq.png", cv2.IMREAD_GRAYSCALE)
if img is not None:
    # Basic Punc: y_start = 370, y_end = 393 (scaled: y=1771 to 1881)
    # with pad_y = 19, crop is y=1752 to 1900
    crop = img[1752:1900, :]
    _, thresh = cv2.threshold(crop, 30, 255, cv2.THRESH_BINARY)
    
    # Bounding boxes
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    boxes = []
    for c in contours:
        x, y, w, h = cv2.boundingRect(c)
        if w > 5 and h > 5:
            boxes.append((x, y, w, h))
            
    boxes = sorted(boxes, key=lambda b: b[0])
    print(f"Detected {len(boxes)} contours in Basic Punc:")
    for idx, (x, y, w, h) in enumerate(boxes):
        print(f"  Contour {idx:2d}: x={x:4d}, y={y:3d}, w={w:3d}, h={h:3d}")
