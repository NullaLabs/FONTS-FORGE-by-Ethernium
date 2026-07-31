"""Shared fixtures for the Font Forge suite."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Windows system fonts used to render synthetic specimen sheets. Tests that
# need them skip rather than fail, so the suite stays runnable off-Windows.
FONT_LATIN = Path(r"C:\Windows\Fonts\arialbd.ttf")
FONT_HISTORIC = Path(r"C:\Windows\Fonts\seguihis.ttf")   # Runic, Cuneiform
FONT_SYMBOL = Path(r"C:\Windows\Fonts\seguisym.ttf")     # Alchemical


@pytest.fixture(scope="session")
def project_root() -> Path:
    return ROOT


def require_font(path: Path):
    if not path.is_file():
        pytest.skip(f"system font not available: {path}")
    return path


def render_sheet(
    dest: Path,
    rows: list[str],
    font_path: Path,
    size: int = 96,
    invert: bool = False,
) -> Path:
    """
    Draw an alphabet as a plain specimen sheet - the kind of image a user
    would drop in, with nothing measured or annotated in advance.
    """
    from PIL import Image, ImageDraw, ImageFont

    font = ImageFont.truetype(str(font_path), size)
    probe = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    gap = int(size * 0.45)
    widths = [sum(int(probe.textlength(c, font=font)) + gap for c in row) for row in rows]

    margin, line_h = int(size * 0.7), int(size * 2.0)
    width = max(widths) + margin * 2
    height = line_h * len(rows) + margin * 2

    bg, fg = ("black", "white") if invert else ("white", "black")
    image = Image.new("RGB", (width, height), bg)
    draw = ImageDraw.Draw(image)

    y = margin
    for row in rows:
        x = margin
        for char in row:
            draw.text((x, y), char, font=font, fill=fg)
            x += int(draw.textlength(char, font=font)) + gap
        y += line_h

    image.save(dest)
    return dest


@pytest.fixture
def latin_sheet(tmp_path) -> tuple[Path, list[str]]:
    rows = ["ABCDEFGHIJKLMNOPQRSTUVWXYZ",
            "abcdefghijklmnopqrstuvwxyz",
            "0123456789"]
    path = render_sheet(tmp_path / "latin.png", rows, require_font(FONT_LATIN))
    return path, rows
