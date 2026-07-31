import cv2

img = cv2.imread("ethernium_sheet_hq.png")
if img is not None:
    # Band 2 is y=228 to 495
    crop = img[200:520, :]
    cv2.imwrite("tools/band2.png", crop)
    print("Saved tools/band2.png")
