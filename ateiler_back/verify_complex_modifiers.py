import sys
import os
from pathlib import Path

# Add current path to sys.path
sys.path.append(str(Path(__file__).parent.absolute()))

from patterns import Measurements, EdgeRole
import geometry_modifiers as GM
import components as C
import export

def test_split_and_insert_wedge():
    print("Testing split_and_insert_wedge (Model 3)...")
    m = Measurements(waist_cm=72, hip_cm=98, length_cm=70)
    base = C.StraightSkirtPattern(m)
    front = base.front_panel()
    
    pieces = GM.split_and_insert_wedge(front, split_x_ratio=0.6, pleated=True)
    piece_names = [p.name for p in pieces]
    print(f"Generated split pieces: {piece_names}")
    
    assert len(pieces) == 3
    assert "front_panel_left" in piece_names
    assert "front_panel_right" in piece_names
    assert "front_panel_wedge_pleated" in piece_names
    
    for p in pieces:
        pts = p.points
        assert abs(pts[0][0] - pts[-1][0]) < 1e-5 and abs(pts[0][1] - pts[-1][1]) < 1e-5, f"{p.name} contour is not closed!"
        s = 0.0
        for i in range(len(pts) - 1):
            s += pts[i][0] * pts[i+1][1] - pts[i+1][0] * pts[i][1]
        area = abs(s) / 2.0
        assert area > 0, f"{p.name} has zero area!"
        print(f"  [OK] {p.name:30s} area = {area:.1f} cm2")
        
    print("split_and_insert_wedge: SUCCESS\n")

def test_apply_draped_wrap():
    print("Testing apply_draped_wrap (Model 1)...")
    m = Measurements(waist_cm=72, hip_cm=98, length_cm=70)
    base = C.StraightSkirtPattern(m)
    front = base.front_panel()
    
    # Extension width overlap
    ov = m.H * 0.25
    draped = GM.apply_draped_wrap(front, overlap_cm=ov, cascade_depth_cm=15.0)
    
    pts = draped.points
    assert abs(pts[0][0] - pts[-1][0]) < 1e-5 and abs(pts[0][1] - pts[-1][1]) < 1e-5, "Draped wrap contour is not closed!"
    
    # Check that Y coordinates extend below the base hem (which is 70 cm)
    ys = [p[1] for p in pts]
    max_y = max(ys)
    print(f"Base length = 70.0, max Y of draped wrap = {max_y:.1f} (expected ~85.0)")
    assert max_y > 84.0, f"Expected cascading hem Y > 84.0, got {max_y}"
    
    print("apply_draped_wrap: SUCCESS\n")

def test_apply_double_layer_wrap():
    print("Testing apply_double_layer_wrap (Model 4)...")
    m = Measurements(waist_cm=72, hip_cm=98, length_cm=70)
    base = C.StraightSkirtPattern(m)
    front = base.front_panel()
    
    ov = m.H * 0.25
    pieces = GM.apply_double_layer_wrap(front, overlap_cm=ov)
    piece_names = [p.name for p in pieces]
    print(f"Generated double wrap pieces: {piece_names}")
    
    assert len(pieces) == 2
    assert "front_panel_double_outer" in piece_names
    assert "front_panel_double_inner" in piece_names
    
    for p in pieces:
        assert p.quantity == 1, f"Expected quantity=1 for individual double wrap layers, got {p.quantity}"
        pts = p.points
        assert abs(pts[0][0] - pts[-1][0]) < 1e-5 and abs(pts[0][1] - pts[-1][1]) < 1e-5, "Contour not closed"
        
    print("apply_double_layer_wrap: SUCCESS\n")

def test_assemblies():
    print("Testing full assemblies resolution for Model 1, 3, and 4...")
    m = Measurements(waist_cm=72, hip_cm=98, length_cm=70)
    
    # 1. Model 1: draped wrap
    m1_sel = {
        "silhouette": "straight",
        "waistband": "band",
        "closure": "zip_back",
        "detail": ["draped_wrap", "straps"]
    }
    m1_asm = C.resolve(m1_sel, m)
    names1 = [p.name for p in m1_asm.pieces]
    print(f"Model 1 pieces: {names1}")
    assert "front_panel_draped_wrap" in names1
    assert "tie" in names1
    
    # 2. Model 3: A-line with pleated godet insert
    m3_sel = {
        "silhouette": "a_line",
        "waistband": "band",
        "closure": "zip_back",
        "detail": ["pleated_insert"]
    }
    m3_asm = C.resolve(m3_sel, m)
    names3 = [p.name for p in m3_asm.pieces]
    print(f"Model 3 pieces: {names3}")
    assert "front_panel_left" in names3
    assert "front_panel_right" in names3
    assert "front_panel_wedge_pleated" in names3
    
    # 3. Model 4: double wrap skort with pockets and straps
    m4_sel = {
        "silhouette": "skort",
        "waistband": "crossover",
        "closure": "zip_back",
        "detail": ["double_wrap", "pockets", "straps"]
    }
    m4_asm = C.resolve(m4_sel, m)
    names4 = [p.name for p in m4_asm.pieces]
    print(f"Model 4 pieces: {names4}")
    assert "skirt_flap_double_outer" in names4
    assert "skirt_flap_double_inner" in names4
    assert "waistband_crossover" in names4
    assert "tie" in names4
    
    # Export verification for Model 4
    tmp_svg = "m4_test.svg"
    export.export_svg(m4_asm.pieces, tmp_svg)
    assert os.path.exists(tmp_svg) and os.path.getsize(tmp_svg) > 200
    os.unlink(tmp_svg)
    
    print("Assemblies resolution: SUCCESS\n")

if __name__ == "__main__":
    test_split_and_insert_wedge()
    test_apply_draped_wrap()
    test_apply_double_layer_wrap()
    test_assemblies()
    print("ALL ADVANCED MODIFIERS PASSED TESTS SUCCESSFULLY!")
