# 🌐 ETHERNIUM FONT v3.0

Este directorio contiene los archivos tipográficos definitivos y las interfaces interactivas listas para el usuario final.

---

## 📦 Contenido del Paquete

### Archivos de Fuente
- **`Ethernium_Sym.ttf`**: Fuente de escritorio TrueType. Haz doble clic para instalar (Windows/macOS).
- **`Ethernium_Sym.woff`** y **`Ethernium_Sym.woff2`**: Fuentes web comprimidas (WOFF2 = 52% compresión).
- **`Ethernium_Sym.flf`**: Fuente FIGlet para generar ASCII art en terminal.

### Interfaces Interactivas
- **`INSTALL.html`**: 📋 Guía de instalación visual con auto-detección de plataforma (Windows/macOS/Linux/Web).
- **`preview_font.html`**: 🔤 Mapa de caracteres completo + specimen waterfall + codepoint tooltips + click-to-copy.
- **`ascii_generator.html`**: ⌨️ Generador ASCII art interactivo — convierte texto a arte ASCII con múltiples estilos y colores.
- **`unicode_converter.html`**: ✨ Convertidor de texto Unicode para redes sociales (Discord, Twitter/X, Instagram).
- **`presentation_generator.html`**: 🎨 Generador visual premium de banners 1080p con estilo cyberpunk/neón.

### Recursos
- **`logo_emblem.png`**: Emblema rúnico circular oficial.
- **`glyph_atlas.png`**: Atlas visual de todos los glifos de la tipografía.
- **`build_report.json`**: Informe de validación del último build.

---

## 🚀 Instalación Rápida

### Escritorio (Windows/macOS)
1. Haz doble clic en **`Ethernium_Sym.ttf`**
2. Clic en **Instalar**
3. ¡Listo! Disponible como `Ethernium Sym` en Photoshop, Word, Figma, Illustrator, Premiere...

### Linux
```bash
cp Ethernium_Sym.ttf ~/.local/share/fonts/
fc-cache -fv
```

### Web (CSS)
```css
@font-face {
    font-family: 'Ethernium Sym';
    src: url('Ethernium_Sym.woff2') format('woff2'),
         url('Ethernium_Sym.woff') format('woff');
    font-weight: normal;
    font-style: normal;
    font-display: swap;
}

.ethernium-text {
    font-family: 'Ethernium Sym', sans-serif;
    font-size: 2.5rem;
    letter-spacing: 0.1em;
}
```

### ASCII Art (Terminal/Discord)
```
 .=%@#:.  *@%%%%@@  =@@- -@@+
 #@=:+#-  ==-@@+-*  :@@:.:@@:
 #@..-.      %@-    -@@. .@@-
 #@#%+..  ...@@=..  -@@###@@-
 #@#%=    . .@@- .  -@@*+*@@-
 #@..=-.  . .@@- .  -@@: .@@-
 #@=-##-  . .@@- .  -@@-.:@@-
 :=%#=    . :@@+..  -@@- -@@=
```

---

## 🔬 Especificaciones Técnicas

| Propiedad | Valor |
|-----------|-------|
| Formato | TrueType (TTF) + WOFF/WOFF2 + FIGlet |
| UPM | 1024 |
| Peso | Regular (400) |
| Cobertura | ASCII completo (95 chars) + 10 símbolos especiales |
| Kerning | Legacy kern table (21+ pares) |
| Tablas | cmap, glyf, gasp, kern, OS/2 (cap/x-height), name |
| Tamaño TTF | ~13 KB |
| Tamaño WOFF2 | ~7 KB (52% compresión) |
| Validación | Grade A+ |
