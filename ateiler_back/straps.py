"""
AtelierAI — РЕМНИ, ЛЯМКИ И ШЛЁВКИ (NEW FILE, аддитивно).

Макрос для построения ремней, бедренных лямок и шлёвок (детали для фото 1 с портупеей).
Все координаты в сантиметрах.
"""
from __future__ import annotations

from typing import List, Tuple
from patterns import Measurements, PatternPiece, Edge, EdgeRole

def _rect_edges(w: float, h: float) -> List[Edge]:
    """Строит прямоугольник против часовой стрелки из семантических ребер."""
    return [
        Edge(role=EdgeRole.INTERNAL, points=[(0.0, 0.0), (0.0, h)]),
        Edge(role=EdgeRole.HEM, points=[(0.0, h), (w, h)]),
        Edge(role=EdgeRole.INTERNAL, points=[(w, h), (w, 0.0)]),
        Edge(role=EdgeRole.WAIST, points=[(w, 0.0), (0.0, 0.0)]),
    ]

def build_straps_and_loops(m: Measurements) -> Tuple[List[PatternPiece], List[str]]:
    """
    Генерирует набор деталей для шлевок, ремня и бедренных лямок портупеи.
    """
    pieces = []
    steps = [
        "Ремни и шлёвки:",
    ]
    
    # 1. Шлёвки (Belt Loops) - 5 штук
    loop_w, loop_h = 1.5, 8.0
    loop_piece = PatternPiece(
        name="belt_loop",
        edges=_rect_edges(loop_w, loop_h),
        grain_line=((loop_w * 0.5, 1.0), (loop_w * 0.5, loop_h - 1.0)),
        labels=[{"text": "ШЛЁВКА ×5", "x": loop_w * 0.5, "y": loop_h * 0.5, "size": 0.6, "bold": True}],
        notches=[],
        cut_on_fold=False,
        quantity=5
    )
    pieces.append(loop_piece)
    steps.append(f"  • Заутюжить и отстрочить 5 шлёвок ({loop_w:g}×{loop_h:g} см). Настрочить на пояс.")

    # 2. Ремень (Waist Belt) - 1 штука
    belt_w = 3.0
    belt_len = round(m.waist_cm + 15.0, 1)
    belt_piece = PatternPiece(
        name="waist_belt",
        edges=_rect_edges(belt_len, belt_w),
        grain_line=((5.0, belt_w * 0.5), (belt_len - 5.0, belt_w * 0.5)),
        labels=[{"text": f"РЕМЕНЬ ПОЯСНОЙ ×1 ({belt_len:g}×{belt_w:g})", "x": belt_len * 0.5, "y": belt_w * 0.5, "size": 0.8, "bold": True}],
        notches=[(m.waist_cm, belt_w * 0.5)],
        cut_on_fold=False,
        quantity=1
    )
    pieces.append(belt_piece)
    steps.append(f"  • Изготовить ремень поясной ({belt_len:g}×{belt_w:g} см), установить пряжку.")

    # 3. Бедренные лямки портупеи (Thigh/Harness Straps) - 2 штуки
    strap_w = 2.5
    strap_len = round(m.hip_cm * 0.6, 1)
    strap_piece = PatternPiece(
        name="harness_strap",
        edges=_rect_edges(strap_len, strap_w),
        grain_line=((5.0, strap_w * 0.5), (strap_len - 5.0, strap_w * 0.5)),
        labels=[{"text": f"ЛЯМКА БЕДРЕННАЯ ×2 ({strap_len:g}×{strap_w:g})", "x": strap_len * 0.5, "y": strap_w * 0.5, "size": 0.8, "bold": True}],
        notches=[],
        cut_on_fold=False,
        quantity=2
    )
    pieces.append(strap_piece)
    steps.append(f"  • Изготовить 2 бедренные лямки портупеи ({strap_len:g}×{strap_w:g} см), прикрепить к кокетке/поясу.")

    return pieces, steps
