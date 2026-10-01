"""
Standalone build script for FONTS-FORGE.
Builds a single-file portable Windows executable.
"""
import subprocess
import sys
from pathlib import Path
from PIL import Image

REPO_ROOT = Path(r"E:\font forge by ethernium 2").resolve()
ICON_PATH = REPO_ROOT / "icon.ico"
LOGO_PATH = REPO_ROOT / "logo_emblem.png"

# Ensure icon.ico exists
if not ICON_PATH.exists() and LOGO_PATH.exists():
    img = Image.open(LOGO_PATH).convert("RGBA")
    img.save(ICON_PATH, format="ICO", sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
    print(f"[+] Generado icono: {ICON_PATH}")

cmd = [
    sys.executable,
    "-m",
    "PyInstaller",
    "--noconfirm",
    "--onefile",
    "--name=FONTS-FORGE",
    f"--icon={ICON_PATH}",
    f"--add-data={REPO_ROOT / 'font_forge' / 'studio.html'};font_forge",
    "--hidden-import=fontTools",
    "--hidden-import=fontTools.ttLib",
    "--hidden-import=fontTools.pens.ttGlyphPen",
    "--hidden-import=brotli",
    "--hidden-import=cv2",
    "--hidden-import=numpy",
    "--hidden-import=PIL",
    str(REPO_ROOT / "font_forge" / "__main__.py"),
]

print("[*] Iniciando compilación PyInstaller...")
print(" ".join(cmd))
res = subprocess.run(cmd, cwd=REPO_ROOT)
if res.returncode == 0:
    exe_path = REPO_ROOT / "dist" / "FONTS-FORGE.exe"
    print(f"\n[OK] Compilación exitosa!")
    print(f"[+] Binario generado: {exe_path} ({exe_path.stat().st_size / (1024*1024):.2f} MB)")
else:
    print(f"\n[ERROR] Falló la compilación con código {res.returncode}")
    sys.exit(res.returncode)
