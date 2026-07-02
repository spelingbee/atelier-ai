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
from enum import Enum, auto
from typing import List, Tuple, Dict, Type

Point = Tuple[float, float]


class EdgeRole(Enum):
    WAIST = auto()
    HEM = auto()
    SIDE_LEFT = auto()
    SIDE_RIGHT = auto()
    CENTER_FOLD = auto()
    CENTER_SEAM = auto()
    DART_LEG = auto()
    INTERNAL = auto()


@dataclass
class Edge:
    role: EdgeRole
    points: List[Point]
    curve_type: str = "line"


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
    edges: List[Edge] = field(default_factory=list)
    grain_line: Tuple[Point, Point] = ((0, 0), (0, 0))
    labels: List[dict] = field(default_factory=list)
    notches: List[Point] = field(default_factory=list)
    cut_on_fold: bool = False                 # левый край — сгиб
    quantity: int = 1

    def __init__(self, name: str, points: List[Point] = None, edges: List[Edge] = None,
                 grain_line: Tuple[Point, Point] = ((0, 0), (0, 0)),
                 labels: List[dict] = None, notches: List[Point] = None,
                 cut_on_fold: bool = False, quantity: int = 1):
        self.name = name
        self.grain_line = grain_line
        self.labels = labels if labels is not None else []
        self.notches = notches if notches is not None else []
        self.cut_on_fold = cut_on_fold
        self.quantity = quantity
        
        if edges is not None:
            self.edges = edges
        elif points is not None:
            self.edges = [Edge(role=EdgeRole.INTERNAL, points=points)]
        else:
            self.edges = []

    @property
    def points(self) -> List[Point]:
        if not self.edges:
            return []
        pts = []
        for edge in self.edges:
            pts.extend(edge.points[1:] if pts else edge.points)
        # Close contour if not already closed
        if pts and pts[0] != pts[-1]:
            pts.append(pts[0])
        return pts

    @points.setter
    def points(self, new_points: List[Point]):
        self.edges = [Edge(role=EdgeRole.INTERNAL, points=new_points)]


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

        # Define edges, counter-clockwise starting at fold/top
        edges = [
            Edge(role=EdgeRole.CENTER_FOLD, points=[(0.0, 0.0), (0.0, L)]),
            Edge(role=EdgeRole.HEM, points=[(0.0, L), (hem_x, L)]),
            Edge(role=EdgeRole.SIDE_RIGHT, points=[(hem_x, L), (hip_q, hd), (waist_side_x, 0.0)]),
        ]
        
        # waist dart, centred between fold and side
        dc = waist_side_x * 0.5
        if dart_w > 0:
            edges.extend([
                Edge(role=EdgeRole.WAIST, points=[(waist_side_x, 0.0), (dc + dart_w / 2, 0.0)]),
                Edge(role=EdgeRole.DART_LEG, points=[(dc + dart_w / 2, 0.0), (dc, dart_len)]),
                Edge(role=EdgeRole.DART_LEG, points=[(dc, dart_len), (dc - dart_w / 2, 0.0)]),
                Edge(role=EdgeRole.WAIST, points=[(dc - dart_w / 2, 0.0), (0.0, 0.0)]),
            ])
        else:
            edges.append(
                Edge(role=EdgeRole.WAIST, points=[(waist_side_x, 0.0), (0.0, 0.0)])
            )

        return PatternPiece(
            name=name,
            edges=edges,
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
        edges = [
            Edge(role=EdgeRole.INTERNAL, points=[(0.0, 0.0), (total, 0.0)]),
            Edge(role=EdgeRole.SIDE_RIGHT, points=[(total, 0.0), (total, h)]),
            Edge(role=EdgeRole.WAIST, points=[(total, h), (0.0, h)]),
            Edge(role=EdgeRole.SIDE_LEFT, points=[(0.0, h), (0.0, 0.0)]),
        ]
        return PatternPiece(
            name="waistband", edges=edges,
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


class CulottesPattern:
    """Юбка-брюки (Culottes)."""
    title = "ЮБКА-БРЮКИ"

    def __init__(self, m: Measurements):
        self.m = m

    def _panel(self, hip_q: float, waist_q: float, dart_ratio: float,
               max_dart: float, name: str, label: str, is_front: bool) -> PatternPiece:
        m = self.m
        hd = m.hip_depth
        L = m.length_cm

        # Crotch depth and extension width
        crotch_depth = min(0.25 * m.hip_cm + 1.5, L - 10.0)
        if is_front:
            crotch_ext = 0.04 * m.hip_cm
        else:
            crotch_ext = 0.08 * m.hip_cm

        # Suppression calculations
        suppression = hip_q - waist_q
        dart_w = min(suppression * dart_ratio, max_dart)
        side_take = suppression - dart_w
        dart_len = 10.0 if not is_front else 9.0
        waist_side_x = hip_q - side_take

        # Smooth Bezier curve for the crotch
        curve_pts = []
        steps = 8
        p0 = (crotch_ext, crotch_depth - 8.0)
        p1 = (crotch_ext, crotch_depth)
        p2 = (0.0, crotch_depth)
        for i in range(steps + 1):
            t = i / steps
            x = (1 - t)**2 * p0[0] + 2 * (1 - t) * t * p1[0] + t**2 * p2[0]
            y = (1 - t)**2 * p0[1] + 2 * (1 - t) * t * p1[1] + t**2 * p2[1]
            curve_pts.append((x, y))

        seam_points = [(crotch_ext, 0.0), (crotch_ext, crotch_depth - 8.0)]
        seam_points.extend(curve_pts[1:])

        leg_points = [(0.0, crotch_depth), (0.0, L)]
        hem_points = [(0.0, L), (crotch_ext + hip_q, L)]
        side_points = [(crotch_ext + hip_q, L), (crotch_ext + hip_q, hd), (crotch_ext + waist_side_x, 0.0)]

        edges = [
            Edge(role=EdgeRole.CENTER_SEAM, points=seam_points),
            Edge(role=EdgeRole.INTERNAL, points=leg_points),
            Edge(role=EdgeRole.HEM, points=hem_points),
            Edge(role=EdgeRole.SIDE_RIGHT, points=side_points),
        ]

        # Waist dart
        dc = crotch_ext + waist_side_x * 0.5
        if dart_w > 0:
            edges.extend([
                Edge(role=EdgeRole.WAIST, points=[(crotch_ext + waist_side_x, 0.0), (dc + dart_w / 2, 0.0)]),
                Edge(role=EdgeRole.DART_LEG, points=[(dc + dart_w / 2, 0.0), (dc, dart_len)]),
                Edge(role=EdgeRole.DART_LEG, points=[(dc, dart_len), (dc - dart_w / 2, 0.0)]),
                Edge(role=EdgeRole.WAIST, points=[(dc - dart_w / 2, 0.0), (crotch_ext, 0.0)]),
            ])
        else:
            edges.append(
                Edge(role=EdgeRole.WAIST, points=[(crotch_ext + waist_side_x, 0.0), (crotch_ext, 0.0)])
            )

        cx = crotch_ext + hip_q * 0.45
        return PatternPiece(
            name=name,
            edges=edges,
            grain_line=((cx, 5), (cx, L - 5)),
            labels=[
                {"text": label, "x": cx, "y": L * 0.5, "size": 1.4, "bold": True},
                {"text": f"Т{m.waist_cm:g} Б{m.hip_cm:g} Д{m.length_cm:g}",
                 "x": cx, "y": L * 0.5 + 2, "size": 0.7},
            ],
            notches=[(crotch_ext + hip_q, hd)],
            cut_on_fold=False,
            quantity=2,
        )

    def front_panel(self) -> PatternPiece:
        return self._panel(self.m.H / 2 + 0.5, self.m.W / 2 + 0.5,
                           0.60, 3.0, "front_panel", f"ПЕРЕД — {self.title}", is_front=True)

    def back_panel(self) -> PatternPiece:
        return self._panel(self.m.H / 2 - 0.5, self.m.W / 2 - 0.5,
                           0.65, 3.5, "back_panel", f"СПИНКА — {self.title}", is_front=False)

    def waistband(self) -> PatternPiece:
        return StraightSkirtPattern(self.m).waistband()

    def generate(self) -> List[PatternPiece]:
        return [self.front_panel(), self.back_panel(), self.waistband()]


class Gored6SkirtPattern:
    """Юбка-шестиклинка (6-Gored Skirt). 6 одинаковых симметричных клиньев."""
    title = "ШЕСТИКЛИНКА"

    def __init__(self, m: Measurements):
        self.m = m

    def gored_panel(self) -> PatternPiece:
        m = self.m
        hd = m.hip_depth
        L = m.length_cm

        # Width of one wedge (6 total)
        waist_w = (m.waist_cm + m.ease_waist) / 6.0
        hip_w = (m.hip_cm + m.ease_hip) / 6.0
        hem_w = hip_w * 1.5

        # Horizontal offset to keep all coordinates non-negative
        dx = (hem_w - hip_w) / 2.0

        # Unshifted/unraised key points on left side
        W_L = (dx + (hip_w - waist_w) / 2.0, 0.0)
        H_L = (dx, hd)
        P_hem_un = (0.0, L)

        # Side seam length alignment to prevent drooping
        d_up = math.dist(W_L, H_L)
        d_down = L - d_up
        d_lower_un = math.dist(H_L, P_hem_un)
        
        # Calculate ratio to raise left hem point
        r = d_down / d_lower_un if d_lower_un > 0 else 1.0
        Hem_L = (H_L[0] + r * (P_hem_un[0] - H_L[0]), H_L[1] + r * (P_hem_un[1] - H_L[1]))

        # Center line of wedge symmetry
        cx = hem_w / 2.0

        # Symmetric points on right side
        Hem_R = (2 * cx - Hem_L[0], Hem_L[1])
        H_R = (2 * cx - H_L[0], H_L[1])
        W_R = (2 * cx - W_L[0], W_L[1])

        # Define edges in CCW order
        side_l = Edge(role=EdgeRole.SIDE_LEFT, points=[W_L, H_L, Hem_L])
        hem_pts = [Hem_L, (cx, L), Hem_R]
        hem = Edge(role=EdgeRole.HEM, points=hem_pts)
        side_r = Edge(role=EdgeRole.SIDE_RIGHT, points=[Hem_R, H_R, W_R])
        waist_pts = [W_R, (cx, 0.5), W_L]
        waist = Edge(role=EdgeRole.WAIST, points=waist_pts)

        edges = [side_l, hem, side_r, waist]

        return PatternPiece(
            name="gored_panel",
            edges=edges,
            grain_line=((cx, 5), (cx, L - 5)),
            labels=[
                {"text": f"КЛИН × 6", "x": cx, "y": L * 0.4, "size": 1.4, "bold": True},
                {"text": f"Т{m.waist_cm:g} Б{m.hip_cm:g} Д{m.length_cm:g}",
                 "x": cx, "y": L * 0.4 + 2.5, "size": 0.7},
            ],
            notches=[(dx, hd), (2 * cx - dx, hd)],
            cut_on_fold=False,
            quantity=6,
        )

    def waistband(self) -> PatternPiece:
        return StraightSkirtPattern(self.m).waistband()

    def generate(self) -> List[PatternPiece]:
        return [self.gored_panel(), self.waistband()]


# --------------------------------------------------------------------------- #
#  Registry
# --------------------------------------------------------------------------- #
PATTERN_REGISTRY: Dict[str, Type] = {
    "straight": StraightSkirtPattern,
    "pencil": PencilSkirtPattern,
    "a_line": ALineSkirtPattern,
    "half_circle": HalfCircleSkirtPattern,
    "full_circle": FullCircleSkirtPattern,
    "culottes": CulottesPattern,
    "gored_6": Gored6SkirtPattern,
}


def build_pattern(skirt_type: str, m: Measurements) -> List[PatternPiece]:
    cls = PATTERN_REGISTRY.get(skirt_type, StraightSkirtPattern)
    return cls(m).generate()
