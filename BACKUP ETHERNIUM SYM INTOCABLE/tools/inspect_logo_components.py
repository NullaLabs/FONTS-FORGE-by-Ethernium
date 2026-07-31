import cv2
import numpy as np

img = cv2.imread("ethernium_sheet_hq.png", cv2.IMREAD_GRAYSCALE)
if img is not None:
    # Logo region is y=228 to 495
    sub = img[228:495, :]
    _, thresh = cv2.threshold(cv2.medianBlur(sub, 3), 30, 255, cv2.THRESH_BINARY)
    
    # Find contours
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    boxes = []
    for c in contours:
        x, y, w, h = cv2.boundingRect(c)
        if w > 20 and h > 50:
            boxes.append((x, y, w, h))
            
    boxes = sorted(boxes, key=lambda b: b[0])
    print("Detected components in logo:")
    for idx, (x, y, w, h) in enumerate(boxes):
        print(f"  Component {idx:2d}: x={x:4d}, y={y:3d}, w={w:3d}, h={h:3d}")
