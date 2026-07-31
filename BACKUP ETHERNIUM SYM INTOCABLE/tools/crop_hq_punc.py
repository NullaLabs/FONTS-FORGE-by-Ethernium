import cv2

img = cv2.imread("ethernium_sheet_hq.png")
if img is not None:
    # y=1650 to 2050 on HQ sheet
    crop = img[1650:2050, :]
    cv2.imwrite("tools/hq_punc_inspect.png", crop)
    print("Saved tools/hq_punc_inspect.png")
