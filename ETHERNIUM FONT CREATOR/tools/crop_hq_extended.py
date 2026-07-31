import cv2

img = cv2.imread("ethernium_sheet_hq.png")
if img is not None:
    # y=2000 to 2600 on HQ sheet
    crop = img[2000:2600, :]
    cv2.imwrite("tools/hq_extended_inspect.png", crop)
    print("Saved tools/hq_extended_inspect.png")
