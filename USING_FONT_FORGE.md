# Using Font Forge — a builder's field guide

Written by the developer who took the pipeline to v4.0, from actually using it:
building a Latin font, then runic, alchemical and Sumero-Akkadian cuneiform
fonts from plain images. Every claim here has a command behind it.

---

## What it is

Font Forge turns an image of an alphabet into a real OpenType font (`.ttf`,
`.woff`, `.woff2`). Drop a picture of letters, symbols or signs laid out in
rows; get a font whose glyphs are traced from those shapes.

There are two ways in, and they share one engine:

```
                 ┌─ studio (drag image, correct, build) ─┐
   your image ─→ ┤                                        ├─→ config.json ─→ engine ─→ font
                 └─ autodetect + CLI (headless) ──────────┘
```

The studio never builds fonts itself. It measures your sheet, lets you fix what
it got wrong, and writes a `config.json` that the same engine consumes. So
anything you make interactively is reproducible headlessly — the config is the
source of truth, the image and the font are derived from it.

---

## Getting started

```bash
pip install -e .          # installs the `font-forge` command and deps
font-forge studio         # opens the drag-and-drop studio in your browser
```

That is the whole setup. No account, no key, no config to write by hand.

### The studio path (recommended for a first font)

1. **Drop an image.** Any alphabet, symbol set or specimen — PNG, JPG, WEBP, BMP.
   Black on white or white on black both work; polarity is detected.
2. **Read the overlay.** Cyan line = detected baseline. Dashed = row band. Boxes
   = detected glyphs. The count per row shows next to each.
3. **Type what each row spells,** in order, one row at a time. As you type, the
   tally goes green when your character count matches the detected glyph count,
   and the sheet is re-cut to match what you typed.
4. **Correct anything wrong.** Drag the baseline if it sits off. Edit the top /
   baseline / bottom numbers directly. Leave a row blank to skip it (titles,
   ornaments).
5. **Name the font and build.** You get a live preview rendered in your new
   font, plus download links for `.ttf`, `.woff`, `.woff2` and the `config.json`.

### The CLI path (for repeatable builds)

```bash
font-forge build my_config.json      # build from a config
font-forge build                     # build the bundled Ethernium Sym
```

A studio session leaves its `config.json` in `studio_out/`. Copy it anywhere,
edit it in a text editor, and `font-forge build` reproduces the font exactly.

---

## What it does well

**It measures instead of guessing.** The hard part of making a font from a sheet
used to be reading off, by hand, where every row sits and where each baseline
falls. The detector does that: rows from projection valleys, baselines from the
dominant cluster of glyph bottoms (so descenders don't drag them down), scale
from measured cap height. On the bundled Ethernium sheet its baselines land
within a pixel or two of the hand-authored config.

**It handles scripts far beyond Latin.** Verified end to end, with fidelity
measured against the source typefaces:

| Script | Glyphs | Aspect-ratio error (median) |
| :--- | :--- | :--- |
| Latin (A–Z, a–z, 0–9) | 62 | 0.4% |
| Elder Futhark runes | 24 | 0.3% |
| Alchemical symbols | 36 | 0.7% |
| Sumero-Akkadian cuneiform | 16 | 0.1% |

Cuneiform is the real test: each sign is several separate wedges, so counting
shapes finds far more pieces than signs. When you tell it a row has 8 signs, it
treats that as ground truth and re-cuts the row to match — which is what makes
those scripts work at all.

**The output is a real font.** Correct baselines and descenders, an `OS/2`
table, a `gasp` table for screen rendering, and — as of v4.0 — a kern table that
actually contains pairs (it never did before; see the developer notes).

**It is honest about reproducibility.** Because the studio emits a config, there
is no hidden state. Delete the font, keep the config and the sheet, rebuild
byte-for-byte.

---

## Feedback as a user

Things that worked, and things that would have saved me time.

**Good**
- The green/amber tally is the right feedback loop. You always know whether the
  machine and you agree on a row before you commit.
- The live preview in your own font, in the same page, closes the loop — you see
  the result without leaving the tool.
- Polarity and skew detection meant I never once had to pre-process an image.

**Friction**
- **No undo.** Drag a baseline wrong and you fix it by dragging back; there's no
  history. For fiddly rows this is nervy.
- **The character-to-glyph mapping is positional and invisible.** You type a
  string and trust that glyph 3 got character 3. When a row mis-segments there is
  no per-glyph view showing which shape became which character. On cuneiform I
  wanted to click a box and see its assigned sign.
- **Row skipping is implicit.** You skip a row by leaving it blank, which is
  discoverable only from the hint text. A visible "skip this row" toggle would
  be clearer.
- **No project reload.** You can't drop a `config.json` back into the studio to
  keep editing. Once you close the tab, further changes are text-editor work.
- **One font at a time.** The studio holds a single sheet in a single session.
  There's no batching a folder of sheets.

---

## Feedback as a developer

**What's well built**
- The outline stage is genuinely good: sub-pixel contour refinement against the
  grayscale, RDP simplification, and extrema constraints for clean Bézier
  tangents. This is more than most sheet-to-font hobby tools attempt.
- The modular split (`vision` raster, `vector` outline, `core` orchestration,
  `watermark`, `autodetect`, `studio`) is clean and testable.
- The steganographic watermark — copyright signature in coordinate low bits — is
  a real, auditable idea, now opt-in so it doesn't sign fonts that aren't yours.

**Bugs found while using it** (all fixed)
- **The kern table never compiled.** The build set `kern.subtables`, but
  fontTools compiles from `kern.kernTables`. Every release shipped a kern table
  with zero pairs while the code built 82. It looked like it worked because the
  table existed — it was just empty. This is the "code that never ran" failure
  mode: present, plausible, never verified.
- **Branding was compiled in.** Name records, `ETHN` vendor ID, the
  `SteveBlackbeard` watermark, geometric `$ ^ \` |` glyphs and the Latin kern
  pairs were all hardcoded, so every generic font — runic, cuneiform, anyone's —
  carried Ethernium's identity inside. Now all config-driven.
- **A cache-buster broke a route.** The studio client requests
  `/api/sheet.png?t=<timestamp>`; the server matched the raw path and returned
  404, so the canvas never rendered. Every Python-level test passed; only
  driving a real browser caught it.
- **Otsu understated separability on small samples.** Computing class means from
  histogram bin centres made genuinely bimodal gap sets look uniform, so evenly
  spaced letters got merged. Fixed by evaluating Otsu exactly over the sorted
  sample.
- **Fixed pixel clamps assumed UPM 1024.** The coordinate limits discarded
  legitimate descenders (dropping `y`) and mis-scaled non-1024 fonts. Now
  em-relative.

The common thread: **the defects lived in code that was never exercised.** The
outline maths, exercised on every build, was solid. The kern table, the branding
on non-Ethernium fonts, the studio route under a real browser — none had a test
or a user until now. The lesson the test suite encodes: build a thing, then make
something run it.

---

## What's missing

Ordered by how much it limits the tool today.

1. **Overlap removal.** Traced outlines can self-intersect where strokes cross.
   A `skia-pathops` union pass would make every glyph a clean filled region.
   Not yet done.
2. **Curve fitting proper.** Outlines are polygons approximated from the pixel
   contour, then smoothed. A Potrace-style corner-detection + curve-optimization
   pass (then `cu2qu` to quadratics) would remove the last of the stair-stepping
   without per-font epsilon tuning.
3. **Hinting.** No `ttfautohint` pass. At 12–16px — exactly where people preview
   — hinting is the single biggest quality lever, and it's absent.
4. **GPOS kerning.** Kerning is emitted as the legacy `kern` table only. Modern
   apps and browsers read GPOS; a `feaLib` feature would reach them.
5. **Script assumptions.** Left-to-right rows only. No right-to-left, no vertical
   layouts. `TARGET_CAP_RATIO` imposes Latin cap proportions, so uniform-height
   scripts (cuneiform) come out at ~0.83 of source scale — faithful in shape,
   smaller in size, overridable via `scale_base`.
6. **Studio round-trip.** Load a saved `config.json` back into the studio to keep
   editing (see user feedback).
7. **A per-glyph review grid** in the studio, so a mis-assigned sign is visible
   and clickable rather than inferred from a count.

---

## Verifying a change

```bash
pytest                      # 64 tests: detector units, Ethernium regression,
                            #   four writing systems, studio HTTP, de-branding
pytest -m "not slow"        # fast subset, no font builds
pip install -e .            # install audit — must build and expose `font-forge`
chronolith-pro check --strict   # DNA parity and doc immunity
```

A change is done when those are green. The regression suite rebuilds Ethernium
Sym and compares it glyph-for-glyph against the shipped font, so you find out
immediately if a change for one sheet altered the flagship face.

---

## Scorecard

| Dimension | Assessment |
| :--- | :--- |
| Concept | Strong — measure-don't-guess is the right idea, and it holds across scripts. |
| Outline quality | Good — sub-pixel + RDP + extrema is above its weight class. Missing overlap removal and hinting. |
| Reproducibility | Excellent — config is the source of truth, studio and CLI agree. |
| Genericness | Fixed in v4.0 — was Ethernium-specific inside; now truly generic. |
| Test coverage | Now real — 64 tests where there were none, including the bugs above as guards. |

The tool does the thing it claims and does the hard part — non-Latin scripts —
better than expected. Its weaknesses now are the classic last-mile font-quality
passes (overlap, curves, hinting), not correctness.
