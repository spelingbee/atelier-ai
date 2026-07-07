"""
AtelierAI — КАРМАНЫ (NEW FILE, аддитивно).

Движок patterns.py / export.py НЕ РЕДАКТИРУЕТСЯ. Здесь только построение
лекал карманов на тех же примитивах (Measurements, PatternPiece). Карман —
это локальная ДЕТАЛЬ (слот SLOT_DETAIL покомпонентной модели): он
добавляет свои детали кроя к лекалу и шаги в ТЗ, не меняя несущий силуэт.

4 базовых типа:
  • inseam  — карман в боковом шве (невидимый, мешковина)
  • patch   — накладной карман (прямоугольный со скруглённым низом)
  • cargo   — накладной карман-карго с боковиной (объёмный) + клапан
  • welt    — прорезной карман (обтачки + мешковина)

Все координаты в сантиметрах. X = ширина (вправо), Y = вниз.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Dict, Callable

import patterns as P
from patterns import Measurements, PatternPiece


# --------------------------------------------------------------------------- #
#  Геометрические помощники
# --------------------------------------------------------------------------- #
def _rect(w: float, h: float) -> List[P.Point]:
    """Замкнутый прямоугольник от (0,0), против часовой."""
    return [(0.0, 0.0), (0.0, h), (w, h), (w, 0.0), (0.0, 0.0)]


def _round_bottom(w: float, h: float, r: float, steps: int = 14) -> List[P.Point]:
    """Прямоугольник со скруглёнными НИЖНИМИ углами (верх прямой)."""
    r = max(0.0, min(r, w / 2 - 0.01, h / 2 - 0.01))
    if r <= 0:
        return _rect(w, h)
    pts: List[P.Point] = [(0.0, 0.0)]
    pts += P._arc(r, h - r, r, 180, 90, steps=steps)       # (0,h-r) -> (r,h)
    pts += P._arc(w - r, h - r, r, 90, 0, steps=steps)      # (w-r,h) -> (w,h-r)
    pts += [(w, 0.0), (0.0, 0.0)]
    return pts


# --------------------------------------------------------------------------- #
#  Результат построения кармана
# --------------------------------------------------------------------------- #
@dataclass
class PocketResult:
    key: str
    title: str
    pieces: List[PatternPiece] = field(default_factory=list)
    sewing_steps: List[str] = field(default_factory=list)
    placement: str = ""
    notes: str = ""


# --------------------------------------------------------------------------- #
#  1. Карман в боковом шве (INSEAM)
# --------------------------------------------------------------------------- #
def build_inseam_pocket(m: Measurements, mouth: float = 15.0,
                        width: float = 15.0, depth: float = 30.0) -> PocketResult:
    """Невидимый карман: прямой левый край — притачивается к боковому шву,
    скруглённый низ — мешковина. Вход отмечен двумя надсечками."""
    mouth = min(mouth, depth - 6.0)
    pts = _round_bottom(width, depth, r=width * 0.45)
    top_offset = 3.0
    notches = [(0.0, top_offset), (0.0, top_offset + mouth)]
    piece = PatternPiece(
        name="pocket_inseam_bag", points=pts,
        grain_line=((width * 0.4, 4), (width * 0.4, depth - 4)),
        labels=[
            {"text": "МЕШКОВИНА КАРМАНА", "x": width * 0.45, "y": depth * 0.5, "size": 1.0, "bold": True},
            {"text": f"вход {mouth:g}см · ×4", "x": width * 0.45, "y": depth * 0.5 + 2, "size": 0.7},
        ],
        notches=notches, cut_on_fold=False, quantity=4,
    )
    steps = [
        f"Карман в боковом шве: вход {mouth:g} см между надсечками.",
        "Притачать по 2 мешковины к припускам бокового шва (перёд + спинка).",
        "Стачать мешковины по контуру, закрепить вход закрепками.",
    ]
    return PocketResult("inseam", "Карман в боковом шве", [piece], steps,
                        placement=f"в боковом шве, ниже талии ~{max(0.0, m.hip_depth - 3):g} см",
                        notes="невидимый карман; кроится ×4 (2 на сторону)")


# --------------------------------------------------------------------------- #
#  2. Накладной карман (PATCH)
# --------------------------------------------------------------------------- #
def build_patch_pocket(m: Measurements, width: float = 14.0, height: float = 16.0,
                       hem: float = 3.5, round_r: float = 2.5) -> PocketResult:
    """Накладной карман: прямоугольник с припуском на подгиб верха и скруглённым низом."""
    body_h = height + hem
    pts = _round_bottom(width, body_h, r=round_r)
    notches = [(0.0, hem), (width, hem)]   # линия подгиба верха
    piece = PatternPiece(
        name="pocket_patch", points=pts,
        grain_line=((width * 0.5, hem + 3), (width * 0.5, body_h - 3)),
        labels=[
            {"text": "НАКЛАДНОЙ КАРМАН", "x": width * 0.5, "y": body_h * 0.5, "size": 1.0, "bold": True},
            {"text": f"{width:g}×{height:g}см · ×2", "x": width * 0.5, "y": body_h * 0.5 + 2, "size": 0.7},
        ],
        notches=notches, cut_on_fold=False, quantity=2,
    )
    steps = [
        f"Накладной карман {width:g}×{height:g} см: подогнуть верх {hem:g} см, отстрочить.",
        "Заутюжить припуски по контуру, настрочить на полотнище по разметке.",
    ]
    return PocketResult("patch", "Накладной карман", [piece], steps,
                        placement="на переде/спинке по разметке",
                        notes="скруглённый низ")


# --------------------------------------------------------------------------- #
#  3. Карман-карго с боковой объемной стенкой + клапан (CARGO)
# --------------------------------------------------------------------------- #
def build_cargo_pocket(m: Measurements, width: float = 16.0, height: float = 18.0,
                       hem: float = 3.5, gusset: float = 3.0, flap_h: float = 6.0) -> PocketResult:
    """Объёмный карман: лицевая деталь + боковина (объёмная вставка по 3 сторонам) + клапан."""
    face_h = height + hem
    face = PatternPiece(
        name="pocket_cargo_face", points=_round_bottom(width, face_h, r=1.5),
        grain_line=((width * 0.5, hem + 3), (width * 0.5, face_h - 3)),
        labels=[{"text": "КАРГО — ЛИЦО", "x": width * 0.5, "y": face_h * 0.5, "size": 1.0, "bold": True},
                {"text": f"{width:g}×{height:g}см · ×2", "x": width * 0.5, "y": face_h * 0.5 + 2, "size": 0.7}],
        notches=[(0.0, hem), (width, hem)], quantity=2,
    )
    g_len = 2 * height + width   # боковина оборачивает 2 бока + низ
    gusset_notches = [(height, 0.0), (height, gusset),
                      (height + width, 0.0), (height + width, gusset)]
    gus = PatternPiece(
        name="pocket_cargo_gusset", points=_rect(g_len, gusset),
        grain_line=((g_len * 0.5, gusset * 0.3), (g_len * 0.5, gusset * 0.7)),
        labels=[{"text": f"БОКОВИНА КАРМАНА {gusset:g}см ×2", "x": g_len * 0.5, "y": gusset * 0.5, "size": 0.8, "bold": True}],
        notches=gusset_notches, quantity=2,
    )
    fl_w = width + 1.0
    flap_pts = [(0.0, 0.0), (0.0, flap_h - 1.0), (1.0, flap_h),
                (fl_w - 1.0, flap_h), (fl_w, flap_h - 1.0), (fl_w, 0.0), (0.0, 0.0)]
    flap = PatternPiece(
        name="pocket_cargo_flap", points=flap_pts,
        grain_line=((fl_w * 0.5, 1.5), (fl_w * 0.5, flap_h - 1.5)),
        labels=[{"text": "КЛАПАН ×4", "x": fl_w * 0.5, "y": flap_h * 0.5, "size": 0.8, "bold": True}],
        notches=[(fl_w * 0.5, 0.0)], quantity=4,
    )
    steps = [
        f"Карман-карго {width:g}×{height:g} см с боковиной {gusset:g} см.",
        "Притачать боковину по 3 сторонам лицевой детали (надсечки — углы).",
        "Подогнуть верх лица, настрочить карман на полотнище.",
        "Обтачать клапан (2 детали), настрочить над карманом.",
    ]
    return PocketResult("cargo", "Карман-карго", [face, gus, flap], steps,
                        placement="на передних/боковых полотнищах",
                        notes="объёмный, с объемной боковиной и клапаном")


# --------------------------------------------------------------------------- #
#  4. Прорезной карман (WELT)
# --------------------------------------------------------------------------- #
def build_welt_pocket(m: Measurements, opening: float = 14.0,
                      welt_w: float = 1.5, depth: float = 15.0) -> PocketResult:
    """Прорезной карман: обтачки (велт) + мешковина (сложить вдвое)."""
    welt_h = welt_w * 2 + 2.0
    welt_l = opening + 3.0
    welt = PatternPiece(
        name="pocket_welt", points=_rect(welt_l, welt_h),
        grain_line=((welt_l * 0.5, welt_h * 0.3), (welt_l * 0.5, welt_h * 0.7)),
        labels=[{"text": "ОБТАЧКА (велт) ×2", "x": welt_l * 0.5, "y": welt_h * 0.5, "size": 0.8, "bold": True}],
        notches=[(1.5, welt_h * 0.5), (welt_l - 1.5, welt_h * 0.5)], quantity=2,
    )
    bag_l = opening + 4.0
    bag_h = depth * 2 + 2.0
    bag = PatternPiece(
        name="pocket_welt_bag", points=_rect(bag_l, bag_h),
        grain_line=((bag_l * 0.5, 4), (bag_l * 0.5, bag_h - 4)),
        labels=[{"text": "МЕШКОВИНА (сложить вдвое)", "x": bag_l * 0.5, "y": bag_h * 0.5, "size": 0.9, "bold": True},
                {"text": f"вход {opening:g}см · ×1", "x": bag_l * 0.5, "y": bag_h * 0.5 + 2, "size": 0.7}],
        notches=[(0.0, bag_h * 0.5), (bag_l, bag_h * 0.5)], quantity=1,
    )
    steps = [
        f"Прорезной карман: вход {opening:g} см, обтачка {welt_w:g} см.",
        "Притачать обтачки по линии входа, рассечь, вывернуть.",
        "Притачать мешковину, стачать по контуру.",
    ]
    return PocketResult("welt", "Прорезной карман", [welt, bag], steps,
                        placement="на переднем/заднем полотнище, наклон по разметке",
                        notes="в рамку/с обтачкой")


def build_jeans_pocket(m: Measurements, pocket_width: float = 16.0,
                       pocket_depth: float = 24.0) -> PocketResult:
    """Джинсовый передний карман:
    1. Мешковина кармана (pocket_jeans_lining)
    2. Подзор кармана из денима (pocket_jeans_facing)
    3. Монетный кармашек (pocket_jeans_coin)
    """
    w = pocket_width
    h = pocket_depth
    scoop_x = 7.0
    scoop_y = 9.0

    # 1. Мешковина (lining)
    lining_pts = [
        (0.0, 0.0),
        (w - scoop_x, 0.0),
        (w - scoop_x + 1.0, 2.0),
        (w - 2.0, scoop_y - 1.0),
        (w, scoop_y),
        (w, h - 4.0),
        (w - 4.0, h),
        (0.0, h),
        (0.0, 0.0)
    ]
    lining = PatternPiece(
        name="pocket_jeans_lining", points=lining_pts,
        grain_line=((w * 0.3, 4.0), (w * 0.3, h - 4.0)),
        labels=[
            {"text": "МЕШКОВИНА ДЖИНС. КАРМАНА", "x": w * 0.45, "y": h * 0.5, "size": 0.9, "bold": True},
            {"text": "х4 (хлопок)", "x": w * 0.45, "y": h * 0.5 + 1.5, "size": 0.8},
        ],
        cut_on_fold=False, quantity=4
    )

    # 2. Подзор (facing)
    facing_pts = [
        (0.0, 0.0),
        (1.0, 2.0),
        (scoop_x + 1.0, scoop_y - 1.0),
        (scoop_x + 3.0, scoop_y),
        (scoop_x + 3.0, 15.0),
        (0.0, 15.0),
        (0.0, 0.0)
    ]
    facing = PatternPiece(
        name="pocket_jeans_facing", points=facing_pts,
        grain_line=((2.0, 2.0), (2.0, 13.0)),
        labels=[
            {"text": "ПОДЗОР КАРМАНА", "x": 4.0, "y": 6.0, "size": 0.8, "bold": True},
            {"text": "х2 (деним)", "x": 4.0, "y": 7.5, "size": 0.7},
        ],
        cut_on_fold=False, quantity=2
    )

    # 3. Монетный карман (coin pocket)
    coin_w, coin_h = 7.0, 8.0
    coin_pts = [
        (0.0, 0.0),
        (0.0, coin_h),
        (coin_w, coin_h),
        (coin_w, 0.0),
        (0.0, 0.0)
    ]
    coin = PatternPiece(
        name="pocket_jeans_coin", points=coin_pts,
        grain_line=((coin_w * 0.5, 1.5), (coin_w * 0.5, coin_h - 1.5)),
        labels=[
            {"text": "МОНЕТНЫЙ", "x": coin_w * 0.5, "y": coin_h * 0.4, "size": 0.6, "bold": True},
            {"text": "х2 (деним)", "x": coin_w * 0.5, "y": coin_h * 0.7, "size": 0.5},
        ],
        cut_on_fold=False, quantity=2
    )

    steps = [
        "Джинсовый карман: настрочить монетный карман на правый подзор.",
        "Настрочить джинсовые подзоры на хлопковые мешковины кармана.",
        "Притачать мешковину по линии входа (скругление scoop), рассечь припуски, вывернуть и отстрочить.",
        "Совместить срезы мешковины, стачать нижний шов.",
        "Закрепить карман по талии и боковому шву вспомогательной строчкой."
    ]
    return PocketResult("jeans", "Джинсовый карман", [lining, facing, coin], steps,
                        placement="на переднем полотнище (вход сбоку)",
                        notes="классический джинсовый карман с подзором и часовым кармашком")


# --------------------------------------------------------------------------- #
#  Реестр
# --------------------------------------------------------------------------- #
POCKET_REGISTRY: Dict[str, Callable[..., PocketResult]] = {
    "inseam": build_inseam_pocket,
    "patch": build_patch_pocket,
    "cargo": build_cargo_pocket,
    "welt": build_welt_pocket,
    "jeans": build_jeans_pocket,
}

POCKET_TITLES = {
    "inseam": "Карман в боковом шве",
    "patch": "Накладной карман",
    "cargo": "Карман-карго",
    "welt": "Прорезной карман",
    "jeans": "Джинсовый карман",
}


def build_pocket(kind: str, m: Measurements, **kwargs) -> PocketResult:
    """Построить лекало кармана заданного типа. Неизвестный тип → накладной."""
    fn = POCKET_REGISTRY.get(kind, build_patch_pocket)
    return fn(m, **kwargs)


def pocket_catalog() -> List[Dict[str, str]]:
    """Список типов карманов для UI/ИИ."""
    return [{"key": k, "title": v} for k, v in POCKET_TITLES.items()]
