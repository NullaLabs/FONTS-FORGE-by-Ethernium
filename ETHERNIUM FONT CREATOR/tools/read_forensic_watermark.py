"""
Ethernium Sym — Steganographic Watermark Decoder
────────────────────────────────────────────────
Forensic analysis utility that reads any TrueType (.ttf) font file,
extracts the least-significant bits (LSBs) of target glyph coordinates,
and decodes the secret, unforgeable digital signature copyright watermark.
"""
import sys
from pathlib import Path
from fontTools.ttLib import TTFont

def read_watermark(ttf_path: Path) -> str | None:
    if not ttf_path.exists():
        print(f"Error: Font file not found at {ttf_path}")
        return None
        
    font = TTFont(str(ttf_path))
    glyf = font["glyf"]
    cmap = font.getBestCmap()
    
    if not cmap:
        print("Error: Could not retrieve character map (cmap) from font.")
        return None
        
    bits = []
    
    # Target characters in the exact deterministic order
    target_chars = ['E', 'M', '\u03a9', 'O', 'V', 'W', '0', 'A', 'B', 'C', 'D', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'N']
    
    for char in target_chars:
        gname = cmap.get(ord(char))
        if not gname or gname not in glyf:
            continue
            
        glyph = glyf[gname]
        if glyph.numberOfContours <= 0 or not hasattr(glyph, "coordinates"):
            continue
            
        coords = glyph.coordinates
        for x, y in coords:
            # Extract LSB from X
            x_int = int(round(x))
            bits.append(x_int & 1)
            
            # Extract LSB from Y
            y_int = int(round(y))
            bits.append(y_int & 1)
            
    # Group bits into bytes
    decoded_bytes = bytearray()
    for i in range(0, len(bits), 8):
        byte_bits = bits[i:i+8]
        if len(byte_bits) < 8:
            break
            
        # Reconstruct byte
        b = 0
        for bit_idx in range(8):
            b |= (byte_bits[bit_idx] << bit_idx)
            
        if b == 0:
            # Null-terminator found, stop decoding
            break
        decoded_bytes.append(b)
        
    try:
        return decoded_bytes.decode('utf-8')
    except UnicodeDecodeError:
        return None

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Decode forensic steganographic watermark from a TTF font.")
    parser.add_argument("ttf_path", nargs="?", default="Ethernium_Sym.ttf", help="Path to TTF font file")
    args = parser.parse_args()
    
    root = Path(__file__).resolve().parent.parent
    ttf = Path(args.ttf_path)
    if not ttf.is_absolute():
        ttf = root / ttf
        
    print("======================================================================")
    print("           ETHERNIUM FORENSICS — WATERMARK DECODER")
    print("======================================================================")
    print(f"Analyzing binary coordinates of: {ttf.name}...")
    
    watermark = read_watermark(ttf)
    
    print("----------------------------------------------------------------------")
    if watermark:
        print(f"\033[92m[✓] FORENSIC DECODING SUCCESSFUL!\033[0m")
        print(f"\033[1mDecoded Steganographic Copyright Signature:\033[0m")
        print(f"  » \033[96m{watermark}\033[0m «")
    else:
        print("\033[91m[✗] FORENSIC WARNING: No valid steganographic watermark detected.\033[0m")
        print("    Either this is an unauthorized clone or the coordinates have been altered.")
    print("======================================================================")
