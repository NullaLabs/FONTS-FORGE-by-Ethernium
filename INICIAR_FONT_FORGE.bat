@echo off
title Font Forge Studio :: Ethernium / NullaLabs
cd /d "%~dp0"

echo ========================================================================
echo    FONTS FORGE STUDIO :: Ethernium Sovereign Typography Suite
echo    Transforma cualquier imagen o abecedario en fuentes perfectas (TTF/WOFF2)
echo ========================================================================
echo.

if exist "dist\FONTS-FORGE.exe" (
    echo [OK] Ejecutando binario autonomo de alta velocidad...
    "dist\FONTS-FORGE.exe"
    exit /b 0
)

where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Python no fue encontrado en el PATH del sistema.
    echo Instala Python 3.10+ o compila el binario independiente con tools/build_standalone.py.
    pause
    exit /b 1
)

echo Iniciando servidor local en http://127.0.0.1:8730 ...
echo Abriendo estudio en tu navegador predeterminado...
echo.

python -m font_forge studio --port 8730
pause
