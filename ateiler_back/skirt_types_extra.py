"""
AtelierAI — ДОПОЛНИТЕЛЬНЫЕ ТИПЫ ЮБОК (NEW FILE, аддитивно).

Движок patterns.py / export.py НЕ РЕДАКТИРУЕТСЯ. Здесь только новые классы
лекал, построенные на тех же примитивах (Measurements, PatternPiece).
Вызовите register_extra_types() один раз — они добавятся в PATTERN_REGISTRY,
и build_pattern("pleated"|"tiered"|"yoke", m) начнёт их строить.

Все координаты в сантиметрах. X = ширина (вправо), Y = вниз.
"""
from __future__ import annotations

from typing import List

import patterns as P
from patterns import Measurements, PatternPiece, StraightSkirtPattern


def _rect(w: float, h: float) -> List[P.Point]:
    """Замкнутый прямоугольник от (0,0)."""
    return [(0.0, 0.0), (0.0, h), (w, h), (w, 0.0), (0.0, 0.0)]


# --------------------------------------------------------------------------- #
#  1. Плиссе / складки (PLEATED)
# --------------------------------------------------------------------------- #
class PleatedSkirtPattern:
    title = "ПЛИССЕ"
    fullness = 3.0
    pleat_width = 3.0

    def __init__(self, m: Measurements, fullness: float | None = None,
                 pleat_width: float | None = None):
        self.m = m
        if fullness:
            self.fullness = fullness
        if pleat_width:
            self.pleat_width = pleat_width

    def _panel(self, width: float, name: str, label: str) -> PatternPiece:
        L = self.m.length_cm
        pts = _rect(width, L)
        n = max(1, int(round(width / self.pleat_width)))
        notches = []
        for i in range(1, n):
            x = i * self.pleat_width
            notches.append((x, 0.0))
            notches.append((x, L))
        return PatternPiece(
            name=name, points=pts,
            grain_line=((width * 0.5, 5), (width * 0.5, L - 5)),
            labels=[
                {"text": label, "x": width * 0.5, "y": L * 0.5, "size": 1.4, "bold": True},
                {"text": f"складка {self.pleat_width:g}см ×{n}",
                 "x": width * 0.5, "y": L * 0.5 + 2, "size": 0.7},
            ],
            notches=notches, cut_on_fold=False,
        )

    def generate(self) -> List[PatternPiece]:
        waist_eff = self.m.waist_cm + self.m.ease_waist
        total = waist_eff * self.fullness
        half = total / 2
        front = self._panel(half, "front_panel", f"ПОЛОТНИЩЕ ПЕРЕД — {self.title}")
        back = self._panel(half, "back_panel", f"ПОЛОТНИЩЕ СПИНКА — {self.title}")
        wb = StraightSkirtPattern(self.m).waistband()
        return [front, back, wb]


# --------------------------------------------------------------------------- #
#  2. Ярусная / с воланами (TIERED)
# --------------------------------------------------------------------------- #
class TieredSkirtPattern:
    title = "ЯРУСНАЯ"
    n_tiers = 3
    gather_ratio = 1.5

    def __init__(self, m: Measurements, n_tiers: int | None = None,
                 gather_ratio: float | None = None):
        self.m = m
        if n_tiers:
            self.n_tiers = n_tiers
        if gather_ratio:
            self.gather_ratio = gather_ratio

    def generate(self) -> List[PatternPiece]:
        m = self.m
        tier_h = m.length_cm / self.n_tiers
        waist_eff = m.waist_cm + m.ease_waist
        hip_eff = m.hip_cm + m.ease_hip
        width = max(hip_eff, waist_eff * self.gather_ratio)
        pieces: List[PatternPiece] = []
        for i in range(self.n_tiers):
            half = width / 2
            pts = _rect(half, tier_h)
            pieces.append(PatternPiece(
                name=f"tier_{i + 1}", points=pts,
                grain_line=((half * 0.5, 3), (half * 0.5, tier_h - 3)),
                labels=[
                    {"text": f"ЯРУС {i + 1}/{self.n_tiers} — {self.title}",
                     "x": half * 0.5, "y": tier_h * 0.5, "size": 1.1, "bold": True},
                    {"text": f"×2 по сгибу, сборка ×{self.gather_ratio:g}",
                     "x": half * 0.5, "y": tier_h * 0.5 + 2, "size": 0.7},
                ],
                notches=[(half, tier_h)], cut_on_fold=True, quantity=2,
            ))
            width *= self.gather_ratio
        wb = StraightSkirtPattern(m).waistband()
        pieces.append(wb)
        return pieces


# --------------------------------------------------------------------------- #
#  3. Кокетка + сборка (YOKE + GATHERED)
# --------------------------------------------------------------------------- #
class YokeGatheredSkirtPattern:
    title = "КОКЕТКА+СБОРКА"
    gather_ratio = 1.8

    def __init__(self, m: Measurements, yoke_depth: float | None = None,
                 gather_ratio: float | None = None):
        self.m = m
        self.yoke_depth = yoke_depth if yoke_depth else m.hip_depth
        if gather_ratio:
            self.gather_ratio = gather_ratio

    def _yoke(self, hip_q: float, waist_q: float, name: str, label: str) -> PatternPiece:
        d = self.yoke_depth
        pts = [(0.0, 0.0), (0.0, d), (hip_q, d), (waist_q, 0.0), (0.0, 0.0)]
        return PatternPiece(
            name=name, points=pts,
            grain_line=((hip_q * 0.4, 2), (hip_q * 0.4, d - 2)),
            labels=[{"text": label, "x": hip_q * 0.4, "y": d * 0.5, "size": 1.0, "bold": True}],
            notches=[(hip_q, d)], cut_on_fold=True,
        )

    def generate(self) -> List[PatternPiece]:
        m = self.m
        front_yoke = self._yoke(m.H / 2 + 0.5, m.W / 2 + 0.5,
                                "front_yoke", f"КОКЕТКА ПЕРЕД — {self.title}")
        back_yoke = self._yoke(m.H / 2 - 0.5, m.W / 2 - 0.5,
                               "back_yoke", f"КОКЕТКА СПИНКА — {self.title}")
        hip_eff = m.hip_cm + m.ease_hip
        skirt_len = max(5.0, m.length_cm - self.yoke_depth)
        half = hip_eff * self.gather_ratio / 2
        skirt = PatternPiece(
            name="skirt_panel", points=_rect(half, skirt_len),
            grain_line=((half * 0.5, 5), (half * 0.5, skirt_len - 5)),
            labels=[{"text": f"ПОЛОТНИЩЕ (сборка ×{self.gather_ratio:g})",
                     "x": half * 0.5, "y": skirt_len * 0.5, "size": 1.1, "bold": True}],
            notches=[(half, skirt_len)], cut_on_fold=True, quantity=2,
        )
        wb = StraightSkirtPattern(m).waistband()
        return [front_yoke, back_yoke, skirt, wb]


EXTRA_REGISTRY = {
    "pleated": PleatedSkirtPattern,
    "tiered": TieredSkirtPattern,
    "yoke": YokeGatheredSkirtPattern,
}

ALL_TYPES = [
    "straight", "pencil", "a_line", "half_circle", "full_circle",
    "pleated", "tiered", "yoke",
]


def register_extra_types() -> dict:
    P.PATTERN_REGISTRY.update(EXTRA_REGISTRY)
    return dict(P.PATTERN_REGISTRY)


register_extra_types()
