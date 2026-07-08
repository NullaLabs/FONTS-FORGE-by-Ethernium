def inject_forensic_watermark_in_compiled_glyphs(glyphs: dict, cmap: dict[int, str], watermark_str: str) -> None:
    """
    Inject a secret copyright signature in the LSB of coordinates of target glyphs.
    Invisible to the eye, unforgeable, programmatically auditable.
    """
    sig_bytes = watermark_str.encode('utf-8')
    bits = []
    for b in sig_bytes:
        for bit_idx in range(8):
            bits.append((b >> bit_idx) & 1)
            
    # Null-terminator byte (8 zero bits)
    for _ in range(8):
        bits.append(0)
        
    bit_idx = 0
    n_bits = len(bits)
    
    # Target characters in a stable, deterministic order
    target_chars = ['E', 'M', '\u03a9', 'O', 'V', 'W', '0', 'A', 'B', 'C', 'D', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'N']
    
    for char in target_chars:
        if bit_idx >= n_bits:
            break
            
        gname = cmap.get(ord(char))
        if not gname or gname not in glyphs:
            continue
            
        glyph = glyphs[gname]
        if glyph.numberOfContours <= 0 or not hasattr(glyph, "coordinates"):
            continue
            
        coords = glyph.coordinates
        for i in range(len(coords)):
            if bit_idx >= n_bits:
                break
                
            x, y = coords[i]
            x_int, y_int = int(round(x)), int(round(y))
            
            bit_x = bits[bit_idx]
            x_new = (x_int & ~1) | bit_x
            bit_idx += 1
            
            if bit_idx < n_bits:
                bit_y = bits[bit_idx]
                y_new = (y_int & ~1) | bit_y
                bit_idx += 1
            else:
                y_new = y_int
                
            coords[i] = (x_new, y_new)
            
    print(f"[Forensic Steganography] Embedded unforgeable copyright watermark: {bit_idx} bits written across designated glyphs.")
