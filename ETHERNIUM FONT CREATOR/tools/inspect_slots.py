import cv2
import numpy as np

img = cv2.imread("ethernium_sheet_hq.png", cv2.IMREAD_GRAYSCALE)
if img is not None:
    # Let's check where the pixels are in the column for L, M, N, O
    # Row 1 (Uppercase) goes from y=861 to 1077 (with padding 842 to 1096)
    # Let's crop the entire Row 1
    row_crop = img[842:1096, :]
    _, thresh = cv2.threshold(row_crop, 30, 255, cv2.THRESH_BINARY)
    
    # We want to find the horizontal coordinates of the slots
    # Let's do the same grid or contour extraction logic to see what bounding boxes are found for letters L, M, N, O (indices 11, 12, 13, 14)
    # Let's see the bounding boxes found in the row
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    boxes = []
    for c in contours:
        x, y, w, h = cv2.boundingRect(c)
        if w > 200*4.78 or h < 3*4.78 or w < 2*4.78:
            continue
        boxes.append((x, y, w, h))
    
    # Sort boxes left to right
    boxes = sorted(boxes, key=lambda b: b[0])
    
    # Merge boxes (same as in core.py)
    # merge gap is max(3, 4*4.78) = 19
    # max_merge_width is 55*4.78 = 263
    merged = []
    used = set()
    gap_px = 19
    max_merge_width = 263
    
    for i, b1 in enumerate(boxes):
        if i in used:
            continue
        group = [b1]
        used.add(i)
        changed = True
        while changed:
            changed = False
            for j, b2 in enumerate(boxes):
                if j in used:
                    continue
                merge_ok = False
                for member in group:
                    x1, _, w1, _ = member[:4]
                    x2, _, w2, _ = b2[:4]
                    h_dist = max(0, max(x1, x2) - min(x1 + w1, x2 + w2))
                    if h_dist <= gap_px:
                        xs = [b[0] for b in group] + [x2]
                        ws = [b[2] for b in group] + [w2]
                        span = max(x + w for x, w in zip(xs, ws)) - min(xs)
                        if max_merge_width and span > max_merge_width:
                            continue
                        merge_ok = True
                        break
                if merge_ok:
                    group.append(b2)
                    used.add(j)
                    changed = True
        xs = [b[0] for b in group]
        ys = [b[1] for b in group]
        ws = [b[2] for b in group]
        hs = [b[3] for b in group]
        min_x, max_x = min(xs), max(x + w for x, w in zip(xs, ws))
        min_y, max_y = min(ys), max(y + h for y, h in zip(ys, hs))
        merged.append((min_x, min_y, max_x - min_x, max_y - min_y))
    
    merged = sorted(merged, key=lambda g: g[0])
    
    print("Uppercase Row Extracted Slots:")
    for idx, (x, y, w, h) in enumerate(merged):
        char = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"[idx] if idx < 26 else "?"
        print(f"  Slot {idx:2d} ({char}): x={x:4d}, y={y:3d}, w={w:3d}, h={h:3d} | absolute y on sheet: {842+y} to {842+y+h}")
