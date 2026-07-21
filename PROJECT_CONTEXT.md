# Project Context

## Purpose

Font Forge converts a raster specimen sheet - an image of an alphabet, symbol
set or sign list - into an OpenType font. It targets sheets laid out as rows of
glyphs read left to right.

## Architecture

The build path is deterministic and config-driven. A config states, in
reference pixels, where each row sits and where its baseline falls; the engine
consumes that and emits `.ttf`, `.woff` and `.woff2` plus a build report.

| Module | Responsibility |
| :--- | :--- |
| `font_forge/core.py` | Build orchestration: rows to glyphs, metrics, kerning, output |
| `font_forge/vision.py` | Raster stage: binarization, row cropping, box extraction |
| `font_forge/vector.py` | Outline stage: sub-pixel refinement, RDP, extrema constraints |
| `font_forge/watermark.py` | Forensic signature embedded in coordinate low bits |
| `font_forge/autodetect.py` | Measures an unannotated sheet and emits a config |
| `font_forge/studio.py` | Local HTTP front end over the detector; stdlib only |
| `font_forge/config.py` | Config loading and reference-resolution scaling |

`autodetect` does not build fonts. It measures a sheet and writes a config that
the same engine consumes, so a studio session and a headless build produce
identical output and any font made interactively remains reproducible.

## Detection method

| Stage | Method |
| :--- | :--- |
| Polarity | Border luminance against image mean; alpha used only on genuinely cut-out images |
| Deskew | `minAreaRect` over all ink, applied between 0.2 and 15 degrees |
| Rows | Horizontal projection valleys, floor scaled to observed band heights |
| Glyph bounds | Connected components merged by an Otsu-derived gap threshold |
| Baseline | Dominant cluster of component bottom edges, so descenders do not bias it |
| Scale | `scale_base` derived from measured cap height against `TARGET_CAP_RATIO` |

When the caller supplies the character count for a row, that count is treated as
ground truth and the row is re-cut to match it exactly, which is what makes
scripts assembled from detached strokes tractable.

## Verification

| Gate | Command |
| :--- | :--- |
| Unit and pipeline tests | `pytest` |
| Fast subset | `pytest -m "not slow"` |
| Install audit | `pip install -e .` |
| Parity and doc immunity | `chronolith-pro check` |

Coverage spans the detector primitives in isolation, a regression guard that
rebuilds Ethernium Sym and compares it against the shipped font, end-to-end
builds across four writing systems (Latin, Runic, Alchemical, Sumero-Akkadian
cuneiform) with fidelity measured against the source typefaces, and the studio
HTTP contract driven over real sockets.

## Known limitations

- `TARGET_CAP_RATIO` normalizes every script to Latin cap proportions. Scripts
  whose signs share one height, cuneiform among them, render at roughly 0.83 of
  source scale. Outline fidelity is unaffected; override `scale_base` to change it.
- Row segmentation assumes left-to-right order and does not handle right-to-left
  or vertical layouts.
- Kerning is emitted as a legacy `kern` table only; there is no GPOS feature.
- Glyph names, `.notdef` fallbacks and the default kern pairs are still specific
  to the Ethernium face rather than driven by config.
