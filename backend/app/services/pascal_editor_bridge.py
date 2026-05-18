"""
pascal_editor_bridge.py  —  layout_engine output → Pascal Editor JS state
=========================================================================
Drop into:  app/services/pascal_editor_bridge.py
Zero side-effects on existing pipeline. Only called by editor_route.py.
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional

ROOM_COLORS: Dict[str, str] = {
    "living_room":      "#e8f4e8",
    "dining_room":      "#e0f7fa",
    "master_bedroom":   "#ede7f6",
    "parents_bedroom":  "#f3e5f5",
    "bedroom":          "#e8eaf6",
    "kitchen":          "#fff3e0",
    "wet_kitchen":      "#fff3e0",
    "dry_kitchen":      "#fff8e1",
    "bathroom":         "#e3f2fd",
    "common_bathroom":  "#e3f2fd",
    "guest_powder_room":"#e8eaf6",
    "corridor":         "#f5f5f5",
    "passage":          "#f5f5f5",
    "staircase":        "#fafafa",
    "staircase_landing":"#fafafa",
    "car_porch":        "#eceff1",
    "sit_out":          "#f1f8e9",
    "store_room":       "#efebe9",
    "utility_room":     "#efebe9",
    "home_office":      "#fce4ec",
    "balcony":          "#f1f8e9",
    "terrace":          "#e8f5e9",
    "family_lounge":    "#e8f4e8",
    "pooja_room":       "#fff9c4",
    "servant_quarters": "#fbe9e7",
    "walk_in_wardrobe": "#f0e6ff",
    "foyer":            "#fff3e0",
    "guest_bedroom":    "#e8f0fe",
}

# Proportional furniture templates: ox/oy = offset ratio, rw/rh = size ratio of room
_FURNITURE: Dict[str, List[Dict[str, Any]]] = {
    "living_room": [
        {"name": "Sofa L-Shape",  "fcat": "sofa_l",       "ox": 0.05, "oy": 0.10, "rw": 0.45, "rh": 0.50},
        {"name": "Coffee Table",  "fcat": "coffee_table",  "ox": 0.20, "oy": 0.60, "rw": 0.25, "rh": 0.18},
        {"name": "TV Unit",       "fcat": "tv_unit",       "ox": 0.05, "oy": 0.04, "rw": 0.55, "rh": 0.09},
        {"name": "Plant",         "fcat": "plant",         "ox": 0.85, "oy": 0.06, "rw": 0.08, "rh": 0.10},
    ],
    "dining_room": [
        {"name": "Dining Table",  "fcat": "dining_table",  "ox": 0.12, "oy": 0.15, "rw": 0.65, "rh": 0.65},
    ],
    "master_bedroom": [
        {"name": "Bed (Double)",  "fcat": "bed",           "ox": 0.08, "oy": 0.10, "rw": 0.55, "rh": 0.62},
        {"name": "Wardrobe",      "fcat": "wardrobe",      "ox": 0.70, "oy": 0.08, "rw": 0.26, "rh": 0.15},
        {"name": "Basin/Sink",    "fcat": "basin",         "ox": 0.70, "oy": 0.30, "rw": 0.18, "rh": 0.14},
    ],
    "parents_bedroom": [
        {"name": "Bed (Double)",  "fcat": "bed",           "ox": 0.08, "oy": 0.10, "rw": 0.55, "rh": 0.62},
        {"name": "Wardrobe",      "fcat": "wardrobe",      "ox": 0.70, "oy": 0.08, "rw": 0.26, "rh": 0.15},
    ],
    "bedroom": [
        {"name": "Bed (Single)",  "fcat": "bed_single",   "ox": 0.08, "oy": 0.10, "rw": 0.45, "rh": 0.62},
        {"name": "Wardrobe",      "fcat": "wardrobe",      "ox": 0.60, "oy": 0.08, "rw": 0.32, "rh": 0.15},
    ],
    "guest_bedroom": [
        {"name": "Bed (Single)",  "fcat": "bed_single",   "ox": 0.08, "oy": 0.10, "rw": 0.45, "rh": 0.62},
        {"name": "Wardrobe",      "fcat": "wardrobe",      "ox": 0.60, "oy": 0.08, "rw": 0.32, "rh": 0.15},
    ],
    "kitchen": [
        {"name": "Kitchen Counter","fcat":"kitchen_counter","ox":0.05, "oy": 0.05, "rw": 0.88, "rh": 0.25},
        {"name": "Fridge",         "fcat": "fridge",        "ox": 0.05, "oy": 0.70, "rw": 0.22, "rh": 0.25},
    ],
    "wet_kitchen": [
        {"name": "Kitchen Counter","fcat":"kitchen_counter","ox":0.05, "oy": 0.05, "rw": 0.88, "rh": 0.28},
        {"name": "Washing Machine","fcat":"washing_machine","ox":0.05, "oy": 0.70, "rw": 0.28, "rh": 0.28},
    ],
    "dry_kitchen": [
        {"name": "Kitchen Counter","fcat":"kitchen_counter","ox":0.05, "oy": 0.05, "rw": 0.88, "rh": 0.28},
    ],
    "bathroom": [
        {"name": "Toilet",        "fcat": "toilet",        "ox": 0.08, "oy": 0.08, "rw": 0.55, "rh": 0.48},
        {"name": "Basin/Sink",    "fcat": "basin",         "ox": 0.08, "oy": 0.65, "rw": 0.45, "rh": 0.28},
    ],
    "common_bathroom": [
        {"name": "Toilet",        "fcat": "toilet",        "ox": 0.08, "oy": 0.08, "rw": 0.55, "rh": 0.48},
        {"name": "Basin/Sink",    "fcat": "basin",         "ox": 0.08, "oy": 0.65, "rw": 0.45, "rh": 0.28},
    ],
    "guest_powder_room": [
        {"name": "Toilet",        "fcat": "toilet",        "ox": 0.08, "oy": 0.08, "rw": 0.55, "rh": 0.48},
        {"name": "Basin/Sink",    "fcat": "basin",         "ox": 0.08, "oy": 0.65, "rw": 0.45, "rh": 0.28},
    ],
    "car_porch": [
        {"name": "Car",           "fcat": "car",           "ox": 0.08, "oy": 0.05, "rw": 0.75, "rh": 0.88},
    ],
    "home_office": [
        {"name": "Modular Desk",  "fcat": "desk",          "ox": 0.06, "oy": 0.06, "rw": 0.80, "rh": 0.38},
        {"name": "Chair",         "fcat": "chair",         "ox": 0.35, "oy": 0.52, "rw": 0.25, "rh": 0.30},
        {"name": "Bookshelf",     "fcat": "bookshelf",     "ox": 0.06, "oy": 0.82, "rw": 0.70, "rh": 0.15},
    ],
    "staircase": [
        {"name": "Stair Steps",   "fcat": "stairs",        "ox": 0.05, "oy": 0.05, "rw": 0.90, "rh": 0.90},
    ],
    "family_lounge": [
        {"name": "Sofa (3-seat)", "fcat": "sofa",          "ox": 0.06, "oy": 0.12, "rw": 0.80, "rh": 0.38},
        {"name": "Coffee Table",  "fcat": "coffee_table",  "ox": 0.22, "oy": 0.56, "rw": 0.40, "rh": 0.24},
    ],
    "utility_room": [
        {"name": "Washing Machine","fcat":"washing_machine","ox":0.08, "oy": 0.08, "rw": 0.35, "rh": 0.40},
    ],
    "servant_quarters": [
        {"name": "Bed (Single)",  "fcat": "bed_single",   "ox": 0.08, "oy": 0.10, "rw": 0.50, "rh": 0.65},
    ],
}

_FLOOR_LABELS = {0: "Ground Floor", 1: "First Floor", 2: "Second Floor", 3: "Third Floor"}

_uid_ctr = [0]
def _uid() -> str:
    _uid_ctr[0] += 1
    return f"be_{_uid_ctr[0]}"


def layout_to_editor_state(
    per_floor_layouts: Dict[str, Any],
    parsed: Dict[str, Any],
    floor_labels: Optional[Dict[int, str]] = None,
) -> Dict[str, Any]:
    """
    Convert layout_engine per-floor output → Pascal Editor `state` dict.

    Args:
        per_floor_layouts : { "0": layout_dict, "1": layout_dict, ... }
                            Direct output of generate_layout() per floor.
        parsed            : llm_parser output dict (for meta fields).
        floor_labels      : optional label overrides { 0: "Ground Floor", ... }

    Returns:
        JSON-serialisable dict — inject into editor.html as
        window.__INITIAL_STATE__ = <json>;
    """
    labels = floor_labels or _FLOOR_LABELS
    floors_out = []
    walk_x, walk_y = 200.0, 200.0

    for fi_str, layout in sorted(per_floor_layouts.items(), key=lambda kv: int(kv[0])):
        fi = int(fi_str)
        rooms_out: List[Dict] = []
        furn_out:  List[Dict] = []

        for r in layout.get("rooms", []):
            cat   = str(r.get("__cat", ""))
            rname = str(r.get("name", "Room"))
            color = ROOM_COLORS.get(cat, "#e8f4e8")

            rx = round(float(r.get("x", 0)), 1)
            ry = round(float(r.get("y", 0)), 1)
            rw = round(float(r.get("width", 80)), 1)
            rh = round(float(r.get("height", 80)), 1)

            rooms_out.append({
                "id": _uid(), "name": rname,
                "x": rx, "y": ry, "w": rw, "h": rh,
                "color": color, "floor": fi, "rot": 0, "type": "room",
                "__cat": cat,
                "vastu_zone": r.get("__vastu_zone", ""),
            })

            # Auto-place proportional furniture
            for tmpl in _FURNITURE.get(cat, []):
                fw = round(rw * tmpl["rw"], 1)
                fh = round(rh * tmpl["rh"], 1)
                # Skip if furniture would be too tiny to render
                if fw < 12 or fh < 8:
                    continue
                furn_out.append({
                    "id": _uid(), "name": tmpl["name"], "fcat": tmpl["fcat"],
                    "x": round(rx + rw * tmpl["ox"], 1),
                    "y": round(ry + rh * tmpl["oy"], 1),
                    "w": fw, "h": fh,
                    "floor": fi, "rot": 0, "type": "furniture",
                })

        # Walk start = centre of first habitable room on ground floor
        if fi == 0 and rooms_out:
            first = next(
                (r for r in rooms_out if r["__cat"] in ("living_room","sitting_room","foyer")),
                rooms_out[0]
            )
            walk_x = first["x"] + first["w"] / 2
            walk_y = first["y"] + first["h"] / 2

        floors_out.append({
            "name":      labels.get(fi, f"Floor {fi}"),
            "rooms":     rooms_out,
            "furniture": furn_out,
        })

    return {
        "floors":       floors_out,
        "currentFloor": 0,
        "view":         "2d",
        "gridOn":       True,
        "meta": {
            "plot_facing":     parsed.get("plot_facing", "east"),
            "vastu_compliant": bool(parsed.get("vastu_compliant", False)),
            "bhk":             parsed.get("bhk", ""),
            "style":           parsed.get("style", ""),
            "plot_width_ft":   parsed.get("plot_width_ft", 40),
            "plot_depth_ft":   parsed.get("plot_depth_ft", 60),
        },
        "walk": {"x": walk_x, "y": walk_y, "angle": 0, "floor": 0},
    }