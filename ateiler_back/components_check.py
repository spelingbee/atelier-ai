"""Проверка Фазы 1: слоты + компоненты + стыки + решатель."""
from patterns import Measurements
import components as C
from export import export_svg, export_pdf_tiled

m = Measurements(waist_cm=72, hip_cm=98, length_cm=70)

print("=== КАТАЛОГ СЛОТОВ ===")
for slot, opts in C.slot_catalog().items():
    print(f"  {slot:11s}: " + ", ".join(o["key"] for o in opts))

cases = [
    ("Классика", {"silhouette": "straight", "waistband": "band", "closure": "zip_side"}),
    ("Карандаш без шлицы", {"silhouette": "pencil", "closure": "zip_side"}),
    ("Солнце + пояс", {"silhouette": "full_circle", "waistband": "band"}),
    ("Плиссе + притачной пояс", {"silhouette": "pleated", "waistband": "band"}),
    ("Плиссе + резинка", {"silhouette": "pleated", "waistband": "elastic", "closure": "none"}),
    ("Баллон + резинка", {"silhouette": "bubble", "waistband": "elastic", "closure": "none"}),
    ("Солнце + годе (конфликт)", {"silhouette": "full_circle", "detail": ["godet"]}),
    ("Карандаш + годе + оверлей-кокетка",
     {"silhouette": "pencil", "closure": "slit", "detail": ["godet"], "overlay": "yoke_overlay"}),
]

for title, sel in cases:
    a = C.resolve(sel, m)
    print(f"\n=== {title} ===")
    print("  выбор:", {k: v for k, v in a.selection.items()})
    wj = a.waist_join
    print(f"  талиевый стык: срез {wj['skirt_waist_cm']} см → пояс {wj['waistband_cm']} см | ×{wj['ratio']} | {wj['method']}")
    print("  детали кроя:", ", ".join(f"{p.name}×{p.quantity}" for p in a.pieces))
    if a.warnings:
        for w in a.warnings:
            print("   ⚠", w)

# сквозная проверка экспорта: собранное из частей лекало -> SVG/PDF
print("\n=== ЭКСПОРТ СОБРАННОГО ЛЕКАЛА ===")
a = C.resolve({"silhouette": "a_line", "waistband": "band", "closure": "zip_side"}, m)
w, h = export_svg(a.pieces, "comp_assembly.svg")
rows, cols = export_pdf_tiled(a.pieces, "comp_assembly.pdf")
print(f"  SVG {w:.0f}x{h:.0f}см, PDF A4 {rows}x{cols}, деталей={len(a.pieces)}")
print("  ТЗ:")
for line in a.sewing_spec:
    print("   •", line)
print("\nOK")
