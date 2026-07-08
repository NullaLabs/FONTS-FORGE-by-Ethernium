import cv2
import numpy as np
from pathlib import Path

def resolve_sheet_path(root: Path, sheet_name: str) -> Path:
    exact = root / sheet_name
    if exact.is_file():
        return exact
    for fallback in ("ethernium_sheet_hq.png", "ethernium_sheet.png"):
        path = root / fallback
        if path.is_file():
            return path
    raise FileNotFoundError(
        f"No sheet found. Place '{sheet_name}' in {root}"
    )


def effective_upscale(width: int) -> int:
    """HQ sheets need less upscaling to avoid blur."""
    if width >= 3000:
        return 1
    if width >= 1500:
        return 2
    return 4


def make_image_symmetrical(crop: np.ndarray, blend: float) -> np.ndarray:
    pts = np.argwhere(crop > 0)
    if len(pts) == 0:
        return crop

    xs = pts[:, 1]
    xmin, xmax = xs.min(), xs.max()
    center = (xmin + xmax) / 2.0
    int_center = int(np.floor(center))
    h, w = crop.shape
    sym_crop = np.zeros_like(crop)

    for x in range(0, int_center + 1):
        mirrored_x = int(np.round(2 * center - x))
        if 0 <= mirrored_x < w:
            sym_crop[:, x] = crop[:, x]
            sym_crop[:, mirrored_x] = crop[:, x]

    if center.is_integer():
        c_idx = int(center)
        if 0 <= c_idx < w:
            sym_crop[:, c_idx] = crop[:, c_idx]

    if blend >= 1.0:
        return sym_crop
    return cv2.addWeighted(sym_crop, blend, crop, 1.0 - blend, 0)


def refine_glyph_bitmap(crop: np.ndarray) -> np.ndarray:
    k = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
    closed = cv2.morphologyEx(crop, cv2.MORPH_CLOSE, k, iterations=1)
    return cv2.addWeighted(closed, 0.55, crop, 0.45, 0)


def smooth_binary_bitmap(crop: np.ndarray, pixel_scale: float) -> np.ndarray:
    """Anti-aliasing threshold smoothing to remove jagged stair-step pixelation."""
    k = 5 if pixel_scale >= 3.0 else 3
    padded = cv2.copyMakeBorder(crop, 6, 6, 6, 6, cv2.BORDER_CONSTANT, value=0)
    blurred = cv2.GaussianBlur(padded, (k, k), 0)
    _, smoothed = cv2.threshold(blurred, 110, 255, cv2.THRESH_BINARY)
    return smoothed[6:-6, 6:-6]


def sharpen_gray(gray: np.ndarray, amount: float = 0.35) -> np.ndarray:
    """Light unsharp mask — crisp edges on HQ sheets without changing geometry."""
    blurred = cv2.GaussianBlur(gray, (0, 0), 1.2)
    sharp = cv2.addWeighted(gray, 1.0 + amount, blurred, -amount, 0)
    return np.clip(sharp, 0, 255).astype(np.uint8)


def prepare_binary(gray: np.ndarray, fixed_thresh: int | None, sharpen: bool = False) -> np.ndarray:
    """Sharp binarization: optional unsharp + median + threshold."""
    work = sharpen_gray(gray) if sharpen else gray
    denoised = cv2.medianBlur(work, 3)
    if fixed_thresh is not None:
        _, binary = cv2.threshold(denoised, fixed_thresh, 255, cv2.THRESH_BINARY)
    else:
        _, binary = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return binary


def row_content_x_bounds(crop: np.ndarray, pixel_scale: float) -> tuple[int, int]:
    """Left/right ink bounds for glyph grid (ignores far-right decorations)."""
    proj = np.sum(crop > 0, axis=0).astype(np.float32)
    if proj.max() == 0:
        return 0, crop.shape[1]
    thresh = proj.max() * 0.12
    idx = np.where(proj >= thresh)[0]
    x1, x2 = int(idx[0]), int(idx[-1]) + 1
    # Drop isolated right-side ornaments (connectors, wide art)
    max_orament_w = int(90 * pixel_scale)
    scan_x = x2 - 1
    while scan_x > x1 + int(200 * pixel_scale):
        col = crop[:, max(x1, scan_x - 20) : scan_x + 1]
        if col.size and np.sum(col > 0) > col.size * 0.02:
            break
        block = proj[max(x1, scan_x - max_orament_w) : scan_x + 1]
        if block.size and block.max() >= thresh:
            scan_x -= max_orament_w
            continue
        x2 = max(x1 + 1, scan_x)
        break
    return x1, x2


def extract_glyphs_grid(
    crop: np.ndarray,
    char_count: int,
    pixel_scale: float,
    pad: int | None = None,
) -> list[tuple[int, int, int, int]]:
    """Split row into equal slots — one glyph per cell, exact shapes from reference."""
    if pad is None:
        pad = max(1, int(2 * pixel_scale))
    x1, x2 = row_content_x_bounds(crop, pixel_scale)
    slot_w = (x2 - x1) / char_count
    boxes = []
    for i in range(char_count):
        sx1 = int(x1 + i * slot_w) + pad
        sx2 = int(x1 + (i + 1) * slot_w) - pad
        if sx2 <= sx1:
            sx2 = sx1 + 1
        slot = crop[:, sx1:sx2]
        pts = np.argwhere(slot > 0)
        if len(pts) == 0:
            boxes.append((sx1, 0, max(1, sx2 - sx1), crop.shape[0]))
            continue
        ys, xs = pts[:, 0], pts[:, 1]
        gy1, gy2 = int(ys.min()), int(ys.max()) + 1
        gx1, gx2 = int(xs.min()) + sx1, int(xs.max()) + sx1 + 1
        boxes.append((gx1, gy1, gx2 - gx1, gy2 - gy1))
    return boxes


def merge_boxes(
    boxes: list,
    gap_px: int,
    max_merge_width: int | None = None,
) -> list[tuple[int, int, int, int]]:
    if not boxes:
        return []

    merged = []
    used: set[int] = set()

    for i, b1 in enumerate(boxes):
        if i in used:
            continue
        group = [b1]
        used.add(i)
        changed = True
        while changed:
            changed = False
            for j, b2 in enumerate(boxes):
                if j in used:
                    continue
                merge_ok = False
                for member in group:
                    x1, _, w1, _ = member[:4]
                    x2, _, w2, _ = b2[:4]
                    h_dist = max(0, max(x1, x2) - min(x1 + w1, x2 + w2))
                    if h_dist <= gap_px:
                        xs = [b[0] for b in group] + [x2]
                        ws = [b[2] for b in group] + [w2]
                        span = max(x + w for x, w in zip(xs, ws)) - min(xs)
                        if max_merge_width and span > max_merge_width:
                            continue
                        merge_ok = True
                        break
                if merge_ok:
                    group.append(b2)
                    used.add(j)
                    changed = True

        xs = [b[0] for b in group]
        ys = [b[1] for b in group]
        ws = [b[2] for b in group]
        hs = [b[3] for b in group]
        min_x, max_x = min(xs), max(x + w for x, w in zip(xs, ws))
        min_y, max_y = min(ys), max(y + h for y, h in zip(ys, hs))
        merged.append((min_x, min_y, max_x - min_x, max_y - min_y))

    return sorted(merged, key=lambda g: g[0])
