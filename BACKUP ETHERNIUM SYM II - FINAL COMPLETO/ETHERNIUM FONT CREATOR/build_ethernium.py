"""Build Ethernium Sym using the generic font_forge system."""
from font_forge.config import load_config
from font_forge.core import SheetToFontBuilder
from pathlib import Path

ROOT = Path(__file__).resolve().parent

if __name__ == "__main__":
    config = load_config(ROOT / "configs" / "ethernium.json")
    SheetToFontBuilder(config, ROOT).build()
    print("Open preview_font.html to review.")
