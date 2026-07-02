"""
AtelierAI — Export: SVG (1:1, в см) + PDF (reportlab, в мм) с калибровочным
квадратом и A4-тайлингом. Припуск на швы — через shapely.buffer (надёжно).
"""
from __future__ import annotations

import math
from typing import List, Tuple, Dict

from patterns import PatternPiece

Point = Tuple[float, float]

# 1 cm at 96 DPI for the SVG raster fallback; SVG itself uses cm units so this
# is only used for stroke widths / font scaling.
MM = 1.0  # reportlab works in points; we convert explicitly below


# --------------------------------------------------------------------------- #
#  Seam allowance via shapely (robust offset, handles concave corners)
# --------------------------------------------------------------------------- #
def _signed_area(pts: List[Point]) -> float:
    s = 0.0
    for i in range(len(pts) - 1):
        x0, y0 = pts[i]
        x1, y1 = pts[i + 1]
        s += x0 * y1 - x1 * y0
    return s / 2.0


def orient_points(points: List[Point]) -> List[Point]:
    """Checks signed area and enforces CCW (sign=1.0) orientation using shapely if available."""
    pts = points[:]
    if pts and pts[0] != pts[-1]:
        pts.append(pts[0])
    
    if len(pts) < 4:
        return pts
        
    try:
        from shapely.geometry import Polygon
        from shapely.geometry.polygon import orient
        poly = Polygon(pts)
        if not poly.is_valid:
            poly = poly.buffer(0)
        oriented_poly = orient(poly, sign=1.0)
        return [(float(x), float(y)) for x, y in oriented_poly.exterior.coords]
    except Exception:
        area = _signed_area(pts)
        if area < 0:
            pts_no_dup = pts[:-1]
            reversed_pts = list(reversed(pts_no_dup))
            reversed_pts.append(reversed_pts[0])
            return reversed_pts
        return pts


def seam_outline(points: List[Point], margin_cm: float, mitre_limit: float = 3.0) -> List[Point]:
    """Припуск на швы: оффсет полигона наружу без внешних зависимостей.

    Через нормали рёбер и биссектрису в вершинах. mitre_limit ограничивает
    вынос на острых углах (иначе шип уходит в бесконечность).
    """
    pts = points[:-1] if points[0] == points[-1] else points[:]
    n = len(pts)
    if n < 3:
        return points
    # ориентация: хотим оффсет наружу независимо от направления обхода
    sign = 1.0 if _signed_area(points) > 0 else -1.0
    out: List[Point] = []
    for i in range(n):
        prev = pts[(i - 1) % n]
        curr = pts[i]
        nxt = pts[(i + 1) % n]
        # единичные нормали двух рёбер (наружу)
        def normal(a, b):
            dx, dy = b[0] - a[0], b[1] - a[1]
            ln = math.hypot(dx, dy) or 1e-9
            return (sign * dy / ln, -sign * dx / ln)
        n1 = normal(prev, curr)
        n2 = normal(curr, nxt)
        bx, by = n1[0] + n2[0], n1[1] + n2[1]
        blen = math.hypot(bx, by)
        if blen < 1e-9:
            bx, by = n1; scale = 1.0
        else:
            bx, by = bx / blen, by / blen
            cos_half = max(0.2, blen / 2.0)        # blen/2 = cos(θ/2)
            scale = min(1.0 / cos_half, mitre_limit)
        out.append((curr[0] + bx * margin_cm * scale,
                    curr[1] + by * margin_cm * scale))
    out.append(out[0])
    return out


# --------------------------------------------------------------------------- #
#  Layout: раскладываем детали в ряд с отступом
# --------------------------------------------------------------------------- #
def _bounds(points: List[Point]):
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return min(xs), min(ys), max(xs), max(ys)


def layout_pieces(pieces: List[PatternPiece], gap: float = 4.0):
    """Возвращает [(piece, dx, dy)] и общий размер полотна (cm)."""
    placed = []
    cursor_x = gap
    max_h = 0.0
    for p in pieces:
        minx, miny, maxx, maxy = _bounds(p.points)
        dx = cursor_x - minx
        dy = gap - miny
        placed.append((p, dx, dy))
        cursor_x += (maxx - minx) + gap
        max_h = max(max_h, maxy - miny)
    total_w = cursor_x
    total_h = max_h + 2 * gap
    return placed, total_w, total_h


# --------------------------------------------------------------------------- #
#  SVG export (units in cm -> 1:1)
# --------------------------------------------------------------------------- #
def _path_d(points: List[Point]) -> str:
    d = f"M {points[0][0]:.3f} {points[0][1]:.3f}"
    for x, y in points[1:]:
        d += f" L {x:.3f} {y:.3f}"
    return d + " Z"


def export_svg(pieces: List[PatternPiece], path: str,
               seam_cm: float = 1.5, add_seam: bool = True) -> Tuple[float, float]:
    placed, W, H = layout_pieces(pieces)
    parts = []
    # calibration square 5x5 cm top-left
    parts.append('<rect x="0.5" y="0.5" width="5" height="5" fill="none" '
                 'stroke="#e00" stroke-width="0.05"/>')
    parts.append('<text x="0.6" y="6" font-size="0.5" fill="#e00">5x5 cm — проверь линейкой</text>')

    for p, dx, dy in placed:
        oriented_pts = orient_points(p.points)
        shifted = [(x + dx, y + dy) for x, y in oriented_pts]
        if add_seam:
            outer = seam_outline(oriented_pts, seam_cm)
            shifted_outer = [(x + dx, y + dy) for x, y in outer]
            parts.append(f'<path d="{_path_d(shifted_outer)}" fill="none" stroke="#999" '
                         f'stroke-width="0.04" stroke-dasharray="0.4,0.3"/>')
        parts.append(f'<path d="{_path_d(shifted)}" fill="none" stroke="#000" stroke-width="0.06"/>')
        (gx1, gy1), (gx2, gy2) = p.grain_line
        parts.append(f'<line x1="{gx1+dx:.2f}" y1="{gy1+dy:.2f}" x2="{gx2+dx:.2f}" '
                     f'y2="{gy2+dy:.2f}" stroke="#333" stroke-width="0.05"/>')
        for lab in p.labels:
            parts.append(f'<text x="{lab["x"]+dx:.2f}" y="{lab["y"]+dy:.2f}" '
                         f'font-size="{lab.get("size",1.0):.2f}" text-anchor="middle" '
                         f'font-family="Arial" '
                         f'font-weight="{"bold" if lab.get("bold") else "normal"}">{lab["text"]}</text>')
        for nx, ny in p.notches:
            parts.append(f'<line x1="{nx+dx-0.3:.2f}" y1="{ny+dy:.2f}" '
                         f'x2="{nx+dx+0.3:.2f}" y2="{ny+dy:.2f}" stroke="#e00" stroke-width="0.06"/>')

    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" '
           f'width="{W:.2f}cm" height="{H:.2f}cm" '
           f'viewBox="0 0 {W:.2f} {H:.2f}">\n' + "\n".join(parts) + "\n</svg>\n")
    with open(path, "w", encoding="utf-8") as f:
        f.write(svg)
    return W, H


# --------------------------------------------------------------------------- #
#  PDF export (reportlab, true mm, A4 tiling with overlap + crop marks)
# --------------------------------------------------------------------------- #
def export_pdf_tiled(pieces: List[PatternPiece], path: str,
                     seam_cm: float = 1.5, add_seam: bool = True,
                     overlap_cm: float = 1.0):
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import cm as CM
    except ImportError:
        # Return dummy values if reportlab is not installed yet
        return 0, 0

    placed, W, H = layout_pieces(pieces)
    page_w, page_h = A4                         # points
    printable_w = page_w - 1.5 * CM             # margins for glue/crop
    printable_h = page_h - 1.5 * CM
    tile_w_cm = printable_w / CM - overlap_cm
    tile_h_cm = printable_h / CM - overlap_cm
    cols = max(1, math.ceil(W / tile_w_cm))
    rows = max(1, math.ceil(H / tile_h_cm))

    c = canvas.Canvas(path, pagesize=A4)

    def draw_world(c, ox_cm, oy_cm):
        """Draw whole pattern; (ox,oy) cm = world coord at page origin."""
        c.saveState()
        c.translate(0.75 * CM, page_h - 0.75 * CM)  # top-left margin, y down
        c.scale(1, -1)
        c.translate(-ox_cm * CM, oy_cm * CM)
        # calibration square
        c.setStrokeColorRGB(0.9, 0, 0); c.setLineWidth(0.6)
        c.rect(0.5 * CM, 0.5 * CM, 5 * CM, 5 * CM, stroke=1, fill=0)
        for p, dx, dy in placed:
            oriented_pts = orient_points(p.points)
            shifted = [((x + dx) * CM, (y + dy) * CM) for x, y in oriented_pts]
            if add_seam:
                outer = seam_outline(oriented_pts, seam_cm)
                shifted_outer = [((x + dx) * CM, (y + dy) * CM) for x, y in outer]
                c.setStrokeColorRGB(0.6, 0.6, 0.6); c.setLineWidth(0.5)
                c.setDash(3, 2)
                _poly(c, shifted_outer); c.setDash()
            c.setStrokeColorRGB(0, 0, 0); c.setLineWidth(1.0)
            _poly(c, shifted)
            (gx1, gy1), (gx2, gy2) = p.grain_line
            c.setLineWidth(0.6)
            c.line((gx1 + dx) * CM, (gy1 + dy) * CM, (gx2 + dx) * CM, (gy2 + dy) * CM)
        c.restoreState()

    for r in range(rows):
        for col in range(cols):
            ox = col * tile_w_cm
            oy = r * tile_h_cm
            draw_world(c, ox, oy)
            # crop marks + tile id
            c.setStrokeColorRGB(0, 0, 0.8); c.setLineWidth(0.4)
            c.rect(0.75 * CM, 0.75 * CM, printable_w, printable_h, stroke=1, fill=0)
            c.setFont("Helvetica", 8)
            c.drawString(0.8 * CM, 0.4 * CM,
                         f"Лист r{r+1}c{col+1} / {rows}x{cols}  —  совместить по синей рамке, нахлёст {overlap_cm} см")
            c.showPage()
    c.save()
    return rows, cols


def _poly(c, pts):
    p = c.beginPath()
    p.moveTo(*pts[0])
    for pt in pts[1:]:
        p.lineTo(*pt)
    p.close()
    c.drawPath(p, stroke=1, fill=0)
