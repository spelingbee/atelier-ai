"""
AtelierAI — ДРАПИРОВКИ (NEW FILE, аддитивно, Фаза 3+).

Ядро (patterns.py / export.py), Фаза 1 (components.py) и оверлеи (overlays.py)
НЕ РЕДАКТИРУЮТСЯ. Здесь добавляются НАСТОЯЩИЕ драпировки как верхний крой
(слот OVERLAY): мягкие заложенные складки ткани — в отличие от существующего
'bow' (лента-пояс с узлом).

2 типа:
  • cowl_front   — косая драпировка спереди (cowl): крой по косой, мягкие
                   провисающие складки по верхнему срезу переда.
  • cascade_side — каскад/водопад сбоку: сектор кольца, внешний срез ложится
                   асимметричным водопадом складок вдоль бока.

Модуль САМ регистрируется:
  • в overlays._BUILDERS  → overlays.build_overlay/assemble/verify_overlay
    подхватывают новые ключи;
  • в components.OVERLAY_SPECS → components.resolve принимает их без
    предупреждения (geometry_ready=True).

Все координаты в сантиметрах. X = ширина (вправо), Y = вниз. Отрицательный Y
у cowl — провис над линией талии; раскладка при экспорте сдвигает всё в
положительные координаты.
"""
from __future__ import annotations

import math
from typing import List

from patterns import Measurements, PatternPiece
import components as C
import overlays as O



# --------------------------------------------------------------------------- #
#  1. Косая драпировка спереди (COWL)
# --------------------------------------------------------------------------- #
def _cowl(m: Measurements, swags: int = 2, swag_rise: float = 11.0) -> O.OverlayResult:
    waist_eff = m.waist_cm + m.ease_waist
    front_w = waist_eff * 0.5                   # ширина переда по талии (стык)
    L = m.hip_depth + 16.0                       # длина драпированной панели
    bottom_extra = 4.0
    steps_per = 16

    top: List = []
    for s in range(swags):
        x0 = front_w * s / swags
        x1 = front_w * (s + 1) / swags
        c = (x0 + x1) / 2.0
        half = (x1 - x0) / 2.0
        start_i = 1 if s > 0 else 0              # не дублировать стык сегментов
        for i in range(start_i, steps_per + 1):
            x = x0 + (x1 - x0) * i / steps_per
            t = (x - c) / half
            y = -swag_rise * (1.0 - t * t)       # провис вверх (над талией)
            top.append((x, y))

    pts = list(top) + [(front_w + bottom_extra, L), (-bottom_extra, L)]
    pts = O._close(pts)

    cx = front_w * 0.5
    g = 8.0
    piece = PatternPiece(
        name="drape_cowl_front", points=pts,
        grain_line=((round(cx - g / 2, 2), round(L * 0.4 - g / 2, 2)),
                    (round(cx + g / 2, 2), round(L * 0.4 + g / 2, 2))),   # косая 45°
        labels=O._label("ДРАПИРОВКА COWL × 1 (по косой)", cx, L * 0.55),
        notches=[(round(front_w, 2), 0.0)], cut_on_fold=False, quantity=1)

    steps = [
        "Выкроить переднюю драпированную панель ПО КОСОЙ (долевая под 45°).",
        f"Верхний фигурный срез заложить {swags} мягкими складками-cowl, "
        f"припосадить до ширины переда {front_w:.0f} см.",
        "Притачать верхний срез к талии переда поверх базы; складки направить вниз.",
        "Боковые срезы вложить в боковые швы; низ обработать подгибкой.",
    ]
    notes = [
        f"Крой по косой; {swags} мягких провиса, центр поднят на {swag_rise:g} см "
        f"→ излишек уходит в cowl-складки.",
        f"Низ панели на {L:.0f} см (≈ до линии бёдер).",
    ]
    return O.OverlayResult(
        "cowl_front", "Косая драпировка (cowl)", [piece], "waist_front",
        round(front_w, 1), layer=2, sewing_steps=steps, notes=notes)


# --------------------------------------------------------------------------- #
#  2. Каскад/водопад сбоку (CASCADE)
# --------------------------------------------------------------------------- #
def _cascade(m: Measurements, sweep_deg: float = 160.0) -> O.OverlayResult:
    attach_len = m.length_cm * 0.55              # длина притачивания вдоль бока
    sweep = math.radians(sweep_deg)
    r_in = attach_len / sweep
    cascade_len = m.length_cm * 0.5
    r_out = r_in + cascade_len

    pts = O._annular_sector(r_in, r_out, sweep, steps=28)

    mid = sweep / 2.0
    g_in = (r_in * math.cos(mid), r_in * math.sin(mid))
    g_out = (r_out * math.cos(mid), r_out * math.sin(mid))
    lab_r = (r_in + r_out) / 2.0
    lab = (lab_r * math.cos(mid), lab_r * math.sin(mid))
    piece = PatternPiece(
        name="drape_cascade_side", points=pts,
        grain_line=(O._r2(g_in), O._r2(g_out)),       # радиальная (косая к срезам)
        labels=O._label("КАСКАД-ВОДОПАД × 1", lab[0], lab[1]),
        notches=[O._r2(g_in)], cut_on_fold=False, quantity=1)

    outer_arc = r_out * sweep
    steps = [
        "Выкроить каскад как сектор кольца (радиальный крой → мягкие волны).",
        f"Притачать короткий внутренний срез ({attach_len:.0f} см) к боковому "
        f"шву/талии сверху вниз.",
        "Внешний срез обработать узкой подгибкой — он ляжет водопадом складок.",
        "Для симметрии — зеркалить вторую деталь на противоположный бок.",
    ]
    notes = [
        f"Сектор кольца: r_вн {r_in:.1f} → r_нар {r_out:.1f} см, разворот {sweep_deg:g}°.",
        f"Внешний срез {outer_arc:.0f} см против притачного {attach_len:.0f} см "
        f"→ приток ткани даёт каскад.",
    ]
    return O.OverlayResult(
        "cascade_side", "Каскад/водопад сбоку", [piece], "side",
        round(attach_len, 1), layer=2, sewing_steps=steps, notes=notes)


# --------------------------------------------------------------------------- #
#  Реестр + регистрация (аддитивно)
# --------------------------------------------------------------------------- #
DRAPE_BUILDERS = {"cowl_front": _cowl, "cascade_side": _cascade}

DRAPE_INFO = {
    "cowl_front": ("Косая драпировка (cowl)", "перед по косой, мягкий провис складок"),
    "cascade_side": ("Каскад/водопад сбоку", "асимметричный каскад складок по боку"),
}

# 1) реестр построителей оверлеев
O._BUILDERS.update(DRAPE_BUILDERS)

# 2) спецификации в покомпонентном каркасе
for _k, (_title, _note) in DRAPE_INFO.items():
    if _k not in C.OVERLAY_SPECS:
        C.OVERLAY_SPECS[_k] = C.ComponentSpec(
            _k, C.SLOT_OVERLAY, _title, geometry_ready=True, note=_note)
    else:
        C.OVERLAY_SPECS[_k].geometry_ready = True


def build_drape(key: str, m: Measurements) -> O.OverlayResult:
    return O.build_overlay(key, m)


def drape_catalog() -> List[dict]:
    return [{"key": k, "title": t} for k, (t, n) in DRAPE_INFO.items()]


def verify_drape(key: str, m: Measurements, export_prefix=None):
    chk = O.verify_overlay(key, m, export_prefix=export_prefix)
    ov = O.build_overlay(key, m)
    chk.infos.append(
        f"стык: {ov.attach}, притачной срез {ov.attach_len_cm:g} см "
        f"(излишек ткани → драпировка)")
    return chk
