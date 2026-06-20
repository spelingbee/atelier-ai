"""Numeric proof that the HI-LOW waist edge now matches the body waist.

Before the fix the inner (waist) arc was a FULL circle of radius waist/pi, so the
assembled waist edge was ~2x the body waist (1.92x) while the model claimed a
fitted/darted waist -> internally inconsistent. After the fix:
  fitted   : r_in = waist_eff / (2*pi)        -> waist edge == waist_eff (1:1 drape)
  gathered : r_in = waist_eff*gather / (2*pi) -> waist edge == waist_eff*gather
"""
import math
from patterns import Measurements
import skirt_types_more as S


def inner_arc_len(pts):
    # the first 73 points (steps+1) form the inner / waist arc of the panel
    return sum(math.dist(pts[i], pts[i + 1]) for i in range(72))


def assembled_waist(pieces):
    front = next(p for p in pieces if p.name == "front_panel")
    back = next(p for p in pieces if p.name == "back_panel")
    fa = inner_arc_len(front.points) * (2 if front.cut_on_fold else 1)
    ba = inner_arc_len(back.points) * max(1, back.quantity)
    return fa + ba


m = Measurements(waist_cm=72, hip_cm=98, length_cm=70)
waist_eff = m.waist_cm + m.ease_waist
print(f"body waist_eff = {waist_eff:g} cm\n")

fails = 0
checks = [
    ("hi_low (fitted)", S.HiLowSkirtPattern(m), waist_eff, 0.08),
    ("hi_low_gathered", S.HiLowGatheredSkirtPattern(m), waist_eff * 1.6, 0.08),
    ("hi_low waist_mode='gathered' x2.0", S.HiLowSkirtPattern(m, gather=2.0), waist_eff * 2.0, 0.08),
]
for name, pat, expect, tol in checks:
    w = assembled_waist(pat.generate())
    ratio = w / waist_eff
    ok = abs(w - expect) <= expect * tol
    fails += 0 if ok else 1
    print(f"  [{'OK ' if ok else 'BAD'}] {name:34s} waist_edge={w:6.1f}cm  "
          f"expect~{expect:6.1f}  ratio={ratio:.2f}")

print(f"\n{'ALL OK' if fails == 0 else f'FAILS: {fails}'}")
