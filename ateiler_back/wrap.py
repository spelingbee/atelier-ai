"""
AtelierAI — Wrap skirt module (NEW FILE, additive).

Юбка с запахом (как серая юбка-шорты с фото): заднее полотнище +
ДВА передних полотнища, которые заходят друг на друга (нахлёст = overlap),
плюс завязки/бант.

Геометрия запаха = реальная: каждое переднее полотнище шире половины
переда на величину нахлёста. Бант — отдельная деталь-завязка (пошив).
Шорты (skort) — опциональный нижний слой, пока отмечается в инструкции.

Импортирует движок без изменений.
"""
from __future__ import annotations

from typing import List

from patterns import (
    Measurements, PatternPiece, ALineSkirtPattern, StraightSkirtPattern,
)


class WrapSkirtPattern:
    """Юбка с запахом.

    Args:
        m: мерки.
        overlap_frac: доля нахлёста от ширины переда (0.3..0.8).
        base: базовый силуэт — "a_line" (расклёш) или "straight".
    """
    title = "ЗАПАХ"

    def __init__(self, m: Measurements, overlap_frac: float = 0.5,
                 base: str = "a_line"):
        self.m = m
        self.overlap_frac = min(max(overlap_frac, 0.2), 0.8)
        self.base = base if base in ("a_line", "straight") else "a_line"

    def _flare(self) -> float:
        if self.base != "a_line":
            return 0.0
        below_hip = max(0.0, self.m.length_cm - self.m.hip_depth)
        return below_hip * 0.18

    def _front_wrap(self) -> PatternPiece:
        m = self.m
        hd, L = m.hip_depth, m.length_cm
        front_hip = m.H                       # полная ширина переда по бёдрам
        ov = front_hip * self.overlap_frac    # нахлёст
        hip_w = front_hip + ov
        waist_target = m.W + ov * 0.85        # талия переда + нахлёст
        supp = max(0.0, hip_w - waist_target)
        dart_w = min(supp * 0.30, 2.5)
        side_take = max(0.0, supp - 2 * dart_w)
        waist_right = hip_w - side_take
        flare = self._flare()
        dlen = 9.0

        # ЛЕВЫЙ край (x=0) = ведущая кромка запаха (вертикаль, без клёша)
        # ПРАВЫЙ край = боковой срез (расклёш по низу)
        pts: List = [
            (0.0, 0.0),                       # ведущая кромка, верх
            (0.0, L),                         # ведущая кромка, низ
            (hip_w + flare, L),               # низ у бокового среза (клёш)
            (hip_w, hd),                       # линия бёдер у бока
            (waist_right, 0.0),               # талия у бока
        ]
        # две вытачки между боком и ведущей кромкой
        for c in (waist_right * 0.66, waist_right * 0.33):
            pts += [(c + dart_w / 2, 0.0), (c, dlen), (c - dart_w / 2, 0.0)]
        pts.append((0.0, 0.0))

        return PatternPiece(
            name="front_wrap",
            points=pts,
            grain_line=((hip_w * 0.5, 5), (hip_w * 0.5, L - 5)),
            labels=[
                {"text": f"ПЕРЕД ЗАПАХ × 2 (зерк.)", "x": hip_w * 0.5, "y": L * 0.5,
                 "size": 1.2, "bold": True},
                {"text": f"нахлёст {ov:.0f}см", "x": hip_w * 0.5, "y": L * 0.5 + 2, "size": 0.7},
            ],
            notches=[(hip_w, hd), (0.0, hd)],
            cut_on_fold=False,
            quantity=2,
        )

    def _back(self) -> PatternPiece:
        # заднее полотнище — берём из базового силуэта (крой по сгибу)
        if self.base == "a_line":
            back = ALineSkirtPattern(self.m).generate()[1]
        else:
            back = StraightSkirtPattern(self.m).back_panel()
        back.labels = [{"text": "СПИНКА ЗАПАХ", "x": self.m.H / 2 * 0.45,
                        "y": self.m.length_cm * 0.5, "size": 1.2, "bold": True}]
        return back

    def _ties(self) -> PatternPiece:
        m = self.m
        # длина завязки = пол-талии на оборот + хвост на бант
        tie_len = m.waist_cm * 0.75 + 45.0
        h = 8.0
        pts = [(0, 0), (tie_len, 0), (tie_len, h), (0, h), (0, 0)]
        return PatternPiece(
            name="tie", points=pts,
            grain_line=((tie_len * 0.2, h / 2), (tie_len * 0.8, h / 2)),
            labels=[{"text": f"ЗАВЯЗКА/БАНТ × 2 ({tie_len:.0f}×{h:.0f})",
                     "x": tie_len / 2, "y": h / 2, "size": 1.0, "bold": True}],
            notches=[(tie_len, h / 2)], quantity=2,
        )

    def generate(self) -> List[PatternPiece]:
        return [self._front_wrap(), self._back(), self._ties()]

    # аналитика для тестов
    def front_hip_width(self) -> float:
        return self.m.H * (1.0 + self.overlap_frac)
