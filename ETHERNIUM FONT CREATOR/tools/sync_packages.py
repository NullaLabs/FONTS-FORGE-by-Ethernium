"""
Sync Packages Tool
──────────────────
Automatically synchronizes the root development files into the release packages:
1. ETHERNIUM FONT (the client-facing installable package)
2. ETHERNIUM FONT CREATOR (the developer-facing compiler toolkit)
"""
import shutil
from pathlib import Path

def sync():
    root = Path(__file__).resolve().parent.parent
    font_pkg = root / "ETHERNIUM FONT"
    creator_pkg = root / "ETHERNIUM FONT CREATOR"

    # Create directories if they don't exist
    font_pkg.mkdir(exist_ok=True)
    creator_pkg.mkdir(exist_ok=True)

    print("========================================")
    # 1. Syncing ETHERNIUM FONT
    print("Syncing release package 'ETHERNIUM FONT'...")
    font_files = [
        "Ethernium_Sym.ttf",
        "Ethernium_Sym.woff",
        "Ethernium_Sym.woff2",
        "Ethernium_Sym.flf",
        "INSTALL.html",
        "LICENSE.txt",
        "ascii_generator.html",
        "build_report.json",
        "logo_emblem.png",
        "presentation_generator.html",
        "preview_font.html",
        "unicode_converter.html",
    ]
    for f in font_files:
        src = root / f
        if src.is_file():
            shutil.copy2(src, font_pkg / f)
            print(f"  Copied {f}")

    # Copy atlas if exists
    atlas = root / "tools" / "glyph_atlas.png"
    if atlas.is_file():
        shutil.copy2(atlas, font_pkg / "glyph_atlas.png")
        print("  Copied tools/glyph_atlas.png -> glyph_atlas.png")

    # Font package specific README
    src_readme = font_pkg / "README.md"
    if not src_readme.is_file() and (root / "README.md").is_file():
        shutil.copy2(root / "README.md", src_readme)

    # 2. Syncing ETHERNIUM FONT CREATOR
    print("\nSyncing developer package 'ETHERNIUM FONT CREATOR'...")
    creator_files = [
        "LICENSE.txt",
        "build.bat",
        "build_ethernium.py",
        "build_report.json",
        "requirements.txt",
        "ethernium_sheet.png",
        "ethernium_sheet_hq.png",
    ]
    for f in creator_files:
        src = root / f
        if src.is_file():
            shutil.copy2(src, creator_pkg / f)
            print(f"  Copied {f}")

    # Copy subdirectories for Creator
    subdirs = ["configs", "font_forge", "tools"]
    for d in subdirs:
        src_dir = root / d
        dst_dir = creator_pkg / d
        if src_dir.is_dir():
            if dst_dir.is_dir():
                shutil.rmtree(dst_dir)
            shutil.copytree(src_dir, dst_dir, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".git"))
            print(f"  Synchronized subdirectory: {d}/")

    # Copy the custom developer README
    creator_readme_src = root / "README_CREATOR.md"
    if not creator_readme_src.is_file() and (creator_pkg / "README_CREATOR.md").is_file():
        creator_readme_src = creator_pkg / "README_CREATOR.md"
    
    if creator_readme_src.is_file():
        shutil.copy2(creator_readme_src, creator_pkg / "README.md")
        print("  Copied README_CREATOR.md -> README.md (Release)")

    print("========================================")
    print("Package synchronization complete!")

if __name__ == "__main__":
    sync()
