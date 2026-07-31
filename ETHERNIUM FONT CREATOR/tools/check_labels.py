import cv2
import numpy as np

img = cv2.imread("ethernium_sheet_hq.png", cv2.IMREAD_GRAYSCALE)
if img is not None:
    # Row 1 (Uppercase) goes from y=861 to 1077
    # Let's check y from 830 to 865
    sub = img[830:865, :]
    _, thresh = cv2.threshold(sub, 30, 255, cv2.THRESH_BINARY)
    
    # Let's count active pixels in columns to see where the label text is
    col_proj = np.sum(thresh > 0, axis=0)
    
    print("Label regions in y=830 to 865 (active pixel count > 0 columns):")
    # Group contiguous active columns
    active = col_proj > 0
    intervals = []
    start = None
    for i, val in enumerate(active):
        if val and start is None:
            start = i
        elif not val and start is not None:
            intervals.append((start, i))
            start = None
    if start is not None:
        intervals.append((start, len(active)))
        
    for idx, (x1, x2) in enumerate(intervals):
        print(f"  Interval {idx+1}: x={x1:4d} to {x2:4d} (width={x2-x1})")
