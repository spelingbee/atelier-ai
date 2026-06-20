"""Проверка драпировок: геометрия + сшиваемость + многослойная сборка.

Запуск: python3 drapes_check.py
"""
import os
from patterns import Measurements
import overlays as O
import drapes as D
import export

os.makedirs(os.path.abspath("/data/skirt"), exist_ok=True)
m = Measurements(waist_cm=72, hip_cm=98, length_cm=70)

print("=== ДРАПИРОВКИ: ГЕОМЕТРИЯ ===")
for key in ["cowl_front", "cascade_side"]:
    ov = D.build_drape(key, m)
    names = ", ".join(f"{p.name}×{p.quantity}" for p in ov.pieces)
    print(f"  {ov.title:26s} слой {ov.layer} | стык {ov.attach} {ov.attach_len_cm:g}см | {names}")
    for n in ov.notes:
        print("      -", n)

print("\n=== verify_drape (сшиваемость + экспорт) ===")
ok = 0
keys = ["cowl_front", "cascade_side"]
for key in keys:
    chk = D.verify_drape(key, m, export_prefix=f"drape_{key}")
    flag = "OK " if chk.ok else "FAIL"
    print(f"  [{flag}] {key}")
    for x in chk.infos:
        print("      \u2713", x)
    for x in chk.warns:
        print("      \u26a0", x)
    for x in chk.fails:
        print("      \u274c", x)
    if chk.ok:
        ok += 1
print(f"\nДРАПИРОВОК ПРОШЛО: {ok}/{len(keys)}")

print("\n=== СБОРКА: А-силуэт + cowl спереди ===")
la = O.assemble({"silhouette": "a_line", "overlay": "cowl_front",
                 "waistband": "band", "closure": "zip_side"}, m)
print("Слои (от тела наружу):")
for Lr in la.layer_plan:
    print(f"  слой {Lr['layer']}: {Lr['title']} (стык {Lr['attach']})")
print("Детали кроя:", ", ".join(f"{p.name}×{p.quantity}" for p in la.pieces))
print("Предупреждения:", la.assembly.warnings or "нет")
print("Порядок пошива:")
for i, s in enumerate(la.sewing_order, 1):
    print(f"  {i}. {s}")
w, h = export.export_svg(la.pieces, "/data/skirt/layered_cowl.svg")
rows, cols = export.export_pdf_tiled(la.pieces, "/data/skirt/layered_cowl.pdf")
print(f"\nЭкспорт многослойного лекала: {w:.0f}×{h:.0f} см, A4 {rows}×{cols} листов")

print("\n=== СБОРКА: прямая + каскад сбоку ===")
la2 = O.assemble({"silhouette": "straight", "overlay": "cascade_side"}, m)
for Lr in la2.layer_plan:
    print(f"  слой {Lr['layer']}: {Lr['title']} (стык {Lr['attach']})")
print("Детали кроя:", ", ".join(f"{p.name}×{p.quantity}" for p in la2.pieces))
print("Предупреждения:", la2.assembly.warnings or "нет")
print("\nOK")
