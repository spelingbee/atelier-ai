"""Проверка Фазы 2: решатель стыков + генератор ТЗ + verify_assembly."""
from patterns import Measurements
import reconcile as R

m = Measurements(waist_cm=72, hip_cm=98, length_cm=70)

cases = [
    ("Прямая + пояс", {"silhouette": "straight", "waistband": "band"}),
    ("Карандаш + шлица", {"silhouette": "pencil", "closure": "slit"}),
    ("Солнце + пояс", {"silhouette": "full_circle", "waistband": "band"}),
    ("Плиссе + резинка", {"silhouette": "pleated", "waistband": "elastic", "closure": "none"}),
    ("Баллон + резинка", {"silhouette": "bubble", "waistband": "elastic", "closure": "none"}),
    ("Асимметрия (фото) + пояс + молния", {"silhouette": "hi_low", "waistband": "band", "closure": "zip_side"}),
    ("Hi-Low GATHER + elastic", {"silhouette": "hi_low_gathered", "waistband": "elastic", "closure": "none"}),
]

print("=== РЕШАТЕЛЬ СТЫКОВ ===")
for title, sel in cases:
    p = R.reconcile_waist(R.C.resolve(sel, m), m)
    extra = ""
    if p.darts:
        extra = " | " + "; ".join(f"{d.location} {d.count}×{d.intake_cm}см/{d.length_cm:g}см" for d in p.darts)
        extra += f" + бок {p.side_take_cm}см"
    elif p.pleats:
        extra = f" | складок ≈{p.pleats['count']}×{p.pleats['width_cm']:g}см глуб.{p.pleats['depth_cm']:g}см"
    elif p.gather_ratio != 1.0:
        extra = f" | сборка ×{p.gather_ratio}"
    print(f"  {title:32s} → {p.method_title}: раствор {p.intake_total_cm:g}см, готов {p.finished_waist_cm:g}см{extra}")

print("\n=== verify_assembly (сшиваемость собранных лекал) ===")
ok_n = 0
for i, (title, sel) in enumerate(cases):
    chk = R.verify_assembly(sel, m, export_prefix=f"asm_{i}")
    flag = "OK " if chk.ok else "FAIL"
    print(f"  [{flag}] {title}")
    for f in chk.fails:
        print("      ❌", f)
    for w in chk.warns:
        print("      ⚠", w)
    if chk.ok:
        ok_n += 1
print(f"\nСШИВАЕМЫХ СБОРОК: {ok_n}/{len(cases)}")

print("\n=== СТРУКТУРНОЕ ТЗ (пример: Асимметрия с фото) ===")
tz = R.build_tech_spec({"silhouette": "hi_low", "waistband": "band", "closure": "zip_side"}, m)
print(R.render_spec_markdown(tz))
print("\nOK")
