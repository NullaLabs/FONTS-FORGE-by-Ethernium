from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import RecordingPen

font = TTFont('Ethernium_Sym.ttf')
glyf = font['glyf']
cmap = font.getBestCmap()

def get_glyph_summary(char):
    gname = cmap.get(ord(char))
    if not gname:
        return "None"
    g = glyf[gname]
    pen = RecordingPen()
    g.draw(pen, glyf)
    # Simple summary of drawing commands
    ops = [op[0] for op in pen.value]
    # Count of lines vs curves
    line_count = ops.count('lineTo')
    move_count = ops.count('moveTo')
    return f"{gname} | contours={g.numberOfContours} | lines={line_count} | moves={move_count} | bbox=({g.xMin},{g.yMin})-({g.xMax},{g.yMax})"

print("=== ETHERNIUM GLYPH DETAILED ANALYSIS ===")
for char in "ETHERNIUM":
    print(f"Char '{char}': {get_glyph_summary(char)}")
