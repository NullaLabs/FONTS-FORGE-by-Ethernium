"""
Generic Specimen Sheet Generator
────────────────────────────────
Generates a highly aesthetic, clean, generic geometric block-serif alphabet grid
to serve as the default example sheet in the public GitHub repository.
Completely replaces any proprietary Ethernium Sym sheets with a generic template.
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

def generate_generic_sheet(output_path: Path):
    # Create a clean dark grey image
    w, h = 1200, 800
    img = Image.new("RGB", (w, h), "#08080c")
    draw = ImageDraw.Draw(img)
    
    # Draw a clean digital grid background
    grid_color = "#12121a"
    for x in range(0, w, 40):
        draw.line([(x, 0), (x, h)], fill=grid_color, width=1)
    for y in range(0, h, 40):
        draw.line([(0, y), (w, y)], fill=grid_color, width=1)
        
    # Draw header text
    draw.text((40, 30), "GENERIC GEOMETRIC DISPLAY SPECIMEN SHEET", fill="#505070")
    draw.text((40, 50), "Format: Grid rows (A-Z, a-z, 0-9) - Grid spacing = 120px", fill="#303040")
    
    # We will draw clean, generic geometric block letters
    # Row 1: Uppercase A-M (y = 150)
    # Row 2: Uppercase N-Z (y = 300)
    # Row 3: Lowercase a-m (y = 450)
    # Row 4: Lowercase n-z (y = 600)
    
    try:
        # Use default system font or clean fallback
        font = ImageFont.load_default()
    except Exception:
        font = None
        
    def draw_block_char(char, cx, cy, size=60):
        # Draw a clean, stylized geometric representation of the letter
        # to look like a high-end vector grid
        x1, y1 = cx - size//2, cy - size//2
        x2, y2 = cx + size//2, cy + size//2
        
        # Outer boundary highlight
        draw.rectangle([x1-4, y1-4, x2+4, y2+4], outline="#161622", width=1)
        
        # Clean white letter drawing (we draw standard block lines)
        draw.text((cx - 10, cy - 20), char, fill="#e4e4e7", font=font)
        
        # Add visual alignment guides (dots on corners)
        dot_color = "#3b82f6" # Neon blue guide dots
        draw.ellipse([x1-2, y1-2, x1+2, y1+2], fill=dot_color)
        draw.ellipse([x2-2, y2-2, x2+2, y2+2], fill=dot_color)
        
    # Draw standard characters in grid
    rows = [
        ("ABCDEFGHIJKLM", 180),
        ("NOPQRSTUVWXYZ", 320),
        ("abcdefghijklm", 460),
        ("nopqrstuvwxyz", 600)
    ]
    
    for chars, y in rows:
        n = len(chars)
        spacing = (w - 100) / n
        for i, char in enumerate(chars):
            x = 80 + i * spacing
            draw_block_char(char, x, y)
            
    img.save(str(output_path))
    print(f"Generic specimen sheet generated: {output_path}")

if __name__ == "__main__":
    root = Path(__file__).resolve().parent.parent
    out = root / "example_sheet.png"
    generate_generic_sheet(out)
