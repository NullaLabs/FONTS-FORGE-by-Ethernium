from fontTools.ttLib import TTFont
font = TTFont('Ethernium_Sym.ttf')
glyf = font['glyf']
cmap = font.getBestCmap()

gname = cmap[ord('M')]
g = glyf[gname]
print("Glyph name for M:", gname)
print("Number of contours:", g.numberOfContours)
print("Bounding Box:", g.xMin, g.yMin, g.xMax, g.yMax)
if g.numberOfContours > 0:
    coords = list(g.coordinates)
    print("Coordinates of M:")
    for i, pt in enumerate(coords):
        print(f"  [{i}] {pt}")
