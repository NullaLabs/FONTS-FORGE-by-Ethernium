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

## Pipeline v4.0 (Trazado Determinista de Precisión)

| Paso | Qué hace |
|------|----------|
| Upscale auto | 1× si la hoja ya es grande; 2×/4× si es pequeña |
| Detección Sub-píxel | Muestreo bilineal en escala de grises para encontrar cruces exactos de umbral sin dientes de sierra. |
| Simplificación RDP | Algoritmo Ramer-Douglas-Peucker global a escala UPM para limpiar nodos redundantes. |
| Tangentes Extrema | Alineación forzada horizontal/vertical en los extremos cardinales (min/max X/Y) para curvas Bézier perfectas. |
| Snap Geométrico | Ángulos ajustables a 45°/90° para glifos rúnicos nítidos. |
| Simetría Ethernium | Espejado inteligente de contornos para glifos simétricos (M, O, Ω, etc.). |
| Marcas de Agua | Inyección esteganográfica de firma forense de autoría en el LSB de las coordenadas. |

## Arquitectura Modular (`font_forge/`)

El compilador ha sido refactorizado físicamente para aislar responsabilidades:
*   [**vision.py**](file:///E:/font%20forge%20by%20ethernium%202/font_forge/vision.py): Procesamiento de imagen y OpenCV (binarización, cuadrículas, filtros, morfología).
*   [**vector.py**](file:///E:/font%20forge%20by%20ethernium%202/font_forge/vector.py): Geometría Bézier, interpolación sub-píxel, simplificación RDP y restricciones de tangencia.
*   [**watermark.py**](file:///E:/font%20forge%20by%20ethernium%202/font_forge/watermark.py): Sistema de marcas de agua forenses legibles y deterministas.
*   [**core.py**](file:///E:/font%20forge%20by%20ethernium%202/font_forge/core.py): Orquestador minimalista y constructor de tablas OpenType (`gasp`, `kern`, `OS/2`).

## Herramientas (`tools/`)

| Script | Uso |
|--------|-----|
| `python tools/debug_rows.py` | Genera `tools/sheet_rows_debug.png` con las cajas de cada fila |
| `python tools/calibrate_sheet.py` | Detecta bandas Y y sugiere coordenadas para un JSON nuevo |
| `python tools/export_atlas.py` | Atlas visual `tools/glyph_atlas.png` desde el TTF |
| `python tools/forensic_analyzer.py` | Audita la inyección esteganográfica forense y extrae la firma del TTF |
| `build.bat` | Instala deps, build, debug y atlas en un clic |

## Vista previa

Abre `preview_font.html` en el navegador. Muestra el estado del build leyendo `build_report.json`.
