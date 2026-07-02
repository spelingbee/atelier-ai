import sys
import os

sys.path.append(os.path.abspath("c:/My/Projects/Work/Atelier AI/ateiler_back"))

import patterns as P
from patterns import Measurements, EdgeRole
import geometry_modifiers as GM

def test_asymmetry():
    print("Testing Asymmetry Mirror...")
    m = Measurements(waist_cm=72, hip_cm=98, length_cm=70)
    base = P.StraightSkirtPattern(m)
    front = base.front_panel()
    
    print(f"Original front panel points: {len(front.points)}")
    print(f"Original edges: {[e.role.name for e in front.edges]}")
    
    mirrored = GM.mirror_asymmetry(front)[0]
    print(f"Mirrored piece name: {mirrored.name}")
    print(f"Mirrored points count: {len(mirrored.points)}")
    print(f"Mirrored edges: {[e.role.name for e in mirrored.edges]}")
    assert not mirrored.cut_on_fold
    print("Asymmetry Mirror: SUCCESS\n")

def test_yoke_cut():
    print("Testing Yoke Cutting & Dart Closure...")
    m = Measurements(waist_cm=72, hip_cm=98, length_cm=70)
    base = P.StraightSkirtPattern(m)
    front = base.front_panel()
    
    # Test horizontal cut
    pieces_h = GM.cut_yoke(front, 15.0)
    yoke_h = next(p for p in pieces_h if "yoke" in p.name)
    assert len([e for e in yoke_h.edges if e.role == EdgeRole.DART_LEG]) == 0
    
    # Test diagonal cut
    pieces_d = GM.cut_yoke(front, 10.0, height_right_cm=20.0)
    print(f"Diagonal cut yoke returned {len(pieces_d)} pieces.")
    yoke_d = next(p for p in pieces_d if "yoke" in p.name)
    remainder_d = next(p for p in pieces_d if "remainder" in p.name)
    
    print(f"Yoke D edges: {[e.role.name for e in yoke_d.edges]}")
    print(f"Remainder D edges: {[e.role.name for e in remainder_d.edges]}")
    
    assert len([e for e in yoke_d.edges if e.role == EdgeRole.DART_LEG]) == 0
    print("Yoke Cutting & Dart Closure: SUCCESS\n")

def test_pleating():
    print("Testing Pleating...")
    m = Measurements(waist_cm=72, hip_cm=98, length_cm=70)
    base = P.StraightSkirtPattern(m)
    front = base.front_panel()
    
    pleated = GM.apply_pleats(front, count=3, pleat_width=4.0)[0]
    print(f"Pleated piece name: {pleated.name}")
    print(f"Original points count: {len(front.points)} -> Pleated points count: {len(pleated.points)}")
    print(f"Pleated edges: {[e.role.name for e in pleated.edges]}")
    print("Pleating: SUCCESS\n")

def test_wrap():
    print("Testing Wrap...")
    m = Measurements(waist_cm=72, hip_cm=98, length_cm=70)
    base = P.StraightSkirtPattern(m)
    front = base.front_panel()
    
    ov = 20.0
    wrapped = GM.apply_wrap(front, ov)
    print(f"Wrapped piece name: {wrapped.name}")
    print(f"Original points count: {len(front.points)} -> Wrapped points count: {len(wrapped.points)}")
    print(f"Wrapped edges: {[e.role.name for e in wrapped.edges]}")
    assert not wrapped.cut_on_fold
    print("Wrap: SUCCESS\n")

def test_placket():
    print("Testing Placket...")
    m = Measurements(waist_cm=72, hip_cm=98, length_cm=70)
    base = P.StraightSkirtPattern(m)
    front = base.front_panel()
    
    plack = GM.apply_placket(front, placket_width=3.0)
    print(f"Placket piece name: {plack.name}")
    print(f"Original points count: {len(front.points)} -> Placket points count: {len(plack.points)}")
    print(f"Placket edges: {[e.role.name for e in plack.edges]}")
    assert not plack.cut_on_fold
    assert any("🔘" in l["text"] for l in plack.labels)
    print("Placket: SUCCESS\n")

def test_paperbag():
    print("Testing Paperbag...")
    m = Measurements(waist_cm=72, hip_cm=98, length_cm=70)
    base = P.StraightSkirtPattern(m)
    front = base.front_panel()
    
    paper = GM.apply_paperbag(front, ruffle_h=4.0)
    print(f"Paperbag piece name: {paper.name}")
    print(f"Original points count: {len(front.points)} -> Paperbag points count: {len(paper.points)}")
    print(f"Paperbag edges: {[e.role.name for e in paper.edges]}")
    y_coords = [p[1] for p in paper.points]
    assert min(y_coords) == -4.0, f"Expected min Y is -4.0, got {min(y_coords)}"
    print("Paperbag: SUCCESS\n")

if __name__ == "__main__":
    test_asymmetry()
    test_yoke_cut()
    test_pleating()
    test_wrap()
    test_placket()
    test_paperbag()
    print("ALL TESTS PASSED SUCCESSFULLY!")
