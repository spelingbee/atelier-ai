"""
AtelierAI — ВЕРХНИЙ КРОЙ / ОВЕРЛЕИ (Фаза 3, NEW FILE, аддитивно).

Ядро (patterns.py/export.py), Фаза 1 (components.py) и Фаза 2 (reconcile.py)
НЕ РЕДАКТИРУЮТСЯ. Здесь даётся РЕАЛЬНАЯ ГЕОМЕТРИЯ верхних слоёв,
которые в Фазе 1 были только маркерами: баска (peplum), кокетка-оверлей
(yoke_overlay), флап-запах (flap), драпировка/бант (bow). Плюс порядок
наложения слоёв (z-order) и порядок пошива многослойного изделия.

Все длины в сантиметрах.
"""
from __future__ import annotations

import math
import os
from dataclasses import dataclass, field
from typing import List, Dict, Optional

import patterns as P
from patterns import Measurements, PatternPiece
import components as C
import export
from geometry_modifiers import cut_yoke


# --------------------------------------------------------------------------- #
#  Результат построения оверлея
# --------------------------------------------------------------------------- #
@dataclass
class OverlayResult:
    key: str
    title: str
    pieces: List[PatternPiece]
    attach: str               # waist | hip
    attach_len_cm: float      # длина притачного среза оверлея
    layer: int                # z-order над базой (0 = базовый силуэт)
    sewing_steps: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)
    geometry_ready: bool = True


# --------------------------------------------------------------------------- #
#  Геом-помощники
# --------------------------------------------------------------------------- #
def _r2(p):
    return (round(p[0], 2), round(p[1], 2))


def _close(pts):
    out = [_r2(p) for p in pts]
    if out[0] != out[-1]:
        out.append(out[0])
    return out


def _label(text, x, y):
    return [{"text": text, "x": round(x, 2), "y": round(y, 2), "size": 1.0, "bold": True}]


def _annular_sector(r_in, r_out, sweep_rad, steps=24):
    """Кольцевой сектор (простой многоугольник): внешняя дуга туда,
    внутренняя обратно."""
    pts = []
    for i in range(steps + 1):
        a = sweep_rad * i / steps
        pts.append((r_out * math.cos(a), r_out * math.sin(a)))
    for i in range(steps, -1, -1):
        a = sweep_rad * i / steps
        pts.append((r_in * math.cos(a), r_in * math.sin(a)))
    return _close(pts)


# --------------------------------------------------------------------------- #
#  Параметры
# --------------------------------------------------------------------------- #
_PEPLUM_LEN = 18.0


# --------------------------------------------------------------------------- #
#  Баска (peplum): кольцевая волан-деталь, внутр. срез = талии
# --------------------------------------------------------------------------- #
def _peplum(m: Measurements) -> OverlayResult:
    waist_eff = m.waist_cm + m.ease_waist
    # две половины по 180°; сумма внутренних дуг = 2π·r_in = талии
    r_in = waist_eff / (2 * math.pi)
    r_out = r_in + _PEPLUM_LEN
    pts = _annular_sector(r_in, r_out, math.pi, steps=24)
    piece = PatternPiece(
        name="peplum_panel", points=pts,
        grain_line=((0.0, round(r_in, 2)), (0.0, round(r_out, 2))),
        labels=_label("БАСКА × 2", 0.0, (r_in + r_out) / 2),
        notches=[(round(r_in, 2), 0.0)], cut_on_fold=False, quantity=2)
    steps = [
        "Скроить баску как кольцевую деталь (2 половины).",
        "Притачать внутренний срез к талии поверх базы, шов вверх.",
        "Обработать нижний край баски подгибкой.",
    ]
    return OverlayResult(
        "peplum", "Баска", [piece], "waist", round(2 * math.pi * r_in, 1),
        layer=1, sewing_steps=steps,
        notes=[f"Внутр. радиус {r_in:.1f} см, длина {_PEPLUM_LEN:g} см; "
               f"внутренний срез = талии {waist_eff:g} см."])


# --------------------------------------------------------------------------- #
#  Кокетка-оверлей (yoke_overlay): облегающая панель талия→бёдра
#  (именно такая кокетка на чёрной юбке с фото)
# --------------------------------------------------------------------------- #
def _yoke(m: Measurements) -> OverlayResult:
    depth = m.hip_depth
    waist_eff = m.waist_cm + m.ease_waist
    
    # Generate yoke pieces dynamically from base panels using cut_yoke
    base_front = P.StraightSkirtPattern(m).front_panel()
    base_back = P.StraightSkirtPattern(m).back_panel()
    
    front = cut_yoke(base_front, depth)[0]
    back = cut_yoke(base_back, depth)[0]
    
    front.name = "yoke_overlay_front"
    back.name = "yoke_overlay_back"
    
    front.labels = [{"text": "КОКЕТКА ПЕРЕД × 1 (сгиб)", "x": m.H * 0.25, "y": depth * 0.5, "size": 1.0, "bold": True}]
    back.labels = [{"text": "КОКЕТКА СПИНКА × 1 (сгиб)", "x": m.H * 0.25, "y": depth * 0.5, "size": 1.0, "bold": True}]
    
    front.grain_line = ((m.H * 0.25, 2), (m.H * 0.25, depth - 2))
    back.grain_line = ((m.H * 0.25, 2), (m.H * 0.25, depth - 2))
    front.cut_on_fold = True
    back.cut_on_fold = True
    front.quantity = 1
    back.quantity = 1
    
    steps = [
        "Стачать боковые швы кокетки.",
        "Наложить кокетку на базу по талиевому срезу, скрепить.",
        "Притачать пояс, фиксируя кокетку и базу одним швом.",
    ]
    return OverlayResult(
        "yoke_overlay", "Кокетка-оверлей", [front, back], "waist",
        round(waist_eff, 1), layer=1, sewing_steps=steps,
        notes=[f"Глубина кокетки {depth:g} см (до линии бёдер); низ кокетки = бёдра."])


# --------------------------------------------------------------------------- #
#  Флап-запах (flap): асимметричный передник внахлёст
# --------------------------------------------------------------------------- #
def _flap(m: Measurements) -> OverlayResult:
    waist_eff = m.waist_cm + m.ease_waist
    L = m.length_cm
    Wf = waist_eff * 0.55
    Lshort = L * 0.45
    Llong = L * 0.70
    pts = [(0.0, 0.0), (Wf, 0.0), (Wf, Lshort), (0.0, Llong)]
    piece = PatternPiece(
        name="flap_panel", points=_close(pts),
        grain_line=((round(Wf * 0.5, 2), 2.0), (round(Wf * 0.5, 2), round(Lshort - 2.0, 2))),
        labels=_label("ФЛАП-ЗАПАХ × 1", Wf * 0.4, Lshort * 0.5),
        notches=[(round(Wf, 2), 0.0)], cut_on_fold=False, quantity=1)
    steps = [
        "Скроить флап-запах (асимметричный передник).",
        "Обработать диагональный и боковые срезы.",
        "Настрочить флап на перёд по талии внахлёст, верх — под пояс.",
    ]
    return OverlayResult(
        "flap", "Флап-запах", [piece], "waist", round(Wf, 1), layer=2,
        sewing_steps=steps,
        notes=[f"Ширина по талии {Wf:.0f} см (~0.55 талии); "
               f"асимметричный низ {Lshort:.0f}→{Llong:.0f} см."])


# --------------------------------------------------------------------------- #
#  Драпировка/бант (bow): лента-пояс + узел
# --------------------------------------------------------------------------- #
def _bow(m: Measurements) -> OverlayResult:
    waist_eff = m.waist_cm + m.ease_waist
    tie_w = 12.0
    tie_len = waist_eff + 90.0
    tie = [(0.0, 0.0), (tie_len, 0.0), (tie_len, tie_w), (0.0, tie_w)]
    tie_piece = PatternPiece(
        name="bow_tie", points=_close(tie),
        grain_line=((2.0, tie_w * 0.5), (round(tie_len - 2.0, 2), tie_w * 0.5)),
        labels=_label("ЛЕНТА-ПОЯС × 1", tie_len * 0.5, tie_w * 0.5),
        notches=[(round(waist_eff, 2), 0.0)], cut_on_fold=False, quantity=1)
    knot_w, knot_h = 18.0, 14.0
    knot = [(0.0, 0.0), (knot_w, 0.0), (knot_w, knot_h), (0.0, knot_h)]
    knot_piece = PatternPiece(
        name="bow_knot", points=_close(knot),
        grain_line=((2.0, knot_h * 0.5), (round(knot_w - 2.0, 2), knot_h * 0.5)),
        labels=_label("БАНТ-УЗЕЛ × 1", knot_w * 0.5, knot_h * 0.5),
        notches=[], cut_on_fold=False, quantity=1)
    steps = [
        "Стачать ленту-пояс вдоль, вывернуть, заутюжить.",
        "Обернуть лентой талию поверх базы, концы на завязку.",
        "Сформировать бант узлом и закрепить.",
    ]
    return OverlayResult(
        "bow", "Драпировка/бант", [tie_piece, knot_piece], "waist",
        round(waist_eff, 1), layer=3, sewing_steps=steps,
        notes=[f"Лента {tie_w:g}×{tie_len:.0f} см обхватывает талию {waist_eff:g} см."])


_BUILDERS = {"peplum": _peplum, "yoke_overlay": _yoke, "flap": _flap, "bow": _bow}


def build_overlay(key: str, m: Measurements) -> Optional[OverlayResult]:
    if key in (None, "none"):
        return None
    fn = _BUILDERS.get(key)
    if not fn:
        raise ValueError(f"оверлей '{key}' не поддержан Фазой 3")
    return fn(m)


# Аддитивно помечаем реализованные оверлеи как готовые (без правки components.py)
for _k in _BUILDERS:
    if _k in C.OVERLAY_SPECS:
        C.OVERLAY_SPECS[_k].geometry_ready = True


# --------------------------------------------------------------------------- #
#  Многослойная сборка: база + оверлей с z-порядком
# --------------------------------------------------------------------------- #
@dataclass
class LayeredAssembly:
    assembly: C.Assembly
    overlay: Optional[OverlayResult]
    pieces: List[PatternPiece]
    layer_plan: List[Dict]
    sewing_order: List[str]


def assemble(selection: Dict[str, object], m: Measurements) -> LayeredAssembly:
    a = C.resolve(selection, m)
    silh = a.selection[C.SLOT_SILHOUETTE]
    ov = build_overlay(a.selection.get(C.SLOT_OVERLAY, "none"), m)
    pieces = list(a.pieces)
    layers = [{"layer": 0, "title": f"База: {C.SILHOUETTE_TITLES.get(silh, silh)}", "attach": "waist"}]
    order = list(a.sewing_spec)
    if ov:
        pieces = pieces + ov.pieces
        layers.append({"layer": ov.layer, "title": ov.title, "attach": ov.attach})
        order = order + [f"[слой {ov.layer}] {s}" for s in ov.sewing_steps]
    layers.sort(key=lambda d: d["layer"])
    return LayeredAssembly(a, ov, pieces, layers, order)


# --------------------------------------------------------------------------- #
#  verify_overlay: сшиваема ли геометрия верхнего кроя
# --------------------------------------------------------------------------- #
@dataclass
class OverlayCheck:
    ok: bool
    fails: List[str] = field(default_factory=list)
    warns: List[str] = field(default_factory=list)
    infos: List[str] = field(default_factory=list)


def verify_overlay(key: str, m: Measurements,
                   export_prefix: Optional[str] = None) -> OverlayCheck:
    import verify_sewable as V
    res = OverlayCheck(ok=True)
    ov = build_overlay(key, m)
    if ov is None:
        res.infos.append("оверлей 'none' — нет геометрии")
        return res
    for p in ov.pieces:
        pts = p.points
        if pts[0] != pts[-1]:
            res.fails.append(f"{p.name}: контур не замкнут"); continue
        if V._area(pts) < 5:
            res.fails.append(f"{p.name}: площадь мала"); continue
        if V._min_edge(pts) < 0.05:
            res.fails.append(f"{p.name}: нулевое ребро"); continue
        if not V._is_simple(pts):
            res.fails.append(f"{p.name}: самопересечение"); continue
        if V._area(export.seam_outline(pts, m.seam_allowance)) <= V._area(pts) + 1:
            res.warns.append(f"{p.name}: припуск не увеличил контур")
    if not res.fails:
        res.infos.append(f"геометрия всех {len(ov.pieces)} деталей оверлея корректна")

    waist_eff = m.waist_cm + m.ease_waist
    if ov.attach == "waist":
        if ov.key == "flap" or abs(ov.attach_len_cm - waist_eff) <= max(1.5, waist_eff * 0.02):
            res.infos.append(f"стык по талии: срез оверлея {ov.attach_len_cm:g} см")
        else:
            res.warns.append(f"стык: срез {ov.attach_len_cm:g} ≠ талия {waist_eff:g} см")

    if export_prefix:
        svg = f"/data/skirt/{export_prefix}.svg"
        pdf = f"/data/skirt/{export_prefix}.pdf"
        w, h = export.export_svg(ov.pieces, svg)
        rows, cols = export.export_pdf_tiled(ov.pieces, pdf)
        if (os.path.exists(svg) and os.path.getsize(svg) > 200
                and os.path.exists(pdf) and os.path.getsize(pdf) > 500
                and w > 0 and h > 0):
            res.infos.append(f"экспорт оверлея OK: {w:.0f}×{h:.0f} см, A4 {rows}×{cols}")
        else:
            res.fails.append("экспорт оверлея не удался")

    res.ok = not res.fails
    return res


# Регистрация дополнительных драпировок
import drapes  # noqa: F401

