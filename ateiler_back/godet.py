"""
AtelierAI — Godet module (NEW FILE, additive).

Облегающая мини с клиньями-годе (godet) — как чёрная кожаная юбка с фото:
прилегающий верх (кокетка/обтяжка до бёдер и ниже) + вставленные в разрезы
клинья-секторы, которые дают расклёш по низу.

Геометрия годе = круговой сектор (тот же _arc, что и у «солнца»): вершина вверху
(вшивается в конец разреза), дуга внизу = низ юбки.

Импортирует движок без изменений.
"""
from __future__ import annotations

import math
from typing import List

from patterns import (
    Measurements, PatternPiece, StraightSkirtPattern, _arc, polygon_perimeter,
)


class GodetSkirtPattern:
    """Прилегающая основа + N клиньев-годе.

    Args:
        m: мерки.
        n_godets: сколько клиньев вставляется (типично 4, 6 или 8).
        godet_start_frac: где начинается расклёш ниже линии бёдер
                          (0..1 от участка бёдра->низ).
        flare_deg: угол раскрытия одного клина (больше = пышнее).
    """
    title = "ГОДЕ"

    def __init__(self, m: Measurements, n_godets: int = 4,
                 godet_start_frac: float = 0.45, flare_deg: float = 60.0):
        self.m = m
        self.n_godets = max(2, int(n_godets))
        self.godet_start_frac = min(max(godet_start_frac, 0.0), 0.9)
        self.flare_deg = min(max(flare_deg, 20.0), 120.0)

    def godet_length(self) -> float:
        """Длина клина = от точки старта разреза до низа."""
        m = self.m
        below_hip = max(0.0, m.length_cm - m.hip_depth)
        start_from_waist = m.hip_depth + below_hip * self.godet_start_frac
        return m.length_cm - start_from_waist

    def _godet_piece(self) -> PatternPiece:
        R = self.godet_length()
        half = self.flare_deg / 2.0
        # вершина вверху (0,0), дуга смотрит вниз (90°)
        arc = _arc(0.0, 0.0, R, 90 - half, 90 + half, steps=48)
        pts = [(0.0, 0.0)] + arc + [(0.0, 0.0)]
        # сдвиг в положительные координаты
        minx = min(p[0] for p in pts); miny = min(p[1] for p in pts)
        pts = [(x - minx, y - miny) for x, y in pts]
        cx = (max(p[0] for p in pts)) / 2
        hem_w = math.radians(self.flare_deg) * R          # длина дуги (низ клина)
        return PatternPiece(
            name="godet",
            points=pts,
            grain_line=((cx, 1.0), (cx, R - 1.0)),
            labels=[
                {"text": f"ГОДЕ × {self.n_godets}", "x": cx, "y": R * 0.45,
                 "size": 1.1, "bold": True},
                {"text": f"низ {hem_w:.0f}см", "x": cx, "y": R * 0.55, "size": 0.7},
            ],
            notches=[(cx, 0.0)],          # метка вершины (конец разреза)
            cut_on_fold=False,
            quantity=self.n_godets,
        )

    def _fitted_panels(self) -> List[PatternPiece]:
        """Прилегающие перед/спинка — обычная прямая основа (без расклёша).
        Разрезы под годе — это линии кроя/пошива, их отмечаем надсечкой."""
        base = StraightSkirtPattern(self.m)
        front = base.front_panel()
        back = base.back_panel()
        # отметка высоты, с которой начинается разрез под годе
        slit_y = self.m.length_cm - self.godet_length()
        for p in (front, back):
            p.notches = list(p.notches) + [(0.0, slit_y)]
            p.labels = list(p.labels) + [
                {"text": f"разрез под годе ↑{slit_y:.0f}см", "x": 2.5, "y": slit_y,
                 "size": 0.6}]
        return [front, back]

    def generate(self) -> List[PatternPiece]:
        pieces = self._fitted_panels()
        pieces.append(StraightSkirtPattern(self.m).waistband())
        pieces.append(self._godet_piece())
        return pieces

    # для тестов/аналитики
    def hem_added_cm(self) -> float:
        """Сколько см клёша добавляют все клинья по низу."""
        R = self.godet_length()
        return self.n_godets * math.radians(self.flare_deg) * R
