import cv2
import numpy as np

img = cv2.imread("ethernium_sheet_hq.png", cv2.IMREAD_GRAYSCALE)
if img is not None:
    # Crop Uppercase row
    # y=880 to 1060
    crop = img[880:1060, :]
    _, thresh = cv2.threshold(crop, 30, 255, cv2.THRESH_BINARY)
    
    # Find contours
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    boxes = []
    for c in contours:
        x, y, w, h = cv2.boundingRect(c)
        if w > 10 and h > 10:
            boxes.append((x, y, w, h))
            
    boxes = sorted(boxes, key=lambda b: b[0])
    print(f"Detected {len(boxes)} raw contours in Uppercase row:")
    for idx, (x, y, w, h) in enumerate(boxes):
        print(f"  Contour {idx:2d}: x={x:4d}, y={y:3d}, w={w:3d}, h={h:3d}")
