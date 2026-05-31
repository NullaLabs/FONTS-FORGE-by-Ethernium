import cv2
import numpy as np

img = cv2.imread("ethernium_sheet_hq.png", cv2.IMREAD_GRAYSCALE)
if img is not None:
    # Extended Punc row: y_start = 423, y_end = 448 (scaled: y=2024 to 2144)
    # with pad_y = 19, crop is y=2005 to 2163
    crop = img[2005:2163, :]
    _, thresh = cv2.threshold(crop, 30, 255, cv2.THRESH_BINARY)
    
    # Let's see the bounding boxes of contours
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    boxes = []
    for c in contours:
        x, y, w, h = cv2.boundingRect(c)
        if w > 5 and h > 5:
            boxes.append((x, y, w, h))
            
    boxes = sorted(boxes, key=lambda b: b[0])
    print(f"Detected {len(boxes)} contours in Extended Punc row crop:")
    for idx, (x, y, w, h) in enumerate(boxes):
        print(f"  Contour {idx:2d}: x={x:4d}, y={y:3d}, w={w:3d}, h={h:3d}")
