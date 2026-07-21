"""
Automatic sheet analysis: raster image -> font_forge config.

The build engine in ``core`` is deterministic but needs a config that states,
in reference pixels, where each row of glyphs lives and where its baseline
sits. Measuring that by hand is the whole manual cost of making a font.

This module measures it instead:

    image -> polarity -> deskew -> binarize -> rows -> glyphs -> baselines

The output is a *prepared sheet* (normalized so ink is bright, as the engine
expects) plus a config dict pointing at it. Builds stay reproducible: the
studio only writes the config, it never bypasses the engine.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

import cv2
import numpy as np

# --- tunables -----------------------------------------------------------
# Fractions are relative to row height or image size so they hold at any
# resolution; absolute pixel floors keep them sane on tiny inputs.

NOISE_AREA_FRACTION = 0.004   # component area vs row area, below = speckle
ROW_VALLEY_FRACTION = 0.012   # ink density that still counts as "inside a row"
MIN_ROW_HEIGHT_FRAC = 0.015   # of image height
CLUSTER_TOLERANCE_FRAC = 0.09  # of row height, for baseline/height clustering
MAX_DESKEW_DEG = 15.0
MIN_DESKEW_DEG = 0.2


@dataclass
class GlyphBox:
    x: int
    y: int
    w: int
    h: int

    @property
    def right(self) -> int:
        return self.x + self.w

    @property
    def bottom(self) -> int:
        return self.y + self.h


@dataclass
class RowAnalysis:
    index: int
    y_start: int
    y_end: int
    baseline: int
    x_height: int | None
    cap_height: int | None
    merge_gap: int
    max_merge_width: int
    boxes: list[GlyphBox] = field(default_factory=list)
    # Pre-merge components, kept so a row can be re-segmented against a known
    # character count without re-reading the image.
    raw_boxes: list[GlyphBox] = field(default_factory=list, repr=False)

    @property
    def glyph_count(self) -> int:
        return len(self.boxes)


@dataclass
class SheetAnalysis:
    width: int
    height: int
    inverted: bool
    deskew_angle: float
    threshold: int
    rows: list[RowAnalysis]

    def to_dict(self) -> dict[str, Any]:
        return {
            "width": self.width,
            "height": self.height,
            "inverted": self.inverted,
            "deskew_angle": round(self.deskew_angle, 3),
            "threshold": self.threshold,
            "rows": [
                {
                    **{k: v for k, v in asdict(row).items() if k != "raw_boxes"},
                    "glyph_count": row.glyph_count,
                }
                for row in self.rows
            ],
        }


# --- preprocessing ------------------------------------------------------


def load_ink_gray(path: Path) -> tuple[np.ndarray, bool]:
    """
    Load any image as a grayscale map where bright == ink.

    Returns (gray, inverted). Transparent PNGs use the alpha channel as the
    ink mask; otherwise polarity is inferred from the border, which in a
    specimen sheet is background by construction.
    """
    raw = cv2.imdecode(
        np.fromfile(str(path), dtype=np.uint8), cv2.IMREAD_UNCHANGED
    )
    if raw is None:
        raise ValueError(f"Cannot decode image: {path}")

    if raw.ndim == 3 and raw.shape[2] == 4:
        alpha = raw[:, :, 3]
        # Alpha is the ink mask only on a genuinely cut-out image. Opaque
        # sheets often carry a few near-transparent pixels from compression,
        # so require a real transparent region before trusting it.
        if float((alpha < 128).mean()) > 0.05:
            return alpha, False
        raw = raw[:, :, :3]

    if raw.ndim == 3:
        gray = cv2.cvtColor(raw, cv2.COLOR_BGR2GRAY)
    else:
        gray = raw

    if _is_dark_ink(gray):
        return cv2.bitwise_not(gray), True
    return gray, False


def _is_dark_ink(gray: np.ndarray) -> bool:
    """Ink is dark when the border (always background) is brighter than the mean."""
    h, w = gray.shape
    band = max(1, min(h, w) // 40)
    border = np.concatenate([
        gray[:band, :].ravel(),
        gray[-band:, :].ravel(),
        gray[:, :band].ravel(),
        gray[:, -band:].ravel(),
    ])
    return float(np.median(border)) > float(np.mean(gray))


def estimate_deskew(ink: np.ndarray) -> float:
    """Angle in degrees needed to level the sheet, 0 when already straight."""
    pts = cv2.findNonZero(ink)
    if pts is None or len(pts) < 50:
        return 0.0
    angle = cv2.minAreaRect(pts)[-1]
    if angle < -45:
        angle += 90
    elif angle > 45:
        angle -= 90
    if abs(angle) < MIN_DESKEW_DEG or abs(angle) > MAX_DESKEW_DEG:
        return 0.0
    return float(angle)


def apply_deskew(gray: np.ndarray, angle: float) -> np.ndarray:
    if angle == 0.0:
        return gray
    h, w = gray.shape
    matrix = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
    return cv2.warpAffine(
        gray, matrix, (w, h),
        flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_CONSTANT, borderValue=0,
    )


def binarize(gray: np.ndarray) -> tuple[np.ndarray, int]:
    """Otsu binarization; returns (mask, threshold) with ink == 255."""
    denoised = cv2.medianBlur(gray, 3)
    thresh, mask = cv2.threshold(
        denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
    )
    return mask, int(thresh)


# --- segmentation -------------------------------------------------------


def detect_rows(mask: np.ndarray) -> list[tuple[int, int]]:
    """Split the sheet into horizontal bands of ink via projection valleys."""
    projection = (mask > 0).sum(axis=1).astype(np.float32)
    if projection.max() == 0:
        return []

    # Smooth so that the gap between an 'i' and its dot is not read as a valley.
    kernel = max(3, int(mask.shape[0] * 0.004) | 1)
    smoothed = cv2.GaussianBlur(projection.reshape(-1, 1), (1, kernel), 0).ravel()

    cutoff = smoothed.max() * ROW_VALLEY_FRACTION
    inside = smoothed > cutoff

    bands: list[tuple[int, int]] = []
    start: int | None = None
    for y, is_ink in enumerate(inside):
        if is_ink and start is None:
            start = y
        elif not is_ink and start is not None:
            bands.append((start, y))
            start = None
    if start is not None:
        bands.append((start, len(inside)))

    if not bands:
        return []

    # Scale the noise floor to the bands actually present rather than to the
    # image, so a sheet of small rows is not thrown away wholesale.
    typical = float(np.median([b - a for a, b in bands]))
    min_height = max(3, int(min(typical * 0.35, mask.shape[0] * MIN_ROW_HEIGHT_FRAC)))
    return [(a, b) for a, b in bands if b - a >= min_height]


def _components(row_mask: np.ndarray) -> list[GlyphBox]:
    contours, _ = cv2.findContours(
        row_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )
    row_area = row_mask.shape[0] * row_mask.shape[1]
    min_area = max(4.0, row_area * NOISE_AREA_FRACTION * 0.01)

    boxes = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        if w * h < min_area:
            continue
        boxes.append(GlyphBox(x, y, w, h))
    return sorted(boxes, key=lambda b: b.x)


def otsu_1d(values: list[float]) -> tuple[float, float]:
    """
    Otsu's threshold on a 1D sample, with its separability score.

    Applied to inter-component gaps this separates the two natural
    populations - gaps *within* a glyph (the bar of an 'i', an umlaut) from
    gaps *between* glyphs - without any hand-tuned constant.

    Otsu splits *any* sample, including one that has no two populations to
    begin with, so the second return value is the separability ratio
    (between-class variance over total variance). Near 1 the split is real;
    low means the sample is one population and the threshold is meaningless.
    """
    if len(values) < 2:
        return (float(values[0]) if values else 0.0), 0.0

    data = np.sort(np.asarray(values, dtype=np.float64))
    lo, hi = data[0], data[-1]
    if hi - lo < 1e-9:
        return float(hi), 0.0

    # Evaluated exactly over the sorted sample rather than over a histogram.
    # Binning would compute class means from bin centres, which on the small
    # samples a row of glyphs produces understates the separation enough to
    # make a genuinely bimodal set look like one population.
    total = len(data)
    cumulative = np.cumsum(data)
    grand_total = cumulative[-1]

    best_threshold, best_variance = float(hi), -1.0
    for k in range(1, total):
        if data[k] == data[k - 1]:
            continue  # a split must fall between distinct values
        n0, n1 = k, total - k
        mu0 = cumulative[k - 1] / n0
        mu1 = (grand_total - cumulative[k - 1]) / n1
        variance = n0 * n1 * (mu0 - mu1) ** 2
        if variance > best_variance:
            best_variance = variance
            best_threshold = float((data[k - 1] + data[k]) / 2.0)

    if best_variance < 0:
        return float(hi), 0.0

    spread = float(data.var()) * total * total
    separability = (best_variance / spread) if spread > 0 else 0.0
    return best_threshold, min(1.0, separability)


# Below this separability the gap sample is a single population, meaning every
# gap separates glyphs and nothing should be merged.
BIMODAL_SEPARABILITY = 0.72


def _gaps_between(boxes: list[GlyphBox]) -> list[float]:
    return [float(max(0, nxt.x - cur.right)) for cur, nxt in zip(boxes, boxes[1:])]


def adaptive_merge_gap(boxes: list[GlyphBox]) -> int:
    """
    Largest gap that still belongs *inside* one glyph.

    Used when the row's character count is unknown; prefer
    ``solve_merge_gap`` whenever it is known, since that is exact.
    """
    if len(boxes) < 3:
        return 1
    gaps = _gaps_between(boxes)
    if not gaps:
        return 1

    threshold, separability = otsu_1d(gaps)
    if separability < BIMODAL_SEPARABILITY:
        return 1  # one population: every gap is a glyph boundary

    intra = [g for g in gaps if g < threshold]
    # Sit just above the widest intra-glyph gap, below the inter-glyph ones.
    return int(max(intra) + 1) if intra else 1


def solve_merge_gap(
    boxes: list[GlyphBox], target_count: int, max_width: int
) -> tuple[int, int]:
    """
    Find the merge gap that yields exactly ``target_count`` glyphs.

    Knowing what the row spells is far stronger evidence than any statistic:
    instead of guessing which gaps are internal, we search the gap values that
    actually occur for the one reproducing the expected count. Returns
    (gap, resulting_count) - compare the count to know whether it worked.
    """
    if not boxes:
        return 1, 0

    candidates = sorted({0} | {int(g) for g in _gaps_between(boxes)})
    best = (1, len(boxes))
    for gap in candidates:
        count = len(merge_by_gap(boxes, gap, max_width))
        if count == target_count:
            return gap, count
        if abs(count - target_count) < abs(best[1] - target_count):
            best = (gap, count)
        if count < target_count:
            break  # merging further only reduces the count
    return best


def merge_by_gap(boxes: list[GlyphBox], gap: int, max_width: int) -> list[GlyphBox]:
    """Left-to-right sweep merging boxes closer than ``gap``."""
    if not boxes:
        return []

    merged = [boxes[0]]
    for box in boxes[1:]:
        last = merged[-1]
        distance = box.x - last.right
        span = box.right - last.x
        if distance <= gap and span <= max_width:
            top = min(last.y, box.y)
            bottom = max(last.bottom, box.bottom)
            merged[-1] = GlyphBox(last.x, top, box.right - last.x, bottom - top)
        else:
            merged.append(box)
    return merged


# --- vertical metrics ---------------------------------------------------


def dominant_value(values: list[int], tolerance: float) -> int | None:
    """
    Robust mode: the median of the largest cluster.

    Baselines cannot be read as "the lowest ink" because descenders sit below
    them, nor as a mean because those descenders drag it down. Most glyphs do
    rest exactly on the baseline, so the densest cluster of bottom edges is
    the baseline and the descenders fall out as a smaller cluster.
    """
    if not values:
        return None

    ordered = sorted(values)
    best_cluster: list[int] = []
    for i, anchor in enumerate(ordered):
        cluster = [v for v in ordered[i:] if v - anchor <= tolerance]
        if len(cluster) > len(best_cluster):
            best_cluster = cluster
    return int(np.median(best_cluster)) if best_cluster else None


def measure_row(boxes: list[GlyphBox], row_height: int) -> tuple[int, int | None, int | None]:
    """Return (baseline, x_height_top, cap_height_top) in row-local pixels."""
    tolerance = max(2.0, row_height * CLUSTER_TOLERANCE_FRAC)

    baseline = dominant_value([b.bottom for b in boxes], tolerance)
    if baseline is None:
        baseline = row_height

    tops = [b.y for b in boxes]
    cap_top = dominant_value(tops, tolerance)

    # x-height: the dominant top among glyphs that do *not* reach the cap line.
    x_top = None
    if cap_top is not None:
        short = [t for t in tops if t > cap_top + tolerance]
        x_top = dominant_value(short, tolerance)

    return baseline, x_top, cap_top


# --- top level ----------------------------------------------------------


def analyze(path: Path) -> tuple[SheetAnalysis, np.ndarray]:
    """
    Measure a specimen sheet.

    Returns the analysis plus the *prepared* grayscale sheet those
    measurements refer to (deskewed, ink-bright). Persist that image with
    ``save_prepared`` and point the config at it, or the coordinates will
    not line up with the original file.
    """
    gray, inverted = load_ink_gray(path)

    probe, _ = binarize(gray)
    angle = estimate_deskew(probe)
    gray = apply_deskew(gray, angle)

    mask, threshold = binarize(gray)
    height, width = mask.shape

    rows: list[RowAnalysis] = []
    for index, (y1, y2) in enumerate(detect_rows(mask)):
        band = mask[y1:y2, :]
        raw_boxes = _components(band)
        if not raw_boxes:
            continue

        absolute = [GlyphBox(b.x, y1 + b.y, b.w, b.h) for b in raw_boxes]
        gap = adaptive_merge_gap(absolute)
        # A glyph should not span a large share of the row; this stops a
        # runaway merge from swallowing a whole row into one box.
        max_width = max(8, int(np.median([b.w for b in absolute]) * 3.5))
        boxes = merge_by_gap(absolute, gap, max_width)

        baseline, x_top, cap_top = measure_row(boxes, y2 - y1)

        rows.append(RowAnalysis(
            index=index,
            y_start=y1,
            y_end=y2,
            baseline=baseline,
            x_height=x_top,
            cap_height=cap_top,
            merge_gap=gap,
            max_merge_width=max_width,
            boxes=boxes,
            raw_boxes=absolute,
        ))

    analysis = SheetAnalysis(
        width=width,
        height=height,
        inverted=inverted,
        deskew_angle=angle,
        threshold=threshold,
        rows=rows,
    )
    return analysis, gray


def refine_rows(analysis: SheetAnalysis, counts: list[int]) -> SheetAnalysis:
    """
    Re-segment rows now that the expected character counts are known.

    The blind pass has to infer glyph boundaries from gap statistics alone.
    Once the user says what each row spells, the count is hard evidence, so
    each row is re-cut to match it exactly where possible. Rows given a count
    of 0 (or no count at all) keep their blind segmentation.
    """
    for row, target in zip(analysis.rows, counts):
        if target <= 0 or not row.raw_boxes:
            continue

        # The blind width ceiling is a multiple of the median *component*, far
        # too tight for scripts whose signs are assembled from many detached
        # strokes - cuneiform wedges being the extreme case, where it blocks
        # the merges needed to form a sign at all. With the sign count known,
        # the row's own geometry gives a much better bound.
        span = max(b.right for b in row.raw_boxes) - min(b.x for b in row.raw_boxes)
        row.max_merge_width = max(row.max_merge_width, int(span / target * 1.8))

        gap, achieved = solve_merge_gap(row.raw_boxes, target, row.max_merge_width)
        row.merge_gap = gap
        row.boxes = merge_by_gap(row.raw_boxes, gap, row.max_merge_width)
        if achieved == target:
            row.baseline, row.x_height, row.cap_height = measure_row(
                row.boxes, row.y_end - row.y_start
            )
    return analysis


def save_prepared(gray: np.ndarray, path: Path) -> Path:
    ok, buffer = cv2.imencode(".png", gray)
    if not ok:
        raise RuntimeError(f"Cannot encode prepared sheet: {path}")
    path.write_bytes(buffer.tobytes())
    return path


def build_config(
    analysis: SheetAnalysis,
    sheet_name: str,
    row_chars: list[str],
    meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Turn an analysis into a config the engine can build.

    ``row_chars`` holds the characters for each detected row, in order; empty
    entries drop the row. Coordinates are emitted in prepared-sheet pixels and
    ``reference_*`` is set to match, so the engine's scaling is a no-op at 1x
    and stays correct at any upscale factor.
    """
    meta = meta or {}
    family = meta.get("family_name", "My Font")
    style = meta.get("style_name", "Regular")
    version = str(meta.get("version", "1.0"))
    ps_name = f"{family.replace(' ', '')}-{style.replace(' ', '')}"
    basename = meta.get("output_basename", family.replace(" ", "_"))

    rows_config = []
    used_rows: list[RowAnalysis] = []
    for row, chars in zip(analysis.rows, row_chars):
        chars = chars.strip()
        if not chars:
            continue
        used_rows.append(row)
        rows_config.append({
            "name": f"Row {row.index + 1}",
            "y_start": row.y_start,
            "y_end": row.y_end,
            "baseline": row.baseline,
            "chars": chars,
            "grid": len(chars) != row.glyph_count,
            "merge_gap": row.merge_gap,
            "max_merge_width": row.max_merge_width,
        })

    # Metrics come from the rows actually being built. Decorative rows the
    # user skipped (titles, ornaments) would otherwise stretch the em box.
    upm = meta.get("units_per_em", 1024)
    scale_base = meta.get("scale_base") or round(derive_scale_base(used_rows, upm), 4)
    ascent, descent = derive_vertical_metrics(used_rows, upm, scale_base)

    return {
        "sheet": sheet_name,
        "output_basename": basename,
        "reference_width": analysis.width,
        "reference_height": analysis.height,
        "units_per_em": upm,
        "scale_base": scale_base,
        "lsb_offset": meta.get("lsb_offset", 80),
        "rsb_offset": meta.get("rsb_offset", 40),
        "font": {
            "version": version,
            "names": {
                "copyright": meta.get("copyright", family),
                "familyName": family,
                "styleName": style,
                "uniqueFontIdentifier": f"{family} {style}",
                "fullName": f"{family} {style}",
                "version": f"Version {float(version):.3f}",
                "psName": ps_name,
            },
        },
        "pipeline": {
            "upscale": "auto",
            "threshold": analysis.threshold,
            "sharpen": True,
            "extraction": "contour",
            "trace_exact": True,
            "skip_bitmap_refine": True,
            "angle_snap_degrees": 0,
            "contour_epsilon_factor": meta.get("contour_epsilon_factor", 0.0028),
            "symmetry_blend": 1.0,
        },
        "symmetry_chars": [],
        "aliases": {},
        "metrics": {
            "ascent": ascent,
            "descent": descent,
            "win_ascent": int(ascent * 1.1),
            "win_descent": int(abs(descent) * 1.1),
        },
        "rows": rows_config,
    }


# Cap height as a share of the em. 0.70 is the conventional range for Latin
# display faces and is what the engine's default metrics assume.
TARGET_CAP_RATIO = 0.70


def derive_scale_base(rows: list[RowAnalysis], upm: int) -> float:
    """
    Font units per reference pixel, so that cap height lands at ~0.70 em.

    The engine converts sheet pixels with ``scale_base / pixel_scale``. A
    fixed value silently assumes a particular glyph size on the sheet: too
    small and the font renders tiny, too large and outlines blow past the
    engine's coordinate clamp and get dropped entirely. Measuring cap height
    makes any sheet, at any resolution, produce correct proportions.
    """
    cap_heights = [
        row.baseline - row.cap_height
        for row in rows
        if row.cap_height is not None and row.baseline > row.cap_height
    ]
    if not cap_heights:
        return 20.0

    # Rows of caps and rows of digits share a height; x-height-only rows sit
    # lower and would bias a mean, so take the dominant value.
    reference_cap = float(np.median(cap_heights))
    return (upm * TARGET_CAP_RATIO) / reference_cap


def derive_vertical_metrics(
    rows: list[RowAnalysis], upm: int, scale_base: float
) -> tuple[int, int]:
    """
    Ascent/descent in font units, measured from the sheet rather than guessed.

    The tallest ascender and deepest descender across all rows convert
    directly through ``scale_base``, with a small breathing margin.
    """
    ascents, descents = [], []
    for row in rows:
        if not row.boxes:
            continue
        top = min(b.y for b in row.boxes)
        bottom = max(b.bottom for b in row.boxes)
        ascents.append(row.baseline - top)
        descents.append(bottom - row.baseline)

    if not ascents:
        return int(upm * 0.88), -int(upm * 0.22)

    # The extremes are already the outer edge of the ink; a small margin keeps
    # lines from touching, and usWin* carries the extra clearance.
    ascent = int(max(ascents) * scale_base * 1.04)
    descent = -int(max(max(descents), 1) * scale_base * 1.15)

    ascent = max(int(upm * 0.6), min(ascent, int(upm * 1.05)))
    descent = min(-int(upm * 0.08), max(descent, -int(upm * 0.5)))
    return ascent, descent
