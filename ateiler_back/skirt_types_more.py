"""
AtelierAI — ЕЩЁ ТИПЫ ЮБОК (NEW FILE, аддитивно).

Движок patterns.py / export.py НЕ РЕДАКТИРУЕТСЯ. Здесь только новые
классы на тех же примитивах (Measurements, PatternPiece).

Добавляет:
  tulip   — тюльпан (зауженный к низу, peg-силуэт)
  mermaid — русалка / годе-труба (облегание до колена + резкий клёш)
  hi_low  — асимметрия (короткий перед, длинная спинка)
  bubble  — баллон (сборка сверху и снизу, подогнутый низ)
  skort   — юбка-шорты (передний запах-флап + шорты-кулоты)

Вызовите register_more_types() (или просто import skirt_types_more).
Все координаты в сантиметрах. X = ширина (вправо), Y = вниз.
"""
from __future__ import annotations

import math
from typing import List, Optional

import patterns as P
from patterns import Measurements, PatternPiece, StraightSkirtPattern, _arc

Point = P.Point


def _rect(w: float, h: float, x0: float = 0.0, y0: float = 0.0) -> List[Point]:
    return [(x0, y0), (x0, y0 + h), (x0 + w, y0 + h), (x0 + w, y0), (x0, y0)]


def _darted_quarter(m: Measurements, hip_q: float, waist_q: float, *,
                    hem_offset: float, dart_ratio: float, max_dart: float,
                    dart_len: float, name: str, label: str,
                    knee: Optional[tuple] = None,
                    cf_len: Optional[float] = None,
                    side_len: Optional[float] = None) -> PatternPiece:
    """Четверть-панель с вытачкой (логика движка, реплицировано аддитивно).

    hem_offset>0 — клёш наружу, <0 — заужение (peg).
    knee=(dx, y) — доп. точка на боковом срезе между бёдрами и низом (для русалки).
    cf_len / side_len — разная длина по центру и боку (для hi-low).
    """
    hd = m.hip_depth
    L = m.length_cm
    cf = cf_len if cf_len is not None else L
    sl = side_len if side_len is not None else L
    suppression = hip_q - waist_q
    dart_w = min(suppression * dart_ratio, max_dart)
    side_take = suppression - dart_w
    waist_side_x = hip_q - side_take
    hem_x = hip_q + hem_offset

    side_pts = [(hem_x, sl)]
    if knee is not None:
        side_pts.append((hip_q + knee[0], knee[1]))
    side_pts.extend([(hip_q, hd), (waist_side_x, 0.0)])

    edges = [
        P.Edge(role=P.EdgeRole.CENTER_FOLD, points=[(0.0, 0.0), (0.0, cf)]),
        P.Edge(role=P.EdgeRole.HEM, points=[(0.0, cf), (hem_x, sl)]),
        P.Edge(role=P.EdgeRole.SIDE_RIGHT, points=side_pts),
        P.Edge(role=P.EdgeRole.WAIST, points=[(waist_side_x, 0.0), (0.0, 0.0)]),
    ]

    notches = [(hip_q, hd)]
    internal_edges = []
    dc = waist_side_x * 0.5
    if dart_w > 0:
        notches.append((dc - dart_w / 2, 0.0))
        notches.append((dc + dart_w / 2, 0.0))
        internal_edges.append(
            P.Edge(role=P.EdgeRole.DART_LEG, points=[(dc - dart_w / 2, 0.0), (dc, dart_len), (dc + dart_w / 2, 0.0)])
        )

    return PatternPiece(
        name=name, edges=edges, internal_edges=internal_edges,
        grain_line=((hip_q * 0.45, 5), (hip_q * 0.45, min(cf, sl) - 5)),
        labels=[{"text": label, "x": hip_q * 0.42, "y": min(cf, sl) * 0.5,
                 "size": 1.3, "bold": True}],
        notches=notches, cut_on_fold=True,
    )


# --------------------------------------------------------------------------- #
#  1. ТЮЛЬПАН (peg / tulip)
# --------------------------------------------------------------------------- #
class TulipSkirtPattern:
    title = "ТЮЛЬПАН"
    peg = 7.0   # см заужения по низу относительно бёдер

    def __init__(self, m: Measurements, peg: Optional[float] = None):
        self.m = m
        if peg:
            self.peg = peg

    def generate(self) -> List[PatternPiece]:
        m = self.m
        front = _darted_quarter(
            m, m.H / 2 + 0.5, m.W / 2 + 0.5, hem_offset=-self.peg,
            dart_ratio=0.6, max_dart=3.0, dart_len=9.0,
            name="front_panel", label=f"ПЕРЕД — {self.title}")
        back = _darted_quarter(
            m, m.H / 2 - 0.5, m.W / 2 - 0.5, hem_offset=-self.peg,
            dart_ratio=0.65, max_dart=3.5, dart_len=10.0,
            name="back_panel", label=f"СПИНКА — {self.title}")
        return [front, back, StraightSkirtPattern(m).waistband()]


# --------------------------------------------------------------------------- #
#  2. РУСАЛКА / ГОДЕ-ТРУБА (mermaid / trumpet)
# --------------------------------------------------------------------------- #
class MermaidSkirtPattern:
    title = "РУСАЛКА"
    flare_start_frac = 0.62   # доля длины, где начинается клёш
    flare = 22.0              # расширение по низу (на боковой срез)

    def __init__(self, m: Measurements, flare: Optional[float] = None,
                 flare_start_frac: Optional[float] = None):
        self.m = m
        if flare:
            self.flare = flare
        if flare_start_frac:
            self.flare_start_frac = flare_start_frac

    def _panel(self, hip_q, waist_q, dart_ratio, max_dart, dart_len, name, label):
        m = self.m
        knee_y = m.hip_depth + (m.length_cm - m.hip_depth) * self.flare_start_frac
        # облегание до колена: бок чуть уже бёдер
        return _darted_quarter(
            m, hip_q, waist_q, hem_offset=self.flare,
            dart_ratio=dart_ratio, max_dart=max_dart, dart_len=dart_len,
            name=name, label=label, knee=(-1.5, knee_y))

    def generate(self) -> List[PatternPiece]:
        m = self.m
        # русалка облегающая — минимум свободы по бёдрам
        front = self._panel(m.H / 2 + 0.5, m.W / 2 + 0.5, 0.6, 3.0, 9.0,
                            "front_panel", f"ПЕРЕД — {self.title}")
        back = self._panel(m.H / 2 - 0.5, m.W / 2 - 0.5, 0.65, 3.5, 10.0,
                           "back_panel", f"СПИНКА — {self.title}")
        return [front, back, StraightSkirtPattern(m).waistband()]


# --------------------------------------------------------------------------- #
#  3. АСИММЕТРИЯ hi-low (короткий перед / длинная спинка)
# --------------------------------------------------------------------------- #
class HiLowSkirtPattern:
    title = "HI-LOW"
    rise = 22.0   # насколько перед короче бока
    drop = 18.0   # насколько спинка длиннее бока
    coverage = 0.5 # полусолнце

    waist_mode = "fitted"   # fitted = radial drape (edge = waist 1:1); gathered = edge x gather
    gather = 1.0

    def __init__(self, m: Measurements, rise: Optional[float] = None,
                 drop: Optional[float] = None, gather: Optional[float] = None,
                 waist_mode: Optional[str] = None):
        self.m = m
        if rise is not None:
            self.rise = rise
        if drop is not None:
            self.drop = drop
        if waist_mode is not None:
            self.waist_mode = waist_mode
        if gather is not None:
            self.gather = gather
        elif self.waist_mode == "gathered" and self.gather <= 1.0:
            self.gather = 1.6

    def _panel(self, a0: float, a1: float, is_front: bool, name: str, label: str) -> PatternPiece:
        m = self.m
        waist_eff = m.waist_cm + m.ease_waist
        r_in = (waist_eff * self.gather) / (2 * math.pi) # радиус талии для полусолнца
        
        steps = 72
        pts = []
        
        # 1. Внутренний радиус (талия) от a0 до a1
        for i in range(steps + 1):
            a_deg = a0 + (a1 - a0) * i / steps
            a_rad = math.radians(a_deg)
            pts.append((r_in * math.cos(a_rad), r_in * math.sin(a_rad)))
            
        # 2. Внешний радиус (подол) от a1 до a0 (обратный ход)
        for i in range(steps + 1):
            a_deg = a1 + (a0 - a1) * i / steps
            a_rad = math.radians(a_deg)
            
            if is_front:
                # a_deg идет от 0 до -90
                factor = math.sin(-a_rad) # sin(90) = 1
                L_a = m.length_cm - self.rise * factor
            else:
                # a_deg идет от 90 до 0
                factor = math.sin(a_rad) # sin(90) = 1
                L_a = m.length_cm + self.drop * factor
                
            r_out = r_in + L_a
            pts.append((r_out * math.cos(a_rad), r_out * math.sin(a_rad)))
            
        # Закрываем
        pts.append(pts[0])
        
        # Сдвиг в положительные координаты
        min_x = min(p[0] for p in pts)
        min_y = min(p[1] for p in pts)
        pts = [(x - min_x, y - min_y) for x, y in pts]
        
        cx = (max(p[0] for p in pts)) / 2
        cy = (r_in + m.length_cm) / 2 - min_y
        
        return PatternPiece(
            name=name, points=pts,
            grain_line=((cx, cy - 5), (cx, cy + 5)),
            labels=[
                {"text": label, "x": cx, "y": cy, "size": 1.2, "bold": True},
                {"text": f"Т{m.waist_cm:g} Б{m.hip_cm:g} Д{m.length_cm:g}",
                 "x": cx, "y": cy + 2, "size": 0.7}
            ],
            notches=[],
            cut_on_fold=is_front,
            quantity=1 if is_front else 2
        )

    def generate(self) -> List[PatternPiece]:
        front = self._panel(-90.0, 0.0, is_front=True, name="front_panel", label=f"ПЕРЕД — {self.title} (по сгибу)")
        back = self._panel(0.0, 90.0, is_front=False, name="back_panel", label=f"СПИНКА — {self.title} (2 детали)")
        wb = StraightSkirtPattern(self.m).waistband()
        return [front, back, wb]


# --------------------------------------------------------------------------- #
#  4. БАЛЛОН (bubble)
# --------------------------------------------------------------------------- #
class BubbleSkirtPattern:
    title = "БАЛЛОН"
    fullness = 1.8     # расход ткани по ширине (сборка)
    pouf = 0.18        # доля доп. длины на «пузырь»

    def __init__(self, m: Measurements, fullness: Optional[float] = None):
        self.m = m
        if fullness:
            self.fullness = fullness

    def generate(self) -> List[PatternPiece]:
        m = self.m
        hip_eff = m.hip_cm + m.ease_hip
        width = hip_eff * self.fullness
        half = width / 2
        cut_len = m.length_cm * (1 + self.pouf)     # кроится длиннее: низ подбирается
        # основное полотнище — сборка сверху (пояс) и снизу (подкладка)
        panel = PatternPiece(
            name="balloon_panel", points=_rect(half, cut_len),
            grain_line=((half * 0.5, 5), (half * 0.5, cut_len - 5)),
            labels=[
                {"text": f"ПОЛОТНИЩЕ — {self.title}", "x": half * 0.5,
                 "y": cut_len * 0.5, "size": 1.3, "bold": True},
                {"text": f"сборка сверху+снизу ×{self.fullness:g}",
                 "x": half * 0.5, "y": cut_len * 0.5 + 2.5, "size": 0.7},
            ],
            notches=[(half, 0.0), (half, cut_len)], cut_on_fold=True, quantity=2,
        )
        # нижняя обтачка (подгиб) — уже, формирует «пузырь»
        hem_w = hip_eff * 0.85 / 2
        hem = PatternPiece(
            name="hem_facing", points=_rect(hem_w, 6.0),
            grain_line=((hem_w * 0.5, 1.5), (hem_w * 0.5, 4.5)),
            labels=[{"text": "ОБТАЧКА НИЗА ×2", "x": hem_w * 0.5, "y": 3.0,
                     "size": 0.9, "bold": True}],
            notches=[], cut_on_fold=True, quantity=2,
        )
        wb = StraightSkirtPattern(m).waistband()
        return [panel, hem, wb]


# --------------------------------------------------------------------------- #
#  5. ЮБКА-ШОРТЫ (skort): передний флап + шорты-кулоты
# --------------------------------------------------------------------------- #
class SkortPattern:
    """Юбка-шорты: видимый передний запах (А-флап) поверх шорт-кулот.

    Шорты моделируются как 4 панели (перед/спинка ×2) с промежностным
    ластовицей (кулоты с ластовицей) — простой и швейно корректный блок.
    """
    title = "ЮБКА-ШОРТЫ"
    flap_len = 42.0       # длина видимого флапа
    short_len = 32.0      # длина шорт по боку

    def __init__(self, m: Measurements, flap_len: Optional[float] = None,
                 short_len: Optional[float] = None):
        self.m = m
        if flap_len:
            self.flap_len = flap_len
        if short_len:
            self.short_len = short_len

    def _short_panel(self, q_width: float, name: str, label: str) -> PatternPiece:
        m = self.m
        rise = m.hip_depth + 7.0          # высота сидения
        total_h = rise + self.short_len
        crotch = q_width * 0.35           # ластовичный выступ
        # левый край — центр (сгиб/шов), внизу выступ ластовицы внутрь
        pts = [
            (crotch, 0.0),                 # талия у центра
            (crotch, rise),                # до линии сидения
            (0.0, rise + 6.0),             # ластовичный крюк
            (crotch, rise + 12.0),         # начало внутр. шва ноги
            (crotch, total_h),             # низ штанины (внутр.)
            (crotch + q_width, total_h),   # низ штанины (внешн.)
            (crotch + q_width, rise),      # бок на линии сидения
            (crotch + q_width - 1.0, 0.0),  # талия у бока
            (crotch, 0.0),
        ]
        return PatternPiece(
            name=name, points=pts,
            grain_line=((crotch + q_width * 0.5, 4), (crotch + q_width * 0.5, total_h - 4)),
            labels=[{"text": label, "x": crotch + q_width * 0.45,
                     "y": total_h * 0.55, "size": 1.0, "bold": True}],
            notches=[(crotch, rise)], cut_on_fold=False, quantity=2,
        )

    def _flap(self) -> PatternPiece:
        m = self.m
        below = max(0.0, self.flap_len - m.hip_depth)
        flare = below * 0.22
        return _darted_quarter(
            m, m.H / 2 + 0.5, m.W / 2 + 0.5, hem_offset=flare,
            dart_ratio=0.55, max_dart=2.5, dart_len=9.0,
            name="skirt_flap", label=f"ФЛАП ПЕРЕД — {self.title}",
            cf_len=self.flap_len, side_len=self.flap_len)

    def generate(self) -> List[PatternPiece]:
        m = self.m
        q = (m.hip_cm + m.ease_hip + 6.0) / 4   # четверть + свобода на шорты
        legs_front = self._short_panel(q, "shorts_front", f"ШОРТЫ ПЕРЕД — {self.title}")
        legs_back = self._short_panel(q, "shorts_back", f"ШОРТЫ СПИНКА — {self.title}")
        flap = self._flap()
        wb = StraightSkirtPattern(m).waistband()
        return [flap, legs_front, legs_back, wb]


# --------------------------------------------------------------------------- #
#  Регистрация
# --------------------------------------------------------------------------- #
class HiLowGatheredSkirtPattern(HiLowSkirtPattern):
    """HI-LOW with gathered waist (radial cut, waist edge x gather)."""
    title = "HI-LOW СБОРКА"
    waist_mode = "gathered"
    gather = 1.6


MORE_REGISTRY = {
    "tulip": TulipSkirtPattern,
    "mermaid": MermaidSkirtPattern,
    "hi_low": HiLowSkirtPattern,
    "hi_low_gathered": HiLowGatheredSkirtPattern,
    "bubble": BubbleSkirtPattern,
    "skort": SkortPattern,
}

MORE_TYPES = list(MORE_REGISTRY.keys())


def register_more_types() -> dict:
    """Добавить новые типы в PATTERN_REGISTRY (идемпотентно)."""
    P.PATTERN_REGISTRY.update(MORE_REGISTRY)
    return dict(P.PATTERN_REGISTRY)


register_more_types()
