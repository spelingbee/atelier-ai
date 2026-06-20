"""Проверка геометрии карманов: замкнутость, площадь>0, без самопересечений.

Запуск:  python pockets_check.py
"""
import sys
from patterns import Measurements
import pockets as PK


def shoelace_area(pts):
    a = 0.0
    for i in range(len(pts) - 1):
        x1, y1 = pts[i]
        x2, y2 = pts[i + 1]
        a += x1 * y2 - x2 * y1
    return abs(a) / 2.0


def is_closed(pts):
    return abs(pts[0][0] - pts[-1][0]) < 1e-9 and abs(pts[0][1] - pts[-1][1]) < 1e-9


def _seg_intersect(p1, p2, p3, p4):
    def ccw(a, b, c):
        return (c[1] - a[1]) * (b[0] - a[0]) - (b[1] - a[1]) * (c[0] - a[0])
    d1 = ccw(p3, p4, p1)
    d2 = ccw(p3, p4, p2)
    d3 = ccw(p1, p2, p3)
    d4 = ccw(p1, p2, p4)
    if ((d1 > 0) != (d2 > 0)) and ((d3 > 0) != (d4 > 0)):
        return True
    return False


def has_self_intersection(pts):
    n = len(pts) - 1  # последняя точка == первой
    edges = [(pts[i], pts[i + 1]) for i in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            if abs(i - j) <= 1 or (i == 0 and j == n - 1):
                continue
            if _seg_intersect(edges[i][0], edges[i][1], edges[j][0], edges[j][1]):
                return (i, j)
    return None


def main():
    m = Measurements(waist_cm=72, hip_cm=98, length_cm=70)
    ok = True
    for kind in PK.POCKET_REGISTRY:
        res = PK.build_pocket(kind, m)
        print(f"\n=== {kind}: {res.title} | деталей={len(res.pieces)} | шагов={len(res.sewing_steps)} ===")
        assert res.pieces, f"{kind}: нет деталей"
        assert res.sewing_steps, f"{kind}: нет шагов ТЗ"
        for pc in res.pieces:
            closed = is_closed(pc.points)
            area = shoelace_area(pc.points)
            si = has_self_intersection(pc.points)
            xs = [p[0] for p in pc.points]; ys = [p[1] for p in pc.points]
            w = max(xs) - min(xs); h = max(ys) - min(ys)
            status = "OK"
            if not closed or area <= 0 or si is not None:
                status = "FAIL"; ok = False
            print(f"  [{status}] {pc.name:24s} точек={len(pc.points):3d} "
                  f"габарит={w:.1f}×{h:.1f}см площадь={area:.1f}см² кол-во={pc.quantity} "
                  f"closed={closed} self_int={si}")
    print("\nИТОГ:", "ВСЕ ОК" if ok else "ЕСТЬ ОШИБКИ")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
