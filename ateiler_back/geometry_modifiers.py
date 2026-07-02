"""
AtelierAI — GEOMETRIC MODIFIERS (Layer 2)

This module provides vector-based operations on PatternPiece objects
utilizing their semantic Edge sequences.
"""
from __future__ import annotations

import math
from typing import List, Tuple, Callable, Optional

from patterns import Point, Edge, EdgeRole, PatternPiece

try:
    from shapely.geometry import Polygon, LineString, Point as ShPoint
    from shapely.geometry.polygon import orient
    from shapely.ops import split
    _HAS_SHAPELY = True
except ImportError:
    _HAS_SHAPELY = False


def mirror_point(p: Point) -> Point:
    return (-p[0], p[1])


def line_intersection(p1: Point, p2: Point, p3: Point, p4: Point) -> Optional[Point]:
    """Finds intersection of line passing through p1, p2 and line passing through p3, p4."""
    xdiff = (p1[0] - p2[0], p3[0] - p4[0])
    ydiff = (p1[1] - p2[1], p3[1] - p4[1])

    def det(a, b):
        return a[0] * b[1] - a[1] * b[0]

    div = det(xdiff, ydiff)
    if abs(div) < 1e-9:
        return None

    d = (det(p1, p2), det(p3, p4))
    x = det(d, xdiff) / div
    y = det(d, ydiff) / div
    return x, y


def _validate_and_fix_piece(piece: PatternPiece, original_piece: PatternPiece) -> PatternPiece:
    """
    Validates piece's polygon using shapely.is_valid.
    If self-intersecting, attempts auto-fixing via polygon.buffer(0).
    If that fails or is invalid, catches BufferError or invalidity, logs detailed warnings,
    and falls back to safe original geometry.
    """
    if not _HAS_SHAPELY:
        return piece

    try:
        poly = Polygon(piece.points)
        if not poly.is_valid:
            print(f"[WARNING] Invalid polygon detected for piece '{piece.name}'. Attempting auto-fix using buffer(0).")
            fixed_poly = poly.buffer(0)
            
            if fixed_poly.is_empty or not fixed_poly.is_valid:
                raise ValueError("Polygon auto-fix resulted in empty or invalid geometry.")
            
            if fixed_poly.geom_type == "MultiPolygon":
                fixed_poly = max(fixed_poly.geoms, key=lambda g: g.area)
            
            # Orient the polygon to make sure it is CCW
            fixed_poly = orient(fixed_poly, sign=1.0)
            
            new_pts = [(float(x), float(y)) for x, y in fixed_poly.exterior.coords]
            piece.points = new_pts
            print(f"[INFO] Auto-fix succeeded for piece '{piece.name}'.")

        return piece
    except Exception as e:
        print(f"[ERROR] Geometry modification failed for piece '{piece.name}': {e}. Falling back to safe default geometry.")
        return original_piece


# --------------------------------------------------------------------------- #
#  1. Mirror Asymmetry (Разворот в полную ширину)
# --------------------------------------------------------------------------- #
def mirror_asymmetry(piece: PatternPiece, fold_axis: str = "CF") -> List[PatternPiece]:
    """
    Mirrors a half-pattern piece (cut_on_fold=True) across the axis X = 0.
    Returns a single, full-width piece.
    """
    if not piece.cut_on_fold:
        return [piece]

    # Filter out CENTER_FOLD edges
    non_fold_edges = [e for e in piece.edges if e.role != EdgeRole.CENTER_FOLD]

    # Mirror and reverse the non-fold edges to form the other half of the contour
    mirrored_edges = []
    for edge in reversed(non_fold_edges):
        new_role = edge.role
        if edge.role == EdgeRole.SIDE_RIGHT:
            new_role = EdgeRole.SIDE_LEFT
        elif edge.role == EdgeRole.SIDE_LEFT:
            new_role = EdgeRole.SIDE_RIGHT
            
        mirrored_pts = [mirror_point(p) for p in reversed(edge.points)]
        mirrored_edges.append(Edge(role=new_role, points=mirrored_pts, curve_type=edge.curve_type))

    # Combine original and mirrored edges
    new_edges = non_fold_edges + mirrored_edges

    # Mirror labels and notches
    new_labels = []
    for l in piece.labels:
        new_labels.append(l)
        new_labels.append(dict(l, x=-l["x"], text=f"{l['text']} (ЛЕВ)"))
        
    new_notches = list(piece.notches) + [mirror_point(p) for p in piece.notches]

    mirrored_piece = PatternPiece(
        name=f"{piece.name}_mirrored",
        edges=new_edges,
        grain_line=piece.grain_line,
        labels=new_labels,
        notches=new_notches,
        cut_on_fold=False,
        quantity=1
    )
    return [_validate_and_fix_piece(mirrored_piece, piece)]


# --------------------------------------------------------------------------- #
#  2. Yoke Cutting with Dart Closure (Отрезная кокетка + закрытие вытачек)
# --------------------------------------------------------------------------- #
def recover_edges(new_points: List[Point], original_edges: List[Edge], slice_line: LineString) -> List[Edge]:
    """
    Recovers semantic edge roles for a newly sliced polygon by mapping its segments
    back to original edges or identifying them as cut seams (INTERNAL).
    """
    segments = []
    for i in range(len(new_points) - 1):
        p1 = new_points[i]
        p2 = new_points[i + 1]

        # Check if segment lies along the cut line
        mid = ((p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2)
        on_cut = False
        if _HAS_SHAPELY:
            on_cut = (slice_line.distance(ShPoint(mid)) < 1e-3)

        if on_cut:
            segments.append((p1, p2, EdgeRole.INTERNAL, -1))
            continue

        # Find original edge containing segment midpoint
        mid = ((p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2)
        found_role = EdgeRole.INTERNAL
        found_idx = -1
        
        if _HAS_SHAPELY:
            mid_pt = ShPoint(mid)
            best_dist = 1e-3
            for idx, orig in enumerate(original_edges):
                if len(orig.points) >= 2:
                    line = LineString(orig.points)
                    dist = line.distance(mid_pt)
                    if dist < best_dist:
                        best_dist = dist
                        found_role = orig.role
                        found_idx = idx
        else:
            # Simple distance fallback
            best_dist = 1e-3
            for idx, orig in enumerate(original_edges):
                for j in range(len(orig.points) - 1):
                    a, b = orig.points[j], orig.points[j + 1]
                    # distance from mid to segment a->b
                    dx, dy = b[0] - a[0], b[1] - a[1]
                    l2 = dx*dx + dy*dy
                    if l2 == 0:
                        dist = math.dist(mid, a)
                    else:
                        t = max(0, min(1, ((mid[0] - a[0]) * dx + (mid[1] - a[1]) * dy) / l2))
                        proj = (a[0] + t * dx, a[1] + t * dy)
                        dist = math.dist(mid, proj)
                    if dist < best_dist:
                        best_dist = dist
                        found_role = orig.role
                        found_idx = idx

        segments.append((p1, p2, found_role, found_idx))

    # Group consecutive segments with the same role AND same original edge index
    grouped = []
    curr_key = None
    curr_pts = []
    for p1, p2, role, idx in segments:
        key = (role, idx)
        if key != curr_key:
            if curr_pts:
                grouped.append(Edge(role=curr_key[0], points=curr_pts))
            curr_key = key
            curr_pts = [p1, p2]
        else:
            curr_pts.append(p2)
    if curr_pts:
        grouped.append(Edge(role=curr_key[0], points=curr_pts))

    # Merge first and last edge if keys match
    if len(grouped) > 1:
        first_segment = segments[0]
        last_segment = segments[-1]
        if first_segment[2] == last_segment[2] and first_segment[3] == last_segment[3]:
            first = grouped[0]
            last = grouped.pop()
            first.points = last.points[:-1] + first.points

    return grouped


def rotate_point(p: Point, origin: Point, angle_rad: float) -> Point:
    dx = p[0] - origin[0]
    dy = p[1] - origin[1]
    cos_a = math.cos(angle_rad)
    sin_a = math.sin(angle_rad)
    rx = dx * cos_a - dy * sin_a
    ry = dx * sin_a + dy * cos_a
    return (rx + origin[0], ry + origin[1])


def close_darts_in_yoke(yoke: PatternPiece) -> PatternPiece:
    """
    Finds and closes all darts (pairs of EdgeRole.DART_LEG) in a yoke piece.
    Rotates the right-side vertices to collapse each dart.
    """
    edges = list(yoke.edges)
    
    # Process darts from right to left (based on X coordinate of apex)
    while True:
        # Find adjacent dart legs
        dart_indices = []
        for i in range(len(edges) - 1):
            if edges[i].role == EdgeRole.DART_LEG and edges[i + 1].role == EdgeRole.DART_LEG:
                dart_indices.append(i)
                
        if not dart_indices:
            break
            
        # Take the first dart to process
        idx = dart_indices[0]
        leg1 = edges[idx]
        leg2 = edges[idx + 1]
        
        # Coordinates: leg1 goes V_R -> V_A1, leg2 goes V_A2 -> V_L
        # Waist points V_R (right), V_L (left)
        v_r = leg1.points[0]
        v_l = leg2.points[-1]
        
        # Check if they share the apex
        if math.dist(leg1.points[-1], leg2.points[0]) < 1e-3:
            v_a = leg1.points[-1]
        else:
            # Sliced dart: find original apex by line intersection
            v_a = line_intersection(leg1.points[0], leg1.points[-1], leg2.points[-1], leg2.points[0])
            if v_a is None:
                v_a = leg1.points[-1]
        
        # Compute rotation angle about V_A to align V_R with V_L
        vec_l = (v_l[0] - v_a[0], v_l[1] - v_a[1])
        vec_r = (v_r[0] - v_a[0], v_r[1] - v_a[1])
        angle_l = math.atan2(vec_l[1], vec_l[0])
        angle_r = math.atan2(vec_r[1], vec_r[0])
        theta = angle_l - angle_r
        
        # Rotate all vertices of edges that are to the right of the apex
        apex_x = v_a[0]
        for e in edges:
            # Rotate points of this edge if they are to the right of the dart
            new_pts = []
            for p in e.points:
                if p[0] >= apex_x - 0.1:  # right side of the dart
                    new_pts.append(rotate_point(p, v_a, theta))
                else:
                    new_pts.append(p)
            e.points = new_pts
            
        # Rotate labels and notches on the right side
        yoke.labels = [
            dict(l, x=rotate_point((l["x"], l["y"]), v_a, theta)[0],
                   y=rotate_point((l["x"], l["y"]), v_a, theta)[1])
            if l["x"] >= apex_x - 0.1 else l
            for l in yoke.labels
        ]
        yoke.notches = [
            rotate_point(n, v_a, theta) if n[0] >= apex_x - 0.1 else n
            for n in yoke.notches
        ]
        
        # Remove the two dart leg edges by merging waist edges
        # We replace edges[idx] and edges[idx+1] with a single waist point transition
        # edges[idx-1] ends at V_R (which is now rotated to V_L), and edges[idx+2] starts at V_L
        edges.pop(idx + 1) # remove leg2
        edges.pop(idx)     # remove leg1
        
    yoke.edges = edges
    return yoke


def cut_yoke(piece: PatternPiece, height_cm: float, height_right_cm: Optional[float] = None) -> List[PatternPiece]:
    """
    Slices the pattern piece (horizontally or diagonally) using slice_line.
    Creates [yoke_piece, remainder_piece] and closes darts on the yoke.
    """
    if not _HAS_SHAPELY:
        # Fallback if Shapely is missing: return original piece
        return [piece]

    h_left = height_cm
    h_right = height_right_cm if height_right_cm is not None else height_cm

    poly = Polygon(piece.points)
    slice_line = LineString([(-1000, h_left), (1000, h_right)])
    split_result = split(poly, slice_line)

    yoke_polys = []
    remainder_polys = []

    for geom in split_result.geoms:
        cx, cy = geom.centroid.x, geom.centroid.y
        # Check if centroid is above the cut line
        cutoff_y = h_left + (h_right - h_left) * (cx + 1000.0) / 2000.0
        coords = list(geom.exterior.coords)
        if cy < cutoff_y:
            yoke_polys.append(coords)
        else:
            remainder_polys.append(coords)

    # Process lower remainder piece
    remainder_pieces = []
    for idx, coords in enumerate(remainder_polys):
        rem_edges = recover_edges(coords, piece.edges, slice_line)
        # Sliced bottom seam is now an EdgeRole.WAIST for the remainder skirt
        for e in rem_edges:
            if e.role == EdgeRole.INTERNAL:
                mid = e.points[len(e.points)//2]
                if slice_line.distance(ShPoint(mid)) < 1e-3:
                    e.role = EdgeRole.WAIST
                
        rem_piece = PatternPiece(
            name=f"{piece.name}_remainder_{idx+1}" if len(remainder_polys) > 1 else f"{piece.name}_remainder",
            edges=rem_edges,
            grain_line=piece.grain_line,
            labels=[l for l in piece.labels if l["y"] > h_left],
            notches=[n for n in piece.notches if n[1] >= min(h_left, h_right)],
            cut_on_fold=piece.cut_on_fold,
            quantity=piece.quantity
        )
        rem_piece = _validate_and_fix_piece(rem_piece, piece)
        remainder_pieces.append(rem_piece)

    # Process yoke piece
    yoke_pieces = []
    for idx, coords in enumerate(yoke_polys):
        yoke_edges = recover_edges(coords, piece.edges, slice_line)
        
        yoke_piece = PatternPiece(
            name=f"{piece.name}_yoke_{idx+1}" if len(yoke_polys) > 1 else f"{piece.name}_yoke",
            edges=yoke_edges,
            grain_line=(piece.grain_line[0], (piece.grain_line[1][0], min(h_left, h_right))),
            labels=[l for l in piece.labels if l["y"] < max(h_left, h_right)],
            notches=[n for n in piece.notches if n[1] < max(h_left, h_right)],
            cut_on_fold=piece.cut_on_fold,
            quantity=piece.quantity
        )
        # Close darts on the yoke (rotating parts to merge dart edges)
        yoke_piece = close_darts_in_yoke(yoke_piece)
        yoke_piece = _validate_and_fix_piece(yoke_piece, piece)
        yoke_pieces.append(yoke_piece)

    return yoke_pieces + remainder_pieces


# --------------------------------------------------------------------------- #
#  3. Pleating (Параллельное/коническое разведение)
# --------------------------------------------------------------------------- #
def apply_pleats(piece: PatternPiece, count: int, pleat_width: float, side: str = "right") -> List[PatternPiece]:
    """
    Slashed and spreads the pattern piece to add pleats width.
    Inserts fold geometry into the piece.
    """
    total_intake = count * pleat_width
    if total_intake <= 0:
        return [piece]
        
    # Find middle of the piece width to slash
    xs = [p[0] for p in piece.points]
    min_x, max_x = min(xs), max(xs)
    slash_x = (min_x + max_x) / 2
    
    new_edges = []
    for edge in piece.edges:
        new_pts = []
        for p in edge.points:
            if p[0] > slash_x:
                new_pts.append((p[0] + total_intake, p[1]))
            elif abs(p[0] - slash_x) < 1e-4:
                new_pts.append(p)
            else:
                new_pts.append(p)
        new_edges.append(Edge(role=edge.role, points=new_pts, curve_type=edge.curve_type))
        
    # Insert notches for pleats on the waist and hem edges
    new_notches = []
    for n in piece.notches:
        if n[0] > slash_x:
            new_notches.append((n[0] + total_intake, n[1]))
        else:
            new_notches.append(n)
            
    # Add fold notches at slash_x
    for y in (0.0, piece.points[1][1]):  # waist top and hem bottom roughly
        for i in range(count + 1):
            new_notches.append((slash_x + i * pleat_width, y))
            
    new_piece = PatternPiece(
        name=f"{piece.name}_pleated",
        edges=new_edges,
        grain_line=piece.grain_line,
        labels=piece.labels + [{"text": f"плиссе ×{count}", "x": slash_x + total_intake/2, "y": 15.0, "size": 0.8}],
        notches=new_notches,
        cut_on_fold=piece.cut_on_fold,
        quantity=piece.quantity
    )
    return [_validate_and_fix_piece(new_piece, piece)]


def apply_wrap(piece: PatternPiece, overlap_cm: float) -> PatternPiece:
    """
    Takes a front panel piece (with CENTER_FOLD at X=0, coordinates in X >= 0)
    and extends it past the center line (into negative X) to construct a wrap panel.
    Shifts the coordinates to keep the left wrap edge at X=0.
    """
    if overlap_cm <= 0:
        return piece

    edges = list(piece.edges)
    new_edges = []
    for edge in edges:
        shifted_points = [(x + overlap_cm, y) for x, y in edge.points]
        new_edges.append(Edge(role=edge.role, points=shifted_points, curve_type=edge.curve_type))

    # Find the CENTER_FOLD edge (which is typically at X = overlap_cm after shifting)
    fold_idx = -1
    for idx, edge in enumerate(new_edges):
        if edge.role == EdgeRole.CENTER_FOLD:
            fold_idx = idx
            break

    if fold_idx != -1:
        fold_edge = new_edges[fold_idx]
        pts = fold_edge.points
        y_coords = [p[1] for p in pts]
        y_min = min(y_coords)
        y_max = max(y_coords)
        
        is_bottom_to_top = (pts[0][1] > pts[-1][1])
        
        if is_bottom_to_top:
            bottom_ext = Edge(role=EdgeRole.HEM, points=[(overlap_cm, y_max), (0.0, y_max)])
            left_edge = Edge(role=EdgeRole.INTERNAL, points=[(0.0, y_max), (0.0, y_min)])
            top_ext = Edge(role=EdgeRole.WAIST, points=[(0.0, y_min), (overlap_cm, y_min)])
            new_edges = new_edges[:fold_idx] + [bottom_ext, left_edge, top_ext] + new_edges[fold_idx+1:]
        else:
            top_ext = Edge(role=EdgeRole.WAIST, points=[(overlap_cm, y_min), (0.0, y_min)])
            left_edge = Edge(role=EdgeRole.INTERNAL, points=[(0.0, y_min), (0.0, y_max)])
            bottom_ext = Edge(role=EdgeRole.HEM, points=[(0.0, y_max), (overlap_cm, y_max)])
            new_edges = new_edges[:fold_idx] + [top_ext, left_edge, bottom_ext] + new_edges[fold_idx+1:]

    wrapped_piece = PatternPiece(
        name=piece.name + "_wrap",
        edges=new_edges,
        grain_line=((piece.grain_line[0][0] + overlap_cm, piece.grain_line[0][1]),
                    (piece.grain_line[1][0] + overlap_cm, piece.grain_line[1][1])),
        labels=[{**lbl, "x": lbl["x"] + overlap_cm} for lbl in piece.labels],
        notches=[(n[0] + overlap_cm, n[1]) for n in piece.notches],
        cut_on_fold=False,
        quantity=piece.quantity
    )
    return _validate_and_fix_piece(wrapped_piece, piece)


def apply_placket(piece: PatternPiece, placket_width: float = 3.0) -> PatternPiece:
    """
    Takes a front panel piece (with CENTER_FOLD at X=0, coordinates in X >= 0)
    and adds a button placket extension along the center fold edge.
    Shifts the coordinates to keep the left edge at X=0.
    """
    if placket_width <= 0:
        return piece

    edges = list(piece.edges)
    new_edges = []
    for edge in edges:
        shifted_points = [(x + placket_width, y) for x, y in edge.points]
        new_edges.append(Edge(role=edge.role, points=shifted_points, curve_type=edge.curve_type))

    # Find the CENTER_FOLD edge (typically at X = placket_width after shifting)
    fold_idx = -1
    for idx, edge in enumerate(new_edges):
        if edge.role == EdgeRole.CENTER_FOLD:
            fold_idx = idx
            break

    if fold_idx != -1:
        fold_edge = new_edges[fold_idx]
        pts = fold_edge.points
        y_coords = [p[1] for p in pts]
        y_min = min(y_coords)
        y_max = max(y_coords)
        
        is_bottom_to_top = (pts[0][1] > pts[-1][1])
        
        if is_bottom_to_top:
            bottom_ext = Edge(role=EdgeRole.HEM, points=[(placket_width, y_max), (0.0, y_max)])
            left_edge = Edge(role=EdgeRole.INTERNAL, points=[(0.0, y_max), (0.0, y_min)])
            top_ext = Edge(role=EdgeRole.WAIST, points=[(0.0, y_min), (placket_width, y_min)])
            new_edges = new_edges[:fold_idx] + [bottom_ext, left_edge, top_ext] + new_edges[fold_idx+1:]
        else:
            top_ext = Edge(role=EdgeRole.WAIST, points=[(placket_width, y_min), (0.0, y_min)])
            left_edge = Edge(role=EdgeRole.INTERNAL, points=[(0.0, y_min), (0.0, y_max)])
            bottom_ext = Edge(role=EdgeRole.HEM, points=[(0.0, y_max), (placket_width, y_max)])
            new_edges = new_edges[:fold_idx] + [top_ext, left_edge, bottom_ext] + new_edges[fold_idx+1:]

    # Add notches for fold lines and button center line
    new_notches = [(n[0] + placket_width, n[1]) for n in piece.notches]
    y_min_val = min(p[1] for p in piece.points)
    y_max_val = max(p[1] for p in piece.points)
    new_notches.append((placket_width, y_min_val))
    new_notches.append((placket_width, y_max_val))
    new_notches.append((placket_width / 2.0, y_min_val))
    new_notches.append((placket_width / 2.0, y_max_val))

    # Add button markings as labels along the center line (X = placket_width / 2)
    new_labels = [{**lbl, "x": lbl["x"] + placket_width} for lbl in piece.labels]
    h_total = y_max_val - y_min_val
    for i in range(1, 6):
        by = y_min_val + h_total * (i / 6.0)
        new_labels.append({"text": "🔘", "x": placket_width / 2.0, "y": by, "size": 0.8})

    placket_piece = PatternPiece(
        name=piece.name + "_placket",
        edges=new_edges,
        grain_line=((piece.grain_line[0][0] + placket_width, piece.grain_line[0][1]),
                    (piece.grain_line[1][0] + placket_width, piece.grain_line[1][1])),
        labels=new_labels,
        notches=new_notches,
        cut_on_fold=False,
        quantity=piece.quantity
    )
    return _validate_and_fix_piece(placket_piece, piece)


def apply_paperbag(piece: PatternPiece, ruffle_h: float = 4.0) -> PatternPiece:
    """
    Extends the waist edge of the pattern piece upwards by ruffle_h.
    Adds notches at the original waist height to mark the casing line.
    """
    if ruffle_h <= 0:
        return piece

    edges = []
    for edge in piece.edges:
        edges.append(Edge(role=edge.role, points=list(edge.points), curve_type=edge.curve_type))

    # 1. Shift all points in WAIST edges upwards by ruffle_h (decreasing Y)
    for edge in edges:
        if edge.role == EdgeRole.WAIST:
            edge.points = [(p[0], p[1] - ruffle_h) for p in edge.points]

    # 2. Stitch the adjacent edges to ensure connectivity
    for i in range(len(edges)):
        next_idx = (i + 1) % len(edges)
        edges[next_idx].points[0] = edges[i].points[-1]

    # 3. Add notches at the original waist height (casing line)
    new_notches = list(piece.notches)
    for edge in edges:
        if edge.role == EdgeRole.WAIST:
            for p in edge.points:
                new_notches.append((p[0], p[1] + ruffle_h))

    grain_start = (piece.grain_line[0][0], piece.grain_line[0][1] - ruffle_h)
    grain_end = piece.grain_line[1]

    paperbag_piece = PatternPiece(
        name=piece.name + "_paperbag",
        edges=edges,
        grain_line=(grain_start, grain_end),
        labels=piece.labels,
        notches=new_notches,
        cut_on_fold=piece.cut_on_fold,
        quantity=piece.quantity
    )
    return _validate_and_fix_piece(paperbag_piece, piece)
