from fontTools.ttLib import TTFont
font = TTFont('Ethernium_Sym.ttf')
glyf = font['glyf']
cmap = font.getBestCmap()

def inspect_contours(char):
    gname = cmap[ord(char)]
    g = glyf[gname]
    print(f"\nGlyph {char} ({gname}): contours={g.numberOfContours}")
    if g.numberOfContours > 0:
        coords = list(g.coordinates)
        end_pts = g.endPtsOfContours
        start = 0
        for idx, end in enumerate(end_pts):
            contour_pts = coords[start:end+1]
            xs = [p[0] for p in contour_pts]
            ys = [p[1] for p in contour_pts]
            print(f"  Contour {idx}: points={len(contour_pts)}, bbox=({min(xs)},{min(ys)})-({max(xs)},{max(ys)})")
            start = end + 1

inspect_contours('N')
inspect_contours('O')
inspect_contours('P')
