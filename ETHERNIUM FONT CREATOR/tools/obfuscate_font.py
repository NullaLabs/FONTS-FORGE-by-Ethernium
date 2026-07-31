"""
Ethernium Sym — Dynamic Web Font Obfuscator & DRM Scrambler
───────────────────────────────────────────────────────────
Protects web fonts against theft. Scrambles the binary 'cmap' table
by mapping standard characters to random Private Use Area (PUA) codepoints
and generates a client-side JavaScript translator mapping dictionary.
"""
import random
import sys
from pathlib import Path
from fontTools.ttLib import TTFont

def obfuscate(ttf_path: Path, output_path: Path, js_path: Path):
    if not ttf_path.exists():
        print(f"Error: Source font not found at {ttf_path}")
        return
        
    font = TTFont(str(ttf_path))
    cmap_table = font["cmap"]
    
    # 1. Extract best cmap
    best_cmap = font.getBestCmap()
    if not best_cmap:
        print("Error: Could not retrieve best cmap from font.")
        return
        
    # 2. Build scrambled map
    # We will map each standard printable character (32 to 126) to a unique PUA codepoint (0xE000 to 0xF8FF)
    pua_start = 0xE000
    pua_pool = list(range(pua_start, pua_start + 1000))
    # Keep it deterministic but scrambled per run using a seed if desired, or randomized
    random.seed(42) # Seed to keep mappings stable but scrambled
    random.shuffle(pua_pool)
    
    mapping = {}
    js_map = {}
    
    # Reverse lookup for cmap reconstruction
    new_cmap = {}
    
    pua_idx = 0
    for code, gname in sorted(best_cmap.items()):
        # Scramble printable ASCII
        if 32 <= code <= 126:
            scrambled_code = pua_pool[pua_idx]
            pua_idx += 1
            
            new_cmap[scrambled_code] = gname
            
            # For JavaScript mapper
            mapping[chr(code)] = chr(scrambled_code)
            js_map[chr(code)] = format(scrambled_code, 'x')
        else:
            # Keep special characters, notdef, and null chars unchanged
            new_cmap[code] = gname
            
    # 3. Update the cmap tables inside the font
    # Remove existing tables and compile a new format 4/12 subtable
    from fontTools.ttLib.tables._c_m_a_p import cmap_format_4
    
    # Rebuild cmap object
    cmap_table.tables = []
    
    # Format 4 (standard platform 3 encoding 1)
    subtable = cmap_format_4(4)
    subtable.platformID = 3
    subtable.platEncID = 1
    subtable.language = 0
    subtable.cmap = new_cmap
    cmap_table.tables.append(subtable)
    
    # Save the scrambled font
    font.save(str(output_path))
    print(f"Obfuscated TTF font saved: {output_path.name}")
    
    # Build woff/woff2 if formats exist
    try:
        for flavor, ext in (("woff", ".woff"), ("woff2", ".woff2")):
            out = output_path.with_suffix(ext)
            font.flavor = flavor
            font.save(str(out))
            print(f"Obfuscated {flavor.upper()} saved: {out.name}")
    except Exception as e:
        print(f"Note: Could not save web formats: {e}")
        
    # 4. Generate the beautiful JavaScript DRM mapper file
    js_content = f"""/**
 * Ethernium DRM — Web Font Decryption Mapper
 * ──────────────────────────────────────────
 * Automatically translates standard strings into their scrambled PUA equivalents
 * on the fly, rendering text correctly using the obfuscated Ethernium font,
 * while preventing scraping and direct copy-paste font theft.
 */
const ETHERNIUM_DRM_MAP = {dict_to_js_str(mapping)};

/**
 * Encrypts standard text into scrambled PUA codepoints.
 * @param {{string}} text - The clean input text.
 * @returns {{string}} - The scrambled text mapped to the DRM font.
 */
function encryptEtherniumText(text) {{
    return text.split('').map(char => {{
        return ETHERNIUM_DRM_MAP[char] || char;
    }}).join('');
}}

/**
 * Scrambles all HTML elements marked with class "ethernium-drm-text".
 */
function applyEtherniumDRM() {{
    const elements = document.querySelectorAll('.ethernium-drm-text');
    elements.forEach(el => {{
        if (!el.dataset.drmActive) {{
            el.dataset.originalText = el.textContent;
            el.textContent = encryptEtherniumText(el.textContent);
            el.dataset.drmActive = 'true';
        }}
    }});
}}

// Apply DRM on page load
window.addEventListener('DOMContentLoaded', applyEtherniumDRM);
"""
    js_path.write_text(js_content, encoding="utf-8")
    print(f"JavaScript DRM mapper saved: {js_path.name}")
    print("----------------------------------------------------------------------")
    print("Web Integration Guide:")
    print("  1. Load the obfuscated font in CSS (uses Private Use Area glyphs).")
    print("  2. Add the class 'ethernium-drm-text' to your HTML elements.")
    print("  3. Include the generated javascript mapper to decrypt on-the-fly.")
    print("  4. If someone copies the text or downloads the font, they get scrambled PUA gibberish!")

def dict_to_js_str(d: dict) -> str:
    import json
    return json.dumps(d, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Obfuscate a font's character map for dynamic web deployment DRM.")
    parser.add_argument("ttf_path", nargs="?", default="Ethernium_Sym.ttf", help="Path to TTF font file")
    args = parser.parse_args()
    
    root = Path(__file__).resolve().parent.parent
    ttf = Path(args.ttf_path)
    if not ttf.is_absolute():
        ttf = root / ttf
        
    out_ttf = ttf.parent / f"{ttf.stem}_obfuscated.ttf"
    js_file = ttf.parent / "ethernium_drm.js"
    
    print("======================================================================")
    print("           ETHERNIUM FORENSICS — WEB FONT OBFUSCATOR & DRM")
    print("======================================================================")
    print(f"Scrambling binary tables of: {ttf.name}...")
    
    obfuscate(ttf, out_ttf, js_file)
    print("======================================================================")
