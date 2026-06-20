"""Проверка Фазы 3: геометрия оверлеев + слои + многослойная сборка."""
from patterns import Measurements
import overlays as O
import export

m = Measurements(waist_cm=72, hip_cm=98, length_cm=70)

print("=== ОВЕРЛЕИ: ГЕОМЕТРИЯ ===")
for key in ["peplum", "yoke_overlay", "flap", "bow"]:
    ov = O.build_overlay(key, m)
    names = ", ".join(f"{p.name}×{p.quantity}{' (сгиб)' if p.cut_on_fold else ''}" for p in ov.pieces)
    print(f"  {ov.title:18s} слой {ov.layer} | стык {ov.attach} {ov.attach_len_cm:g}см | {names}")
    for n in ov.notes:
        print("      -", n)

print("\n=== verify_overlay (сшиваемость верхнего кроя) ===")
ok = 0
keys = ["peplum", "yoke_overlay", "flap", "bow"]
for key in keys:
    chk = O.verify_overlay(key, m, export_prefix=f"ov_{key}")
    flag = "OK " if chk.ok else "FAIL"
    print(f"  [{flag}] {key}")
    for x in chk.infos:
        print("      ✓", x)
    for x in chk.warns:
        print("      ⚠", x)
    for x in chk.fails:
        print("      ❌", x)
    if chk.ok:
        ok += 1
print(f"\nОВЕРЛЕЕВ ПРОШЛО: {ok}/{len(keys)}")

print("\n=== МНОГОСЛОЙНАЯ СБОРКА (юбка с фото: карандаш + кокетка-оверлей) ===")
la = O.assemble({"silhouette": "pencil", "overlay": "yoke_overlay",
                 "waistband": "band", "closure": "slit"}, m)
print("Слои (от тела наружу):")
for Lr in la.layer_plan:
    print(f"  слой {Lr['layer']}: {Lr['title']} (стык {Lr['attach']})")
print("Детали кроя:", ", ".join(f"{p.name}×{p.quantity}" for p in la.pieces))
print("Порядок пошива:")
for i, s in enumerate(la.sewing_order, 1):
    print(f"  {i}. {s}")
w, h = export.export_svg(la.pieces, "/data/skirt/layered_photo.svg")
rows, cols = export.export_pdf_tiled(la.pieces, "/data/skirt/layered_photo.pdf")
print(f"\nЭкспорт многослойного лекала: {w:.0f}×{h:.0f} см, A4 {rows}×{cols} листов")
print("\nOK")
