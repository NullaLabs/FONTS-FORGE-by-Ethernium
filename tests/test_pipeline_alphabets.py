"""
End-to-end pipeline tests against real writing systems.

Latin is the easy case. The hard cases are scripts whose signs are not one
connected shape: alchemical symbols carry detached dots and rings, and
Sumero-Akkadian cuneiform builds every sign from separate wedges, so counting
connected components cannot find sign boundaries at all. Those are what the
character-count solver exists for, and what these tests pin down.

Fidelity is measured against the source typeface rather than eyeballed: a
faithful trace reproduces each glyph's aspect ratio closely.
"""
from __future__ import annotations

import json
import statistics

import pytest
from fontTools.pens.boundsPen import BoundsPen
from fontTools.ttLib import TTFont

from font_forge.autodetect import analyze, build_config, refine_rows, save_prepared
from font_forge.core import SheetToFontBuilder

from conftest import (
    FONT_HISTORIC,
    FONT_LATIN,
    FONT_SYMBOL,
    render_sheet,
    require_font,
)

pytestmark = pytest.mark.slow

# Elder Futhark; alchemical symbols; Sumero-Akkadian cuneiform signs.
RUNIC = ["ᚠᚢᚦᚨᚱᚲᚷᚹᚺᚾᛁᛃ", "ᛇᛈᛉᛊᛋᛏᛒᛖᛗᛚᛜᛞ"]
MAGIC = ["".join(chr(c) for c in range(0x1F700, 0x1F70C)),
         "".join(chr(c) for c in range(0x1F70C, 0x1F718))]
SUMERIAN = ["".join(chr(c) for c in range(0x12000, 0x12008)),
            "".join(chr(c) for c in range(0x12008, 0x12010))]

CASES = [
    pytest.param("runic", RUNIC, FONT_HISTORIC, 110, id="runic"),
    pytest.param("magic", MAGIC, FONT_SYMBOL, 110, id="alchemical"),
    pytest.param("sumerian", SUMERIAN, FONT_HISTORIC, 120, id="cuneiform"),
]


def build_from_sheet(workspace, name, rows, font_path, size):
    """Run the whole path a studio session runs: detect, refine, build."""
    sheet = render_sheet(workspace / f"{name}.png", rows, require_font(font_path), size)

    analysis, prepared = analyze(sheet)
    refine_rows(analysis, [len(row) for row in rows])
    save_prepared(prepared, workspace / f"{name}_prepared.png")

    config = build_config(analysis, f"{name}_prepared.png", rows,
                          {"family_name": f"{name} test",
                           "output_basename": name})
    report = SheetToFontBuilder(config, workspace).build()
    return analysis, config, report, TTFont(str(workspace / f"{name}.ttf"))


def aspect_errors(built: TTFont, source_path, chars: set[str]) -> list[float]:
    """Relative aspect-ratio difference per glyph, against the source face."""
    def bounds(font: TTFont):
        cmap, glyphset = font.getBestCmap(), font.getGlyphSet()
        upm = font["head"].unitsPerEm
        out = {}
        for char in chars:
            name = cmap.get(ord(char))
            if not name or name not in glyphset:
                continue
            pen = BoundsPen(glyphset)
            glyphset[name].draw(pen)
            if pen.bounds is None:
                continue
            x1, y1, x2, y2 = pen.bounds
            out[char] = ((x2 - x1) / upm, (y2 - y1) / upm)
        return out

    source = TTFont(str(source_path), fontNumber=0, lazy=True)
    try:
        got, want = bounds(built), bounds(source)
    finally:
        source.close()

    errors = []
    for char in got.keys() & want.keys():
        gw, gh = got[char]
        sw, sh = want[char]
        if sw <= 0 or sh <= 0 or gh <= 0:
            continue
        errors.append(abs((gw / gh) - (sw / sh)) / (sw / sh))
    return errors


# --- Latin --------------------------------------------------------------


def test_latin_alphabet_round_trip(tmp_path, latin_sheet):
    """Every letter and digit survives from a plain black-on-white image."""
    sheet, rows = latin_sheet
    analysis, prepared = analyze(sheet)

    assert analysis.inverted is True, "black-on-white must be detected and inverted"
    assert len(analysis.rows) == len(rows)

    refine_rows(analysis, [len(row) for row in rows])
    assert [row.glyph_count for row in analysis.rows] == [len(r) for r in rows]

    save_prepared(prepared, tmp_path / "prepared.png")
    config = build_config(analysis, "prepared.png", rows,
                          {"family_name": "latin test", "output_basename": "latin"})
    report = SheetToFontBuilder(config, tmp_path).build()

    assert all(row["ok"] for row in report["rows"])
    font = TTFont(str(tmp_path / "latin.ttf"))
    try:
        mapped = {chr(c) for c in font.getBestCmap()}
        assert set("".join(rows)) <= mapped
    finally:
        font.close()


def test_latin_descenders_sit_below_the_baseline(tmp_path, latin_sheet):
    """
    Guard for the em-relative clamp: fixed pixel bounds used to discard
    descenders outright, dropping 'y' from the font.
    """
    sheet, rows = latin_sheet
    analysis, prepared = analyze(sheet)
    refine_rows(analysis, [len(row) for row in rows])
    save_prepared(prepared, tmp_path / "prepared.png")
    config = build_config(analysis, "prepared.png", rows,
                          {"family_name": "latin test", "output_basename": "latin"})
    SheetToFontBuilder(config, tmp_path).build()

    font = TTFont(str(tmp_path / "latin.ttf"))
    try:
        cmap, glyphset = font.getBestCmap(), font.getGlyphSet()
        for char in "gjpqy":
            pen = BoundsPen(glyphset)
            glyphset[cmap[ord(char)]].draw(pen)
            assert pen.bounds[1] < 0, f"'{char}' has no descender below the baseline"
    finally:
        font.close()


# --- non-Latin ----------------------------------------------------------


@pytest.mark.parametrize("name, rows, font_path, size", CASES)
def test_exotic_alphabet_segments_and_builds(tmp_path, name, rows, font_path, size):
    analysis, config, report, font = build_from_sheet(
        tmp_path, name, rows, font_path, size)
    try:
        assert [row.glyph_count for row in analysis.rows] == [len(r) for r in rows], (
            f"{name}: segmentation did not resolve to the expected sign counts")
        assert all(row["ok"] for row in report["rows"])

        mapped = {chr(c) for c in font.getBestCmap()}
        assert set("".join(rows)) <= mapped
    finally:
        font.close()


@pytest.mark.parametrize("name, rows, font_path, size", CASES)
def test_exotic_alphabet_does_not_need_the_grid_fallback(
        tmp_path, name, rows, font_path, size):
    """
    Grid mode splits a row into equal slots. It rescues a mis-segmented row
    only when the source happens to be evenly spaced, so relying on it hides
    a real segmentation failure rather than fixing one.
    """
    _, config, _, font = build_from_sheet(tmp_path, name, rows, font_path, size)
    font.close()
    fell_back = [row["name"] for row in config["rows"] if row.get("grid")]
    assert not fell_back, f"{name}: fell back to grid mode on {fell_back}"


@pytest.mark.parametrize("name, rows, font_path, size", CASES)
def test_exotic_alphabet_traces_faithfully(tmp_path, name, rows, font_path, size):
    _, _, _, font = build_from_sheet(tmp_path, name, rows, font_path, size)
    try:
        errors = aspect_errors(font, require_font(font_path), set("".join(rows)))
        assert errors, "no glyphs were comparable against the source"
        assert statistics.median(errors) < 0.05
        assert max(errors) < 0.15
    finally:
        font.close()


def test_non_bmp_scripts_get_conventional_glyph_names(tmp_path):
    """Cuneiform sits above the BMP and must not be named ``uniXXXXX``."""
    _, _, _, font = build_from_sheet(
        tmp_path, "sumerian", SUMERIAN, FONT_HISTORIC, 120)
    try:
        names = set(font.getBestCmap().values())
        assert any(n.startswith("u1") and not n.startswith("uni") for n in names)
        assert not any(len(n) > 7 and n.startswith("uni") for n in names)
    finally:
        font.close()
