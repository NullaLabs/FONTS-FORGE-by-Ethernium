from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import RecordingPen

font = TTFont('Ethernium_Sym.ttf')
glyf = font['glyf']
cmap = font.getBestCmap()

def dump_glyph_shape(char):
    gname = cmap.get(ord(char))
    if not gname:
        return "Not mapped"
    g = glyf[gname]
    if g.numberOfContours <= 0:
        return "Empty"
    
    pen = RecordingPen()
    g.draw(pen, glyf)
    
    # Get all points
    out = []
    for cmd in pen.value:
        op, args = cmd[0], cmd[1]
        if op == 'moveTo':
            out.append(f"M {args[0][0]:.0f},{args[0][1]:.0f}")
        elif op == 'lineTo':
            out.append(f"L {args[0][0]:.0f},{args[0][1]:.0f}")
        elif op == 'closePath':
            out.append("Z")
    return " ".join(out)

for char in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
    print(f"Char '{char}': {dump_glyph_shape(char)}")
