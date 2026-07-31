"""
Regression guard for the shipped Ethernium Sym font.

The engine is shared with the auto-detection pipeline, so a change made for
an arbitrary sheet can silently alter the flagship font. This rebuilds it
from its committed config and compares the result against the font in the
repository: same characters, same contours.
"""
from __future__ import annotations

import pytest
from fontTools.ttLib import TTFont

from font_forge.config import load_config
from font_forge.core import SheetToFontBuilder, glyph_name_for

pytestmark = pytest.mark.slow


@pytest.fixture(scope="module")
def rebuilt(project_root, tmp_path_factory):
    """Rebuild Ethernium under a throwaway name, leaving the shipped one alone."""
    config = load_config(project_root / "configs" / "ethernium.json")
    config["output_basename"] = "_regression_build"
    report = SheetToFontBuilder(config, project_root).build()

    built = project_root / "_regression_build.ttf"
    font = TTFont(str(built))
    yield font, report

    font.close()
    for suffix in (".ttf", ".woff", ".woff2"):
        (project_root / f"_regression_build{suffix}").unlink(missing_ok=True)


def test_every_row_extracts_the_expected_glyph_count(rebuilt):
    _, report = rebuilt
    failed = [row for row in report["rows"] if not row["ok"]]
    assert not failed, f"rows did not match their expected count: {failed}"


def test_character_map_matches_the_shipped_font(project_root, rebuilt):
    font, _ = rebuilt
    shipped = TTFont(str(project_root / "Ethernium_Sym.ttf"))
    try:
        assert set(font.getBestCmap()) == set(shipped.getBestCmap())
    finally:
        shipped.close()


def test_outlines_match_the_shipped_font(project_root, rebuilt):
    """Contour counts are a cheap, sensitive proxy for outline drift."""
    font, _ = rebuilt
    shipped = TTFont(str(project_root / "Ethernium_Sym.ttf"))
    try:
        common = set(font.getGlyphOrder()) & set(shipped.getGlyphOrder())
        drifted = [
            name for name in common
            if font["glyf"][name].numberOfContours
            != shipped["glyf"][name].numberOfContours
        ]
        assert not drifted, f"outlines changed for: {drifted}"
    finally:
        shipped.close()


def test_no_glyph_is_accidentally_empty(rebuilt):
    font, _ = rebuilt
    empty = [
        name for name in font.getGlyphOrder()
        if name != "space" and font["glyf"][name].numberOfContours == 0
    ]
    assert not empty, f"empty outlines: {empty}"


# --- glyph naming -------------------------------------------------------


@pytest.mark.parametrize("char, expected", [
    ("A", "A"),
    ("7", "7"),
    ("Ω", "uni03A9"),      # Greek omega, inside the BMP
    ("◊", "uni25CA"),      # lozenge, inside the BMP
    ("\U0001f700", "u1F700"),   # alchemical, above the BMP
    ("\U00012000", "u12000"),   # cuneiform, above the BMP
])
def test_glyph_names_follow_the_adobe_convention(char, expected):
    """
    ``uniXXXX`` is defined for four hex digits only. Codepoints above the BMP
    need the ``uXXXXX`` form or tools cannot map the name back to Unicode.
    """
    assert glyph_name_for(char) == expected
