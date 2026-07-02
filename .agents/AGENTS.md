# Project-Scoped Rules: Atelier AI Geometry & Pattern Scaling

This document contains rules and guidelines for future modifications and scaling of the pattern engine.

## 1. Shapely Polygon Validation & Robustness

- **Validation Check**: Always validate polygons after applying geometric modifications (e.g., `cut_yoke`, `apply_pleats`, `split_panels`, or custom offsets) using `polygon.is_valid`.
- **Self-Intersections**: Extreme user measurements or very deep darts can cause self-intersections.
- **Auto-Fixing**: Where possible, use `polygon.buffer(0)` to resolve self-intersections.
- **Error Handling**: Gracefully catch `BufferError` or geometry invalidity, log detailed warnings/errors, and fall back to safe default geometry instead of crashing.

## 2. Contour Winding Order (CCW Direction)

- **Counter-Clockwise Winding**: All pattern pieces and individual edges MUST maintain a consistent counter-clockwise (CCW) winding order.
- **Mirroring Safety**: When mirroring edges (e.g., in `mirror_asymmetry`), ensure the coordinates are reversed appropriately to maintain the CCW direction.
- **Verification**: Naive coordinate mirroring or inversion can invert the polygon orientation. Prior to exporting to SVG, DXF, or PDF:
  - Check the signed area of the points list.
  - Enforce correct orientation using `shapely.geometry.polygon.orient(poly, sign=1.0)` to ensure CAD-exporters interpret seam allowances correctly.
