"""
Unit tests for the measurement primitives in ``font_forge.autodetect``.

These cover the decisions the detector makes on its own - polarity, glyph
boundaries, baseline placement - in isolation from image decoding, so a
regression points at one function rather than the whole pipeline.
"""
from __future__ import annotations

import numpy as np
import pytest

from font_forge.autodetect import (
    GlyphBox,
    RowAnalysis,
    SheetAnalysis,
    TARGET_CAP_RATIO,
    adaptive_merge_gap,
    derive_scale_base,
    derive_vertical_metrics,
    dominant_value,
    merge_by_gap,
    otsu_1d,
    solve_merge_gap,
    _is_dark_ink,
)


# --- polarity -----------------------------------------------------------


def test_dark_ink_detected_on_light_background():
    """A scanned page: dark marks on white."""
    gray = np.full((100, 100), 255, dtype=np.uint8)
    gray[40:60, 40:60] = 0
    assert _is_dark_ink(gray) is True


def test_light_ink_detected_on_dark_background():
    """A screen-style specimen: bright glyphs on black, needs no inversion."""
    gray = np.zeros((100, 100), dtype=np.uint8)
    gray[40:60, 40:60] = 255
    assert _is_dark_ink(gray) is False


# --- gap statistics -----------------------------------------------------


def test_otsu_separates_two_clear_populations():
    """Tight intra-glyph gaps against wide inter-glyph ones."""
    gaps = [1.0, 2.0, 1.5, 2.0, 40.0, 42.0, 41.0, 39.0]
    threshold, separability = otsu_1d(gaps)
    assert 2.0 < threshold < 40.0
    assert separability > 0.72


def test_otsu_reports_low_separability_for_one_population():
    """
    Otsu splits any sample, so the score is what tells us the split is
    meaningless. Uniform gaps must not be read as two groups.
    """
    _, separability = otsu_1d([20.0, 21.0, 19.0, 20.5, 20.0, 19.5])
    assert separability < 0.72


def test_adaptive_gap_does_not_merge_evenly_spaced_glyphs():
    """
    Regression: evenly spaced letters are one population. Merging them was
    the bug that collapsed 26 uppercase letters into 19.
    """
    boxes = [GlyphBox(x=i * 50, y=0, w=30, h=40) for i in range(8)]
    assert adaptive_merge_gap(boxes) == 1


def test_adaptive_gap_merges_a_detached_mark():
    """An accent or a tittle sits far closer to its stem than the next letter."""
    boxes = [
        GlyphBox(0, 0, 30, 40), GlyphBox(32, 0, 6, 6),    # stem + its dot
        GlyphBox(100, 0, 30, 40), GlyphBox(132, 0, 6, 6),
        GlyphBox(200, 0, 30, 40), GlyphBox(232, 0, 6, 6),
    ]
    assert adaptive_merge_gap(boxes) >= 2


# --- merging ------------------------------------------------------------


def test_merge_respects_the_width_ceiling():
    """The ceiling is what stops a runaway merge swallowing a whole row."""
    boxes = [GlyphBox(i * 20, 0, 15, 40) for i in range(5)]
    unrestricted = merge_by_gap(boxes, gap=10, max_width=1000)
    restricted = merge_by_gap(boxes, gap=10, max_width=40)
    assert len(unrestricted) == 1
    assert len(restricted) > 1


def test_merge_keeps_vertical_extent_of_the_group():
    """A merged box must cover the mark as well as the stem."""
    boxes = [GlyphBox(0, 20, 30, 40), GlyphBox(32, 0, 6, 6)]
    merged = merge_by_gap(boxes, gap=5, max_width=1000)
    assert len(merged) == 1
    assert merged[0].y == 0 and merged[0].bottom == 60


# --- the count solver ---------------------------------------------------


def test_solver_hits_an_exact_target():
    """Two wedges per sign, four signs: the solver must find the gap."""
    boxes = []
    for sign in range(4):
        boxes.append(GlyphBox(sign * 100, 0, 20, 40))
        boxes.append(GlyphBox(sign * 100 + 25, 0, 20, 40))
    gap, count = solve_merge_gap(boxes, target_count=4, max_width=1000)
    assert count == 4
    assert len(merge_by_gap(boxes, gap, 1000)) == 4


def test_solver_reports_its_shortfall_rather_than_lying():
    """
    When no gap yields the target the solver returns its best effort and the
    count it achieved, so the caller can fall back instead of trusting it.
    """
    boxes = [GlyphBox(i * 100, 0, 20, 40) for i in range(3)]
    _, count = solve_merge_gap(boxes, target_count=99, max_width=1000)
    assert count != 99


def test_solver_is_blocked_by_a_tight_width_ceiling():
    """
    Regression for the cuneiform failure: a ceiling derived from median
    component width prevents wedges ever forming a sign.
    """
    boxes = []
    for sign in range(4):
        boxes.append(GlyphBox(sign * 100, 0, 20, 40))
        boxes.append(GlyphBox(sign * 100 + 25, 0, 20, 40))
    _, blocked = solve_merge_gap(boxes, target_count=4, max_width=22)
    assert blocked != 4  # the ceiling makes the target unreachable


# --- vertical metrics ---------------------------------------------------


def test_dominant_value_ignores_descender_outliers():
    """
    The baseline is where most glyphs rest. Descenders are a minority and
    must not drag it down - which a mean or a minimum would.
    """
    bottoms = [100, 101, 100, 99, 100, 101, 100, 140, 141]  # two descenders
    assert dominant_value(bottoms, tolerance=4.0) == pytest.approx(100, abs=1)


def test_dominant_value_returns_none_for_no_input():
    assert dominant_value([], tolerance=3.0) is None


def _row(baseline: int, cap: int, boxes: list[GlyphBox]) -> RowAnalysis:
    return RowAnalysis(index=0, y_start=cap - 5, y_end=baseline + 5,
                       baseline=baseline, x_height=None, cap_height=cap,
                       merge_gap=1, max_merge_width=100, boxes=boxes)


def test_scale_base_puts_cap_height_at_the_target_ratio():
    """
    A fixed scale silently assumes a glyph size on the sheet. Deriving it
    from measured cap height is what makes any resolution work.
    """
    row = _row(baseline=200, cap=150, boxes=[GlyphBox(0, 150, 30, 50)])
    scale = derive_scale_base([row], upm=1024)
    assert (200 - 150) * scale == pytest.approx(1024 * TARGET_CAP_RATIO, rel=1e-6)


def test_scale_base_falls_back_when_cap_height_is_unknown():
    row = _row(baseline=200, cap=150, boxes=[])
    row.cap_height = None
    assert derive_scale_base([row], upm=1024) == 20.0


def test_vertical_metrics_stay_inside_em_bounds():
    """Even a wild row must not produce metrics outside the sane envelope."""
    row = _row(baseline=200, cap=0, boxes=[GlyphBox(0, 0, 30, 400)])
    ascent, descent = derive_vertical_metrics([row], upm=1024, scale_base=50.0)
    assert 0.6 * 1024 <= ascent <= 1.05 * 1024
    assert -0.5 * 1024 <= descent <= -0.08 * 1024


def test_vertical_metrics_have_a_defined_fallback():
    ascent, descent = derive_vertical_metrics([], upm=1024, scale_base=20.0)
    assert ascent > 0 > descent
