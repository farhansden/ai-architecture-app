"""
pascal_scene_converter.py  —  Layout Engine → Pascal Editor Scene Converter
=============================================================================

Converts layout_engine.generate_layout() output into Pascal Editor's JSON
scene format (Site → Building → Level → Wall/Slab/Zone nodes).

Pascal Editor scene structure:
  {
    "nodes": { id: Node },
    "rootNodeIds": [siteId]
  }

Node types used:
  site      → top-level container
  building  → the house
  level     → one floor (Ground Floor, First Floor, etc.)
  wall      → room boundary walls (with height)
  slab      → floor slab per room
  zone      → room zone (color + label, used for room identification)
  item      → door/window items on walls

Coordinate mapping:
  layout_engine: SVG pixels, SCALE=10px/ft, origin top-left, y↓
  Pascal:        metres, origin center, y↑ (right-hand)

  x_pascal = (svg_x - cx_px) * PX2M
  y_pascal = 0 (floor level for slabs/walls)
  z_pascal = (svg_y - cz_px) * PX2M   ← note: z in Pascal = depth (SVG y)

Wall height by room category:
  standard habitable: 3.0m (10ft NBC standard)
  bathroom/WIC:       2.4m
  corridor:           2.7m
  sit_out/car_porch:  0.0 (open, no wall extrusion — just slab)
  terrace/balcony:    0.0 (parapet handled separately)

Multi-floor stacking:
  Ground floor:  y_base = 0.0m
  First floor:   y_base = 3.2m  (3.0m room + 0.2m slab thickness)
  Second floor:  y_base = 6.4m
"""

from __future__ import annotations

import json
import math
import uuid
from typing import Any, Dict, List, Optional, Tuple

# ── Constants ─────────────────────────────────────────────────────────────────

SCALE = 10.0        # px per foot (layout_engine contract)
PX2M  = 0.3048 / SCALE   # pixels → metres (1ft = 0.3048m, 10px/ft)

FLOOR_HEIGHT_M   = 3.0    # standard floor-to-ceiling height
SLAB_THICKNESS_M = 0.2    # floor slab thickness
FLOOR_STEP_M     = FLOOR_HEIGHT_M + SLAB_THICKNESS_M   # 3.2m per floor

EXT_WALL_T_M  = 0.23   # 9-inch external brick wall in metres (NBC standard)
INT_WALL_T_M  = 0.115  # 4.5-inch internal partition in metres

# ── Room category → wall config ───────────────────────────────────────────────

_WALL_CONFIG: Dict[str, Dict[str, Any]] = {
    "living_room":       {"height": 3.0,  "ext_wall": True},
    "dining_room":       {"height": 3.0,  "ext_wall": True},
    "master_bedroom":    {"height": 3.0,  "ext_wall": True},
    "parents_bedroom":   {"height": 3.0,  "ext_wall": True},
    "bedroom":           {"height": 3.0,  "ext_wall": True},
    "guest_bedroom":     {"height": 3.0,  "ext_wall": True},
    "kitchen":           {"height": 2.7,  "ext_wall": True},
    "dry_kitchen":       {"height": 2.7,  "ext_wall": True},
    "wet_kitchen":       {"height": 2.7,  "ext_wall": True},
    "bathroom":          {"height": 2.4,  "ext_wall": False},
    "common_bathroom":   {"height": 2.4,  "ext_wall": False},
    "guest_powder_room": {"height": 2.4,  "ext_wall": False},
    "corridor":          {"height": 2.7,  "ext_wall": False},
    "passage":           {"height": 2.7,  "ext_wall": False},
    "foyer":             {"height": 3.0,  "ext_wall": True},
    "pooja_room":        {"height": 2.7,  "ext_wall": False},
    "utility_room":      {"height": 2.4,  "ext_wall": False},
    "store_room":        {"height": 2.4,  "ext_wall": False},
    "home_office":       {"height": 3.0,  "ext_wall": True},
    "family_lounge":     {"height": 3.0,  "ext_wall": True},
    "servant_quarters":  {"height": 2.7,  "ext_wall": True},
    "walk_in_wardrobe":  {"height": 2.4,  "ext_wall": False},
    "staircase":         {"height": 3.0,  "ext_wall": False},
    "staircase_landing": {"height": 0.0,  "ext_wall": False},  # void
    "sit_out":           {"height": 0.0,  "ext_wall": False},  # open
    "car_porch":         {"height": 0.0,  "ext_wall": False},  # open
    "terrace":           {"height": 1.0,  "ext_wall": False},  # parapet only
    "balcony":           {"height": 1.0,  "ext_wall": False},  # parapet only
    "default":           {"height": 3.0,  "ext_wall": True},
}

# ── Room category → Pascal zone color ────────────────────────────────────────

_ZONE_COLORS: Dict[str, str] = {
    "living_room":       "#FDF6E3",
    "dining_room":       "#FDF6E3",
    "master_bedroom":    "#E8EEF8",
    "parents_bedroom":   "#E8EEF8",
    "bedroom":           "#E8EEF8",
    "guest_bedroom":     "#E8EEF8",
    "kitchen":           "#E8F5EC",
    "dry_kitchen":       "#E8F5EC",
    "wet_kitchen":       "#E8F5EC",
    "bathroom":          "#E0F2F8",
    "common_bathroom":   "#E0F2F8",
    "guest_powder_room": "#E0F2F8",
    "corridor":          "#F5F5EE",
    "foyer":             "#FDF0DC",
    "pooja_room":        "#FDF0DC",
    "utility_room":      "#F0F0EC",
    "store_room":        "#EDEDED",
    "home_office":       "#E8EEF8",
    "family_lounge":     "#FDF6E3",
    "servant_quarters":  "#F0F0EC",
    "walk_in_wardrobe":  "#E8EEF8",
    "staircase":         "#F0F0EC",
    "sit_out":           "#E8F2E8",
    "car_porch":         "#EEEBD8",
    "terrace":           "#E8F2E8",
    "balcony":           "#E8F2E8",
    "default":           "#FAFAFA",
}

# ── Room labels for Pascal zones ──────────────────────────────────────────────

_ZONE_LABELS: Dict[str, str] = {
    "living_room":       "Living Room",
    "dining_room":       "Dining Room",
    "master_bedroom":    "Master Bedroom",
    "parents_bedroom":   "Parents Bedroom",
    "bedroom":           "Bedroom",
    "guest_bedroom":     "Guest Bedroom",
    "kitchen":           "Kitchen",
    "dry_kitchen":       "Dry Kitchen",
    "wet_kitchen":       "Wet Kitchen",
    "bathroom":          "Bathroom",
    "common_bathroom":   "Common Bath",
    "guest_powder_room": "Powder Room",
    "corridor":          "Corridor",
    "foyer":             "Foyer",
    "pooja_room":        "Prayer Room",
    "utility_room":      "Utility",
    "store_room":        "Store Room",
    "home_office":       "Home Office",
    "family_lounge":     "Family Lounge",
    "servant_quarters":  "Servant Qtrs",
    "walk_in_wardrobe":  "Wardrobe",
    "staircase":         "Staircase",
    "staircase_landing": "Void",
    "sit_out":           "Sit-out",
    "car_porch":         "Car Porch",
    "terrace":           "Terrace",
    "balcony":           "Balcony",
    "default":           "Room",
}


# ── ID generator ──────────────────────────────────────────────────────────────

def _id(prefix: str = "") -> str:
    return f"{prefix}{uuid.uuid4().hex[:12]}"


# ── Category resolver ─────────────────────────────────────────────────────────

def _cat(room: Dict) -> str:
    cat = str(room.get("__cat", "") or "")
    if cat and cat != "store_room":
        return cat
    name = str(room.get("name", "")).lower()
    if "master" in name and "bath" in name:    return "bathroom"
    if "master" in name:                       return "master_bedroom"
    if "parent" in name and "bath" in name:    return "bathroom"
    if "parent" in name:                       return "parents_bedroom"
    if "bedroom" in name and "bath" in name:   return "bathroom"
    if "bedroom" in name:                      return "bedroom"
    if "living" in name:                       return "living_room"
    if "dining" in name:                       return "dining_room"
    if "dry_kitchen" in name:                  return "dry_kitchen"
    if "wet_kitchen" in name:                  return "wet_kitchen"
    if "kitchen" in name:                      return "kitchen"
    if "corridor" in name or "passage" in name: return "corridor"
    if "foyer" in name:                        return "foyer"
    if "pooja" in name or "prayer" in name:    return "pooja_room"
    if "util" in name:                         return "utility_room"
    if "store" in name and "stair" not in name: return "store_room"
    if "stair" in name and "land" in name:     return "staircase_landing"
    if "stair" in name:                        return "staircase"
    if "bath" in name or "toilet" in name:     return "bathroom"
    if "common" in name and "bath" in name:    return "common_bathroom"
    if "powder" in name:                       return "guest_powder_room"
    if "sit_out" in name or "sit out" in name or "verandah" in name or "veranda" in name:
        return "sit_out"
    if "car_porch" in name or "porch" in name: return "car_porch"
    if "servant" in name:                      return "servant_quarters"
    if "wardrobe" in name or "wic" in name:    return "walk_in_wardrobe"
    if "office" in name or "study" in name:    return "home_office"
    if "lounge" in name:                       return "family_lounge"
    if "terrace" in name:                      return "terrace"
    if "balcony" in name:                      return "balcony"
    return "default"


# ── Coordinate conversion ─────────────────────────────────────────────────────

def _px_to_pascal(
    svg_x: float, svg_y: float,
    cx_px: float, cz_px: float,
    y_base: float = 0.0,
) -> Tuple[float, float, float]:
    """Convert SVG pixel coords to Pascal world coords (x, y, z)."""
    return (
        round((svg_x - cx_px) * PX2M, 4),
        round(y_base, 4),
        round((svg_y - cz_px) * PX2M, 4),
    )


# ── Pascal node builders ──────────────────────────────────────────────────────

def _make_site(name: str) -> Tuple[str, Dict]:
    nid = _id("site_")
    return nid, {
        "id": nid,
        "type": "site",
        "name": name,
        "position": {"x": 0, "y": 0, "z": 0},
        "rotation": {"x": 0, "y": 0, "z": 0},
        "children": [],
        "parentId": None,
    }


def _make_building(name: str, site_id: str) -> Tuple[str, Dict]:
    nid = _id("bld_")
    return nid, {
        "id": nid,
        "type": "building",
        "name": name,
        "position": {"x": 0, "y": 0, "z": 0},
        "rotation": {"x": 0, "y": 0, "z": 0},
        "children": [],
        "parentId": site_id,
    }


def _make_level(
    name: str,
    building_id: str,
    floor_index: int,
    y_base: float,
) -> Tuple[str, Dict]:
    nid = _id(f"lvl{floor_index}_")
    return nid, {
        "id": nid,
        "type": "level",
        "name": name,
        "floorIndex": floor_index,
        "elevation": round(y_base, 4),
        "height": FLOOR_HEIGHT_M,
        "position": {"x": 0, "y": round(y_base, 4), "z": 0},
        "rotation": {"x": 0, "y": 0, "z": 0},
        "children": [],
        "parentId": building_id,
    }


def _make_slab(
    room: Dict,
    level_id: str,
    cx_px: float, cz_px: float,
    y_base: float,
    cat: str,
) -> Tuple[str, Dict]:
    """Floor slab for a room — a flat rectangle at floor level."""
    rx = float(room["x"])
    ry = float(room["y"])
    rw = float(room["width"])
    rd = float(room["height"])

    # Slab center in Pascal coords
    cx = (rx + rw / 2 - cx_px) * PX2M
    cz = (ry + rd / 2 - cz_px) * PX2M
    sw = rw * PX2M
    sd = rd * PX2M

    nid = _id("slab_")
    return nid, {
        "id": nid,
        "type": "slab",
        "name": f"{_ZONE_LABELS.get(cat, 'Room')} Floor",
        "position": {"x": round(cx, 4), "y": round(y_base, 4), "z": round(cz, 4)},
        "rotation": {"x": 0, "y": 0, "z": 0},
        "width":  round(sw, 4),
        "depth":  round(sd, 4),
        "thickness": SLAB_THICKNESS_M,
        "children": [],
        "parentId": level_id,
        "metadata": {
            "roomName": str(room.get("name", "")),
            "category": cat,
            "areaSqft": float(room.get("area_sqft", 0)),
            "vastuZone": str(room.get("__vastu_zone", "")),
        },
    }


def _make_zone(
    room: Dict,
    level_id: str,
    cx_px: float, cz_px: float,
    y_base: float,
    cat: str,
) -> Tuple[str, Dict]:
    """Zone node for a room — carries label + color."""
    rx = float(room["x"])
    ry = float(room["y"])
    rw = float(room["width"])
    rd = float(room["height"])

    cx = (rx + rw / 2 - cx_px) * PX2M
    cz = (ry + rd / 2 - cz_px) * PX2M
    sw = rw * PX2M
    sd = rd * PX2M

    label = _ZONE_LABELS.get(cat, str(room.get("name", "Room")).replace("_", " ").title())
    color = _ZONE_COLORS.get(cat, "#FAFAFA")

    area_sqft = float(room.get("area_sqft", 0))
    w_ft = float(room.get("width_ft", rw / SCALE))
    d_ft = float(room.get("depth_ft", rd / SCALE))

    nid = _id("zone_")
    return nid, {
        "id": nid,
        "type": "zone",
        "name": label,
        "label": label,
        "color": color,
        "position": {"x": round(cx, 4), "y": round(y_base, 4), "z": round(cz, 4)},
        "rotation": {"x": 0, "y": 0, "z": 0},
        "width":  round(sw, 4),
        "depth":  round(sd, 4),
        "height": FLOOR_HEIGHT_M,
        "children": [],
        "parentId": level_id,
        "metadata": {
            "roomName":   str(room.get("name", "")),
            "category":   cat,
            "areaSqft":   round(area_sqft, 1),
            "widthFt":    round(w_ft, 1),
            "depthFt":    round(d_ft, 1),
            "vastuZone":  str(room.get("__vastu_zone", "")),
            "floor":      int(room.get("floor", 0)),
            "notes":      str(room.get("notes", "")),
        },
    }


def _make_walls_for_room(
    room: Dict,
    level_id: str,
    cx_px: float, cz_px: float,
    y_base: float,
    cat: str,
    bx: float, by_: float, bw: float, bh: float,  # built-up bounds in px
) -> List[Tuple[str, Dict]]:
    """
    Generate 4 wall nodes for a room's perimeter.
    Only exterior walls (touching built-up boundary) use EXT_WALL_T.
    Interior walls use INT_WALL_T (shared with neighbours, so half-thickness each side).
    Walls with height=0 (sit_out, car_porch) are skipped entirely.
    """
    cfg    = _WALL_CONFIG.get(cat, _WALL_CONFIG["default"])
    wall_h = cfg["height"]

    if wall_h == 0.0:
        return []  # open space — no walls

    rx = float(room["x"])
    ry = float(room["y"])
    rw = float(room["width"])
    rd = float(room["height"])

    TOL = 8.0  # px tolerance for exterior wall detection
    is_ext_top    = abs(ry - by_) < TOL
    is_ext_bot    = abs((ry + rd) - (by_ + bh)) < TOL
    is_ext_left   = abs(rx - bx) < TOL
    is_ext_right  = abs((rx + rw) - (bx + bw)) < TOL

    def t(is_ext: bool) -> float:
        return EXT_WALL_T_M if is_ext else INT_WALL_T_M

    walls = []

    # Wall definitions: (start_svg_x, start_svg_y, end_svg_x, end_svg_y, is_exterior, label)
    wall_defs = [
        (rx,      ry,      rx + rw, ry,      is_ext_top,   "North"),
        (rx + rw, ry,      rx + rw, ry + rd, is_ext_right, "East"),
        (rx,      ry + rd, rx + rw, ry + rd, is_ext_bot,   "South"),
        (rx,      ry,      rx,      ry + rd, is_ext_left,  "West"),
    ]

    for (sx, sz, ex, ez, is_ext, label) in wall_defs:
        # Wall center in Pascal coords
        mid_x = (sx + ex) / 2
        mid_z = (sz + ez) / 2
        wx = (mid_x - cx_px) * PX2M
        wz = (mid_z - cz_px) * PX2M

        # Wall dimensions
        is_horizontal = abs(sz - ez) < 0.1
        if is_horizontal:
            wall_len = abs(ex - sx) * PX2M
            wall_w   = wall_len
            wall_d   = t(is_ext)
        else:
            wall_len = abs(ez - sz) * PX2M
            wall_w   = t(is_ext)
            wall_d   = wall_len

        nid = _id("wall_")
        node = {
            "id": nid,
            "type": "wall",
            "name": f"{_ZONE_LABELS.get(cat, 'Room')} {label} Wall",
            "position": {
                "x": round(wx, 4),
                "y": round(y_base + wall_h / 2, 4),
                "z": round(wz, 4),
            },
            "rotation": {"x": 0, "y": 0, "z": 0},
            "width":     round(wall_w, 4),
            "height":    round(wall_h, 4),
            "depth":     round(wall_d, 4),
            "thickness": round(t(is_ext), 4),
            "isExterior": is_ext,
            "children": [],
            "parentId": level_id,
            "metadata": {
                "roomName":  str(room.get("name", "")),
                "wallSide":  label,
                "category":  cat,
            },
        }
        walls.append((nid, node))

    return walls


def _make_window_item(
    wall_id: str,
    wall_node: Dict,
    window_index: int,
    window_count: int,
) -> Tuple[str, Dict]:
    """Window item placed on a wall, evenly distributed."""
    # Position along wall: divide wall into window_count+1 segments
    t = (window_index + 1) / (window_count + 1)
    # Offset along wall's main axis
    wall_w = wall_node["width"]
    wall_d = wall_node["depth"]
    is_h_wall = wall_w > wall_d  # horizontal wall (top/bottom)

    win_width  = min(1.2, (wall_w if is_h_wall else wall_d) * 0.4)
    win_height = 1.2
    win_sill   = 0.9

    # Local offset within wall
    if is_h_wall:
        offset_x = (t - 0.5) * wall_w
        offset_z = 0.0
    else:
        offset_x = 0.0
        offset_z = (t - 0.5) * wall_d

    nid = _id("win_")
    return nid, {
        "id": nid,
        "type": "item",
        "itemType": "window",
        "name": "Window",
        "position": {
            "x": round(wall_node["position"]["x"] + offset_x, 4),
            "y": round(wall_node["position"]["y"] - wall_node["height"] / 2 + win_sill + win_height / 2, 4),
            "z": round(wall_node["position"]["z"] + offset_z, 4),
        },
        "rotation": {"x": 0, "y": 0, "z": 0},
        "width":  round(win_width, 4),
        "height": round(win_height, 4),
        "depth":  0.15,
        "children": [],
        "parentId": wall_id,
    }


def _make_door_item(
    wall_id: str,
    wall_node: Dict,
    door_width_m: float = 0.9,
    door_height_m: float = 2.1,
) -> Tuple[str, Dict]:
    """Door item placed at wall bottom, left-of-center."""
    wall_w = wall_node["width"]
    wall_d = wall_node["depth"]
    is_h_wall = wall_w > wall_d

    # Place door at 1/3 along wall from left
    if is_h_wall:
        offset_x = -wall_w * 0.15
        offset_z = 0.0
    else:
        offset_x = 0.0
        offset_z = -wall_d * 0.15

    nid = _id("door_")
    return nid, {
        "id": nid,
        "type": "item",
        "itemType": "door",
        "name": "Door",
        "position": {
            "x": round(wall_node["position"]["x"] + offset_x, 4),
            "y": round(wall_node["position"]["y"] - wall_node["height"] / 2 + door_height_m / 2, 4),
            "z": round(wall_node["position"]["z"] + offset_z, 4),
        },
        "rotation": {"x": 0, "y": 0, "z": 0},
        "width":  round(door_width_m, 4),
        "height": round(door_height_m, 4),
        "depth":  0.15,
        "children": [],
        "parentId": wall_id,
    }


# ── Main converter ────────────────────────────────────────────────────────────

def layout_to_pascal_scene(
    per_floor_layouts: Dict[str, Dict[str, Any]],
    parsed: Dict[str, Any],
    project_name: str = "Floor Plan",
) -> Dict[str, Any]:
    """
    Convert layout_engine multi-floor output to Pascal Editor scene JSON.

    Args:
        per_floor_layouts: { "0": layout, "1": layout, ... }
        parsed: llm_parser output (for metadata)
        project_name: name shown in Pascal Editor

    Returns:
        Pascal scene dict  { nodes: {...}, rootNodeIds: [...] }
    """
    nodes: Dict[str, Any] = {}

    # Build metadata strings
    bhk     = str(parsed.get("bhk_type", "3BHK"))
    pw_ft   = int(parsed.get("plot_width_ft", 30))
    pd_ft   = int(parsed.get("plot_depth_ft", 50))
    style   = str(parsed.get("style", "Modern")).title()
    name    = project_name or f"{bhk} {pw_ft}×{pd_ft} {style}"

    # ── Site ──────────────────────────────────────────────────────────────────
    site_id, site_node = _make_site(name)
    nodes[site_id] = site_node

    # ── Building ──────────────────────────────────────────────────────────────
    bld_id, bld_node = _make_building(f"{bhk} House", site_id)
    nodes[bld_id] = bld_node
    site_node["children"].append(bld_id)

    # Use ground floor layout for coordinate center calculation
    gf_layout = per_floor_layouts.get("0", {})
    bx   = float(gf_layout.get("built_up_x", 70))
    by_  = float(gf_layout.get("built_up_y", 120))
    bw   = float(gf_layout.get("built_up_w", 260))
    bh   = float(gf_layout.get("built_up_h", 420))

    # Center origin at built-up center
    cx_px = bx + bw / 2
    cz_px = by_ + bh / 2

    floor_labels = {0: "Ground Floor", 1: "First Floor", 2: "Second Floor", 3: "Third Floor"}

    # ── Per-floor loop ────────────────────────────────────────────────────────
    for floor_str, layout in sorted(per_floor_layouts.items(), key=lambda x: int(x[0])):
        floor_idx = int(floor_str)
        y_base    = floor_idx * FLOOR_STEP_M

        label = floor_labels.get(floor_idx, f"Floor {floor_idx}")
        lvl_id, lvl_node = _make_level(label, bld_id, floor_idx, y_base)
        nodes[lvl_id] = lvl_node
        bld_node["children"].append(lvl_id)

        rooms: List[Dict] = layout.get("rooms") or []

        for room in rooms:
            # Skip ghost/carved rooms — they're sub-zones of parent rooms
            name_r = str(room.get("name", "")).lower()
            if room.get("__is_carved", False):
                continue

            cat = _cat(room)
            cfg = _WALL_CONFIG.get(cat, _WALL_CONFIG["default"])

            # ── Slab (floor) ──────────────────────────────────────────────────
            slab_id, slab_node = _make_slab(room, lvl_id, cx_px, cz_px, y_base, cat)
            nodes[slab_id] = slab_node
            lvl_node["children"].append(slab_id)

            # ── Zone (room identity/color/label) ──────────────────────────────
            zone_id, zone_node = _make_zone(room, lvl_id, cx_px, cz_px, y_base, cat)
            nodes[zone_id] = zone_node
            lvl_node["children"].append(zone_id)

            # ── Walls ──────────────────────────────────────────────────────────
            wall_nodes = _make_walls_for_room(
                room, lvl_id, cx_px, cz_px, y_base, cat,
                bx, by_, bw, bh,
            )

            for wall_id, wall_node in wall_nodes:
                nodes[wall_id] = wall_node
                lvl_node["children"].append(wall_id)

                # ── Windows on exterior walls ──────────────────────────────────
                if wall_node.get("isExterior"):
                    win_count = int(room.get("windows", 0))
                    if win_count > 0:
                        win_id, win_node = _make_window_item(
                            wall_id, wall_node, 0, max(win_count, 1)
                        )
                        nodes[win_id] = win_node
                        wall_node["children"].append(win_id)

                # ── Door on top wall (first interior/top wall) ─────────────────
                door_count = int(room.get("door_count", 0))
                if (door_count > 0
                        and not wall_node.get("isExterior")
                        and wall_node["name"].endswith("North Wall")):
                    door_id, door_node = _make_door_item(wall_id, wall_node)
                    nodes[door_id] = door_node
                    wall_node["children"].append(door_id)

    # ── Scene metadata ─────────────────────────────────────────────────────────
    scene = {
        "nodes": nodes,
        "rootNodeIds": [site_id],
        "metadata": {
            "schemaVersion":    "1.0",
            "generator":        "pascal_scene_converter.py",
            "projectName":      name,
            "bhkType":          bhk,
            "plotWidthFt":      pw_ft,
            "plotDepthFt":      pd_ft,
            "style":            style,
            "floors":           len(per_floor_layouts),
            "vastuCompliant":   bool(parsed.get("vastu_compliant", False)),
            "plotFacing":       str(parsed.get("plot_facing", "north")),
            "budget":           int(parsed.get("budget", 0)),
            "totalRooms":       sum(
                len([r for r in (per_floor_layouts.get(k, {}).get("rooms") or [])
                     if not r.get("__is_carved", False)])
                for k in per_floor_layouts
            ),
            "coordinateSystem": "Pascal (metres, y-up, centred on built-up)",
            "px2m":             PX2M,
            "originOffsetPx":   {"cx": cx_px, "cz": cz_px},
        },
    }

    return scene


# ── Single-floor convenience wrapper ─────────────────────────────────────────

def single_layout_to_pascal(
    layout: Dict[str, Any],
    parsed: Dict[str, Any],
    floor_index: int = 0,
    project_name: str = "Floor Plan",
) -> Dict[str, Any]:
    """Wrap a single layout_engine output for conversion."""
    return layout_to_pascal_scene(
        per_floor_layouts={str(floor_index): layout},
        parsed=parsed,
        project_name=project_name,
    )


# ── Serialise to JSON string ─────────────────────────────────────────────────

def to_json(scene: Dict[str, Any], indent: int = 2) -> str:
    return json.dumps(scene, indent=indent, ensure_ascii=False)


# ── Self-test ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    mock_layout = {
        "built_up_x": 70, "built_up_y": 120,
        "built_up_w": 260, "built_up_h": 420,
        "plot_w_px": 300, "plot_h_px": 500,
        "facing": "north",
        "rooms": [
            {"name":"living_room",    "x":70,  "y":120, "width":200,"height":130,"width_ft":20,"depth_ft":13,"area_sqft":260,"__vastu_zone":"N","__cat":"living_room",   "floor":0,"windows":3,"door_count":2,"notes":"NE zone","__is_carved":False},
            {"name":"kitchen",        "x":200, "y":290, "width":130,"height":100,"width_ft":13,"depth_ft":10,"area_sqft":130,"__vastu_zone":"SE","__cat":"kitchen",      "floor":0,"windows":2,"door_count":1,"notes":"SE Vastu","__is_carved":False},
            {"name":"master_bedroom", "x":70,  "y":390, "width":160,"height":130,"width_ft":16,"depth_ft":13,"area_sqft":208,"__vastu_zone":"SW","__cat":"master_bedroom","floor":0,"windows":2,"door_count":1,"notes":"SW Vastu","__is_carved":False},
            {"name":"corridor",       "x":70,  "y":250, "width":260,"height":40, "width_ft":26,"depth_ft":4, "area_sqft":104,"__vastu_zone":"C","__cat":"corridor",      "floor":0,"windows":0,"door_count":0,"notes":"","__is_carved":False},
            {"name":"dining_room",    "x":200, "y":120, "width":130,"height":130,"width_ft":13,"depth_ft":13,"area_sqft":169,"__vastu_zone":"NE","__cat":"dining_room",  "floor":0,"windows":1,"door_count":1,"notes":"","__is_carved":False},
        ],
        "warnings": [], "failed_rooms": [],
    }
    mock_parsed = {
        "bhk_type":"3BHK","plot_width_ft":30,"plot_depth_ft":50,
        "style":"modern","budget":5500000,"floors":1,
        "vastu_compliant":True,"plot_facing":"north",
    }

    scene = single_layout_to_pascal(mock_layout, mock_parsed)
    print(f"✓ Generated Pascal scene: {len(scene['nodes'])} nodes")
    print(f"  Root: {scene['rootNodeIds']}")
    node_types = {}
    for n in scene["nodes"].values():
        t = n["type"]
        node_types[t] = node_types.get(t, 0) + 1
    print(f"  Node types: {node_types}")
    print("\nSample JSON (first 1000 chars):")
    print(to_json(scene)[:1000])