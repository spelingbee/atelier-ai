import sys
import os

sys.path.append(os.path.abspath("c:/My/Projects/Work/Atelier AI/ateiler_back"))

from patterns import Measurements
import components as C
import overlays as O
import export
import seam_shapely  # noqa: F401  (автопатч припуск на швы)

def test_integration():
    print("Testing Wrap Closure & Straps integration...")
    m = Measurements(waist_cm=72, hip_cm=98, length_cm=70)
    
    # We select straight silhouette, wrap closure, waistband and straps/loops detail
    selection = {
        "silhouette": "straight",
        "waistband": "band",
        "closure": "wrap",
        "overlay": "none",
        "detail": ["straps"]
    }
    
    # Resolve through components layer
    assembly = C.resolve(selection, m)
    
    # Verify pieces
    pieces = assembly.pieces
    piece_names = [p.name for p in pieces]
    print(f"Generated pieces: {piece_names}")
    
    # Assert expected pieces exist
    assert "front_panel_wrap" in piece_names, "Wrapped front panel is missing!"
    assert "tie" in piece_names, "Belt ties are missing!"
    assert "belt_loop" in piece_names, "Belt loops are missing!"
    assert "waist_belt" in piece_names, "Waist belt is missing!"
    assert "harness_strap" in piece_names, "Harness straps are missing!"
    
    # Verify geometry of each piece
    for p in pieces:
        pts = p.points
        # Check closed loop
        assert abs(pts[0][0] - pts[-1][0]) < 1e-5 and abs(pts[0][1] - pts[-1][1]) < 1e-5, f"{p.name} contour is not closed!"
        # Check area
        s = 0.0
        for i in range(len(pts) - 1):
            s += pts[i][0] * pts[i+1][1] - pts[i+1][0] * pts[i][1]
        area = abs(s) / 2.0
        assert area > 0, f"{p.name} has zero area!"
        print(f"  [OK] {p.name:20s} area = {area:.1f} cm2, quantity = {p.quantity}, edges = {[e.role.name for e in p.edges]}")
        
    # Export to SVG/PDF to verify exporter works on new pieces
    tmp_svg = "wrap_straps_test.svg"
    tmp_pdf = "wrap_straps_test.pdf"
    w, h = export.export_svg(pieces, tmp_svg)
    rows, cols = export.export_pdf_tiled(pieces, tmp_pdf)
    
    print(f"Export SVG: {w:.1f}x{h:.1f} cm. Export PDF: {rows}x{cols} A4 sheets.")
    assert os.path.exists(tmp_svg) and os.path.getsize(tmp_svg) > 200
    assert os.path.exists(tmp_pdf) and os.path.getsize(tmp_pdf) > 500
    
    # Cleanup
    os.unlink(tmp_svg)
    os.unlink(tmp_pdf)
    print("Integration test: SUCCESS\n")

def test_button_paperbag_integration():
    print("Testing Button Front & Paperbag Waist integration...")
    m = Measurements(waist_cm=72, hip_cm=98, length_cm=70)
    
    selection = {
        "silhouette": "pencil",
        "waistband": "band",
        "closure": "button_front",
        "overlay": "none",
        "detail": ["paperbag", "straps"]
    }
    
    assembly = C.resolve(selection, m)
    pieces = assembly.pieces
    piece_names = [p.name for p in pieces]
    print(f"Generated pieces: {piece_names}")
    print(f"Warnings: {assembly.warnings}")
    
    assert "front_panel_placket_paperbag" in piece_names, "Placket paperbag front panel is missing!"
    assert "back_panel_paperbag" in piece_names, "Paperbag back panel is missing!"
    assert "waistband" in piece_names, "Waistband is missing!"
    assert "belt_loop" in piece_names
    
    assert any("Paperbag несовместима с притачным поясом" in w for w in assembly.warnings), "Expected waistband conflict warning is missing!"
    
    for p in pieces:
        pts = p.points
        assert abs(pts[0][0] - pts[-1][0]) < 1e-5 and abs(pts[0][1] - pts[-1][1]) < 1e-5, f"{p.name} contour is not closed!"
        s = 0.0
        for i in range(len(pts) - 1):
            s += pts[i][0] * pts[i+1][1] - pts[i+1][0] * pts[i][1]
        area = abs(s) / 2.0
        assert area > 0, f"{p.name} has zero area!"
        print(f"  [OK] {p.name:30s} area = {area:.1f} cm2, quantity = {p.quantity}")
        
    print("Button Front & Paperbag integration test: SUCCESS\n")

def test_culottes_integration():
    print("Testing Culottes (skirt-pants) with cargo pockets and paperbag waist...")
    m = Measurements(waist_cm=72, hip_cm=98, length_cm=70)
    
    selection = {
        "silhouette": "culottes",
        "waistband": "elastic",
        "closure": "none",
        "overlay": "none",
        "detail": ["paperbag", "pockets:cargo", "straps"]
    }
    
    assembly = C.resolve(selection, m)
    pieces = assembly.pieces
    piece_names = [p.name for p in pieces]
    print(f"Generated pieces: {piece_names}")
    
    assert "front_panel_paperbag" in piece_names
    assert "back_panel_paperbag" in piece_names
    assert "waistband" in piece_names
    assert "pocket_cargo_face" in piece_names
    assert "pocket_cargo_gusset" in piece_names
    assert "pocket_cargo_flap" in piece_names
    assert "belt_loop" in piece_names
    
    front_piece = next(p for p in pieces if p.name == "front_panel_paperbag")
    y_coords = [pt[1] for pt in front_piece.points]
    assert min(y_coords) == -4.0, "Paperbag modification was not applied to Culottes front panel!"
    
    for p in pieces:
        pts = p.points
        assert abs(pts[0][0] - pts[-1][0]) < 1e-5 and abs(pts[0][1] - pts[-1][1]) < 1e-5, f"{p.name} contour is not closed!"
        s = 0.0
        for i in range(len(pts) - 1):
            s += pts[i][0] * pts[i+1][1] - pts[i+1][0] * pts[i][1]
        area = abs(s) / 2.0
        assert area > 0, f"{p.name} has zero area!"
        print(f"  [OK] {p.name:30s} area = {area:.1f} cm2, quantity = {p.quantity}")
        
    print("Culottes integration test: SUCCESS\n")

if __name__ == "__main__":
    test_integration()
    test_button_paperbag_integration()
    test_culottes_integration()
    print("ALL INTEGRATION TESTS PASSED!")
