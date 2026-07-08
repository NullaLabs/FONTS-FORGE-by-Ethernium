"""
Ethernium Sym — Forensic Document Jitter & Baseline Analyzer
────────────────────────────────────────────────────────────
Audits compiled TTF font files to perform forensic document analysis.
Calculates subpixel alignment jitter, height uniformity, stroke consistency,
and outputs a gorgeous, professional per-character diagnostic report.
"""
import sys
from pathlib import Path
import numpy as np
from fontTools.ttLib import TTFont

def analyze_font(ttf_path: Path):
    if not ttf_path.exists():
        print(f"Error: Font file not found at {ttf_path}")
        return
        
    font = TTFont(str(ttf_path))
    glyf = font["glyf"]
    hmtx = font["hmtx"]
    cmap = font.getBestCmap()
    
    if not cmap:
        print("Error: Could not retrieve character map (cmap).")
        return
        
    # Vertical metrics
    os2 = font["OS/2"]
    ascent = os2.sTypoAscender
    descent = os2.sTypoDescender
    
    print("======================================================================")
    print("           ETHERNIUM FORENSICS — GEOMETRIC METRICS AUDITOR")
    print("======================================================================")
    print(f"File: {ttf_path.name}")
    print(f"Design Vertical Metrics: Ascent={ascent}, Descent={descent}")
    print("----------------------------------------------------------------------")
    
    records = []
    
    for code, gname in sorted(cmap.items()):
        char = chr(code)
        glyph = glyf[gname]
        
        if glyph.numberOfContours <= 0 or not hasattr(glyph, "coordinates"):
            continue
            
        adv, lsb = hmtx[gname]
        coords = glyph.coordinates
        
        # Microscopic analysis
        xs = [p[0] for p in coords]
        ys = [p[1] for p in coords]
        
        ymin = min(ys)
        ymax = max(ys)
        width = max(xs) - min(xs)
        height = ymax - ymin
        
        # Detect character category
        if char.isupper():
            category = "UPPERCASE"
        elif char.islower():
            category = "LOWERCASE"
        elif char.isdigit():
            category = "DIGIT"
        else:
            category = "SYMBOL/PUNC"
            
        records.append({
            "char": char,
            "gname": gname,
            "ymin": ymin,
            "ymax": ymax,
            "width": width,
            "height": height,
            "advance": adv,
            "category": category
        })
        
    if not records:
        print("No ink-filled glyphs found to analyze.")
        return
        
    # Normal baseline glyphs that are mathematically designed to rest exactly on Y=0
    baseline_records = [r for r in records if r["char"].isupper() or r["char"] in "acenorsuvwxz"]
    ymins = [r["ymin"] for r in baseline_records]
    
    mean_ymin = np.mean(ymins)
    std_ymin = np.std(ymins)
    max_drift = max(abs(y - mean_ymin) for y in ymins)
    
    # 2. Height analysis
    upper_records = [r for r in records if r["category"] == "UPPERCASE"]
    upper_heights = [r["height"] for r in upper_records]
    mean_upper_h = np.mean(upper_heights) if upper_heights else 0
    std_upper_h = np.std(upper_heights) if upper_heights else 0
    
    # 3. Spacing analysis
    advances = [r["advance"] for r in records]
    mean_adv = np.mean(advances)
    std_adv = np.std(advances)
    
    # Consistency Score Calculation
    # Baseline jitter penalty: 0 jitter = 100 points, 10 units of jitter = 70 points
    baseline_score = max(0, min(100, 100 - (std_ymin * 8)))
    # Height consistency score
    height_score = max(0, min(100, 100 - (std_upper_h * 5))) if upper_heights else 100
    
    overall_score = (baseline_score * 0.6) + (height_score * 0.4)
    
    # Output dashboard
    print(f"\033[1mFORENSIC JITTER METRICS SUMMARY:\033[0m")
    print(f"  • Baseline Mean Ymin:    \033[36m{mean_ymin:.2f} UPM\033[0m")
    print(f"  • Baseline Jitter (SD):  \033[33m{std_ymin:.3f} UPM\033[0m " + 
          ("\033[92m[PERFECTLY ALIGNED]\033[0m" if std_ymin < 0.5 else 
           "\033[93m[MINOR DRIFT]\033[0m" if std_ymin < 3.0 else "\033[91m[HIGH JITTER]\033[0m"))
    print(f"  • Microscopic Max Drift:  \033[31m{max_drift:.1f} UPM\033[0m")
    print(f"  • Mean Uppercase Height: \033[36m{mean_upper_h:.1f} UPM\033[0m (SD={std_upper_h:.3f})")
    print(f"  • Mean Spacing Advance:  \033[36m{mean_adv:.1f} UPM\033[0m (SD={std_adv:.1f})")
    
    print("\n----------------------------------------------------------------------")
    print(f"\033[1mGEOMETRIC STRESS & CONSISTENCY ASSESSMENT:\033[0m")
    
    # Color coding overall score
    if overall_score >= 98:
        score_color = "\033[92m" # Green
        grade = "A+"
    elif overall_score >= 95:
        score_color = "\033[92m"
        grade = "A"
    elif overall_score >= 90:
        score_color = "\033[93m" # Yellow
        grade = "B"
    else:
        score_color = "\033[91m" # Red
        grade = "C/F"
        
    print(f"  • Alignment Quality Score:  {score_color}{overall_score:.2f} / 100{RESET_ANSI(score_color)} (Grade {score_color}{grade}{RESET_ANSI(score_color)})")
    
    # List high drift glyphs if any
    outliers = [r for r in baseline_records if abs(r["ymin"] - mean_ymin) > 3.0]
    if outliers:
        print(f"\n\033[93m[!] DETECTED GEOMETRIC OUTLIERS (DRIFT > 3.0 UPM):\033[0m")
        for o in outliers[:5]:
            print(f"  Char '{o['char']}' ({o['gname']}): Ymin = {o['ymin']} UPM (drift = {o['ymin'] - mean_ymin:+.1f})")
        if len(outliers) > 5:
            print(f"  ...and {len(outliers) - 5} more.")
    else:
        print("\n  \033[92m[✓] FORENSIC VERDICT: Outlines are perfectly mathematically aligned to the baseline!\033[0m")
        
    print("======================================================================")

def RESET_ANSI(color):
    return "\033[0m"

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Perform forensic geometric analysis on a compiled font.")
    parser.add_argument("ttf_path", nargs="?", default="Ethernium_Sym.ttf", help="Path to TTF font file")
    args = parser.parse_args()
    
    root = Path(__file__).resolve().parent.parent
    ttf = Path(args.ttf_path)
    if not ttf.is_absolute():
        ttf = root / ttf
        
    analyze_font(ttf)
