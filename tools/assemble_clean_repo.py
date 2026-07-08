"""
Assemble Clean Repository Utility
─────────────────────────────────
Creates a pristine, generic version of the Font Creator & Interactive Specimen
suite in a temporary directory, ready to overwrite the remote GitHub repo
so it only contains general tools and interfaces, with no Ethernium-specific
backups, compiled fonts, or development sheets.
"""
import shutil
import subprocess
from pathlib import Path

def run_cmd(cmd, cwd):
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd, encoding="utf-8")
    return res.returncode, res.stdout.strip(), res.stderr.strip()

def assemble():
    root = Path(__file__).resolve().parent.parent
    temp_dir = root / ".temp_git_assembly"

    print("========================================")
    print("ASSEMBLING PRISTINE TOOLKIT FOR GITHUB...")
    print("========================================")

    if temp_dir.exists():
        shutil.rmtree(temp_dir)
    temp_dir.mkdir()

    # 1. Copy font_forge engine
    print("[*] Copying font_forge compiler engine...")
    shutil.copytree(
        root / "font_forge", 
        temp_dir / "font_forge", 
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc")
    )

    # 2. Copy configs (only template.json)
    print("[*] Copying configurations...")
    configs_dst = temp_dir / "configs"
    configs_dst.mkdir()
    shutil.copy2(root / "configs" / "template.json", configs_dst / "template.json")

    # 3. Copy generic tools only
    print("[*] Copying generic tools...")
    tools_dst = temp_dir / "tools"
    tools_dst.mkdir()
    generic_tools = [
        "font_to_ascii.py",
        "validate_font.py",
        "audit_font.py",
        "calibrate_sheet.py",
        "debug_rows.py",
        "export_atlas.py",
        "generate_install_guide.py",
        "sync_packages.py",
        "assemble_clean_repo.py",
        "read_forensic_watermark.py",
        "forensic_analyzer.py",
        "obfuscate_font.py",
    ]
    for gt in generic_tools:
        src = root / "tools" / gt
        if src.is_file():
            shutil.copy2(src, tools_dst / gt)
            print(f"  Copied tools/{gt}")
    print("[*] Copying generic files and interfaces...")
    root_files = [
        "requirements.txt",
        "build.bat",
        "LICENSE.txt",
        "INSTALL.html",
        "ascii_generator.html",
        "presentation_generator.html",
        "preview_font.html",
        "unicode_converter.html",
        ".gitignore",
    ]
    for rf in root_files:
        src = root / rf
        if src.is_file():
            shutil.copy2(src, temp_dir / rf)
            print(f"  Copied {rf}")

    # Copy example sheet as example_sheet.png
    if (root / "ethernium_sheet.png").is_file():
        shutil.copy2(root / "ethernium_sheet.png", temp_dir / "example_sheet.png")
        print("  Copied ethernium_sheet.png -> example_sheet.png")

    # 5. Write a beautiful, premium generic README.md
    print("[*] Writing generic README.md...")
    readme_content = """# 🛠️ FONTS CREATOR & VISUALIZER SUITE

![Suite Example Sheet](example_sheet.png)

A professional, state-of-the-art toolkit to design, compile, and visualize custom vector fonts starting from simple hand-drawn or grid-based raster specimen sheets (PNG).

---

## ✨ Features

*   **Generic Raster-to-Vector Pipeline**: Automatically splits grid-based specimens into perfect character bounding boxes, extracts glyph contours, and converts them to vector formats.
*   **Geometric Snapping & Smoothing**: Features a configurable angle-snapping algorithm (e.g. 45° / 90° snapping) and morphological open/close edge filters to remove jaggies while keeping crisp details.
*   **Dual-Layer Symmetry Engine**: Mirror contours from left-to-right to ensure mathematically perfect symmetry at both vector sub-pixel and integer grid coordinates.
*   **Professional OpenType Tables**: Supports generating robust OS/2 vertical metrics, gasp screen-rendering hinting tables, copyright records, and customizable legacy format kerning maps.
*   **High-End Web & Terminal Previews**:
    *   **Interactive Font Specimen & Map (`preview_font.html`)**: Complete character grid with copy-to-clipboard, waterfall size specimen (12px to 72px), and CSS embedding.
    *   **Canvas-Based ASCII Art Generator (`ascii_generator.html`)**: Real-time canvas pixel parser mapping characters to gorgeous blocks, detail ramps, dots, and custom heights.
    *   **Specimen Presenter Canvas (`presentation_generator.html`)**: Premium presentation graphic card renderer to save showcase posters.
    *   **Runic & Special Symbol Unicode Map (`unicode_converter.html`)**.

---

## 🚀 How to Create Your Custom Font in 4 Steps

### Step 1: Draw Your Specimen Sheet
Draw or construct your font glyphs in a single PNG image (e.g., `my_sheet.png`). Organize your characters from left to right in rows (as shown in the visual example above).

### Step 2: Configure Your Project
Create a copy of `configs/template.json` named `configs/my_font.json`:
1. Define your filename under `"sheet"`.
2. Define the font properties inside `"font"` (copyright, familyName, styleName).
3. Calibrate your rows in `"rows"` specifying `y_start`, `y_end`, `baseline` and the ordered list of `chars`.

*Tip: If you don't know the exact Y coordinates of your rows, calibrate them automatically using:*
```bash
python tools/calibrate_sheet.py my_sheet.png
```

### Step 3: Run the Compiler
Compile the sheet to `.ttf`, `.woff` and `.woff2` formats using the `font_forge` module:
```bash
python -m font_forge configs/my_font.json
```

### Step 4: Preview and Deploy
Open `preview_font.html` in your browser to inspect the glyph grid, test sizes, and copy-paste character codes.

---

## 🔬 Developer Tools Included

*   **`tools/calibrate_sheet.py`**: Automated Y-bounds scanning and band suggestions.
*   **`tools/debug_rows.py`**: Visual verification overlay of coordinate slices.
*   **`tools/audit_font.py`**: Integrity verification of compiled vertical bounds and glyph ranges.
*   **`tools/validate_font.py`**: OpenType specification auditor (returns full pass/warn/fail reports).
*   **`tools/font_to_ascii.py`**: Converts text characters into high-resolution terminal ASCII banners.

---

## 📦 Requirements

Install the Python dependencies:
```bash
pip install -r requirements.txt
```
*Requires Python 3.8+ with `opencv-python`, `numpy`, `fonttools`, and `Pillow`.*

---

## 📄 License
This suite is open source and available under the [MIT License](LICENSE.txt).
"""
    (temp_dir / "README.md").write_text(readme_content, encoding="utf-8")
    print("  ✓ Created generic README.md".replace("✓", "OK"))

    # 6. Initialize git inside .temp_git_assembly
    print("\n[*] Initializing pristine local Git repository in temp directory...")
    run_cmd("git init", temp_dir)
    run_cmd("git checkout -b main", temp_dir)
    run_cmd("git config user.name \"Steve Blackbeard\"", temp_dir)
    run_cmd("git config user.email \"SteveBlackbeard@users.noreply.github.com\"", temp_dir)

    # 7. Add remote origin and push --force!
    print("[*] Adding remote origin...")
    remote_url = "https://github.com/SteveBlackbeard/FONTS-FORGE-by-Ethernium.git"
    run_cmd(f"git remote add origin {remote_url}", temp_dir)

    print("[*] Staging pristine files...")
    run_cmd("git add .", temp_dir)
    print("[*] Creating pristine release commit...")
    commit_msg = "feat: release generic Font Creator & Visualizer Suite - full compiler engine and interactive interfaces"
    code, out, err = run_cmd(f'git commit -m "{commit_msg}"', temp_dir)
    if code != 0:
        print(f"Error committing: {err}")
        return

    print("\n[*] READY FOR PUSH! Overwriting remote history with clean files...")
    print("    Running: git push --force -u origin main")
    
    # Run the force push securely clearing GITHUB_TOKEN
    import os
    env = os.environ.copy()
    env["GITHUB_TOKEN"] = ""
    res = subprocess.run("git push --force -u origin main", shell=True, cwd=temp_dir, env=env, capture_output=True, text=True, encoding="utf-8")
    
    if res.returncode == 0:
        print("\n========================================================")
        print("SUCCESS! Repository has been completely cleaned up!")
        print("  Only generic tools, engines, and interfaces are on Git.")
        print("========================================================")
    else:
        print(f"\n[!] Error pushing: {res.stderr}")

    # 8. Clean up temp folder
    shutil.rmtree(temp_dir)
    print("[*] Cleaned up local temporary directory.")

if __name__ == "__main__":
    assemble()
