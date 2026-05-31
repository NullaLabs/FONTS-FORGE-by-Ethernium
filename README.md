# Ethernium Sym + Font Forge

Este proyecto ha sido organizado y empaquetado de forma profesional en dos carpetas independientes:

1. **[ETHERNIUM FONT](file:///C:/Users/esenc/OneDrive/Documentos/Escritorio/ETHERNIUM%20SYM/ETHERNIUM%20FONT)**: Contiene los archivos finales de la tipografía instalable (`.ttf`, `.woff`, `.woff2`), convertidores de texto y generadores de presentación para el usuario.
2. **[ETHERNIUM FONT CREATOR](file:///C:/Users/esenc/OneDrive/Documentos/Escritorio/ETHERNIUM%20SYM/ETHERNIUM%20FONT%20CREATOR)**: Contiene el motor `font_forge` y todas las herramientas de compilación/calibración para crear nuevas tipografías desde especímenes PNG.

Consulta el archivo `README.md` dentro de cada carpeta para ver las instrucciones específicas.

---

## Estructura de Desarrollo Original (Ahora en Creador)

```
ETHERNIUM SYM/
├── ETHERNUM FONT/            # Carpeta de fuente e interfaces finales
├── ETHERNUM FONT CREATOR/    # Carpeta del compilador y assets de desarrollo
```

## Generar Ethernium Sym

```bash
pip install -r requirements.txt
python build_ethernium.py
```

O:

```bash
python -m font_forge configs/ethernium.json
```

**Hoja HQ:** guarda tu imagen upscaled como `ethernium_sheet_hq.png` o `ethernium_sheet.png` en esta carpeta. Si la altura no es 682px, el sistema escala las filas automáticamente (`reference_height`).

## Crear otra fuente (ejemplo)

1. `cp configs/template.json configs/mi_fuente.json`
2. Edita `sheet`, `output_basename`, `rows` (y1, y2, baseline, chars).
3. Pon `mi_glyph_sheet.png` en la carpeta.
4. `python -m font_forge configs/mi_fuente.json`

## Pipeline v2.2 (trazo de calidad)

| Paso | Qué hace |
|------|----------|
| Upscale auto | 1× si la hoja ya es grande; 2×/4× si es pequeña |
| Otsu + mediana | Bordes más nítidos que blur + umbral fijo |
| Snap 45° | Ángulos geométricos más rectos (como la referencia) |
| Simetría 90 % | M, O, Ω… sin deformar el dibujo |
| CCOMP | Huecos en O, 0, 8, @… |

## Herramientas (`tools/`)

| Script | Uso |
|--------|-----|
| `python tools/debug_rows.py` | Genera `tools/sheet_rows_debug.png` con las cajas de cada fila |
| `python tools/calibrate_sheet.py` | Detecta bandas Y y sugiere coordenadas para un JSON nuevo |
| `python tools/export_atlas.py` | Atlas visual `tools/glyph_atlas.png` desde el TTF |
| `python tools/setup_hq_sheet.py imagen.png` | Instala hoja HQ como `ethernium_sheet_hq.png` |
| `build.bat` | Instala deps, build, debug y atlas en un clic |

**Hoja HQ:** coloca `ethernium_sheet_hq.png` en la raíz (prioridad sobre `ethernium_sheet.png`). No uses `Ethernium_Sym.otf` antiguo; solo TTF/WOFF2 del build actual.

## Vista previa

Abre `preview_font.html` en el navegador. Muestra estado del build leyendo `build_report.json`.

## Límites actuales

- La hoja debe ser **grid por filas** (no tipografía variable ni kerning manual).
- Kerning, pesos (Bold) y hinting requieren edición en Glyphs/FontForge o ampliar el motor.
- Para calzar **exactamente** una referencia visual, ajusta `reference_height` y las Y de cada fila en el JSON.
