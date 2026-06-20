"""Matplotlib preview of all 5 skirt patterns for visual verification."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MplPoly

from patterns import Measurements, build_pattern
from export import seam_outline, layout_pieces

cases = {
    "Прямая (straight)": ("straight", Measurements(68, 96, 60)),
    "Карандаш (pencil)": ("pencil", Measurements(68, 96, 62)),
    "А-силуэт (a_line)": ("a_line", Measurements(70, 98, 70)),
    "Полусолнце (half_circle)": ("half_circle", Measurements(70, 98, 50)),
    "Солнце (full_circle)": ("full_circle", Measurements(70, 98, 45)),
}

fig, axes = plt.subplots(1, 5, figsize=(22, 7))
for ax, (title, (t, m)) in zip(axes, cases.items()):
    pieces = build_pattern(t, m)
    placed, W, H = layout_pieces(pieces)
    for p, dx, dy in placed:
        shifted = [(x + dx, y + dy) for x, y in p.points]
        outer = seam_outline(shifted, 1.5)
        ax.add_patch(MplPoly(outer, closed=True, fill=False,
                             edgecolor="#bbb", ls="--", lw=1))
        ax.add_patch(MplPoly(shifted, closed=True, fill=False,
                             edgecolor="black", lw=1.8))
        (gx1, gy1), (gx2, gy2) = p.grain_line
        ax.plot([gx1 + dx, gx2 + dx], [gy1 + dy, gy2 + dy], color="#555", lw=1)
        for nx, ny in p.notches:
            ax.plot([nx + dx - 0.4, nx + dx + 0.4], [ny + dy, ny + dy], color="red", lw=2)
        for lab in p.labels:
            ax.text(lab["x"] + dx, lab["y"] + dy, lab["text"], ha="center",
                    fontsize=7, fontweight="bold" if lab.get("bold") else "normal")
    ax.set_title(title, fontsize=11)
    ax.set_aspect("equal")
    ax.invert_yaxis()        # y вниз как в лекале
    ax.grid(True, lw=0.3, alpha=0.4)
    ax.set_xlabel("см")

plt.tight_layout()
plt.savefig("/data/skirt/preview.png", dpi=110, bbox_inches="tight")
print("saved preview.png")
