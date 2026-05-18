"""
dxf_renderer.py  —  Professional DXF floor plan generator
===========================================================
Requires: pip install ezdxf

Produces AutoCAD R2010-compatible DXF files with proper layer structure.
Opens natively in: AutoCAD, SketchUp, Revit, BricsCAD, LibreCAD, FreeCAD,
                   Inkscape, Illustrator, QGIS.

LAYER STRUCTURE (industry standard):
  A-BORDER    → plot boundary, setback zones (grey, thin)
  A-WALL      → external walls (black, 0.5mm lineweight)
  A-WALL-INT  → internal partition walls (grey, 0.25mm)
  A-ROOM      → room fill hatches (per-room colours)
  A-TEXT      → room labels and area tags (standard text height)
  A-DIMS      → dimension lines with tick marks
  A-SYMB      → door swings, window symbols, stair treads
  A-COMP      → compass rose / north arrow
  A-TITLE     → title block

UNITS:
  DXF units = millimetres
  Scale = 1:100
  1 foot → 304.8mm → at 1:100 = 3.048 drawing units ≈ 3.048 mm
  Internal pixels (SCALE=10px/ft) → mm at 1:100:
    1 px = 1 ft / 10 = 0.1 ft = 30.48mm → at 1:100 = 0.3048 drawing units
  Simplified: px_to_mm = 0.3048 (multiply all pixel values by this)

ACI COLOUR CODES (AutoCAD Color Index):
  7  = white/black (by screen background — standard for walls)
  8  = grey (partitions, dims, secondary elements)
  1  = red
  2  = yellow
  3  = green
  4  = cyan
  5  = blue
  6  = magenta
  250-255 = greys light→dark

ROOM HATCH COLOURS (ACI approximations):
  Living room     → 51  (warm yellow)
  Bedroom         → 140 (soft blue)
  Kitchen         → 82  (soft green)
  Bathroom        → 130 (blue-grey)
  Pooja room      → 30  (warm amber)
  Corridor        → 253 (light grey)
  Car porch       → 44  (tan)
"""

from __future__ import annotations
import math
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ── Unit conversion ───────────────────────────────────────────────────────────
# layout_engine uses SCALE=10 pixels per foot
# DXF at 1:100 uses mm, where 1 foot = 304.8mm, at 1:100 = 3.048 drawing units
# So: 1 pixel = 1/10 foot = 0.3048 drawing units
PX_TO_DU = 0.3048   # pixels → drawing units (mm at 1:100)
SCALE    = 10        # pixels per foot (from layout_engine)


def _px(value: float) -> float:
    """Convert layout engine pixels to DXF drawing units."""
    return value * PX_TO_DU


def _pt(x: float, y: float) -> Tuple[float, float]:
    """Convert pixel point to DXF point (flip Y axis: DXF Y increases upward)."""
    return (_px(x), -_px(y))


# ── AutoCAD Color Index for room categories ───────────────────────────────────
_ROOM_ACI: Dict[str, int] = {
    "living_room":       51,   # warm cream
    "dining_room":       52,   # slightly darker cream
    "master_bedroom":    140,  # soft periwinkle blue
    "parents_bedroom":   140,
    "bedroom":           141,  # lighter blue
    "kitchen":           82,   # soft green
    "wet_kitchen":       83,
    "dry_kitchen":       82,
    "bathroom":          130,  # blue-grey
    "common_bathroom":   130,
    "guest_powder_room": 131,
    "pooja_room":        30,   # warm amber
    "corridor":          253,  # light grey
    "passage":           253,
    "car_porch":         44,   # tan/sand
    "sit_out":           90,   # pale green
    "utility_room":      252,
    "store_room":        251,
    "staircase":         253,
    "staircase_landing": 250,
    "home_office":       153,  # cool blue-grey
    "family_lounge":     51,
    "servant_quarters":  252,
    "walk_in_wardrobe":  160,
    "terrace":           90,
    "balcony":           90,
    "guest_bedroom":     141,
    "foyer":             253,
}
_DEFAULT_ACI = 254   # very light grey


def _room_aci(name: str) -> int:
    n = name.lower()
    for key, aci in _ROOM_ACI.items():
        if key in n:
            return aci
    return _DEFAULT_ACI


def _room_label(name: str) -> str:
    label_map = {
        "living_room":       "LIVING ROOM",
        "dining_room":       "DINING ROOM",
        "master_bedroom":    "MASTER BEDROOM",
        "parents_bedroom":   "PARENTS BEDROOM",
        "bedroom_2":         "BEDROOM 2",
        "bedroom_3":         "BEDROOM 3",
        "bedroom":           "BEDROOM",
        "kitchen":           "KITCHEN",
        "wet_kitchen":       "WET KITCHEN",
        "dry_kitchen":       "DRY KITCHEN",
        "bathroom":          "BATHROOM",
        "common_bathroom":   "COMMON BATH",
        "guest_powder_room": "POWDER ROOM",
        "pooja_room":        "POOJA ROOM",
        "corridor":          "CORRIDOR",
        "passage":           "PASSAGE",
        "car_porch":         "CAR PORCH",
        "sit_out":           "SIT OUT",
        "utility_room":      "UTILITY",
        "store_room":        "STORE ROOM",
        "staircase":         "STAIRCASE",
        "staircase_landing": "STAIR VOID",
        "home_office":       "HOME OFFICE",
        "family_lounge":     "FAMILY LOUNGE",
        "servant_quarters":  "SERVANT QTRS",
        "servant_bathroom":  "SERVANT BATH",
        "walk_in_wardrobe":  "WARDROBE",
        "terrace":           "TERRACE",
        "balcony":           "BALCONY",
        "guest_bedroom":     "GUEST BEDROOM",
        "foyer":             "FOYER",
    }
    n = name.lower()
    for key, lbl in label_map.items():
        if key == n or (len(key) > 5 and key in n):
            return lbl
    return name.replace("_", " ").upper()


def _fmt_ft(px: float) -> str:
    """Convert pixels to feet-inches: 14'-6" """
    total_in = round((px / SCALE) * 12)
    ft = total_in // 12
    inch = total_in % 12
    return f"{ft}'-{inch}\"" if inch else f"{ft}'-0\""


# ── Main DXF render function ──────────────────────────────────────────────────

def render_floor_plan_dxf(
    layout_data: Dict[str, Any],
    parsed: Dict[str, Any],
    floor_index: int = 0,
    floor_label: str = "GROUND FLOOR",
    output_path: str = "floor_plan.dxf",
) -> str:
    """
    Render a complete architectural floor plan as DXF.

    Returns the output file path on success, error message on failure.

    The DXF opens natively in AutoCAD, SketchUp, LibreCAD, BricsCAD.
    Layers are structured for professional architectural workflow.
    """
    try:
        import ezdxf
        from ezdxf import units
        from ezdxf.enums import TextEntityAlignment
    except ImportError:
        return "ERROR: ezdxf not installed. Run: pip install ezdxf"

    # ── Create document ───────────────────────────────────────────────────────
    doc = ezdxf.new("R2010")
    doc.units = units.MM
    msp = doc.modelspace()

    # ── Layer definitions ─────────────────────────────────────────────────────
    # ACI colour, lineweight in mm×100 (25=0.25mm, 50=0.5mm, 70=0.7mm)
    layer_defs = [
        ("A-BORDER",   8,   13),   # grey, very thin
        ("A-WALL",     7,   50),   # black/white, thick
        ("A-WALL-INT", 8,   25),   # grey, medium
        ("A-ROOM",     8,   9),    # grey, hairline (for hatch borders)
        ("A-TEXT",     7,   13),   # black, thin
        ("A-DIMS",     8,   13),   # grey, thin
        ("A-SYMB",     8,   18),   # grey, medium-thin
        ("A-COMP",     7,   25),   # black, medium
        ("A-TITLE",    7,   35),   # black, medium-thick
    ]
    for lname, colour, lw in layer_defs:
        doc.layers.add(lname, color=colour, lineweight=lw)

    # ── Extract layout data ───────────────────────────────────────────────────
    plot_info  = layout_data.get("plot",     {})
    built_info = layout_data.get("built_up", {})
    rooms      = layout_data.get("rooms",    [])

    plot_w_px  = float(plot_info.get("width_px",   300))
    plot_h_px  = float(plot_info.get("height_px",  500))
    built_x    = float(built_info.get("x",       20))
    built_y    = float(built_info.get("y",       50))
    built_w    = float(built_info.get("width",  260))
    built_h    = float(built_info.get("height", 420))

    # Parsed metadata
    pw_ft    = float(parsed.get("plot_width_ft",  30) or 30)
    pd_ft    = float(parsed.get("plot_depth_ft",  50) or 50)
    bhk      = str(parsed.get("bhk_type",   "3BHK") or "3BHK")
    style    = str(parsed.get("style", "Contemporary") or "Contemporary")
    vastu    = bool(parsed.get("vastu_compliant", False))
    budget   = int(parsed.get("budget", 0) or 0)
    facing   = str(parsed.get("plot_facing", "unknown") or "unknown").upper()
    floors_t = int(parsed.get("floors", 1) or 1)
    storey   = f"G+{floors_t-1} DUPLEX" if floors_t > 1 else "SINGLE STOREY"

    # ── LAYER: A-BORDER — plot boundary and setback zones ────────────────────
    # Plot outer boundary
    plot_pts = [
        _pt(0,        0),
        _pt(plot_w_px, 0),
        _pt(plot_w_px, plot_h_px),
        _pt(0,        plot_h_px),
    ]
    msp.add_lwpolyline(
        plot_pts + [plot_pts[0]],
        dxfattribs={"layer": "A-BORDER", "closed": True},
    )

    # Built-up boundary (setback inset)
    bu_pts = [
        _pt(built_x,           built_y),
        _pt(built_x + built_w, built_y),
        _pt(built_x + built_w, built_y + built_h),
        _pt(built_x,           built_y + built_h),
    ]
    msp.add_lwpolyline(
        bu_pts + [bu_pts[0]],
        dxfattribs={"layer": "A-BORDER", "closed": True, "const_width": 0},
    )

    # ── LAYER: A-ROOM — room fill hatches ─────────────────────────────────────
    for room in rooms:
        rx   = float(room["x"])
        ry   = float(room["y"])
        rw   = float(room["width"])
        rh   = float(room["height"])
        name = str(room.get("name", "room"))
        aci  = _room_aci(name)

        # Room boundary polyline (thin)
        pts = [
            _pt(rx,      ry),
            _pt(rx + rw, ry),
            _pt(rx + rw, ry + rh),
            _pt(rx,      ry + rh),
        ]
        msp.add_lwpolyline(
            pts + [pts[0]],
            dxfattribs={"layer": "A-ROOM", "closed": True},
        )

        # Solid hatch fill
        hatch = msp.add_hatch(color=aci, dxfattribs={"layer": "A-ROOM"})
        hatch.set_pattern_fill("SOLID")
        path = hatch.paths.add_polyline_path(
            [(p[0], p[1], 0) for p in pts],
            is_closed=True,
        )

        # Staircase landing: add diagonal line pattern instead of solid
        if "staircase_landing" in name.lower():
            hatch.set_pattern_fill("LINE", scale=2.0, angle=45)

    # ── LAYER: A-WALL-INT — internal partition walls ──────────────────────────
    wall_half = _px(4.0 / 2)   # 4px internal wall half-thickness

    for room in rooms:
        rx   = float(room["x"])
        ry   = float(room["y"])
        rw   = float(room["width"])
        rh   = float(room["height"])

        # Draw 4 walls as thick polylines (internal wall thickness)
        wall_pts_top    = [_pt(rx, ry),           _pt(rx + rw, ry)]
        wall_pts_right  = [_pt(rx + rw, ry),      _pt(rx + rw, ry + rh)]
        wall_pts_bottom = [_pt(rx + rw, ry + rh), _pt(rx, ry + rh)]
        wall_pts_left   = [_pt(rx, ry + rh),      _pt(rx, ry)]

        for wall in [wall_pts_top, wall_pts_right, wall_pts_bottom, wall_pts_left]:
            msp.add_lwpolyline(
                wall,
                dxfattribs={
                    "layer": "A-WALL-INT",
                    "const_width": _px(4.0),   # 4px wall = ~1.2mm at 1:100
                },
            )

    # ── LAYER: A-WALL — external boundary walls ───────────────────────────────
    ext_wall_w = _px(7.5)   # 7.5px = 9-inch brick wall at scale

    msp.add_lwpolyline(
        bu_pts + [bu_pts[0]],
        dxfattribs={
            "layer": "A-WALL",
            "closed": True,
            "const_width": ext_wall_w,
        },
    )

    # ── LAYER: A-SYMB — door swings ───────────────────────────────────────────
    for room in rooms:
        rx   = float(room["x"])
        ry   = float(room["y"])
        rw   = float(room["width"])
        doors = int(room.get("door_count", 0))
        name  = str(room.get("name", ""))

        if doors <= 0 or "staircase_landing" in name.lower():
            continue

        door_w_px = min(30.0, rw * 0.3)
        # Door position: bottom-left corner of room
        dx, dy = _pt(rx + 2, ry + float(room["height"]))

        # Door leaf
        msp.add_line(
            start=(dx, dy),
            end=(dx + _px(door_w_px), dy),
            dxfattribs={"layer": "A-SYMB"},
        )
        # Door swing arc (quarter circle)
        msp.add_arc(
            center=(dx, dy),
            radius=_px(door_w_px),
            start_angle=0,
            end_angle=90,
            dxfattribs={"layer": "A-SYMB"},
        )

    # ── LAYER: A-SYMB — window symbols ───────────────────────────────────────
    for room in rooms:
        rx      = float(room["x"])
        ry      = float(room["y"])
        rw      = float(room["width"])
        windows = int(room.get("windows", 0))

        if windows <= 0:
            continue

        # 3-line window symbol on top wall
        win_w  = _px(30)
        cx_dxf = _px(rx + rw / 2)
        ty_dxf = -_px(ry)   # top wall, DXF Y flipped

        for i, offset in enumerate([-win_w/2, 0, win_w/2]):
            line_y = ty_dxf + _px(i)
            msp.add_line(
                start=(cx_dxf - win_w/2, line_y),
                end=(cx_dxf + win_w/2,   line_y),
                dxfattribs={"layer": "A-SYMB", "color": 4},   # cyan
            )

    # ── LAYER: A-TEXT — room labels ───────────────────────────────────────────
    text_height = _px(6)   # 6px = ~1.8mm at 1:100 — readable at A1 plot size

    for room in rooms:
        rx   = float(room["x"])
        ry   = float(room["y"])
        rw   = float(room["width"])
        rh   = float(room["height"])
        name = str(room.get("name", "room"))
        wft  = float(room.get("width_ft",  rw / SCALE))
        dft  = float(room.get("depth_ft",  rh / SCALE))
        area = float(room.get("area_sqft", wft * dft))

        label     = _room_label(name)
        dim_str   = f"{_fmt_ft(rw)} x {_fmt_ft(rh)}"
        area_str  = f"{int(round(area))} sqft"

        # Centre of room in DXF coords
        cx, cy = _pt(rx + rw / 2, ry + rh / 2)

        # Room label (bold — use uppercase)
        msp.add_text(
            label,
            dxfattribs={
                "layer":        "A-TEXT",
                "height":       text_height * 1.2,
                "style":        "Standard",
                "halign":       1,   # center
                "valign":       2,   # middle
                "insert":       (cx, cy + text_height * 0.8),
                "align_point":  (cx, cy + text_height * 0.8),
            },
        )

        # Dimension string below label
        if rw > _px(40) and rh > _px(40):   # only if room is large enough
            msp.add_text(
                dim_str,
                dxfattribs={
                    "layer":       "A-TEXT",
                    "height":      text_height * 0.85,
                    "halign":      1,
                    "valign":      2,
                    "insert":      (cx, cy),
                    "align_point": (cx, cy),
                    "color":       8,
                },
            )
            msp.add_text(
                area_str,
                dxfattribs={
                    "layer":       "A-TEXT",
                    "height":      text_height * 0.75,
                    "halign":      1,
                    "valign":      2,
                    "insert":      (cx, cy - text_height * 0.9),
                    "align_point": (cx, cy - text_height * 0.9),
                    "color":       8,
                },
            )

    # ── LAYER: A-DIMS — dimension lines ───────────────────────────────────────
    # Overall plot width (top)
    dim_y_top = -_px(-12)   # 12px above plot top = +12 in DXF Y
    msp.add_linear_dim(
        base=(0, _px(14)),
        p1=_pt(0,        0),
        p2=_pt(plot_w_px, 0),
        dimstyle="EZDXF",
        dxfattribs={"layer": "A-DIMS"},
    ).render()

    # Overall plot depth (left)
    msp.add_linear_dim(
        base=(-_px(16), 0),
        p1=_pt(0, 0),
        p2=_pt(0, plot_h_px),
        angle=90,
        dimstyle="EZDXF",
        dxfattribs={"layer": "A-DIMS"},
    ).render()

    # ── LAYER: A-COMP — compass / north arrow ─────────────────────────────────
    # Place top-right corner
    cx_c = _px(plot_w_px + 30)
    cy_c = -_px(30)
    r_c  = _px(20)

    # Circle
    msp.add_circle(
        center=(cx_c, cy_c),
        radius=r_c,
        dxfattribs={"layer": "A-COMP", "color": 7},
    )

    # North arrow (filled triangle pointing up in DXF Y)
    arrow_tip  = (cx_c, cy_c + r_c - _px(3))
    arrow_bl   = (cx_c - _px(5), cy_c - _px(5))
    arrow_br   = (cx_c + _px(5), cy_c - _px(5))
    msp.add_solid(
        [arrow_tip, arrow_bl, arrow_br, arrow_tip],
        dxfattribs={"layer": "A-COMP", "color": 7},
    )

    # N label
    msp.add_text(
        "N",
        dxfattribs={
            "layer":       "A-COMP",
            "height":      _px(8),
            "halign":      1,
            "insert":      (cx_c, cy_c + r_c + _px(6)),
            "align_point": (cx_c, cy_c + r_c + _px(6)),
            "color":       7,
        },
    )

    # ── LAYER: A-TITLE — title block ──────────────────────────────────────────
    # Bottom strip below the plot
    tb_y  = -_px(plot_h_px + 20)
    tb_h  = _px(40)
    tb_w  = _px(plot_w_px)

    # Title block border
    msp.add_lwpolyline(
        [
            (0, tb_y),
            (tb_w, tb_y),
            (tb_w, tb_y - tb_h),
            (0,    tb_y - tb_h),
            (0,    tb_y),
        ],
        dxfattribs={"layer": "A-TITLE", "closed": True},
    )

    # Vertical dividers (3 columns)
    col_w = tb_w / 3
    msp.add_line((col_w,   tb_y), (col_w,   tb_y - tb_h), dxfattribs={"layer": "A-TITLE"})
    msp.add_line((col_w*2, tb_y), (col_w*2, tb_y - tb_h), dxfattribs={"layer": "A-TITLE"})

    tb_mid_y = tb_y - tb_h / 2
    th = _px(8)

    # Left: project name
    msp.add_text(
        "RESIDENTIAL FLOOR PLAN",
        dxfattribs={"layer": "A-TITLE", "height": th * 1.1,
                    "halign": 1, "insert": (col_w / 2, tb_mid_y + th),
                    "align_point": (col_w / 2, tb_mid_y + th)},
    )
    msp.add_text(
        f"{bhk}  ·  {style.upper()[:20]}  ·  {floor_label}",
        dxfattribs={"layer": "A-TITLE", "height": th * 0.7, "color": 8,
                    "halign": 1, "insert": (col_w / 2, tb_mid_y - th * 0.3),
                    "align_point": (col_w / 2, tb_mid_y - th * 0.3)},
    )

    # Centre: dimensions + scale + storey
    msp.add_text(
        f"{int(pw_ft)}' × {int(pd_ft)}'  |  {storey}",
        dxfattribs={"layer": "A-TITLE", "height": th,
                    "halign": 1, "insert": (col_w * 1.5, tb_mid_y + th * 0.5),
                    "align_point": (col_w * 1.5, tb_mid_y + th * 0.5)},
    )
    msp.add_text(
        f"SCALE 1:100  |  {facing}-FACING",
        dxfattribs={"layer": "A-TITLE", "height": th * 0.75, "color": 8,
                    "halign": 1, "insert": (col_w * 1.5, tb_mid_y - th * 0.6),
                    "align_point": (col_w * 1.5, tb_mid_y - th * 0.6)},
    )

    # Right: Vastu + budget
    right_cx = col_w * 2.5
    vastu_txt = "✓ VASTU COMPLIANT" if vastu else "NON-VASTU"
    vastu_col = 3 if vastu else 8   # green if vastu, grey otherwise
    msp.add_text(
        vastu_txt,
        dxfattribs={"layer": "A-TITLE", "height": th, "color": vastu_col,
                    "halign": 1, "insert": (right_cx, tb_mid_y + th * 0.5),
                    "align_point": (right_cx, tb_mid_y + th * 0.5)},
    )
    if budget >= 100000:
        budget_l = budget // 100000
        msp.add_text(
            f"Budget: ₹{budget_l}L",
            dxfattribs={"layer": "A-TITLE", "height": th * 0.8,
                        "halign": 1, "insert": (right_cx, tb_mid_y - th * 0.6),
                        "align_point": (right_cx, tb_mid_y - th * 0.6)},
        )

    # ── Save ──────────────────────────────────────────────────────────────────
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    doc.saveas(output_path)
    return output_path


# ── Multi-floor DXF (separate file per floor) ────────────────────────────────

def render_all_floors_dxf(
    per_floor_layouts: Dict[str, Dict[str, Any]],
    parsed: Dict[str, Any],
    output_dir: str = "outputs/",
) -> Dict[str, str]:
    """
    Render DXF for every floor. Returns { "0": "/path/floor_ground.dxf", ... }
    """
    _LABELS = {0: "GROUND FLOOR", 1: "FIRST FLOOR", 2: "SECOND FLOOR", 3: "THIRD FLOOR"}
    _SLUGS  = {0: "ground",       1: "first",       2: "second",        3: "third"}
    result: Dict[str, str] = {}

    for floor_str, layout in per_floor_layouts.items():
        fi    = int(floor_str)
        label = _LABELS.get(fi, f"FLOOR {fi}")
        slug  = _SLUGS.get(fi, floor_str)
        path  = str(Path(output_dir) / f"floor_{slug}" / f"floor_plan_{slug}.dxf")
        result[floor_str] = render_floor_plan_dxf(
            layout_data=layout,
            parsed=parsed,
            floor_index=fi,
            floor_label=label,
            output_path=path,
        )

    return result


# ── Validation: check DXF can be read back ────────────────────────────────────

def validate_dxf(dxf_path: str) -> Dict[str, Any]:
    """
    Read the DXF back and count entities per layer.
    Returns validation report.
    """
    try:
        import ezdxf
    except ImportError:
        return {"valid": False, "error": "ezdxf not installed"}

    try:
        doc = ezdxf.readfile(dxf_path)
        msp = doc.modelspace()

        layer_counts: Dict[str, int] = {}
        for entity in msp:
            layer = entity.dxf.layer
            layer_counts[layer] = layer_counts.get(layer, 0) + 1

        return {
            "valid": True,
            "path": dxf_path,
            "file_size_kb": round(Path(dxf_path).stat().st_size / 1024, 1),
            "total_entities": len(list(msp)),
            "layers": layer_counts,
            "dxf_version": doc.dxfversion,
        }
    except Exception as exc:
        return {"valid": False, "error": str(exc)}