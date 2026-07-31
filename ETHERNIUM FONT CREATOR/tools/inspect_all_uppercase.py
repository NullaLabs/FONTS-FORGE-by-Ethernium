from fontTools.ttLib import TTFont
font = TTFont('Ethernium_Sym.ttf')
glyf = font['glyf']
cmap = font.getBestCmap()

for char in "LMNOP":
    gname = cmap[ord(char)]
    g = glyf[gname]
    print(f"\nChar {char} ({gname}): contours={g.numberOfContours}, BBox=({g.xMin},{g.yMin})-({g.xMax},{g.yMax})")
    if g.numberOfContours > 0:
        # print first few points
        coords = list(g.coordinates)
        print(f"  First 5 pts: {coords[:5]}")
        print(f"  Last 5 pts: {coords[-5:]}")
