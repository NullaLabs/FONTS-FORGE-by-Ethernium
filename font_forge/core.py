"""
Generic raster sheet → OpenType font pipeline.
Designed for grid-based specimen sheets (rows of glyphs left-to-right).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont

from font_forge.config import scale_rows
from font_forge.vision import (
    resolve_sheet_path,
    make_image_symmetrical,
    refine_glyph_bitmap,
    smooth_binary_bitmap,
    prepare_binary,
    extract_glyphs_grid,
    merge_boxes,
)
from font_forge.vector import (
    to_font_coord,
    draw_smooth_path,
    snap_contour_points,
    simplify_colinear,
    refine_contour_subpixel,
    rdp_simplify,
    apply_extrema_constraints,
)
from font_forge.watermark import inject_forensic_watermark_in_compiled_glyphs


class SheetToFontBuilder:
    def __init__(self, config: dict[str, Any], root: Path):
        self.config = config
        self.root = root
        self.pipeline = config.get("pipeline", {})
        self.upscale = self.pipeline.get("upscale", "auto")
        self.thresh = self.pipeline.get("threshold", 30)
        self.trace_exact = self.pipeline.get("trace_exact", False)
        self.extraction = self.pipeline.get("extraction", "contour")
        self.snap_deg = self.pipeline.get("angle_snap_degrees", 10)
        self.symmetry_blend = self.pipeline.get("symmetry_blend", 0.90)
        self.symmetry_chars = (
            frozenset()
            if self.trace_exact
            else frozenset(config.get("symmetry_chars", []))
        )
        self.eps_factor = self.pipeline.get("contour_epsilon_factor", 0.010)
        self.skip_refine = self.pipeline.get("skip_bitmap_refine", False)
        self.lsb = config.get("lsb_offset", 80)
        self.units_per_em = config.get("units_per_em", 1024)
        self.scale_base = config.get("scale_base", 20)

    def _upscale_factor(self, width: int) -> int:
        from font_forge.vision import effective_upscale
        if self.upscale == "auto":
            return effective_upscale(width)
        return int(self.upscale)

    def _load_sheet(self, sheet_name: str) -> tuple[np.ndarray, np.ndarray, tuple[int, ...], float, int, str]:
        """Return (thresh, gray, gray_source_shape, pixel_scale, upscale, name)."""
        sheet_path = resolve_sheet_path(self.root, sheet_name)
        img = cv2.imread(str(sheet_path))
        if img is None:
            raise RuntimeError(f"Cannot read sheet: {sheet_path}")

        upscale = self._upscale_factor(img.shape[1])
        if upscale > 1:
            img = cv2.resize(
                img, None, fx=upscale, fy=upscale, interpolation=cv2.INTER_LANCZOS4
            )

        ref_w = self.config.get("reference_width", 1024)
        ref_h = self.config["reference_height"]
        pixel_scale = max(img.shape[1] / ref_w, img.shape[0] / ref_h)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        thresh = prepare_binary(
            gray,
            self.thresh if self.thresh > 0 else None,
            sharpen=self.pipeline.get("sharpen", True),
        )
        return thresh, gray, img.shape, pixel_scale, upscale, sheet_path.name

    def _setup_names(self, fb: FontBuilder) -> None:
        font_meta = self.config["font"]
        fb.setupNameTable(font_meta["names"])

        # Add extended name records
        name_table = fb.font['name']
        for plat_id, enc_id, lang_id in [(3, 1, 0x0409), (1, 0, 0)]:
            name_table.setName("Ethernium Sym \u2014 A cyberpunk-runic display typeface.", 10, plat_id, enc_id, lang_id)
            name_table.setName("https://github.com/EtherniumSym", 11, plat_id, enc_id, lang_id)
            name_table.setName("Created with Ethernium Font Creator", 13, plat_id, enc_id, lang_id)

    def _create_fallback_glyphs(self, glyphs: dict, glyph_order: list, cmap: dict, metrics: dict) -> None:
        # 1. .notdef
        pen = TTGlyphPen(None)
        for coords in [(100, 100), (900, 100), (900, 900), (100, 900)]:
            if coords == (100, 100):
                pen.moveTo(coords)
            else:
                pen.lineTo(coords)
        pen.closePath()
        glyphs[".notdef"] = pen.glyph()
        metrics[".notdef"] = (1000, 100)

        # 2. space (codepoint 32)
        pen_sp = TTGlyphPen(None)
        glyphs["space"] = pen_sp.glyph()
        glyph_order.append("space")
        cmap[32] = "space"
        metrics["space"] = (280, 0)

        # 3. dollar (codepoint 36)
        pen_dl = TTGlyphPen(None)
        pen_dl.moveTo((100, 700))
        pen_dl.lineTo((400, 700))
        pen_dl.lineTo((400, 420))
        pen_dl.lineTo((160, 420))
        pen_dl.lineTo((160, 200))
        pen_dl.lineTo((400, 200))
        pen_dl.lineTo((400, 100))
        pen_dl.lineTo((100, 100))
        pen_dl.lineTo((100, 380))
        pen_dl.lineTo((340, 380))
        pen_dl.lineTo((340, 620))
        pen_dl.lineTo((100, 620))
        pen_dl.closePath()
        pen_dl.moveTo((220, 20))
        pen_dl.lineTo((280, 20))
        pen_dl.lineTo((280, 780))
        pen_dl.lineTo((220, 780))
        pen_dl.closePath()
        glyphs["dollar"] = pen_dl.glyph()
        glyph_order.append("dollar")
        cmap[36] = "dollar"
        metrics["dollar"] = (500, 100)

        # 4. asciicircum (codepoint 94)
        pen_ac = TTGlyphPen(None)
        pen_ac.moveTo((100, 450))
        pen_ac.lineTo((160, 450))
        pen_ac.lineTo((300, 650))
        pen_ac.lineTo((440, 450))
        pen_ac.lineTo((500, 450))
        pen_ac.lineTo((330, 720))
        pen_ac.lineTo((270, 720))
        pen_ac.closePath()
        glyphs["asciicircum"] = pen_ac.glyph()
        glyph_order.append("asciicircum")
        cmap[94] = "asciicircum"
        metrics["asciicircum"] = (600, 100)

        # 5. grave (codepoint 96)
        pen_gr = TTGlyphPen(None)
        pen_gr.moveTo((100, 580))
        pen_gr.lineTo((220, 720))
        pen_gr.lineTo((270, 680))
        pen_gr.lineTo((150, 540))
        pen_gr.closePath()
        glyphs["grave"] = pen_gr.glyph()
        glyph_order.append("grave")
        cmap[96] = "grave"
        metrics["grave"] = (350, 100)

        # 6. bar (codepoint 124)
        pen_br = TTGlyphPen(None)
        pen_br.moveTo((120, -100))
        pen_br.lineTo((180, -100))
        pen_br.lineTo((180, 800))
        pen_br.lineTo((120, 800))
        pen_br.closePath()
        glyphs["bar"] = pen_br.glyph()
        glyph_order.append("bar")
        cmap[124] = "bar"
        metrics["bar"] = (300, 120)

    def _vectorize_contour(
        self,
        contour: np.ndarray,
        gray_glyph_crop: np.ndarray,
        eps_base: float,
        x_min: int,
        baseline: int,
        scale: float,
        y1p: int,
        cy1: int,
        cx1: int
    ) -> list[tuple[int, int]]:
        refined = refine_contour_subpixel(contour, gray_glyph_crop)
        peri = cv2.arcLength(refined, True)
        eps = max(
            eps_base,
            self.eps_factor * peri if self.trace_exact else 0.010 * peri,
        )
        approx = cv2.approxPolyDP(refined, eps, True)
        pts = approx.reshape(-1, 2)
        if len(pts) < 3:
            return []
        if self.snap_deg > 0 and not self.trace_exact:
            pts = snap_contour_points(pts, self.snap_deg)
        font_pts = []
        for px, py in pts:
            abs_x, abs_y = cx1 + px, y1p + cy1 + py
            font_pts.append(
                to_font_coord(abs_x, abs_y, x_min, baseline, scale, self.lsb)
            )
        if not self.trace_exact:
            font_pts = rdp_simplify(font_pts, epsilon=1.5)
            font_pts = apply_extrema_constraints(font_pts, tolerance=8.0)
            font_pts = simplify_colinear(font_pts)
        return font_pts

    def _drop_rogue_paths(self, paths: list[list[tuple[int, int]]]) -> list[list[tuple[int, int]]]:
        cleaned = []
        for path in paths:
            ys = [p[1] for p in path]
            if min(ys) < -120 or max(ys) > 1080:
                continue
            if max(ys) - min(ys) > 980:
                continue
            cleaned.append(path)
        return cleaned

    def _process_glyph_contours(
        self,
        char: str,
        glyph_crop: np.ndarray,
        gray_glyph_crop: np.ndarray,
        x_min: int,
        baseline: int,
        scale: float,
        eps_base: float,
        y1p: int,
        cy1: int,
        cx1: int
    ) -> list[list[tuple[int, int]]]:
        g_contours, hierarchy = cv2.findContours(
            glyph_crop, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE
        )
        path_list: list[list[tuple[int, int]]] = []

        def add_path(contour):
            fp = self._vectorize_contour(
                contour, gray_glyph_crop, eps_base, x_min, baseline, scale, y1p, cy1, cx1
            )
            if len(fp) >= 3:
                path_list.append(fp)

        if hierarchy is not None and len(g_contours):
            hier = hierarchy[0]
            for ci, c in enumerate(g_contours):
                if hier[ci][3] != -1:
                    continue
                add_path(c)
                child = hier[ci][2]
                while child != -1:
                    add_path(g_contours[child])
                    child = hier[child][0]
        else:
            for c in g_contours:
                add_path(c)

        path_list = self._drop_rogue_paths(path_list)
        if not path_list:
            g_contours, _ = cv2.findContours(
                glyph_crop, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )
            path_list = []
            for c in g_contours:
                refined = refine_contour_subpixel(c, gray_glyph_crop)
                peri = cv2.arcLength(refined, True)
                eps = max(eps_base, self.eps_factor * peri)
                approx = cv2.approxPolyDP(refined, eps, True)
                pts = approx.reshape(-1, 2)
                if len(pts) < 3:
                    continue
                fp = [
                    to_font_coord(
                        cx1 + p[0], y1p + cy1 + p[1], x_min, baseline, scale, self.lsb
                    )
                    for p in pts
                ]
                if not self.trace_exact:
                    fp = rdp_simplify(fp, epsilon=1.5)
                    fp = apply_extrema_constraints(fp, tolerance=8.0)
                    fp = simplify_colinear(fp)
                if len(fp) >= 3:
                    path_list.append(fp)
            path_list = self._drop_rogue_paths(path_list)

        return path_list

    def _setup_kerning(self, fb: FontBuilder, cmap: dict[int, str], glyphs: dict) -> None:
        from fontTools.ttLib.tables._k_e_r_n import table__k_e_r_n, KernTable_format_0
        kern = table__k_e_r_n()
        kern.version = 0
        subtable = KernTable_format_0()
        subtable.version = 0
        subtable.coverage = 1
        
        kern_table = {}
        def add_kern_pair(char1, char2, val):
            g1 = cmap.get(ord(char1))
            g2 = cmap.get(ord(char2))
            if g1 and g2 and g1 in glyphs and g2 in glyphs:
                kern_table[(g1, g2)] = val
        
        pairs_to_add = [
            ('A', 'V', -45), ('V', 'A', -45),
            ('A', 'W', -40), ('W', 'A', -40),
            ('A', 'Y', -45), ('Y', 'A', -45),
            ('A', 'T', -35), ('T', 'A', -45),
            ('F', 'A', -35), ('P', 'A', -30),
            ('L', 'T', -40), ('L', 'V', -40),
            ('L', 'W', -35), ('L', 'Y', -40),
            ('T', 'O', -35), ('O', 'T', -35),
            ('T', 'C', -30), ('C', 'T', -30),
            ('Y', 'O', -30), ('O', 'Y', -30),
        ]
        
        for c1, c2, val in pairs_to_add:
            add_kern_pair(c1.upper(), c2.upper(), val)
            add_kern_pair(c1.lower(), c2.lower(), val)
            add_kern_pair(c1.upper(), c2.lower(), val)
            add_kern_pair(c1.lower(), c2.upper(), val)
            
        # Special symbols kerning (Omega and Delta)
        add_kern_pair('\u03a9', '\u0394', -25)
        add_kern_pair('\u0394', '\u03a9', -25)
        
        if kern_table:
            subtable.kernTable = kern_table
            kern.subtables = [subtable]
            fb.font['kern'] = kern

    def _setup_render_tables(self, fb: FontBuilder, metrics_header: dict) -> None:
        fb.setupHorizontalHeader(
            ascent=metrics_header.get("ascent", 900),
            descent=metrics_header.get("descent", -224),
        )
        fb.setupOS2(
            sTypoAscender=metrics_header.get("ascent", 900),
            sTypoDescender=metrics_header.get("descent", -224),
            sTypoLineGap=0,
            usWinAscent=metrics_header.get("win_ascent", 1000),
            usWinDescent=metrics_header.get("win_descent", 250),
            sxHeight=500,
            sCapHeight=700,
            usWeightClass=400,
            usWidthClass=5,
            fsType=0,
            fsSelection=0x0040,  # REGULAR bit
            achVendID="ETHN",
        )
        fb.setupPost()
        fb.setupMaxp()

        # Add gasp table for optimal screen rendering
        from fontTools.ttLib.tables._g_a_s_p import table__g_a_s_p
        gasp = table__g_a_s_p()
        gasp.version = 1
        gasp.gaspRange = {
            8: 0x000A,    # < 8ppem: gridfit only
            20: 0x0007,   # 8-20ppem: gridfit + grayscale + symmetric smoothing
            65535: 0x000F, # > 20ppem: all smoothing options
        }
        fb.font['gasp'] = gasp

    def build(self) -> dict[str, Any]:
        default_sheet = self.config["sheet"]
        ref_h = self.config["reference_height"]

        thresh_main, gray_main, shape_main, pixel_scale_main, upscale_main, main_name = (
            self._load_sheet(default_sheet)
        )
        print(
            f"Main sheet: {main_name} -> {shape_main[1]}x{shape_main[0]} "
            f"(upscale {upscale_main}x, pixel_scale {pixel_scale_main:.2f})"
        )

        sheet_cache: dict[str, tuple] = {
            default_sheet: (thresh_main, gray_main, shape_main, pixel_scale_main, upscale_main)
        }

        font_meta = self.config["font"]
        validation: dict[str, Any] = {
            "version": font_meta.get("version", "1.0"),
            "sheet": main_name,
            "upscale": upscale_main,
            "rows": [],
        }

        fb = FontBuilder(self.units_per_em, isTTF=True)
        self._setup_names(fb)

        glyphs: dict = {}
        glyph_order = [".notdef"]
        cmap: dict[int, str] = {}
        metrics: dict[str, tuple[int, int]] = {}

        self._create_fallback_glyphs(glyphs, glyph_order, cmap, metrics)

        for row in self.config["rows"]:
            name = row["name"]
            char_list = row["chars"]
            row_sheet = row.get("sheet", default_sheet)

            if row_sheet not in sheet_cache:
                t, g, sh, ps, up, _ = self._load_sheet(row_sheet)
                sheet_cache[row_sheet] = (t, g, sh, ps, up)
                print(
                    f"Alt sheet: {row_sheet} -> {sh[1]}x{sh[0]} "
                    f"(pixel_scale {ps:.2f})"
                )

            thresh, gray, shape, pixel_scale, upscale = sheet_cache[row_sheet]
            rows_scaled = scale_rows([row], shape[0], ref_h)[0]
            y1 = rows_scaled["y_start"]
            y2 = rows_scaled["y_end"]
            baseline = rows_scaled["baseline"]

            scale = self.scale_base / pixel_scale
            margin = max(2, int(3 * pixel_scale))
            merge_gap = max(3, int(4 * pixel_scale))
            min_w = max(2, int(2 * pixel_scale))
            min_h = max(2, int(2 * pixel_scale))
            min_area = max(8, int(8 * pixel_scale * pixel_scale))
            max_w = int(200 * pixel_scale)
            eps_base = (0.08 if self.trace_exact else 0.42) * pixel_scale

            print(f"\nRow: {name} (y={y1}-{y2}, sheet={row_sheet})")

            default_pad_y = max(0, int(4 * pixel_scale))
            row_pad_y = row.get("pad_y")
            if row_pad_y is not None:
                pad_y = max(0, int(row_pad_y * pixel_scale))
            else:
                pad_y = default_pad_y
            y1p = max(0, y1 - pad_y)
            y2p = min(thresh.shape[0], y2 + pad_y)
            crop = thresh[y1p:y2p, :]
            y_offset = y1p

            use_grid = self.extraction == "grid" or (
                self.trace_exact and row.get("grid", True)
            )
            if use_grid:
                merged = extract_glyphs_grid(crop, len(char_list), pixel_scale)
            else:
                contours, _ = cv2.findContours(
                    crop, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
                )
                boxes = []
                for c in contours:
                    x, y, w, h = cv2.boundingRect(c)
                    if w > max_w or h < min_h or w < min_w or w * h < min_area:
                        continue
                    boxes.append((x, y, w, h))

                row_gap = row.get("merge_gap")
                gap = max(2, int(row_gap * pixel_scale)) if row_gap else merge_gap
                max_merge_w = row.get("max_merge_width")
                max_merge_w = (
                    int(max_merge_w * pixel_scale)
                    if max_merge_w
                    else int(55 * pixel_scale)
                )
                x_max = row.get("x_max")
                if x_max is not None:
                    x_lim = int(x_max * pixel_scale)
                    boxes = [b for b in boxes if b[0] <= x_lim]
                merged = merge_boxes(boxes, gap, max_merge_width=max_merge_w)
            row_ok = len(merged) == len(char_list)
            if not row_ok:
                print(f"  Warning: got {len(merged)}, expected {len(char_list)}")

            row_report = {
                "row": name,
                "expected": len(char_list),
                "extracted": len(merged),
                "ok": row_ok,
            }
            validation["rows"].append(row_report)

            for idx, (gx, gy, gw, gh) in enumerate(merged):
                if idx >= len(char_list):
                    break
                char = char_list[idx]
                gname = char if char.isalnum() and ord(char) < 128 else f"uni{ord(char):04X}"

                cx1, cy1 = max(0, gx - margin), max(0, gy - margin)
                cx2 = min(crop.shape[1], gx + gw + margin)
                cy2 = min(crop.shape[0], gy + gh + margin)
                glyph_crop = crop[cy1:cy2, cx1:cx2].copy()
                gray_glyph_crop = gray[y1p + cy1 : y1p + cy2, cx1:cx2].copy()
                if not self.skip_refine and not self.trace_exact:
                    glyph_crop = refine_glyph_bitmap(glyph_crop)
                elif self.trace_exact:
                    glyph_crop = smooth_binary_bitmap(glyph_crop, pixel_scale)

                if char in self.symmetry_chars:
                    glyph_crop = make_image_symmetrical(
                        glyph_crop, self.symmetry_blend
                    )

                path_list = self._process_glyph_contours(
                    char, glyph_crop, gray_glyph_crop, gx, baseline, scale, eps_base, y1p, cy1, cx1
                )

                if not path_list:
                    print(f"  Skip '{char}': no valid paths")
                    continue

                all_pts = [p for path in path_list for p in path]
                min_fx = min(p[0] for p in all_pts)
                max_fx = max(p[0] for p in all_pts)
                min_fy = min(p[1] for p in all_pts)
                max_fy = max(p[1] for p in all_pts)
                if (max_fx - min_fx) > 1400:
                    print(f"  Skip '{char}': too wide")
                    continue

                # Auto baseline alignment vertical shift
                is_baseline_char = char.isupper() or char in "acenorsuvwxz"
                shift_y = 0
                if is_baseline_char and self.pipeline.get("auto_baseline_align", True):
                    shift_y = -min_fy

                shift_x = self.lsb - min_fx
                pen = TTGlyphPen(None)
                max_deflection = self.pipeline.get("curve_deflection_threshold", 28.0)
                for path in path_list:
                    shifted = [(p[0] + shift_x, p[1] + shift_y) for p in path]
                    if max_deflection > 0 and not self.trace_exact:
                        draw_smooth_path(pen, shifted, max_deflection)
                    else:
                        pen.moveTo(shifted[0])
                        for pt in shifted[1:]:
                            pen.lineTo(pt)
                        pen.closePath()

                glyph_w = max_fx - min_fx
                rsb = self.config.get("rsb_offset", 40)
                advance = int(glyph_w) + self.lsb + rsb

                glyphs[gname] = pen.glyph()
                glyph_order.append(gname)
                cmap[ord(char)] = gname

                for alias in self.config.get("aliases", {}).get(char, []):
                    cmap[ord(alias)] = gname

                metrics[gname] = (advance, self.lsb)

        # Embed the steganographic watermark!
        watermark_str = self.config.get("watermark", "SteveBlackbeard / FONTS-CREATOR-by-Ethernium")
        inject_forensic_watermark_in_compiled_glyphs(glyphs, cmap, watermark_str)

        fb.setupGlyphOrder(glyph_order)
        fb.setupGlyf(glyphs)
        fb.setupCharacterMap(cmap)
        fb.setupHorizontalMetrics(metrics)

        self._setup_kerning(fb, cmap, glyphs)
        self._setup_render_tables(fb, self.config.get("metrics", {}))

        out_base = self.root / self.config.get("output_basename", "Output")
        ttf_path = out_base.with_suffix(".ttf")
        fb.save(str(ttf_path))
        print(f"\nSaved {ttf_path.name}")

        report_path = self.root / "build_report.json"
        report_path.write_text(
            json.dumps(validation, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        font = TTFont(str(ttf_path))
        for flavor, ext in (("woff", ".woff"), ("woff2", ".woff2")):
            out = out_base.with_suffix(ext)
            font.flavor = flavor
            font.save(str(out))
            print(f"Saved {out.name}")

        return validation
