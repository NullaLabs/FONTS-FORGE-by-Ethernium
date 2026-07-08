import cv2
import numpy as np
from fontTools.pens.ttGlyphPen import TTGlyphPen

def to_font_coord(abs_x, abs_y, x_min, baseline_y, scale, lsb):
    """Map sheet pixels to font UPM; clamp to valid glyf range."""
    fx = int((abs_x - x_min) * scale + lsb)
    fy = int((baseline_y - abs_y) * scale)
    fx = max(-500, min(1200, fx))
    fy = max(-600, min(1100, fy))
    return fx, fy


def draw_smooth_path(pen: TTGlyphPen, path: list[tuple[int, int]], max_deflection_deg: float = 28.0) -> None:
    """
    Classify path vertices using deflection angles:
    - Deflection angle <= max_deflection_deg: Smooth curve (TrueType off-curve control point).
    - Deflection angle > max_deflection_deg: Sharp corner (TrueType on-curve anchor point).
    """
    n = len(path)
    if n < 3:
        if n > 0:
            pen.moveTo(path[0])
            for pt in path[1:]:
                pen.lineTo(pt)
            pen.closePath()
        return

    # 1. Classify points as on-curve (True) or off-curve (False)
    on_curve = []
    for i in range(n):
        p0 = path[i - 1]
        p1 = path[i]
        p2 = path[(i + 1) % n]
        
        v1 = np.array([p1[0] - p0[0], p1[1] - p0[1]], dtype=np.float64)
        v2 = np.array([p2[0] - p1[0], p2[1] - p1[1]], dtype=np.float64)
        
        len1 = np.hypot(v1[0], v1[1])
        len2 = np.hypot(v2[0], v2[1])
        
        if len1 < 1e-5 or len2 < 1e-5:
            on_curve.append(True)
            continue
            
        dot = np.dot(v1, v2)
        cos_theta = np.clip(dot / (len1 * len2), -1.0, 1.0)
        theta = np.degrees(np.arccos(cos_theta))
        
        on_curve.append(theta > max_deflection_deg)

    # 2. Check if we have at least one on-curve point
    if not any(on_curve):
        p_first = path[0]
        p_last = path[-1]
        start_pt = (int(round((p_first[0] + p_last[0]) / 2)), int(round((p_first[1] + p_last[1]) / 2)))
        pen.moveTo(start_pt)
        pen.qCurveTo(*(path + [start_pt]))
        pen.closePath()
        return

    start_idx = on_curve.index(True)
    ordered_path = path[start_idx:] + path[:start_idx]
    ordered_on = on_curve[start_idx:] + on_curve[:start_idx]
    
    pen.moveTo(ordered_path[0])
    
    i = 1
    m = len(ordered_path)
    while i < m:
        if ordered_on[i]:
            pen.lineTo(ordered_path[i])
            i += 1
        else:
            off_curve_pts = []
            while i < m and not ordered_on[i]:
                off_curve_pts.append(ordered_path[i])
                i += 1
            next_pt = ordered_path[i % m]
            pen.qCurveTo(*(off_curve_pts + [next_pt]))
            i += 1
            
    pen.closePath()


def snap_contour_points(pts: np.ndarray, snap_deg: float = 10.0) -> np.ndarray:
    """Snap segment angles to 0/45/90 for crisp geometric strokes."""
    if len(pts) < 3:
        return pts

    snapped = [pts[0].astype(np.float64)]
    snap_targets = np.arange(0, 181, 45)
    min_len = 6.0

    for i in range(1, len(pts)):
        prev = snapped[-1]
        orig = pts[i].astype(np.float64)
        dx, dy = orig[0] - prev[0], orig[1] - prev[1]
        length = np.hypot(dx, dy)
        if length < min_len:
            snapped.append(orig)
            continue

        angle = np.degrees(np.arctan2(dy, dx)) % 180
        best = snap_targets[np.argmin(np.abs(snap_targets - angle))]
        if abs(best - angle) <= snap_deg:
            rad = np.radians(best)
            candidate = np.array(
                [prev[0] + length * np.cos(rad), prev[1] + length * np.sin(rad)]
            )
            if np.hypot(candidate[0] - orig[0], candidate[1] - orig[1]) <= length * 0.35:
                orig = candidate
        snapped.append(orig)

    return np.round(snapped).astype(np.int32)


def simplify_colinear(points: list[tuple[int, int]], tol: float = 2.5) -> list[tuple[int, int]]:
    """Drop middle points on nearly straight segments for cleaner outlines."""
    if len(points) < 3:
        return points
    out = [points[0]]
    for i in range(1, len(points) - 1):
        ax, ay = out[-1]
        bx, by = points[i]
        cx, cy = points[i + 1]
        area = abs((bx - ax) * (cy - ay) - (by - ay) * (cx - ax))
        seg = np.hypot(cx - ax, cy - ay)
        if seg > 0 and area / seg > tol:
            out.append((bx, by))
    out.append(points[-1])
    return out


def refine_contour_subpixel(contour: np.ndarray, gray_crop: np.ndarray, threshold: float = 127.0) -> np.ndarray:
    """
    Refines integer contour point coordinates to sub-pixel accuracy.
    For each point, it samples intensities along the normal vector in the original grayscale image
    and computes the linear interpolation zero-crossing of (intensity - threshold).
    """
    pts = contour.reshape(-1, 2)
    n = len(pts)
    if n < 3:
        return contour

    h, w = gray_crop.shape
    refined_pts = []

    for i in range(n):
        p = pts[i].astype(np.float64)
        p_prev = pts[i - 1].astype(np.float64)
        p_next = pts[(i + 1) % n].astype(np.float64)

        # Tangent vector
        tx, ty = p_next[0] - p_prev[0], p_next[1] - p_prev[1]
        t_len = np.hypot(tx, ty)
        if t_len < 1e-5:
            refined_pts.append(p)
            continue

        # Normal vector (orthogonal to tangent, pointing outwards)
        nx, ny = -ty / t_len, tx / t_len

        # Sample grayscale intensities along the normal at: t in [-1.5, 1.5]
        samples = []
        t_vals = [-1.5, -1.0, -0.5, 0.0, 0.5, 1.0, 1.5]
        valid = True
        for t in t_vals:
            sx = p[0] + t * nx
            sy = p[1] + t * ny
            # Bilinear interpolation
            ix = int(np.floor(sx))
            iy = int(np.floor(sy))
            if 0 <= ix < w - 1 and 0 <= iy < h - 1:
                dx, dy = sx - ix, sy - iy
                val = (1 - dx) * (1 - dy) * gray_crop[iy, ix] + \
                      dx * (1 - dy) * gray_crop[iy, ix + 1] + \
                      (1 - dx) * dy * gray_crop[iy + 1, ix] + \
                      dx * dy * gray_crop[iy + 1, ix + 1]
                samples.append((t, val))
            else:
                valid = False
                break

        if not valid or len(samples) < 2:
            refined_pts.append(p)
            continue

        # Find where intensity crosses the threshold
        ref_t = None
        for j in range(len(samples) - 1):
            t_a, val_a = samples[j]
            t_b, val_b = samples[j+1]
            diff_a = val_a - threshold
            diff_b = val_b - threshold
            if diff_a * diff_b <= 0.0:
                if abs(diff_b - diff_a) > 1e-5:
                    fraction = -diff_a / (diff_b - diff_a)
                    ref_t = t_a + fraction * (t_b - t_a)
                else:
                    ref_t = (t_a + t_b) / 2.0
                break

        if ref_t is not None and abs(ref_t) <= 1.5:
            p_ref = p + ref_t * np.array([nx, ny])
            refined_pts.append(p_ref)
        else:
            refined_pts.append(p)

    return np.array(refined_pts, dtype=np.float32).reshape(-1, 1, 2)


def rdp_simplify(points: list[tuple[float, float]], epsilon: float) -> list[tuple[float, float]]:
    """
    Ramer-Douglas-Peucker algorithm to simplify 2D paths.
    Fits straight lines globally within an epsilon tolerance.
    """
    if len(points) < 3:
        return points

    dmax = 0.0
    index = 0
    end = len(points) - 1

    ax, ay = points[0]
    bx, by = points[end]
    dx, dy = bx - ax, by - ay
    dist_ab = np.hypot(dx, dy)

    for i in range(1, end):
        px, py = points[i]
        if dist_ab > 1e-5:
            area = abs(dx * (ay - py) - dy * (ax - px))
            d = area / dist_ab
        else:
            d = np.hypot(px - ax, py - ay)

        if d > dmax:
            index = i
            dmax = d

    if dmax > epsilon:
        rec1 = rdp_simplify(points[:index + 1], epsilon)
        rec2 = rdp_simplify(points[index:], epsilon)
        return rec1[:-1] + rec2
    else:
        return [points[0], points[end]]


def apply_extrema_constraints(path: list[tuple[float, float]], tolerance: float = 8.0) -> list[tuple[float, float]]:
    """
    Detects extreme points (local min/max in X and Y) and forces their neighboring points
    to align horizontally or vertically, ensuring perfect Bézier tangencies at the extrema.
    """
    n = len(path)
    if n < 3:
        return path

    xs = [p[0] for p in path]
    ys = [p[1] for p in path]

    min_x_idx = int(np.argmin(xs))
    max_x_idx = int(np.argmax(xs))
    min_y_idx = int(np.argmin(ys))
    max_y_idx = int(np.argmax(ys))

    extrema = {
        min_x_idx: 'vert',
        max_x_idx: 'vert',
        min_y_idx: 'horiz',
        max_y_idx: 'horiz'
    }

    modified_path = list(path)
    for idx, alignment in extrema.items():
        prev_idx = (idx - 1) % n
        next_idx = (idx + 1) % n
        
        target = path[idx]
        
        if alignment == 'horiz':
            if abs(path[prev_idx][1] - target[1]) <= tolerance:
                modified_path[prev_idx] = (path[prev_idx][0], target[1])
            if abs(path[next_idx][1] - target[1]) <= tolerance:
                modified_path[next_idx] = (path[next_idx][0], target[1])
        elif alignment == 'vert':
            if abs(path[prev_idx][0] - target[0]) <= tolerance:
                modified_path[prev_idx] = (target[0], path[prev_idx][1])
            if abs(path[next_idx][0] - target[0]) <= tolerance:
                modified_path[next_idx] = (target[0], path[next_idx][1])

    return modified_path
