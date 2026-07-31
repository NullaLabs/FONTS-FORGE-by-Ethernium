# 🛠️ ETHERNIUM FONT CREATOR

Este directorio contiene el motor y las herramientas de compilación para crear tipografías vectoriales profesionales a partir de imágenes de espécimen (en formato PNG con rejilla de glifos organizados por filas).

Puedes reutilizar este sistema para construir cualquier nueva tipografía a partir de una hoja de dibujo.

---

## 📂 Estructura del Creador

- **`font_forge/`**: Código principal del compilador (binarización, anti-aliasing, trazado vectorial y compilación de tablas OpenType).
- **`configs/`**:
  - `template.json`: Plantilla de configuración limpia para nuevos proyectos.
  - `ethernium.json`: Configuración actual y calibración de Ethernium Sym.
- **`tools/`**: Scripts de utilidad para calibrar filas Y, inspeccionar contornos y generar atlas.
- **`build_ethernium.py`**: Script de acceso rápido para compilar Ethernium.
- **`build.bat`**: Script de procesamiento por lotes para Windows (instala dependencias, ejecuta el build y genera el atlas).
- **`requirements.txt`**: Librerías necesarias (`fonttools`, `opencv-python`, `numpy`, `pillow`).

---

## 🚀 Cómo Crear una Nueva Fuente en 4 Pasos

### Paso 1: Diseñar la Hoja de Glifos (PNG)
Diseña tu tipografía en un archivo de imagen (ej. `mi_fuente_sheet.png`). Organiza los caracteres de izquierda a derecha en filas uniformes (ej: Fila 1: A-Z, Fila 2: 0-9).

### Paso 2: Crear el Archivo de Configuración
Copia `configs/template.json` y renombralo como `configs/mi_fuente.json`. Edita las propiedades:
1. `"sheet"`: Nombre de tu archivo de imagen.
2. `"output_basename"`: Nombre final del archivo de fuente (ej. `MiFuente_Regular`).
3. `"rows"`: Agrega las filas que tiene tu hoja indicando:
   - `"name"`: Identificador de la fila (ej. "Mayúsculas").
   - `"y_start"` e `"y_end"`: Coordenadas Y superior e inferior que encierran a los glifos.
   - `"baseline"`: Línea base Y de alineación.
   - `"chars"`: Lista ordenada de caracteres tal y como aparecen en la fila.

> 💡 **Tip de calibración:** Si no sabes las coordenadas Y exactas de tus filas, ejecuta en terminal:
> `python tools/calibrate_sheet.py mi_fuente_sheet.png`
> Esto analizará la imagen y te sugerirá los límites Y de cada banda de tinta.

### Paso 3: Compilar la Fuente
Ejecuta la compilación llamando al módulo `font_forge` con tu archivo de configuración:
```bash
python -m font_forge configs/mi_fuente.json
```
Esto generará los archivos tipográficos definitivos en la raíz:
- `MiFuente_Regular.ttf` (OpenType TrueType)
- `MiFuente_Regular.woff` (Web Open Font Format)
- `MiFuente_Regular.woff2` (WOFF de segunda generación comprimida)

### Paso 4: Ajustar y Pulir
Puedes ajustar la vectorización y nitidez editando la sección `"pipeline"` de tu archivo JSON:
- `"contour_epsilon_factor"`: Regula la fidelidad de las curvas vectoriales.
  - Usa valores bajos (`0.001` a `0.0028`) para una **vectorización exacta y detallada**.
  - Usa valores más altos (`0.006` a `0.008`) para **suavizar imperfecciones** y simplificar trazos.
- `"lsb_offset"` y `"rsb_offset"`: Ajustan el espacio virtual a la izquierda y derecha de cada carácter para regular el espacio entre palabras.

---

## 🔬 Herramientas Incluidas (`tools/`)

- **Calibrar bandas Y:** `python tools/calibrate_sheet.py <tu_imagen.png>`
- **Visualizar límites de filas:** `python tools/debug_rows.py` (crea un mapa visual para validar que las coordenadas Y del JSON no corten las letras).
- **Auditoría de fuente:** `python tools/audit_font.py` (informa del total de glifos, métricas y advierte si algún caracter se está recortando).
