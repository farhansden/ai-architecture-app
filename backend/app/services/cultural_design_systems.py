"""
cultural_design_systems.py  —  Multi-cultural design zone system
=================================================================

Extends compass_engine.py with culture-specific zone rules.

SUPPORTED DESIGN SYSTEMS:
  vastu     → Hindu / Jain Vastu Shastra (default for Indian residential)
  islamic   → Islamic privacy + Qibla orientation rules
  feng_shui → Chinese Bagua zone system
  universal → Sun-path based functional zones (no religious basis)

CRITICAL: This file's _VASTU_ZONE must stay in sync with compass_engine.py.
Zone corrections applied here are the canonical source of truth:
  parents_bedroom = NW (not SW — SW is owner/master zone exclusively)
  utility_room    = S  (not NW — heavy inert work goes to Yama/South)
  home_office     = N  (not W  — North = Kubera/wealth for business)
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple


# ── Compass zone definitions ────────────────────────────────────────────────

# Maps compass direction → (row_position, col_position)
# row: 0=top(front), 1=middle, 2=bottom(rear)
# col: 0=left,       1=center,  2=right
_COMPASS_TO_GRID: Dict[str, Tuple[int, int]] = {
    "NW": (0, 0),  "N": (0, 1),  "NE": (0, 2),
    "W":  (1, 0),  "C": (1, 1),  "E":  (1, 2),
    "SW": (2, 0),  "S": (2, 1),  "SE": (2, 2),
}

# Maps plot_facing → which compass direction each screen edge represents
# Format: (top_compass, bottom_compass, left_compass, right_compass)
_FACING_TO_SCREEN: Dict[str, Tuple[str, str, str, str]] = {
    "east":    ("E",  "W",  "N",  "S"),
    "north":   ("N",  "S",  "W",  "E"),
    "west":    ("W",  "E",  "S",  "N"),
    "south":   ("S",  "N",  "E",  "W"),
    "unknown": ("N",  "S",  "W",  "E"),   # default to north-facing
}

# Vastu zone assignments for each room category
# These are ABSOLUTE compass zones, not screen positions
_VASTU_ZONE: Dict[str, str] = {
    # Ground floor
    "pooja_room":        "NE",  # spiritual purity, morning light
    "living_room":       "N",   # north light, gathering space
    "dining_room":       "N",   # adjacent to living, north
    "kitchen":           "SE",  # fire corner, ideal
    "wet_kitchen":       "SE",  # adjacent to kitchen
    "dry_kitchen":       "SE",  # adjacent to kitchen
    "common_bathroom":   "NW",  # plumbing stack, air corner
    "guest_bedroom":     "NW",  # for visiting elderly, NW corner
    "guest_room":        "NW",  # same as guest bedroom
    "utility_room":      "S",   # CORRECTED: S (Yama/heavy-inert zone). NOT NW (air/movement).
    "store_room":        "S",   # heavy storage, south
    "staircase":         "S",   # south/southwest (structural mass)
    "home_office":       "N",   # CORRECTED: N (Kubera/wealth). NOT W (afternoon shade).
    "study":             "W",   # same as home office
    "servant_quarters":  "S",   # rear south zone
    "car_porch":         "front",  # always entrance side
    "sit_out":           "front",  # always entrance side
    "foyer":             "C",   # center entry transition
    "entrance_foyer":    "C",   # center entry transition
    "corridor":          "C",   # circulation center
    "passage":           "C",   # ground floor passage

    # Upper floor
    "master_bedroom":    "SW",  # earth corner — stable, private
    "parents_bedroom":   "NW",  # CORRECTED: NW (Vayavya) — NOT SW. SW is owner zone only.
                                  # Parents in NW = comfortable visit. Parents in SW = family tension.
    "bedroom":           "NE",  # general bedroom — NE or E
    "bedroom_2":         "NE",  # kids bedroom 1 (oldest child)
    "bedroom_3":         "E",   # kids bedroom 2
    "family_lounge":     "C",   # connecting space, center
    "walk_in_wardrobe":  "SW",  # adjacent to master bedroom
    "terrace":           "N",   # north terrace (shade, views)
    "balcony":           "N",   # north-facing preferred
    "staircase_landing": "C",   # center circulation
}

# Zone priority for screen row assignment
# row 0 = top (front/entrance), row 2 = bottom (rear)
# The row a room occupies in the layout grid
_ZONE_TO_ROW: Dict[str, int] = {
    "front": 0,   # car porch, sit out
    "NW": 1, "N": 1, "NE": 1,   # public band (behind front)
    "W":  2, "C": 2, "E":  2,   # service band (middle-rear)
    "SW": 3, "S": 3, "SE": 3,   # private/rear band
}

# The column a room occupies (0=left, 1=center, 2=right)
# This is in ABSOLUTE compass terms and gets translated to screen
_ZONE_TO_COL_COMPASS: Dict[str, str] = {
    "NW": "left",   "N":  "center", "NE": "right",
    "W":  "left",   "C":  "center", "E":  "right",
    "SW": "left",   "S":  "center", "SE": "right",
    "front": "left",
}


# ── Plot facing → coordinate transforms ─────────────────────────────────────

def get_screen_mapping(plot_facing: str) -> Dict[str, str]:
    """
    Returns a mapping from compass direction to screen position.
    Screen positions: 'top', 'bottom', 'left', 'right', 'center'

    Example for north-facing:
      N→top, S→bottom, W→left, E→right

    This is the KEY function that makes Vastu work for any plot orientation.
    """
    facing = (plot_facing or "unknown").lower().strip()
    top, bottom, left, right = _FACING_TO_SCREEN.get(facing, _FACING_TO_SCREEN["unknown"])

    # Build reverse mapping: compass_direction → screen_side
    mapping = {
        top:    "top",
        bottom: "bottom",
        left:   "left",
        right:  "right",
        "C":    "center",
    }

    # Add diagonal zones
    # top+left corner, top+right corner, etc.
    compass_to_screen_col = {}
    compass_to_screen_row = {}

    # Row mapping (0=top front, 2=bottom rear)
    for compass, screen in mapping.items():
        if screen == "top":
            compass_to_screen_row[compass] = "front_row"
        elif screen == "bottom":
            compass_to_screen_row[compass] = "rear_row"

    return {
        "top":    top,      # which compass direction is at the top of the screen
        "bottom": bottom,   # which compass direction is at the bottom
        "left":   left,     # which compass direction is on the left
        "right":  right,    # which compass direction is on the right
        "facing": facing,
        # Derived diagonal zones
        "top_left":     _combine(top, left),     # e.g. north-facing: N+W = NW
        "top_right":    _combine(top, right),    # north-facing: N+E = NE
        "bottom_left":  _combine(bottom, left),  # north-facing: S+W = SW
        "bottom_right": _combine(bottom, right), # north-facing: S+E = SE
    }


def _combine(primary: str, secondary: str) -> str:
    """Combine two cardinal directions into a diagonal zone: N + E → NE"""
    s = set([primary, secondary])
    combos = {
        frozenset(["N", "E"]): "NE",
        frozenset(["N", "W"]): "NW",
        frozenset(["S", "E"]): "SE",
        frozenset(["S", "W"]): "SW",
    }
    return combos.get(frozenset(s), primary)


# ── Zone → Screen position ───────────────────────────────────────────────────

def zone_to_screen_position(
    vastu_zone: str,
    screen_map: Dict[str, str],
) -> Tuple[str, str]:
    """
    Convert a Vastu compass zone to a screen (row, col) position.
    Returns ('row_band', 'col_side') where:
      row_band: 'front' | 'public' | 'service' | 'private'
      col_side: 'left'  | 'center' | 'right'

    Example: north-facing plot, zone=SW
      SW in screen = bottom_left
      → row_band='private', col_side='left'

    Example: east-facing plot, zone=SW
      east-facing: top=E, bottom=W, left=N, right=S
      SW = bottom+left → S side is RIGHT in screen coords
      Actually for east-facing: SW = bottom (W) + right (S) = bottom_right
      → row_band='private', col_side='right'
    """
    zone = vastu_zone.upper()

    # Map compass zone to screen corners
    # Using the screen_map to find which screen corner each compass zone maps to
    top    = screen_map["top"]      # e.g. "N" for north-facing
    bottom = screen_map["bottom"]   # e.g. "S"
    left   = screen_map["left"]     # e.g. "W"
    right  = screen_map["right"]    # e.g. "E"

    # Row band
    if "front" in zone.lower():
        row_band = "front"
    elif zone == "C":
        row_band = "service"  # center = middle service band
    elif top in zone or zone == top:
        row_band = "public"
    elif bottom in zone or zone == bottom:
        row_band = "private"
    else:
        row_band = "service"  # E, W zones = middle band

    # Column side
    if zone == "C":
        col_side = "center"
    elif "front" in zone.lower():
        col_side = "left"   # default; car_porch will extend
    elif left in zone or zone == left:
        col_side = "left"
    elif right in zone or zone == right:
        col_side = "right"
    else:
        col_side = "center"

    return row_band, col_side


# ── Main API ─────────────────────────────────────────────────────────────────

def assign_vastu_zones(
    rooms: List[Dict[str, Any]],
    plot_facing: str,
    vastu_compliant: bool = True,
    floors: int = 1,
    design_system: str = "vastu",
) -> List[Dict[str, Any]]:
    """
    Assign each room its correct compass zone and screen position.
    Injects '__vastu_zone', '__row_band', '__col_side' into each room dict.

    Now supports multiple design systems:
      vastu     → Hindu/Jain Vastu Shastra zones
      islamic   → Islamic privacy + Qibla zones
      feng_shui → Bagua zones
      universal → Sun-path based functional zones

    Args:
        rooms: list of room dicts from parsed JSON
        plot_facing: 'north' | 'east' | 'south' | 'west' | 'unknown'
        vastu_compliant: backwards compat — if True and design_system='vastu'
        floors: total number of floors
        design_system: 'vastu' | 'islamic' | 'feng_shui' | 'universal'
    """
    # Load zone rules for the detected design system
    zone_rules = None
    try:
        from cultural_design_systems import get_zone_rules, DesignSystem
        ds = DesignSystem(design_system) if design_system in [e.value for e in DesignSystem] \
             else DesignSystem.VASTU if vastu_compliant else DesignSystem.UNIVERSAL
        zone_rules = get_zone_rules(ds, plot_facing).get("zones", {})
    except ImportError:
        pass   # Fall back to built-in _VASTU_ZONE

    screen_map = get_screen_mapping(plot_facing)

    for room in rooms:
        name   = str(room.get("name", "")).lower()
        floor  = int(room.get("floor", 0) or 0)

        # Get zone from the appropriate system's zone map
        if zone_rules:
            zone = _get_zone_from_map(name, zone_rules, floor, floors, screen_map)
        else:
            zone = _get_zone(name, floor, floors, vastu_compliant or design_system == "vastu", screen_map)

        # Convert zone to screen position
        row_band, col_side = zone_to_screen_position(zone, screen_map)

        # Inject into room dict
        room["__vastu_zone"]  = zone
        room["__row_band"]    = row_band
        room["__col_side"]    = col_side

    return rooms


def _get_zone_from_map(
    name: str,
    zone_map: Dict[str, str],
    floor: int,
    floors: int,
    screen_map: Dict[str, str],
) -> str:
    """Get zone for a room using a custom zone map (cultural_design_systems)."""
    # Exact match
    for key, zone in zone_map.items():
        if key == name:
            return zone
    # Substring match
    for key, zone in zone_map.items():
        if len(key) > 4 and key in name:
            return zone
    # Fallback to built-in
    return _get_zone(name, floor, floors, True, screen_map)


def _get_zone(
    name: str,
    floor: int,
    floors: int,
    vastu: bool,
    screen_map: Dict[str, str],
) -> str:
    """
    Return the correct Vastu compass zone for a room by name.
    Falls back to functional zone if Vastu is disabled.
    """
    # Exact match first
    for key, zone in _VASTU_ZONE.items():
        if key == name:
            return zone

    # Prefix/substring match
    for key, zone in _VASTU_ZONE.items():
        if name.startswith(key) or key in name:
            return zone

    # Special cases
    if "bedroom" in name and "_bathroom" not in name:
        if "master" in name or "parent" in name:
            return "SW"
        if "guest" in name:
            return "NW"
        if "_2" in name or "second" in name:
            return "NE"
        if "_3" in name or "third" in name:
            return "E"
        return "E"  # default bedroom

    if "bathroom" in name or "toilet" in name:
        if "common" in name:
            return "NW"
        if "servant" in name:
            return "S"
        return "NW"  # default bathrooms NW

    if "car" in name or "parking" in name:
        return "front"

    if "stair" in name:
        return "S"

    if "lounge" in name or "family_lounge" in name:
        return "C"

    if "terrace" in name or "balcony" in name:
        return "N"

    if "utility" in name or "laundry" in name:
        return "NW"

    if "servant" in name:
        return "S"

    if "office" in name or "study" in name:
        return "W"

    if "store" in name:
        return "S"

    if "foyer" in name or "entrance" in name:
        return "C"

    # Default: center
    return "C"


# ── Vastu violation checker ──────────────────────────────────────────────────

def check_vastu_violations(
    rooms: List[Dict[str, Any]],
    plot_facing: str,
    vastu_notes: List[str],
) -> List[str]:
    """
    Check for Vastu violations after zone assignment.
    Returns list of violation strings for the warnings panel.
    """
    violations = []
    screen_map = get_screen_mapping(plot_facing)

    for room in rooms:
        name = str(room.get("name", "")).lower()
        assigned_zone = room.get("__vastu_zone", "")
        expected_zone = _get_zone(name, int(room.get("floor",0) or 0), 2, True, screen_map)

        if assigned_zone and expected_zone and assigned_zone != expected_zone:
            # Only report violations for Vastu-critical rooms
            critical = {"master_bedroom","kitchen","pooja_room","common_bathroom",
                        "staircase","living_room","guest_bedroom","master_bathroom"}
            if any(c in name for c in critical):
                violations.append(
                    f"VASTU: {name} placed in {assigned_zone} zone "
                    f"(should be {expected_zone} for {plot_facing}-facing plot)"
                )

    return violations


# ── Helper: get sorted rooms for a row band ──────────────────────────────────

def get_rooms_in_row(
    rooms: List[Dict[str, Any]],
    row_band: str,
    floor: int = 0,
) -> List[Dict[str, Any]]:
    """
    Return rooms assigned to a specific row band and floor,
    sorted by column position (left → center → right).
    """
    col_order = {"left": 0, "center": 1, "right": 2}
    result = [
        r for r in rooms
        if r.get("__row_band") == row_band
        and int(r.get("floor", 0) or 0) == floor
    ]
    return sorted(result, key=lambda r: col_order.get(r.get("__col_side", "center"), 1))


# ── Facing-aware vastu sort for layout_engine ────────────────────────────────

def vastu_sort_key(room: Dict[str, Any], row_name: str, plot_facing: str) -> int:
    """
    Return a sort key for a room within a row, based on its Vastu zone
    and the actual plot facing. Replaces the hardcoded vastu_order() in layout_engine.

    The key insight: on an east-facing plot, 'left' = north, 'right' = south.
    On a north-facing plot, 'left' = west, 'right' = east.
    Kitchen must always be on the SE side — which is different screen positions
    depending on the plot facing.
    """
    screen_map = get_screen_mapping(plot_facing)
    col_side = room.get("__col_side", "center")
    col_order = {"left": 0, "center": 1, "right": 2}
    return col_order.get(col_side, 1)