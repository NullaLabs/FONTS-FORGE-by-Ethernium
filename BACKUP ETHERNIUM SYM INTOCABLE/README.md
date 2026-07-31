# Ethernium Sym + Font Forge

Proyecto de fuente **Ethernium Sym** y un sistema reutilizable **`font_forge`** para crear fuentes desde hojas de glifos (PNG).

## ¿Se puede usar para otras fuentes?

**Sí.** `font_forge` es independiente de Ethernium:

1. Diseñas una hoja PNG con filas de caracteres (izquierda → derecha).
2. Copias `configs/template.json` y ajustas coordenadas Y, baseline y lista de caracteres por fila.
3. Ejecutas el build → obtienes `.ttf`, `.woff`, `.woff2`.

## Estructura

```
ETHERNIUM SYM/
├── font_forge/          # Motor genérico sheet → fuente
│   ├── core.py          # Pipeline (binarizado, contornos, snap 45°, simetría)
│   ├── config.py
│   └── __main__.py      # CLI
├── configs/
│   ├── ethernium.json   # Proyecto Ethernium
│   └── template.json    # Plantilla para nuevas fuentes
├── build_ethernium.py   # Atajo Ethernium
├── ethernium_sheet.png  # Hoja de glifos (requerida)
└── preview_font.html
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
