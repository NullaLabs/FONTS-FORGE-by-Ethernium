"""
The engine calls itself a generic sheet-to-font pipeline. These tests hold it
to that: a font built without an identity config must carry none of the
Ethernium project's identity, while the Ethernium build must keep all of it.

The two are driven from the same code path, so together they prove the
branding is config-supplied rather than compiled in.
"""
from __future__ import annotations

import pytest
from fontTools.ttLib import TTFont

from font_forge.autodetect import analyze, build_config, refine_rows, save_prepared
from font_forge.core import SheetToFontBuilder
from font_forge.config import load_config

pytestmark = pytest.mark.slow

ETHERNIUM_MARKERS = ("Ethernium", "EtherniumSym", "SteveBlackbeard", "Font Creator")


def name_strings(font: TTFont) -> list[str]:
    return [record.toUnicode() for record in font["name"].names]


def decode_watermark(font: TTFont) -> str:
    """
    Decode whatever the forensic reader would read from the carrier glyphs.

    Mirrors the injector: low bits of each coordinate, little-endian within a
    byte, terminated by a null byte. On an unwatermarked font this returns
    junk or an empty string - never the Ethernium signature.
    """
    carriers = ['E', 'M', 'Ω', 'O', 'V', 'W', '0', 'A', 'B', 'C',
                'D', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'N']
    cmap, glyf = font.getBestCmap(), font["glyf"]
    bits: list[int] = []
    for char in carriers:
        name = cmap.get(ord(char))
        if not name or name not in glyf:
            continue
        glyph = glyf[name]
        if glyph.numberOfContours <= 0 or not hasattr(glyph, "coordinates"):
            continue
        for x, y in glyph.coordinates:
            bits.append(int(x) & 1)
            bits.append(int(y) & 1)

    out = bytearray()
    for i in range(0, len(bits) - 7, 8):
        byte = sum(bits[i + b] << b for b in range(8))
        if byte == 0:
            break
        out.append(byte)
    try:
        return out.decode("utf-8", errors="replace")
    except Exception:
        return ""


@pytest.fixture(scope="module")
def generic_font(tmp_path_factory, project_root):
    """A font built the way the studio builds one: detector config, no identity."""
    from conftest import FONT_LATIN, render_sheet, require_font

    workspace = tmp_path_factory.mktemp("generic")
    rows = ["ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz", "0123456789"]
    sheet = render_sheet(workspace / "s.png", rows, require_font(FONT_LATIN))

    analysis, prepared = analyze(sheet)
    refine_rows(analysis, [len(r) for r in rows])
    save_prepared(prepared, workspace / "prep.png")
    config = build_config(analysis, "prep.png", rows,
                          {"family_name": "Test Sans", "output_basename": "TestSans"})
    SheetToFontBuilder(config, workspace).build()

    font = TTFont(str(workspace / "TestSans.ttf"))
    yield font
    font.close()


@pytest.fixture(scope="module")
def ethernium_font(project_root, tmp_path_factory):
    config = load_config(project_root / "configs" / "ethernium.json")
    config["output_basename"] = "_branding_build"
    SheetToFontBuilder(config, project_root).build()
    font = TTFont(str(project_root / "_branding_build.ttf"))
    yield font
    font.close()
    for suffix in (".ttf", ".woff", ".woff2"):
        (project_root / f"_branding_build{suffix}").unlink(missing_ok=True)


# --- a generic font must be clean ---------------------------------------


def test_generic_font_has_no_ethernium_in_its_names(generic_font):
    joined = " ".join(name_strings(generic_font))
    for marker in ETHERNIUM_MARKERS:
        assert marker not in joined, f"generic font leaked '{marker}' into its name table"


def test_generic_font_carries_the_users_family_name(generic_font):
    assert any("Test Sans" in s for s in name_strings(generic_font))


def test_generic_font_has_a_neutral_vendor_id(generic_font):
    assert generic_font["OS/2"].achVendID != "ETHN"


def test_generic_font_has_no_ethernium_watermark(generic_font):
    assert "SteveBlackbeard" not in decode_watermark(generic_font)


def test_generic_font_omits_decorative_fallbacks(generic_font):
    """A hand-drawn sheet without a '$' should not gain a geometric one."""
    cmap = generic_font.getBestCmap()
    assert ord("$") not in cmap
    assert ord("|") not in cmap


def test_generic_font_still_has_notdef_and_space(generic_font):
    names = set(generic_font.getGlyphOrder())
    assert ".notdef" in names
    assert generic_font.getBestCmap().get(ord(" ")) == "space"


# --- the Ethernium font must keep its identity --------------------------


def test_ethernium_font_keeps_its_identity(ethernium_font):
    joined = " ".join(name_strings(ethernium_font))
    assert "Ethernium Sym" in joined
    assert ethernium_font["OS/2"].achVendID == "ETHN"


def test_ethernium_font_keeps_its_watermark(ethernium_font):
    assert "SteveBlackbeard" in decode_watermark(ethernium_font)


def test_ethernium_font_keeps_its_decorative_fallbacks(ethernium_font):
    cmap = ethernium_font.getBestCmap()
    for char in "$^`|":
        assert ord(char) in cmap, f"Ethernium lost its '{char}' fallback"


def test_ethernium_font_keeps_its_kerning(ethernium_font):
    assert "kern" in ethernium_font
    pairs = ethernium_font["kern"].kernTables[0].kernTable
    assert pairs, "Ethernium kern table is empty"
