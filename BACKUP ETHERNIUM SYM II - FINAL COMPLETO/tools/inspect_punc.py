import cv2
import numpy as np

img = cv2.imread("ethernium_sheet_hq.png", cv2.IMREAD_GRAYSCALE)
if img is not None:
    # Crop from y=1700 to y=1950
    crop = img[1700:1950, :]
    _, thresh = cv2.threshold(crop, 30, 255, cv2.THRESH_BINARY)
    ink_count = np.sum(thresh > 0)
    print(f"HQ sheet ink count in y=1700..1950: {ink_count}")
    cv2.imwrite("tools/hq_punc_crop.png", crop)
    
    # Let's check std sheet in y=350..410
    img_std = cv2.imread("ethernium_sheet.png", cv2.IMREAD_GRAYSCALE)
    if img_std is not None:
        crop_std = img_std[350:410, :]
        print(f"Std sheet ink count in y=350..410: {np.sum(crop_std < 220)}") # assuming white bg? wait, let's see threshold
        _, thresh_std = cv2.threshold(crop_std, 30, 255, cv2.THRESH_BINARY)
        print(f"Std sheet thresholded ink count in y=350..410: {np.sum(thresh_std > 0)}")
