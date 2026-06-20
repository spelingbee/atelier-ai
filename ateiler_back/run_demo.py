"""Демо + самопроверка геометрии (golden test по периметру талии)."""
import math
from patterns import Measurements, build_pattern, PATTERN_REGISTRY, edge_length
from export import export_svg, export_pdf_tiled


def waist_len_of_panel(piece):
    """Сумма рёбер на линии талии (y≈0) минус раствор вытачки."""
    pts = piece.points
    total = 0.0
    for i in range(len(pts) - 1):
        a, b = pts[i], pts[i + 1]
        if abs(a[1]) < 0.6 and abs(b[1]) < 0.6:   # оба конца на талии
            total += abs(b[0] - a[0])
    return total


def check_straight():
    m = Measurements(waist_cm=68, hip_cm=96, length_cm=60)
    pieces = build_pattern("straight", m)
    front = next(p for p in pieces if p.name == "front_panel")
    back = next(p for p in pieces if p.name == "back_panel")
    # Сумма талии всех четвертей (2×перед + 2×спинка, каждая деталь = половина)
    waist_pattern = 2 * waist_len_of_panel(front) + 2 * waist_len_of_panel(back)
    target = m.waist_cm + m.ease_waist
    print(f"[straight] талия лекала={waist_pattern:.2f} см, цель={target:.2f} см, дельта={waist_pattern-target:+.2f}")
    assert abs(waist_pattern - target) < 0.5, "Периметр талии не сходится!"


def check_circle(kind, coverage):
    m = Measurements(waist_cm=70, hip_cm=98, length_cm=50, ease_waist=1.0)
    cls = PATTERN_REGISTRY[kind]
    inst = cls(m)
    waist_arc_total = coverage * 2 * math.pi * inst.r_in
    target = m.waist_cm + m.ease_waist
    print(f"[{kind}] R_in={inst.r_in:.2f} см, талия лекала={waist_arc_total:.2f} см, цель={target:.2f}")
    assert abs(waist_arc_total - target) < 0.5


if __name__ == "__main__":
    print("=== GOLDEN TESTS ===")
    check_straight()
    check_circle("half_circle", 0.5)
    check_circle("full_circle", 1.0)
    print("✓ все тесты пройдены\n")

    print("=== ГЕНЕРАЦИЯ ФАЙЛОВ ===")
    cases = {
        "straight": Measurements(68, 96, 60),
        "pencil": Measurements(68, 96, 62),
        "a_line": Measurements(70, 98, 70),
        "half_circle": Measurements(70, 98, 50),
        "full_circle": Measurements(70, 98, 45),
    }
    for t, m in cases.items():
        pieces = build_pattern(t, m)
        w, h = export_svg(pieces, f"/data/skirt/out_{t}.svg")
        rows, cols = export_pdf_tiled(pieces, f"/data/skirt/out_{t}.pdf")
        names = ", ".join(p.name for p in pieces)
        print(f"{t:12s} -> SVG {w:.0f}x{h:.0f}см | PDF {rows}x{cols} листов A4 | детали: {names}")
    print("\nГотово.")
