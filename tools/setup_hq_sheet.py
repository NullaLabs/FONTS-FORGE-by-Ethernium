"""Copy an external HQ specimen PNG into the project as ethernium_sheet_hq.png."""
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEST = ROOT / "ethernium_sheet_hq.png"


def main():
    if len(sys.argv) < 2:
        print("Usage: python tools/setup_hq_sheet.py RUTA_A_TU_IMAGEN.png")
        sys.exit(1)
    src = Path(sys.argv[1])
    if not src.is_file():
        print(f"Not found: {src}")
        sys.exit(1)
    shutil.copy2(src, DEST)
    print(f"Copied -> {DEST}")
    print("Edit configs/ethernium.json: set reference_height to image height if not 682.")
    print("Then: python build_ethernium.py")


if __name__ == "__main__":
    main()
