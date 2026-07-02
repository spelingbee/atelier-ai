"""
AtelierAI — Надёжный припуск на швы через shapely.buffer (NEW FILE, аддитивный).

Заменяет ручной offset из export.py на shapely.buffer (надёжно на вогнутых
углах и самопересечениях). Движок НЕ редактируем — подключается монки-патчем:

    import export
    import seam_shapely        # при импорте автоматически патчит export.seam_outline
    export.export_svg(pieces, "out.svg")

Если shapely не установлен — используется проверенный pure-python фолбэк
(тот же алгоритм, что в export.py), чтобы ничего не падало.
Установка shapely:  pip install shapely
"""
from __future__ import annotations

import math
from typing import List, Tuple

Point = Tuple[float, float]

try:
    from shapely.geometry import Polygon
    from shapely.geometry import JOIN_STYLE
    from shapely.geometry.polygon import orient
    _HAS_SHAPELY = True
except Exception:
    _HAS_SHAPELY = False


def _signed_area(pts: List[Point]) -> float:
    s = 0.0
    for i in range(len(pts) - 1):
        x0, y0 = pts[i]
        x1, y1 = pts[i + 1]
        s += x0 * y1 - x1 * y0
    return s / 2.0


def _fallback(points: List[Point], margin_cm: float, mitre_limit: float = 3.0) -> List[Point]:
    """Копия алгоритма из export.py (нормали рёбер + биссектриса)."""
    pts = points[:-1] if points[0] == points[-1] else points[:]
    n = len(pts)
    if n < 3:
        return points
    sign = 1.0 if _signed_area(points) > 0 else -1.0
    out: List[Point] = []
    for i in range(n):
        prev = pts[(i - 1) % n]
        curr = pts[i]
        nxt = pts[(i + 1) % n]
        def normal(a, b):
            dx, dy = b[0] - a[0], b[1] - a[1]
            ln = math.hypot(dx, dy) or 1e-9
            return (sign * dy / ln, -sign * dx / ln)
        n1 = normal(prev, curr)
        n2 = normal(curr, nxt)
        bx, by = n1[0] + n2[0], n1[1] + n2[1]
        blen = math.hypot(bx, by)
        if blen < 1e-9:
            bx, by = n1
            scale = 1.0
        else:
            bx, by = bx / blen, by / blen
            cos_half = max(0.2, blen / 2.0)
            scale = min(1.0 / cos_half, mitre_limit)
        out.append((curr[0] + bx * margin_cm * scale, curr[1] + by * margin_cm * scale))
    out.append(out[0])
    return out


def seam_outline(points: List[Point], margin_cm: float, mitre_limit: float = 3.0) -> List[Point]:
    """Припуск на швы. Если есть shapely — через .buffer (надёжно), иначе фолбэк."""
    if not _HAS_SHAPELY or margin_cm == 0:
        return _fallback(points, margin_cm, mitre_limit)
    try:
        poly = Polygon(points)
        if not poly.is_valid:
            poly = poly.buffer(0)            # чинит самопересечения
        off = poly.buffer(abs(margin_cm),
                          join_style=JOIN_STYLE.mitre, mitre_limit=mitre_limit)
        if off.is_empty:
            return _fallback(points, margin_cm, mitre_limit)
        geom = off
        if geom.geom_type == "MultiPolygon":     # на всякий случай — берём самый большой
            geom = max(geom.geoms, key=lambda g: g.area)
        geom = orient(geom, sign=1.0)
        return [(float(x), float(y)) for x, y in geom.exterior.coords]
    except Exception:
        return _fallback(points, margin_cm, mitre_limit)


def patch_export():
    """Подменяет export.seam_outline на shapely-версию (export_svg/pdf берут её из глобалов)."""
    import export
    export.seam_outline = seam_outline
    return export


# автопатч при импорте
try:
    patch_export()
    _PATCHED = True
except Exception:
    _PATCHED = False


def status() -> str:
    return (f"shapely={'есть' if _HAS_SHAPELY else 'нет (фолбэк)'}, "
            f"export пропатчен={'да' if _PATCHED else 'нет'}")
