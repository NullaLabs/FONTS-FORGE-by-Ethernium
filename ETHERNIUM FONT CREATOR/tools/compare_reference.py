"""Side-by-side: bitmap crop from HQ sheet vs rendered TTF glyph."""
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
SHEET = ROOT / "ethernium_sheet_hq.png"
TTF = ROOT / "Ethernium_Sym.ttf"
OUT = ROOT / "tools" / "reference_vs_font.png"

ROWS = [
    ("Uppercase", 180, 225, "ABCDEFGHIJKLMNOPQRSTUVWXYZ"),
    ("Lowercase", 245, 287, "abcdefghijklmnopqrstuvwxyz"),
]


def main():
    img = cv2.imread(str(SHEET), cv2.IMREAD_GRAYSCALE)
    h, w = img.shape
    factor = h / 682
    _, thresh = cv2.threshold(cv2.medianBlur(img, 3), 30, 255, cv2.THRESH_BINARY)
    font = ImageFont.truetype(str(TTF), 48)

    cell = 56
    cols = 13
    chars = ROWS[0][3][:13] + ROWS[1][3][:13]
    out_h = (len(chars) // cols + 1) * cell * 2 + 40
    out = Image.new("RGB", (cols * cell + 30, out_h), (12, 12, 16))
    draw = ImageDraw.Draw(out)

    for i, ch in enumerate(chars):
        row_i = 0 if i < 13 else 1
        name, y1, y2, _ = ROWS[row_i]
        y1, y2 = int(y1 * factor), int(y2 * factor)
        crop = thresh[y1:y2, :]
        x1, x2 = 0, crop.shape[1]
        proj = np.sum(crop > 0, axis=0)
        idx = np.where(proj >= proj.max() * 0.12)[0]
        if len(idx):
            x1, x2 = int(idx[0]), int(idx[-1]) + 1
        slot_w = (x2 - x1) / (26 if row_i == 0 else 26)
        ci = i if row_i == 0 else i - 13
        sx1 = int(x1 + ci * slot_w)
        sx2 = int(x1 + (ci + 1) * slot_w)
        slot = crop[:, sx1:sx2]
        bmp = Image.fromarray(slot).convert("RGB")
        bmp = bmp.resize((cell - 4, cell - 4), Image.Resampling.NEAREST)

        col, row = i % cols, (i // cols) * 2
        px, py = 15 + col * cell, 20 + row * cell
        out.paste(bmp, (px, py + 1))
        draw.text((px, py + cell), ch, font=font, fill=(240, 240, 245))

    out.save(OUT)
    print(f"Saved {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
