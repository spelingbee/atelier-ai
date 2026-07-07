import os
import sys
from pathlib import Path

# Add current path to sys.path
sys.path.append(str(Path(__file__).parent.absolute()))

from patterns import Measurements
import components as C
import export

# Define measurements for standard S/M size
m_skirt1 = Measurements(waist_cm=72, hip_cm=98, length_cm=55)  # Black asymmetric draped mini-midi
m_skirt2 = Measurements(waist_cm=72, hip_cm=98, length_cm=40)  # Olive green cargo mini wrap
m_skirt3 = Measurements(waist_cm=72, hip_cm=98, length_cm=80)  # Denim midi with crossover and slit
m_skirt4 = Measurements(waist_cm=72, hip_cm=98, length_cm=45)  # Black A-line with pleated insert

# Selection configs
selections = {
    "skirt_1_black_asymmetric": {
        "selection": {
            "silhouette": "straight",
            "waistband": "band",
            "closure": "zip_back",
            "detail": ["draped_wrap", "straps"]
        },
        "measurements": m_skirt1
    },
    "skirt_2_olive_cargo": {
        "selection": {
            "silhouette": "a_line",
            "waistband": "band",
            "closure": "wrap",
            "detail": ["pockets:cargo"]
        },
        "measurements": m_skirt2
    },
    "skirt_3_denim_crossover": {
        "selection": {
            "silhouette": "straight",
            "waistband": "crossover",
            "closure": "zip_back",
            "detail": ["pockets:jeans", "back_yoke", "straps", "slit_detail"]
        },
        "measurements": m_skirt3
    },
    "skirt_4_pleated_insert": {
        "selection": {
            "silhouette": "a_line",
            "waistband": "band",
            "closure": "zip_back",
            "detail": ["pleated_insert"]
        },
        "measurements": m_skirt4
    }
}

out_dir = Path("out_patterns")
out_dir.mkdir(exist_ok=True)

print("--- GENERATING PATTERNS ---")
for name, cfg in selections.items():
    print(f"Generating {name}...")
    assembly = C.resolve(cfg["selection"], cfg["measurements"])
    
    # Export SVG
    svg_path = out_dir / f"{name}.svg"
    w, h = export.export_svg(assembly.pieces, str(svg_path))
    
    # Export PDF if possible
    pdf_path = out_dir / f"{name}.pdf"
    try:
        rows, cols = export.export_pdf_tiled(assembly.pieces, str(pdf_path))
        pdf_status = f"PDF: {rows}x{cols} A4 sheets"
    except Exception as e:
        pdf_status = f"PDF export failed: {e}"
        
    print(f"  Saved to {svg_path} ({w:.1f}x{h:.1f} cm), {pdf_status}")
    if assembly.warnings:
        print(f"  Warnings: {assembly.warnings}")
    print(f"  Sewing steps:")
    for step in assembly.sewing_spec:
        print(f"    - {step}")
    print()
