"""
AtelierAI — Skirt pattern engine (MVP)

Determenistic geometry for 5 skirt types. No ML here — the LLM only classifies
the photo upstream; this module turns (skirt_type + measurements) into real
pattern pieces, in centimeters, with darts, grain lines, notches and labels.

Units: ALL coordinates are in centimeters. X = width (right), Y = down.
The SVG/PDF exporters convert cm -> physical units so prints are 1:1.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Type

Point = Tuple[float, float]


# --------------------------------------------------------------------------- #
#  Core data structures
# --------------------------------------------------------------------------- #
@dataclass
class Measurements:
    waist_cm: float          # обхват талии (full)
    hip_cm: float            # обхват бёдер (full)
    length_cm: float         # длина изделия
    ease_waist: float = 1.0  # припуск на свободу по талии
    ease_hip: float = 4.0    # припуск на свободу по бёдрам
    seam_allowance: float = 1.5

    def __post_init__(self):
        if self.hip_cm < self.waist_cm:
            raise ValueError("hip_cm must be >= waist_cm")
        if not (30 <= self.length_cm <= 150):
            raise ValueError("length_cm out of range 30..150")

    @property
    def W(self) -> float:
        """Половина обхвата талии с припуском (semi-girth)."""
        return (self.waist_cm + self.ease_waist) / 2

    @property
    def H(self) -> float:
        """Половина обхвата бёдер с припуском."""
        return (self.hip_cm + self.ease_hip) / 2

    @property
    def hip_depth(self) -> float:
        """Глубина талия->бёдра (Стандарт ЕМКО, зависит от роста/размера)."""
        return 20.0 if self.hip_cm >= 100 else 18.0


@dataclass
class PatternPiece:
    name: str
    points: List[Point]                       # closed outline, cm
    grain_line: Tuple[Point, Point] = ((0, 0), (0, 0))
    labels: List[dict] = field(default_factory=list)
    notches: List[Point] = field(default_factory=list)
    cut_on_fold: bool = False                 # левый край — сгиб
    quantity: int = 1


# --------------------------------------------------------------------------- #
#  Geometry helpers
# --------------------------------------------------------------------------- #
def _arc(cx: float, cy: float, r: float, a0: float, a1: float, steps: int = 64) -> List[Point]:
    """Points along an arc, angles in degrees."""
    out = []
    for i in range(steps + 1):
        a = math.radians(a0 + (a1 - a0) * i / steps)
        out.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return out


def polygon_perimeter(points: List[Point]) -> float:
    p = 0.0
    for i in range(len(points) - 1):
        p += math.dist(points[i], points[i + 1])
    return p


def edge_length(a: Point, b: Point) -> float:
    return math.dist(a, b)


# --------------------------------------------------------------------------- #
#  Straight skirt (прямая) + Pencil (карандаш)
# --------------------------------------------------------------------------- #
class StraightSkirtPattern:
    """Прямая юбка. Средняя линия — по сгибу (x=0), боковой срез — справа."""
    hem_taper = 0.0     # pencil overrides: сужение к низу (см внутрь)
    has_slit = False
    title = "ПРЯМАЯ"

    def __init__(self, m: Measurements):
        self.m = m

    def _panel(self, hip_q: float, waist_q: float, dart_ratio: float,
               max_dart: float, name: str, label: str) -> PatternPiece:
        m = self.m
        hd = m.hip_depth
        L = m.length_cm
        # total suppression from hip to waist on this quarter
        suppression = hip_q - waist_q
        dart_w = min(suppression * dart_ratio, max_dart)
        side_take = suppression - dart_w        # taken off side seam
        dart_len = 10.0 if "СПИНКА" in label else 9.0
        waist_side_x = hip_q - side_take        # x of side point at the waist
        hem_x = hip_q - self.hem_taper          # pencil tapers hem inwards

        # outline, counter-clockwise starting at fold/top
        pts: List[Point] = [
            (0.0, 0.0),                  # CF/CB top (fold)
            (0.0, L),                    # CF/CB bottom
            (hem_x, L),                  # hem at side
            (hip_q, hd),                 # hip line at side seam
            (waist_side_x, 0.0),         # waist at side seam
        ]
        # waist dart, centred between fold and side
        dc = waist_side_x * 0.5
        pts += [
            (dc + dart_w / 2, 0.0),
            (dc, dart_len),
            (dc - dart_w / 2, 0.0),
        ]
        pts.append((0.0, 0.0))           # close

        return PatternPiece(
            name=name,
            points=pts,
            grain_line=((hip_q * 0.45, 5), (hip_q * 0.45, L - 5)),
            labels=[
                {"text": label, "x": hip_q * 0.45, "y": L * 0.5, "size": 1.4, "bold": True},
                {"text": f"Т{m.waist_cm:g} Б{m.hip_cm:g} Д{m.length_cm:g}",
                 "x": hip_q * 0.45, "y": L * 0.5 + 2, "size": 0.7},
            ],
            notches=[(hip_q, hd)],
            cut_on_fold=True,
        )

    def front_panel(self) -> PatternPiece:
        # +0.5 баланс перед/спинка на бёдрах и талии
        return self._panel(self.m.H / 2 + 0.5, self.m.W / 2 + 0.5,
                           0.60, 3.0, "front_panel", f"ПЕРЕД — {self.title}")

    def back_panel(self) -> PatternPiece:
        return self._panel(self.m.H / 2 - 0.5, self.m.W / 2 - 0.5,
                           0.65, 3.5, "back_panel", f"СПИНКА — {self.title}")

    def waistband(self) -> PatternPiece:
        m = self.m
        total = m.waist_cm + m.ease_waist + 3.0   # +3 см на застёжку
        h = 4.0
        pts = [(0, 0), (total, 0), (total, h), (0, h), (0, 0)]
        return PatternPiece(
            name="waistband", points=pts,
            grain_line=((total * 0.25, h / 2), (total * 0.75, h / 2)),
            labels=[{"text": "ПОЯС × 2", "x": total / 2, "y": h / 2, "size": 1.0, "bold": True}],
            notches=[(total / 2, 0)], quantity=2,
        )

    def generate(self) -> List[PatternPiece]:
        return [self.front_panel(), self.back_panel(), self.waistband()]


class PencilSkirtPattern(StraightSkirtPattern):
    """Юбка-карандаш: обтягивающая, сужается к низу + шлица."""
    hem_taper = 2.0
    has_slit = True
    title = "КАРАНДАШ"

    def __init__(self, m: Measurements):
        m.ease_hip = min(m.ease_hip, 1.5)   # минимальная свобода
        m.ease_waist = min(m.ease_waist, 0.5)
        super().__init__(m)


# --------------------------------------------------------------------------- #
#  A-line (А-силуэт)
# --------------------------------------------------------------------------- #
class ALineSkirtPattern:
    title = "А-СИЛУЭТ"

    def __init__(self, m: Measurements):
        self.m = m
        below_hip = max(0.0, m.length_cm - m.hip_depth)
        self.flare = below_hip * 0.18         # расширение на боковой срез

    def _panel(self, hip_q: float, waist_q: float, name: str, label: str) -> PatternPiece:
        m = self.m
        hd = m.hip_depth
        L = m.length_cm
        suppression = hip_q - waist_q
        dart_w = min(suppression * 0.55, 2.5)
        side_take = suppression - dart_w
        waist_side_x = hip_q - side_take
        hem_x = hip_q + self.flare
        dart_len = 9.0

        pts: List[Point] = [
            (0.0, 0.0),
            (0.0, L),
            (hem_x, L),
            (hip_q, hd),
            (waist_side_x, 0.0),
        ]
        dc = waist_side_x * 0.5
        pts += [(dc + dart_w / 2, 0.0), (dc, dart_len), (dc - dart_w / 2, 0.0)]
        pts.append((0.0, 0.0))

        return PatternPiece(
            name=name, points=pts,
            grain_line=((hip_q * 0.45, 5), (hip_q * 0.45, L - 5)),
            labels=[{"text": label, "x": hip_q * 0.45, "y": L * 0.5, "size": 1.4, "bold": True}],
            notches=[(hip_q, hd)], cut_on_fold=True,
        )

    def generate(self) -> List[PatternPiece]:
        return [
            self._panel(self.m.H / 2 + 0.5, self.m.W / 2 + 0.5, "front_panel", f"ПЕРЕД — {self.title}"),
            self._panel(self.m.H / 2 - 0.5, self.m.W / 2 - 0.5, "back_panel", f"СПИНКА — {self.title}"),
            StraightSkirtPattern(self.m).waistband(),
        ]


# --------------------------------------------------------------------------- #
#  Circle skirts (полусолнце / солнце)
# --------------------------------------------------------------------------- #
class CircleSkirtPattern:
    """Общий класс. coverage = доля полного круга (1.0 = солнце, 0.5 = полусолнце).

    Лекало строится на ДВЕ детали (перед+спинка), поэтому один кусок =
    coverage/2 от полного круга, кроится по сгибу.
    Радиус талии: длина всей талиевой линии = coverage * 2πR = waist  ->  R = waist/(coverage*2π).
    """
    coverage = 1.0
    title = "СОЛНЦЕ"

    def __init__(self, m: Measurements):
        self.m = m
        waist_eff = m.waist_cm + m.ease_waist
        self.r_in = waist_eff / (self.coverage * 2 * math.pi)
        self.r_out = self.r_in + m.length_cm

    def generate(self) -> List[PatternPiece]:
        # одна деталь = половина охвата (кроится по сгибу) -> угол sweep
        sweep = self.coverage * 180.0            # градусы на один кусок
        a0, a1 = -sweep / 2, sweep / 2
        inner = _arc(0, 0, self.r_in, a0, a1, steps=72)
        outer = _arc(0, 0, self.r_out, a1, a0, steps=72)
        pts = inner + outer + [inner[0]]
        # сдвигаем чтобы всё было в положительных координатах
        min_x = min(p[0] for p in pts)
        min_y = min(p[1] for p in pts)
        pts = [(x - min_x, y - min_y) for x, y in pts]
        cx = (max(p[0] for p in pts)) / 2
        cy = (self.r_in + self.r_out) / 2 - min_y
        return [PatternPiece(
            name="circle_panel", points=pts,
            grain_line=((cx, cy - 5), (cx, cy + 5)),
            labels=[{"text": f"{self.title} × 2 (по сгибу)",
                     "x": cx, "y": cy, "size": 1.1, "bold": True},
                    {"text": f"Rталии={self.r_in:.1f}см",
                     "x": cx, "y": cy + 2, "size": 0.7}],
            notches=[], quantity=2,
        )]


class HalfCircleSkirtPattern(CircleSkirtPattern):
    coverage = 0.5
    title = "ПОЛУСОЛНЦЕ"


class FullCircleSkirtPattern(CircleSkirtPattern):
    coverage = 1.0
    title = "СОЛНЦЕ"


# --------------------------------------------------------------------------- #
#  Registry
# --------------------------------------------------------------------------- #
PATTERN_REGISTRY: Dict[str, Type] = {
    "straight": StraightSkirtPattern,
    "pencil": PencilSkirtPattern,
    "a_line": ALineSkirtPattern,
    "half_circle": HalfCircleSkirtPattern,
    "full_circle": FullCircleSkirtPattern,
}


def build_pattern(skirt_type: str, m: Measurements) -> List[PatternPiece]:
    cls = PATTERN_REGISTRY.get(skirt_type, StraightSkirtPattern)
    return cls(m).generate()
