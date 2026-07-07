import sys
import os
from pathlib import Path

# Add current path to sys.path
sys.path.append(str(Path(__file__).parent.absolute()))

from patterns import Measurements, EdgeRole
import geometry_modifiers as GM
import components as C
import pockets
import export

def test_jeans_pockets():
    print("Testing build_jeans_pocket...")
    m = Measurements(waist_cm=72, hip_cm=98, length_cm=70)
    pres = pockets.build_pocket("jeans", m)
    
    assert pres.key == "jeans"
    piece_names = [p.name for p in pres.pieces]
    print(f"Generated pocket pieces: {piece_names}")
    
    assert "pocket_jeans_lining" in piece_names
    assert "pocket_jeans_facing" in piece_names
    assert "pocket_jeans_coin" in piece_names
    
    for p in pres.pieces:
        pts = p.points
        # Check closed loop
        assert abs(pts[0][0] - pts[-1][0]) < 1e-5 and abs(pts[0][1] - pts[-1][1]) < 1e-5, f"{p.name} contour is not closed!"
        # Check area
        s = 0.0
        for i in range(len(pts) - 1):
            s += pts[i][0] * pts[i+1][1] - pts[i+1][0] * pts[i][1]
        area = abs(s) / 2.0
        assert area > 0, f"{p.name} has zero area!"
        print(f"  [OK] {p.name:25s} area = {area:.1f} cm2")
        
    print("build_jeans_pocket: SUCCESS\n")

def test_crossover_waistband():
    print("Testing apply_crossover_waistband...")
    m = Measurements(waist_cm=72, hip_cm=98, length_cm=70)
    
    # 1. Resolve standard waistband
    wb_res = C.build_waistband("crossover", m)
    piece_names = [p.name for p in wb_res.pieces]
    print(f"Generated waistband pieces: {piece_names}")
    assert "waistband_crossover" in piece_names
    
    wb_piece = wb_res.pieces[0]
    pts = wb_piece.points
    assert abs(pts[0][0] - pts[-1][0]) < 1e-5 and abs(pts[0][1] - pts[-1][1]) < 1e-5, "Contour not closed"
    
    # Standard length is waist_eff (72 + 1) + 3 = 76. Crossover adds +6.0 = 82.0.
    xs = [p[0] for p in pts]
    w = max(xs) - min(xs)
    print(f"Standard waist_eff = 73.0, expected crossover band length = 82.0, got = {w:.1f}")
    assert abs(w - 82.0) < 1e-3, f"Expected crossover waistband width 82.0, got {w}"
    print("apply_crossover_waistband: SUCCESS\n")

def test_back_yoke_cut():
    print("Testing cut_back_yoke...")
    m = Measurements(waist_cm=72, hip_cm=98, length_cm=70)
    base = C.StraightSkirtPattern(m)
    back = base.back_panel()
    
    # Slice the back panel with a V-yoke cut deep enough to cover the dart (13.0, 9.0)
    pieces = GM.cut_back_yoke(back, yoke_depth_center=13.0, yoke_depth_side=9.0)
    piece_names = [p.name for p in pieces]
    print(f"Slice returned pieces: {piece_names}")
    
    assert any("yoke" in name for name in piece_names), "Yoke piece missing"
    assert any("remainder" in name for name in piece_names), "Remainder piece missing"
    
    for p in pieces:
        pts = p.points
        assert abs(pts[0][0] - pts[-1][0]) < 1e-5 and abs(pts[0][1] - pts[-1][1]) < 1e-5, f"{p.name} contour is not closed!"
        s = 0.0
        for i in range(len(pts) - 1):
            s += pts[i][0] * pts[i+1][1] - pts[i+1][0] * pts[i][1]
        area = abs(s) / 2.0
        assert area > 0, f"{p.name} has zero area!"
        print(f"  [OK] {p.name:25s} area = {area:.1f} cm2")
        
    print("cut_back_yoke: SUCCESS\n")

def test_denim_assembly_integration():
    print("Testing Denim assembly integration...")
    m = Measurements(waist_cm=72, hip_cm=98, length_cm=70)
    
    selection = {
        "silhouette": "straight",
        "waistband": "crossover",
        "closure": "zip_back",
        "detail": ["pockets:jeans", "back_yoke", "straps"]
    }
    
    assembly = C.resolve(selection, m)
    piece_names = [p.name for p in assembly.pieces]
    print(f"Assembly pieces: {piece_names}")
    
    # Basic panel components (back panel is cut into yoke + remainder)
    assert "front_panel" in piece_names
    assert any("back_panel_yoke" in name for name in piece_names)
    assert any("back_panel_remainder" in name for name in piece_names)
    # Waistband
    assert "waistband_crossover" in piece_names
    # Pockets
    assert "pocket_jeans_lining" in piece_names
    assert "pocket_jeans_facing" in piece_names
    assert "pocket_jeans_coin" in piece_names
    # Straps
    assert "belt_loop" in piece_names
    
    for p in assembly.pieces:
        pts = p.points
        assert abs(pts[0][0] - pts[-1][0]) < 1e-5 and abs(pts[0][1] - pts[-1][1]) < 1e-5, f"{p.name} contour is not closed!"
        s = 0.0
        for i in range(len(pts) - 1):
            s += pts[i][0] * pts[i+1][1] - pts[i+1][0] * pts[i][1]
        area = abs(s) / 2.0
        assert area > 0, f"{p.name} has zero area!"
        print(f"  [OK] {p.name:30s} area = {area:.1f} cm2, quantity = {p.quantity}")
        
    # Test exporting to SVG/PDF to verify exporter compatibility
    tmp_svg = "denim_assembly_test.svg"
    tmp_pdf = "denim_assembly_test.pdf"
    w, h = export.export_svg(assembly.pieces, tmp_svg)
    rows, cols = export.export_pdf_tiled(assembly.pieces, tmp_pdf)
    
    print(f"Export SVG: {w:.1f}x{h:.1f} cm. Export PDF: {rows}x{cols} A4 sheets.")
    assert os.path.exists(tmp_svg) and os.path.getsize(tmp_svg) > 200
    assert os.path.exists(tmp_pdf) and os.path.getsize(tmp_pdf) > 500
    
    # Cleanup
    os.unlink(tmp_svg)
    os.unlink(tmp_pdf)
    
    print("Denim assembly integration: SUCCESS\n")

if __name__ == "__main__":
    test_jeans_pockets()
    test_crossover_waistband()
    test_back_yoke_cut()
    test_denim_assembly_integration()
    print("ALL DENIM EXTENSION TESTS PASSED SUCCESSFULLY!")
