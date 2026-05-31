from fontTools.ttLib import TTFont
import sys
sys.stdout.reconfigure(encoding='utf-8')

font = TTFont('Ethernium_Sym.ttf')
cmap = font.getBestCmap()
glyf = font['glyf']
hmtx = font['hmtx']

print("Glyph Map & Metrics:")
print(f"{'Char':<6} | {'Unicode':<7} | {'Glyph Name':<12} | {'Width':<6} | {'LSB':<5} | {'BBox'}")
print("-" * 65)

for code in sorted(cmap.keys()):
    char = chr(code)
    # Check if printable
    char_str = char if char.isprintable() else " "
    gname = cmap[code]
    width, lsb = hmtx[gname]
    g = glyf[gname]
    bbox = f"({g.xMin},{g.yMin})-({g.xMax},{g.yMax})" if g.numberOfContours > 0 else "Empty"
    print(f"{char_str:<6} | U+{code:04X} | {gname:<12} | {width:<6} | {lsb:<5} | {bbox}")
