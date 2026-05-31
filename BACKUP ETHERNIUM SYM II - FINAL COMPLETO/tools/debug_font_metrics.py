"""Check how glyphs render vertically in the final font - inspect font metrics."""
from fontTools.ttLib import TTFont
from pathlib import Path
import json

root = Path(__file__).resolve().parent.parent
font = TTFont(str(root / "Ethernium_Sym.ttf"))

glyf = font["glyf"]
hmtx = font["hmtx"]

# Check punctuation and symbol glyphs
test_chars = {
    '.': 'period', ',': 'comma', ':': 'colon', ';': 'semicolon',
    '!': 'exclam', '?': 'question', "'": 'quotesingle', '"': 'quotedbl',
    '-': 'hyphen', '_': 'underscore', '/': 'slash', '\\': 'backslash',
    '(': 'parenleft', ')': 'parenright', '[': 'bracketleft', ']': 'bracketright',
    '{': 'braceleft', '}': 'braceright', '<': 'less', '>': 'greater',
    '@': 'at', '#': 'numbersign', '%': 'percent', '&': 'ampersand',
    '*': 'asterisk', '+': 'plus', '=': 'equal', '~': 'asciitilde',
}

# Also check some normal chars for reference
ref_chars = {
    'A': 'A', 'B': 'B', 'H': 'H',
    '0': '0', '1': '1',
}

cmap = font.getBestCmap()

print("=== Reference chars (uppercase/numbers) ===")
for char, name in ref_chars.items():
    gname = cmap.get(ord(char))
    if gname and gname in glyf:
        g = glyf[gname]
        if hasattr(g, 'xMin'):
            print(f"  '{char}' ({gname}): xMin={g.xMin}, yMin={g.yMin}, xMax={g.xMax}, yMax={g.yMax}, "
                  f"h={g.yMax-g.yMin}, advance={hmtx[gname][0]}")

print("\n=== Punctuation chars ===")
for char, name in test_chars.items():
    gname = cmap.get(ord(char))
    if gname and gname in glyf:
        g = glyf[gname]
        if hasattr(g, 'xMin'):
            print(f"  '{char}' ({gname}): xMin={g.xMin}, yMin={g.yMin}, xMax={g.xMax}, yMax={g.yMax}, "
                  f"h={g.yMax-g.yMin}, advance={hmtx[gname][0]}")
    else:
        print(f"  '{char}' ({name}): NOT IN FONT")

print("\n=== Special symbols ===")
specials = [
    ('\u03A9', 'Omega'), ('\u2020', 'dagger'), ('\u2021', 'daggerdbl'),
    ('\u221E', 'infinity'), ('\u0394', 'Delta'), ('\u25CA', 'lozenge'),
    ('\u2609', 'sun'), ('\u263D', 'moon'), ('\u2318', 'command'), ('\u273B', 'star'),
]
for char, name in specials:
    gname = cmap.get(ord(char))
    if gname and gname in glyf:
        g = glyf[gname]
        if hasattr(g, 'xMin'):
            print(f"  {name} ({gname}): xMin={g.xMin}, yMin={g.yMin}, xMax={g.xMax}, yMax={g.yMax}, "
                  f"h={g.yMax-g.yMin}, advance={hmtx[gname][0]}")
    else:
        print(f"  {name}: NOT IN FONT")

# Print font-level metrics
print(f"\n=== Font metrics ===")
print(f"  unitsPerEm: {font['head'].unitsPerEm}")
print(f"  ascent (hhea): {font['hhea'].ascent}")
print(f"  descent (hhea): {font['hhea'].descent}")
print(f"  sTypoAscender: {font['OS/2'].sTypoAscender}")
print(f"  sTypoDescender: {font['OS/2'].sTypoDescender}")
print(f"  usWinAscent: {font['OS/2'].usWinAscent}")
print(f"  usWinDescent: {font['OS/2'].usWinDescent}")
