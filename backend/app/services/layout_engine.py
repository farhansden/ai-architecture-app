"""
layout_engine.py  —  Architect-correct 2D Room Placement Engine
================================================================
Version: 6.6  —  Indian programme size floors + post-budget re-clamp (grid still flush)

PLACEMENT PIPELINE (executed before any rectangle geometry):
  1) Built-up footprint from setbacks (compute_built_up_bounds).
  2) Implicit structural grid via horizontal bands × column strips (aligned walls).
  3) Zoning hierarchy: entrance → public → corridor spine → service → rear service;
     upper floor: lounge → corridor → bedrooms → rear outdoor.
  4) Corridor + stair occupy a dedicated band (circulation first, not leftovers).
  5) Rear band stacks wet/service rooms for plausible plumbing cores.
  6) compass_engine assigns Vastu-aware column preference without breaking NBC minima.

Outputs include per-room functional_zone for JSON consumers (public / semi_private /
private / service / circulation).

ARCHITECTURE: 6-band ground floor (single-storey sleeping row), 4-band upper floor

Ground floor — band IDs (single-storey placement ORDER may differ — see _gf_band_stack_order):
  Band 0 ENTRANCE  (~14ft): car_porch + sit_out + foyer / veranda
  Band 1 PUBLIC    (~15ft): living + drawing + pooja + home_office (NO dining when floors==1)
  Band 4 SERVICE   (~12ft): single kitchen + dining when floors==1 (meal cluster; utility in rear band)
  Band 2 CORRIDOR  (= corridor_width_ft): circulation — placed AFTER meal zone if single-storey
  Band 3 GF_SLEEP  (~12ft+): bedrooms when floors==1 only (never mixed with wet core)
  Band 5 REAR_SVC  (~10ft): servant + utility + store + bathrooms

First floor (front → rear):
  Band 1 PUBLIC    family_lounge
  Band 2 CORRIDOR  corridor + staircase_landing
  Band 6 BEDROOMS  master + bedrooms
  Band 7 REAR      terrace + balcony

KEY DESIGN DECISIONS:
1. Living room depth capped at 15ft for band height (even if LLM gives 18ft)
   This prevents PUBLIC band from becoming 18ft and starving rear zones.
2. Dining room uses its own target depth (NOT band height) — fixed-size room.
3. Corridor/passage uses corridor_width_ft as its depth, not depth_ft which is its run.
4. Staircase goes in CORRIDOR band — its true depth (10ft) sets that band height.
5. home_office in PUBLIC band (north / quiet work zone per compass_engine).
6. Servant quarters in REAR_SVC (south zone, Vastu correct, near utility).
7. Within each band, rooms are ordered by Indian circulation rank (entry → living →
   dining → kitchen; bedrooms off FF lounge/corridor, not off parking).
"""

from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


SCALE            = 10
MARGIN_PX        = 70
INTERNAL_WALL_PX = 4.0
WALL_INSET       = INTERNAL_WALL_PX / 2

_NBC_MIN: Dict[str, Tuple[float, float]] = {
    "drawing_room":      (14.0, 12.0),
    "master_bedroom":    (12.0, 12.0),
    "parents_bedroom":   (11.0, 11.0),
    "bedroom":           (10.0, 10.0),
    "living_room":       (14.0, 12.0),
    "dining_room":       (10.0,  9.0),
    "kitchen":           ( 9.0,  9.0),
    "bathroom":          ( 4.5,  6.0),
    "common_bathroom":   ( 4.5,  6.0),
    "corridor":          ( 4.0,  4.0),
    "passage":           ( 3.5,  4.0),
    # Internal micro-lobbies used only to make wet-core access realistic.
    # Keep narrow so they never push bedrooms outside the envelope.
    "service_passage":   ( 2.5,  4.0),
    "rear_passage":      ( 2.5,  4.0),
    "car_porch":         (11.0, 11.0),
    "sit_out":           ( 8.0,  5.0),
    "pooja_room":        ( 6.5,  6.5),
    "utility_room":      ( 5.0,  5.0),
    "store_room":        ( 4.0,  4.0),
    "staircase":         ( 5.0,  8.0),
    "balcony":           ( 4.0,  3.0),
    "home_office":       ( 9.0,  9.0),
    "servant_quarters":  ( 8.0,  8.0),
    "family_lounge":     ( 8.0,  8.0),
    "walk_in_wardrobe":  ( 5.0,  5.0),
    "foyer":             ( 5.0,  5.0),
    "terrace":           ( 8.0,  6.0),
    "guest_powder_room": ( 4.0,  6.0),
}

# Maximum depth we allow to DRIVE band height for certain rooms
# (prevents one large room from ballooning the band for all its neighbours)
_MAX_BAND_DRIVER_DEPTH: Dict[str, float] = {
    "drawing_room":    14.0,
    "living_room":     14.0,   # cap at 14ft for band height calc (Guide Ch.5)
    "dining_room":     13.0,
    "family_lounge":    8.0,   # compact lounge max 8ft depth
    "kitchen":         13.0,
    "wet_kitchen":     13.0,
    "dry_kitchen":     11.0,
    "master_bedroom":  16.0,
    "bedroom":         13.0,   # WAS 15.0 — standard bedroom max 13ft depth (Fix 13)
    "home_office":     12.0,
    "parents_bedroom": 14.0,   # parents bedroom slightly larger than bedroom (Fix 13)
}

# Max room WIDTH per room type — prevents one room stealing entire band (Guide Ch.11 Fix 3)
_MAX_ROOM_WIDTH_PX: Dict[str, float] = {
    "drawing_room":    200.0,
    "living_room":     220.0,  # 22ft max
    "dining_room":     160.0,  # 16ft max
    "kitchen":         160.0,  # 16ft max
    # Width cap ~8ft — wide enough for credible prayer niche; depth comes from band slab
    "pooja_room":       82.0,
    "master_bedroom":  200.0,  # 20ft max
    "bedroom":         160.0,  # WAS 180.0 — max 16ft for bedroom_2/3 (Fix 13)
    "parents_bedroom": 180.0,
    "family_lounge":    130.0,  # ~13ft max — compact lounge  # parents bedroom max 18ft
}


@dataclass(frozen=True)
class Rect:
    x: float
    y: float
    w: float
    h: float
    @property
    def right(self)  -> float: return self.x + self.w
    @property
    def bottom(self) -> float: return self.y + self.h
    @property
    def cx(self)     -> float: return self.x + self.w / 2
    @property
    def cy(self)     -> float: return self.y + self.h / 2


# ─── CATEGORISATION ──────────────────────────────────────────────────────────

def _cat(name: str, room_dict: Optional[Dict[str, Any]] = None) -> str:
    if room_dict is not None:
        h = room_dict.get("__category_hint", "")
        if h: return h
    n = (name or "").lower()
    if "drawing_room" == n or ("drawing" in n and "room" in n):
        return "drawing_room"
    if "car_porch"         in n or n == "parking":       return "car_porch"
    if "sit_out" in n or "verandah" in n or "veranda" in n:
        return "sit_out"
    if "foyer"             in n or "entrance_foyer" in n: return "foyer"
    if n == "living_room":                                return "living_room"
    if n == "dining_room":                                return "dining_room"
    # Legacy programme names only (llm_parser + visual_floor_plan strip these upstream).
    if "wet_kitchen"       in n:                          return "wet_kitchen"
    if "dry_kitchen"       in n:                          return "dry_kitchen"
    if n == "kitchen"      or n.startswith("kitchen_"):   return "kitchen"
    if "pooja"             in n:                          return "pooja_room"
    if "utility"           in n:                          return "utility_room"
    if "store_room"        in n:                          return "store_room"
    if "store"             in n and "stair" not in n:     return "store_room"
    if "staircase_landing" in n or "stair_void" in n:     return "staircase_landing"
    if "passage"           in n:                          return "passage"
    if "corridor"          in n:                          return "corridor"
    if "common"            in n and ("bath" in n or "toilet" in n): return "common_bathroom"
    if "guest_powder"      in n or "powder_room" in n:    return "guest_powder_room"
    if "bath"              in n or "toilet" in n:         return "bathroom"
    if "master_bedroom"    in n:                          return "master_bedroom"
    if "parents_bedroom"   in n:                          return "parents_bedroom"
    if "guest_room"        in n or "guest_bedroom" in n:  return "guest_bedroom"
    if "bedroom"           in n:                          return "bedroom"
    if "staircase"         in n or "stair" in n:          return "staircase"
    if "balcony"           in n:                          return "balcony"
    if "terrace"           in n:                          return "terrace"
    if "home_office"       in n or "office" in n:         return "home_office"
    if "study"             in n:                          return "home_office"
    if "servant"           in n:                          return "servant_quarters"
    if "lounge"            in n or "family_lounge" in n:  return "family_lounge"
    if "walk_in_wardrobe"  in n or "wardrobe" in n:       return "walk_in_wardrobe"
    return "store_room"


def _is_ghost(name: str) -> bool:
    return (name or "").lower().count("_bathroom") > 1


def _is_attached_child(name: str) -> bool:
    n = (name or "").lower()
    carved = ("master_bedroom", "parents_bedroom", "bedroom_", "servant_quarters", "servant_")
    if n.endswith("_bathroom") and any(p in n for p in carved):
        return True
    if "servant" in n and ("bath" in n or "toilet" in n):
        return True
    if "walk_in_wardrobe" in n:
        return True
    return False


def _nbc(cat: str) -> Tuple[float, float]:
    return _NBC_MIN.get(cat, (4.0, 4.0))


def _dims(room: Dict[str, Any]) -> Tuple[float, float]:
    w = float(room.get("width_ft") or 0.0)
    d = float(room.get("depth_ft") or 0.0)
    if w > 0.5 and d > 0.5:
        return w, d
    area = float(room.get("area_sqft") or 100.0)
    w = math.sqrt(area * 1.25)
    return w, area / max(w, 0.1)


# ─── PUBLIC API: compute_built_up_bounds ─────────────────────────────────────

def compute_built_up_bounds(parsed: Dict[str, Any]) -> Dict[str, float]:
    sb = parsed.get("setbacks") or {}
    pw = float(parsed.get("plot_width_ft") or 40)
    pd = float(parsed.get("plot_depth_ft") or 60)
    l  = float(sb.get("left",  2) or 2)
    r  = float(sb.get("right", 2) or 2)
    f  = float(sb.get("front", 5) or 5)
    re = float(sb.get("rear",  3) or 3)
    return {
        "plot_w_px":  pw * SCALE,
        "plot_h_px":  pd * SCALE,
        "built_up_x": l  * SCALE,
        "built_up_y": f  * SCALE,
        "built_up_w": max((pw - l - r)  * SCALE, 1.0),
        "built_up_h": max((pd - f - re) * SCALE, 1.0),
        "front_px":   f  * SCALE,
    }


# ─── BAND CONSTANTS ──────────────────────────────────────────────────────────

BAND_ENTRANCE = 0   # car_porch, sit_out, foyer
BAND_PUBLIC   = 1   # living_room, dining_room  (floor0) | family_lounge (floor1)
BAND_CORRIDOR = 2   # staircase + corridor spine
BAND_GF_SLEEPING = 3  # ground-floor bedrooms when single-storey only (private band)
BAND_SERVICE  = 4   # sole kitchen (floor0 cooking zone)
BAND_REAR_SVC = 5   # servant + utility + store + bathrooms  (floor0)
BAND_BEDROOMS = 6   # bedrooms (first floor)
BAND_REAR     = 7   # terrace, balcony

# Categories placed in the GF sleeping band for single-storey homes only.
_GF_SLEEPING_CATS = frozenset({
    "master_bedroom", "parents_bedroom", "bedroom", "guest_bedroom",
})

_BAND_F0: Dict[str, int] = {
    "car_porch": BAND_ENTRANCE, "sit_out": BAND_ENTRANCE,
    "foyer": BAND_ENTRANCE, "entrance_foyer": BAND_ENTRANCE,
    "drawing_room": BAND_PUBLIC,
    "living_room": BAND_PUBLIC, "dining_room": BAND_PUBLIC,
    "corridor": BAND_CORRIDOR, "passage": BAND_CORRIDOR,
    # Deterministic service circulation spine (single-storey only):
    # keeps rear wet-core access realistic without changing room adjacency rules.
    "service_passage": BAND_GF_SLEEPING,
    "rear_passage":    BAND_REAR_SVC,
    "staircase": BAND_CORRIDOR,  # with corridor — entry connection, NBC adjacency
    "staircase_landing": BAND_CORRIDOR,
    "kitchen": BAND_SERVICE, "wet_kitchen": BAND_SERVICE, "dry_kitchen": BAND_SERVICE,
    "pooja_room": BAND_PUBLIC,   # NE: adjacent to living room north side (Vastu correct)
    "home_office": BAND_PUBLIC,  # N zone — quiet, natural light, Kubera/wealth (Vastu)
    "utility_room": BAND_REAR_SVC, "store_room": BAND_REAR_SVC,
    "servant_quarters": BAND_REAR_SVC,
    "common_bathroom": BAND_REAR_SVC, "guest_powder_room": BAND_REAR_SVC,
    "bathroom": BAND_REAR_SVC,
    "balcony": BAND_REAR, "terrace": BAND_REAR,
}

_BAND_F1: Dict[str, int] = {
    "family_lounge": BAND_PUBLIC,  # front of FF, compact lounge
    # Quiet work / homework room on upper floor — same social band as lounge (real duplex practice)
    "home_office": BAND_PUBLIC,
    "corridor": BAND_CORRIDOR, "passage": BAND_CORRIDOR,
    "staircase_landing": BAND_CORRIDOR, "staircase": BAND_CORRIDOR,
    "master_bedroom": BAND_BEDROOMS, "parents_bedroom": BAND_BEDROOMS,
    "bedroom": BAND_BEDROOMS, "guest_bedroom": BAND_BEDROOMS,
    "terrace": BAND_REAR, "balcony": BAND_REAR,
}


def _placement_band(cat: str, floor_index: int, floors: int) -> int:
    """
    Vertical band id for an independent room. Single-storey GF bedrooms use
    BAND_GF_SLEEPING so they never share one strip with toilets/utility only.

    Single-storey GF: dining_room sits in BAND_SERVICE with kitchens so the meal
    zone is one compositional strip (dining backs kitchens — realistic service).
    """
    if floor_index == 0 and floors <= 1 and cat in _GF_SLEEPING_CATS:
        return BAND_GF_SLEEPING
    if floor_index == 0 and floors <= 1 and cat == "dining_room":
        return BAND_SERVICE
    bmap = _BAND_F0 if floor_index == 0 else _BAND_F1
    return bmap.get(cat, BAND_REAR_SVC if floor_index == 0 else BAND_BEDROOMS)


def _gf_band_stack_order(floor_index: int, floors: int, occupied_ids: List[int]) -> List[int]:
    """
    Front → rear (screen Y increasing): single-storey GF stacks meal cluster directly
    under the social band so foyer→living→dining/kitchen reads as one arrival sequence,
    then corridor, bedrooms, wet core. Multi-storey / FF uses numeric sort.
    """
    if floor_index != 0 or floors > 1:
        return sorted(occupied_ids)
    priority = (
        BAND_ENTRANCE,
        BAND_PUBLIC,
        BAND_SERVICE,
        BAND_CORRIDOR,
        BAND_GF_SLEEPING,
        BAND_REAR_SVC,
        BAND_REAR,
    )
    ordered = [k for k in priority if k in occupied_ids]
    tail = sorted(k for k in occupied_ids if k not in ordered)
    return ordered + tail


def _get_band(cat: str, fl: int) -> int:
    """Legacy signature — assumes multi-storey if unknown; prefer _placement_band."""
    return _placement_band(cat, fl, floors=2)


# ─── CIRCULATION ORDER (within same column) ───────────────────────────────────
# Indian practice: public approach → social core → service rear; no bedroom off parking.
# Lower value = earlier in visit path, placed toward front/left in band scan order.
_CIRCULATION_RANK: Dict[str, int] = {
    "car_porch": 0,
    "sit_out": 5,
    "foyer": 10,
    "entrance_foyer": 10,
    "guest_powder_room": 12,
    "drawing_room": 17,
    "living_room": 20,
    "pooja_room": 22,
    "family_lounge": 24,
    "home_office": 26,
    "dining_room": 30,
    "kitchen": 40,
    "wet_kitchen": 41,
    "dry_kitchen": 42,
    "corridor": 48,
    "staircase": 46,
    "passage": 49,
    "service_passage": 49,
    "rear_passage": 61,
    "staircase_landing": 47,
    "utility_room": 60,
    "common_bathroom": 62,
    "bathroom": 63,
    "guest_bedroom": 35,
    "guest_room": 35,
    "master_bedroom": 70,
    "parents_bedroom": 71,
    "bedroom": 72,
    "servant_quarters": 85,
    "store_room": 80,
    "terrace": 15,
    "balcony": 18,
}


def _circulation_rank(cat: str) -> int:
    return _CIRCULATION_RANK.get(cat, 50)


# Ground-floor PUBLIC band: formal drawing first after foyer (visitor path), then living,
# then pooja — avoids living blocking the drawing–prayer sequence in plan view.
_GF_PUBLIC_FLOW_RANK: Dict[str, int] = {
    "drawing_room":  17,
    "living_room":   18,
    "pooja_room":    19,
    "home_office":   24,
    "dining_room":   28,
}


def _flow_rank(cat: str, band_id: Optional[int], floor_index: int) -> int:
    if band_id == BAND_PUBLIC and floor_index == 0:
        if cat in _GF_PUBLIC_FLOW_RANK:
            return _GF_PUBLIC_FLOW_RANK[cat]
    return _circulation_rank(cat)


def _luxury_corridor_cap_ft(parsed: Dict[str, Any]) -> float:
    """Allow deeper corridor strips only when brief asks for premium/courtyard programmes."""
    bps = int(parsed.get("budget_per_sqft", 0) or 0)
    budget = int(parsed.get("budget", 0) or 0)
    spatial = str(parsed.get("spatial_type") or "").lower()
    if spatial == "courtyard":
        return 7.5
    if bps >= 15000 or budget >= 20_000_000:
        return 7.0
    if bps >= 10000 or budget >= 8_000_000:
        return 6.5
    return 5.5


def _effective_corridor_width_ft(parsed: Dict[str, Any], raw: float, warns: List[str]) -> float:
    """
    Cap oversized corridor_depth_ft from the LLM — reduces dead hallway strips while
    honouring NBC-ish minimum (~4ft clear). Premium tiers keep wider allowances.
    """
    w = max(4.0, float(raw or 4.0))
    cap = _luxury_corridor_cap_ft(parsed)
    if w > cap:
        warns.append(
            f"CIRCULATION: corridor depth trimmed from {raw}ft to {cap}ft "
            f"(spine stays code-compliant; widen via budget tier or spatial_type=courtyard)."
        )
        return cap
    return w


def _experience_hints(cat: str, layout_band: int, facing: str) -> Dict[str, str]:
    """Lightweight cues for SVG/editor/scoring — no geometry change."""
    facing = (facing or "east").lower()
    tier = "standard"
    role = "support"

    if cat in ("living_room", "drawing_room"):
        tier = "primary_social"
        role = "movement_organiser"
    elif cat == "dining_room":
        tier = "social_daylight"
        role = "kitchen_anchor"
    elif cat in ("foyer", "entrance_foyer"):
        tier = "transitional"
        role = "privacy_filter"
    elif cat == "family_lounge":
        tier = "secondary_social"
        role = "bedroom_preface"
    elif cat in ("corridor", "passage"):
        tier = "borrowed_light"
        role = "spine_connector"
    elif cat == "staircase":
        tier = "borrowed_light"
        role = "vertical_link"
    elif cat in ("kitchen", "wet_kitchen", "dry_kitchen"):
        tier = "cross_vent_priority"
        role = "service_core"
    elif cat in ("master_bedroom", "parents_bedroom", "bedroom", "guest_bedroom"):
        tier = "sleeping_daylight"
        role = "private_suite" if cat == "master_bedroom" else "private_sleeping"
    elif cat in ("utility_room", "store_room"):
        tier = "service_opening"
        role = "wet_adjacency"
    elif cat in ("bathroom", "common_bathroom", "guest_powder_room"):
        tier = "mechanical_vent"
        role = "wet_zone"

    # Facing-aware nudge (South Asian preference: habitable north/east light when front faces east)
    aspect_hint = "dual_aspect_desirable" if cat in (
        "living_room", "drawing_room", "dining_room", "family_lounge",
    ) else "single_aspect_ok"

    return {
        "daylight_tier": tier,
        "circulation_role": role,
        "aspect_hint": aspect_hint,
        "plot_facing": facing,
    }


# Indian residential zoning (privacy gradient) — for JSON / scoring / UX
_PUBLIC = {"car_porch", "sit_out", "foyer", "entrance_foyer", "living_room", "drawing_room"}
_SEMI = {"dining_room", "pooja_room", "family_lounge"}
_PRIVATE = {"master_bedroom", "parents_bedroom", "bedroom", "guest_bedroom",
            "guest_room", "home_office", "study"}
_SERVICE = {"kitchen", "wet_kitchen", "dry_kitchen", "utility_room", "store_room",
              "servant_quarters", "common_bathroom", "guest_powder_room", "bathroom"}
_CIRCULATION = {"corridor", "passage", "staircase", "staircase_landing"}

def _functional_zone(cat: str) -> str:
    if cat in _PUBLIC:
        return "public"
    if cat in _SEMI:
        return "semi_private"
    if cat in _PRIVATE:
        return "private"
    if cat in _SERVICE:
        return "service"
    if cat in _CIRCULATION:
        return "circulation"
    if cat in {"terrace", "balcony"}:
        return "semi_private"
    if cat == "walk_in_wardrobe":
        return "private"
    return "service"


# ─── VASTU SIDE ORDERING ─────────────────────────────────────────────────────

def _vastu_side(cat: str, facing: str) -> int:
    """0=left(north), 1=center, 2=right(south) for east-facing."""
    if facing in ("east", "unknown"):
        L = {"pooja_room","common_bathroom","guest_powder_room","parents_bedroom",
             "guest_bedroom","home_office","family_lounge","sit_out","bedroom"}
        R = {"kitchen","wet_kitchen","dry_kitchen","master_bedroom",
             "servant_quarters","car_porch","utility_room"}
    elif facing == "north":
        L = {"car_porch","servant_quarters","master_bedroom","utility_room","store_room"}
        R = {"pooja_room","kitchen","wet_kitchen","guest_bedroom","common_bathroom"}
    elif facing == "west":
        L = {"kitchen","wet_kitchen","master_bedroom","servant_quarters"}
        R = {"pooja_room","common_bathroom","guest_bedroom","parents_bedroom"}
    else:
        L = {"kitchen","wet_kitchen","servant_quarters"}
        R = {"pooja_room","common_bathroom","master_bedroom"}
    if cat in L: return 0
    if cat in R: return 2
    return 1


# ─── AREA BUDGET ─────────────────────────────────────────────────────────────

def _indian_program_minimums(cat: str, bua_sqft: float, plot_width_ft: float) -> Tuple[float, float, float]:
    """
    Indian residential credibility floors vs built-up envelope (single-storey biased).
    Returns (min_area_sqft, min_width_ft, min_depth_ft). Zeros mean skip that axis beyond area math.
    """
    tight = bua_sqft < 1050.0
    narrow_plot = plot_width_ft < 32.0

    if cat == "kitchen":
        ma = 70.0 if (tight or narrow_plot) else 82.0
        return (ma, 8.5 if narrow_plot else 9.0, 8.0 if tight else 8.5)
    if cat == "dry_kitchen":
        return (52.0, 7.0, 7.0)
    if cat == "wet_kitchen":
        return (44.0, 6.5, 7.0)
    if cat == "pooja_room":
        return (44.0, 6.5, 6.5)
    if cat == "dining_room":
        return ((68.0 if tight else 78.0), 9.5 if narrow_plot else 10.0, 7.5 if tight else 8.5)
    if cat == "living_room":
        return (max(115.0, min(260.0, bua_sqft * 0.125)), 11.5 if narrow_plot else 12.5, 10.5)
    if cat == "drawing_room":
        return (max(105.0, min(240.0, bua_sqft * 0.105)), 11.5 if narrow_plot else 12.5, 10.0)
    if cat in ("foyer",):
        return (44.0, 7.5 if narrow_plot else 8.5, 5.5)
    if cat == "sit_out":
        return (44.0, 7.5, 6.0)
    if cat == "car_porch":
        return (max(105.0, bua_sqft * 0.085), 10.5, 10.0)
    if cat == "utility_room":
        return (38.0, 6.5, 6.0)
    if cat == "store_room":
        return (28.0, 5.5, 5.5)
    if cat == "common_bathroom":
        return (34.0, 5.5, 6.5)
    if cat == "guest_powder_room":
        return (26.0, 5.0, 6.0)
    if cat == "master_bedroom":
        # Keep master suite slightly dominant over secondary bedrooms.
        return (100.0 if tight else 108.0, 10.5, 9.5)
    if cat in ("parents_bedroom", "bedroom", "guest_bedroom"):
        return (90.0, 9.5, 9.0)
    if cat == "home_office":
        return (60.0, 8.5, 8.0)
    if cat == "family_lounge":
        return (88.0, 9.5, 9.0)
    return (0.0, 0.0, 0.0)


def _enforce_indian_program_targets(
    rooms: List[Dict[str, Any]],
    bua_sqft: float,
    plot_width_ft: float,
    warns: List[str],
    *,
    warn_on_touch: bool = True,
    min_scale: float = 1.0,
) -> List[Dict[str, Any]]:
    """
    Lift shrunken programme sizes toward Indian norms before/after area budgeting.
    Placement stays on the flush grid — only target width/depth/area annotations change.
    """
    skip = frozenset({
        "corridor", "passage", "staircase", "staircase_landing",
        "terrace", "balcony",
    })
    sf = max(0.65, min(1.0, float(min_scale or 1.0)))
    out: List[Dict[str, Any]] = []
    touched = False
    for r in rooms:
        cat = _cat(str(r.get("name", "")), r)
        if cat in skip:
            out.append(r)
            continue
        min_a, min_w, min_d = _indian_program_minimums(cat, bua_sqft, plot_width_ft)
        if min_a <= 0:
            out.append(r)
            continue
        # Under severe programme pressure, relax minima proportionally instead of
        # forcing impossible dimensions that make the final plan look stretched.
        if sf < 0.999:
            min_a *= sf
            min_w *= sf
            min_d *= sf
        # Absolute livability floors during compact-fit mode.
        # Keeps rooms usable without changing band topology/alignment rules.
        LIVABLE_FLOOR: Dict[str, Tuple[float, float]] = {
            "kitchen": (6.5, 6.5),
            "dry_kitchen": (5.0, 6.0),
            "wet_kitchen": (5.0, 6.0),
            "dining_room": (7.5, 7.0),
            "pooja_room": (5.0, 5.0),
            "master_bedroom": (9.0, 9.0),
            "bedroom": (8.5, 8.5),
            "parents_bedroom": (8.5, 8.5),
            "guest_bedroom": (8.5, 8.5),
            "common_bathroom": (4.5, 6.0),
            "guest_powder_room": (4.5, 5.0),
            "utility_room": (5.5, 5.5),
            "store_room": (4.5, 4.5),
        }
        lw, ld = LIVABLE_FLOOR.get(cat, (0.0, 0.0))
        min_w = max(min_w, lw)
        min_d = max(min_d, ld)

        w0, d0 = _dims(r)
        a0 = float(r.get("area_sqft") or 0) or (w0 * d0)

        short = (a0 + 1.0 < min_a) or (min_w > 0 and w0 + 0.1 < min_w) or (min_d > 0 and d0 + 0.1 < min_d)
        if not short:
            out.append(r)
            continue

        ar = max(w0 / max(d0, 0.1), 0.55)
        w_t = max(w0, min_w)
        d_t = max(d0, min_d)
        if w_t * d_t < min_a:
            w_t = max(w_t, math.sqrt(min_a * ar))
            d_t = max(min_d, min_a / max(w_t, 0.01))
            if w_t * d_t < min_a:
                w_t = min_a / max(d_t, min_d)
        # Final nudge if still under min area
        if w_t * d_t < min_a:
            d_t = min_a / max(w_t, 0.01)

        r2 = dict(r)
        r2["width_ft"] = round(max(w_t, min_w), 2)
        r2["depth_ft"] = round(max(d_t, min_d), 2)
        r2["area_sqft"] = round(float(r2["width_ft"]) * float(r2["depth_ft"]), 1)
        touched = True
        out.append(r2)

    if touched and warn_on_touch:
        warns.append(
            "PROGRAMME: room sizes lifted toward Indian residential minimums "
            f"(built-up ~{bua_sqft:.0f} sqft, plot ~{plot_width_ft:.0f} ft wide)."
        )
    return out


def _ensure_master_dominance(
    rooms: List[Dict[str, Any]],
    floor_index: int,
    warns: List[str],
) -> List[Dict[str, Any]]:
    """
    Ensure master bedroom is slightly larger than other independent bedrooms.
    Geometry/connectivity is unchanged; only size targets are nudged.
    """
    if floor_index != 0:
        return rooms
    out = [dict(r) for r in rooms]
    master_idx = -1
    secondaries: List[int] = []
    for i, r in enumerate(out):
        c = _cat(str(r.get("name", "")), r)
        if c == "master_bedroom":
            master_idx = i
        elif c in ("bedroom", "parents_bedroom", "guest_bedroom"):
            secondaries.append(i)
    if master_idx < 0 or not secondaries:
        return out

    m = out[master_idx]
    mw, md = _dims(m)
    ma = float(m.get("area_sqft") or (mw * md))
    sec_areas = [float(out[i].get("area_sqft") or (_dims(out[i])[0] * _dims(out[i])[1])) for i in secondaries]
    max_sec = max(sec_areas) if sec_areas else 0.0

    # "Little bigger": at least +8 sqft and +6% over largest secondary.
    req_area = max(max_sec + 8.0, max_sec * 1.06, 96.0)
    if ma + 0.5 >= req_area:
        return out

    ar = max(mw / max(md, 0.1), 0.75)
    nw = max(mw, math.sqrt(req_area * ar))
    nd = max(md, req_area / max(nw, 0.01))
    m["width_ft"] = round(nw, 2)
    m["depth_ft"] = round(nd, 2)
    m["area_sqft"] = round(float(m["width_ft"]) * float(m["depth_ft"]), 1)
    out[master_idx] = m
    warns.append("PROGRAMME: master bedroom nudged slightly larger than secondary bedrooms.")
    return out


def _programme_fit_scale(rooms: List[Dict[str, Any]], budget_sqft: float) -> float:
    """
    Adaptive minimum-size relaxation factor based on programme pressure.
    1.0 means no relaxation. Floors at 0.65 to retain habitability.
    """
    budget_sqft = max(float(budget_sqft or 0.0), 1.0)
    total = sum(float(r.get("area_sqft") or 0.0) for r in rooms)
    if total <= budget_sqft * 1.05:
        return 1.0
    fit = budget_sqft / max(total, 1.0)
    # Smooth response: mild pressure -> tiny relax, heavy pressure -> stronger relax.
    return max(0.72, min(1.0, fit ** 0.45))


def _hybrid_suite_service_merge(
    rooms: List[Dict[str, Any]],
    budget_sqft: float,
    warns: List[str],
) -> List[Dict[str, Any]]:
    """
    Hybrid strategy for tight shells:
    - keep placement/connectivity model unchanged
    - reduce only redundant/mergeable service rooms before band placement
    """
    out = list(rooms)
    if not out:
        return out

    total = sum(float(r.get("area_sqft") or 0.0) for r in out)
    pressure = total / max(float(budget_sqft or 1.0), 1.0)
    has_master = any(_cat(str(r.get("name", "")), r) == "master_bedroom" for r in out)
    if not has_master or pressure <= 1.18:
        return out

    # 1) Remove duplicate stores first (common LLM duplication: "store" + "store_room").
    stores = [(i, r) for i, r in enumerate(out) if _cat(str(r.get("name", "")), r) == "store_room"]
    if len(stores) > 1:
        stores_sorted = sorted(stores, key=lambda t: float(t[1].get("area_sqft") or 0.0), reverse=True)
        keep_idx = stores_sorted[0][0]
        drop_idxs = {idx for idx, _ in stores_sorted[1:]}
        out2: List[Dict[str, Any]] = []
        for i, r in enumerate(out):
            if i in drop_idxs:
                continue
            out2.append(r)
        out = out2
        warns.append(
            "HYBRID FIT: merged duplicate store spaces to protect master suite usability "
            "(connectivity unchanged)."
        )

    # 2) If still highly pressured, merge utility/store programme by dropping smaller one.
    total2 = sum(float(r.get("area_sqft") or 0.0) for r in out)
    pressure2 = total2 / max(float(budget_sqft or 1.0), 1.0)
    if pressure2 > 1.28:
        service_candidates: List[Tuple[int, Dict[str, Any], str]] = []
        for i, r in enumerate(out):
            c = _cat(str(r.get("name", "")), r)
            if c in ("utility_room", "store_room"):
                service_candidates.append((i, r, c))
        if len(service_candidates) >= 2:
            drop_i, drop_r, drop_c = sorted(
                service_candidates,
                key=lambda t: float(t[1].get("area_sqft") or 0.0)
            )[0]
            out = [r for i, r in enumerate(out) if i != drop_i]
            warns.append(
                f"HYBRID FIT: compact service merge removed one {drop_c} under tight shell "
                "(room graph alignment/connectivity preserved)."
            )

    return out


def _bump_gf_sleeping_targets(
    rooms: List[Dict[str, Any]],
    floors: int,
    floor_index: int,
    warns: List[str],
) -> List[Dict[str, Any]]:
    """
    Lift unrealistically small bedroom programmes on single-storey plots before
    area budgeting — avoids ~65 sqft cells when the brief implies habitable rooms.
    """
    if floor_index != 0 or int(floors or 1) > 1:
        return rooms
    min_area = 90.0  # sqft — aligned with _enforce_indian_program_targets sleeping floor
    out: List[Dict[str, Any]] = []
    touched = False
    for r in rooms:
        cat = _cat(str(r.get("name", "")), r)
        if cat not in _GF_SLEEPING_CATS:
            out.append(r)
            continue
        area = float(r.get("area_sqft") or 0)
        if area >= min_area:
            out.append(r)
            continue
        w_ft, d_ft = _dims(r)
        ar = max(w_ft / max(d_ft, 0.1), 0.65)
        new_d = math.sqrt(min_area / max(ar, 0.1))
        new_w = min_area / max(new_d, 0.1)
        r2 = dict(r)
        r2["area_sqft"] = round(min_area, 1)
        r2["width_ft"] = round(new_w, 2)
        r2["depth_ft"] = round(new_d, 2)
        touched = True
        out.append(r2)
    if touched:
        warns.append(
            "PROGRAMME: ground-floor bedroom areas lifted toward ~90+ sqft "
            "(single-storey; avoids unrealistically small sleeping cells)."
        )
    return out


def _budget_check(rooms: List[Dict], bw_ft: float, bh_ft: float, warns: List[str]) -> List[Dict]:
    budget = bw_ft * bh_ft
    total  = sum(float(r.get("area_sqft") or 0) for r in rooms)
    # Slightly looser shell so habitability lifts survive; second pass re-enforces mins
    if total <= budget * 1.22:
        return rooms
    ratio = (budget * 0.92) / max(total, 1.0)
    warns.append(f"AREA BUDGET: {total:.0f}sqft in {budget:.0f}sqft. Scale {ratio:.2f}.")
    sf = math.sqrt(ratio)
    result = []
    for r in rooms:
        r2 = dict(r)
        w, d = _dims(r)
        r2["area_sqft"] = round(float(r.get("area_sqft") or 0) * ratio, 1)
        r2["width_ft"]  = round(w * sf, 2)
        r2["depth_ft"]  = round(d * sf, 2)
        result.append(r2)
    return result


# ─── BAND HEIGHT COMPUTATION ─────────────────────────────────────────────────

def _room_band_depth(r: Dict, cat: str, corridor_w: float) -> float:
    """
    Depth a room contributes to band height calculation.
    Key rules:
    - corridor/passage: use corridor_width (not depth_ft which is the run length)
    - staircase_landing: use width_ft (compact square-ish void)
    - living_room, dining_room, family_lounge: cap at _MAX_BAND_DRIVER_DEPTH
    - all others: use depth_ft
    """
    w_ft, d_ft = _dims(r)
    nbc_w, nbc_d = _nbc(cat)
    if cat in ("corridor", "passage"):
        return max(corridor_w, nbc_d) * SCALE
    if cat == "staircase_landing":
        return max(w_ft, 5.0) * SCALE
    # Apply depth cap for rooms that would balloon the band
    cap = _MAX_BAND_DRIVER_DEPTH.get(cat)
    if cap:
        d_ft = min(d_ft, cap)
    return max(d_ft, nbc_d) * SCALE


def _band_heights(
    bands: Dict[int, List[Dict]],
    built_h: float,
    corridor_w: float,
    warns: List[str],
    spatial_mods: Dict[int, float] = None,
    compact_gf_front: bool = False,
) -> Dict[int, float]:
    # Band height minimums (Guide Ch.5 + Ch.11 Fix 5)
    # CORRIDOR: NEVER compress below 5ft (NBC 2016 mandatory)
    # BAND_REAR: terrace minimum 12ft for usable outdoor space
    HARD_MIN: Dict[int, float] = {
        BAND_CORRIDOR: max(corridor_w * SCALE, 50.0),  # absolute — never compress
    }
    MIN: Dict[int, float] = {
        # Slightly shallower entrance strip on single-storey GF reduces “dead” foyer stack
        BAND_ENTRANCE: 85.0 if compact_gf_front else 100.0,
        BAND_PUBLIC:   110.0,
        BAND_CORRIDOR:  max(corridor_w * SCALE, 50.0),  # 5ft NBC minimum
        BAND_GF_SLEEPING: 115.0,
        BAND_SERVICE:   95.0,
        BAND_REAR_SVC:  80.0,
        BAND_BEDROOMS: 120.0,
        BAND_REAR:     120.0,  # terrace min 12ft (Guide Ch.11 Fix 5, Ch.5)
    }
    raw: Dict[int, float] = {}
    has_master_gf = any(
        _cat(str(r.get("name", "")), r) == "master_bedroom"
        for r in bands.get(BAND_GF_SLEEPING, [])
    )
    has_rear_wet = any(
        _cat(str(r.get("name", "")), r) in ("common_bathroom", "guest_powder_room", "bathroom")
        for r in bands.get(BAND_REAR_SVC, [])
    )
    for bid, rooms in bands.items():
        if not rooms:
            continue
        max_d = max(
            _room_band_depth(r, _cat(str(r.get("name","")), r), corridor_w)
            for r in rooms
        )
        raw[bid] = max(max_d, MIN.get(bid, 70.0))

    # Apply spatial_type band modifications (set by GPT in Call 1)
    if spatial_mods:
        for bid, mult in spatial_mods.items():
            if bid in raw:
                raw[bid] = max(raw[bid] * mult, MIN.get(bid, 60.0))

    if not raw:
        return {}

    total = sum(raw.values())
    # ── CORRIDOR: hard-lock to exact corridor_width, never compress ────────────
    if BAND_CORRIDOR in raw:
        raw[BAND_CORRIDOR] = max(corridor_w * SCALE, 50.0)

    total = sum(raw.values())

    if total > built_h * 0.99:
        # COMPRESS: keep corridor locked, compress flexible bands proportionally
        hard_total = raw.get(BAND_CORRIDOR, 0.0)
        flex_bands = {k: v for k, v in raw.items() if k != BAND_CORRIDOR}
        flex_total = max(sum(flex_bands.values()), 1.0)
        flex_budget = max(built_h * 0.98 - hard_total, flex_total * 0.70)
        flex_ratio = flex_budget / flex_total
        for k in flex_bands:
            raw[k] = max(flex_bands[k] * flex_ratio, MIN.get(k, 60.0))
        if BAND_CORRIDOR in HARD_MIN:
            raw[BAND_CORRIDOR] = HARD_MIN[BAND_CORRIDOR]

    elif total < built_h * 0.95:
        # EXPAND: distribute remaining space to preferred bands
        # Priority: BEDROOMS (cap 18ft=180px), then REAR (cap 14ft=140px)
        remaining = built_h - total
        caps = {
            BAND_SERVICE: 175.0,
            BAND_GF_SLEEPING: 180.0,
            BAND_BEDROOMS: 180.0,
            BAND_REAR: 180.0,
        }
        for bid in [BAND_SERVICE, BAND_GF_SLEEPING, BAND_BEDROOMS, BAND_REAR]:
            if bid in raw and remaining > 0:
                cap = caps.get(bid, 999.0)
                can_add = max(0.0, min(remaining, cap - raw.get(bid, 0.0)))
                raw[bid] = raw.get(bid, MIN.get(bid, 70.0)) + can_add
                remaining -= can_add

    # Master-suite assist: if GF sleeping is too shallow, borrow a little from
    # corridor (while keeping 4'-0" circulation) so bedroom + WIC + bath remain usable.
    if BAND_GF_SLEEPING in raw and BAND_CORRIDOR in raw:
        has_master = any(
            _cat(str(r.get("name", "")), r) == "master_bedroom"
            for r in bands.get(BAND_GF_SLEEPING, [])
        )
        if has_master:
            min_sleep = 92.0  # ~9'-2" preferred compact master-suite slab
            if raw[BAND_GF_SLEEPING] < min_sleep and raw[BAND_CORRIDOR] > 40.0:
                give = min(min_sleep - raw[BAND_GF_SLEEPING], raw[BAND_CORRIDOR] - 40.0)
                if give > 0.1:
                    raw[BAND_GF_SLEEPING] += give
                    raw[BAND_CORRIDOR] -= give
                    warns.append(
                        "MASTER SUITE: borrowed a small depth from corridor band "
                        "to keep bedroom + attached suite usable."
                    )
            # If still shallow, borrow from less-critical bands (without breaking connectivity).
            donors = [
                (BAND_REAR_SVC, 36.0),
                (BAND_SERVICE, 42.0),
                (BAND_PUBLIC, 54.0),
            ]
            for db, floor_px in donors:
                if raw[BAND_GF_SLEEPING] >= min_sleep:
                    break
                if db not in raw:
                    continue
                spare = raw[db] - floor_px
                if spare <= 0.1:
                    continue
                take = min(min_sleep - raw[BAND_GF_SLEEPING], spare)
                raw[db] -= take
                raw[BAND_GF_SLEEPING] += take
            if raw[BAND_GF_SLEEPING] < min_sleep:
                warns.append(
                    "MASTER SUITE: shell is very tight; applied best-effort depth balancing."
                )

    # Rear wet-core assist: keep common toilet/bath practical at rear under tight shells.
    if has_rear_wet and BAND_REAR_SVC in raw:
        min_rear_wet = 60.0  # ~6'-0" target for common bath usability
        if raw[BAND_REAR_SVC] < min_rear_wet:
            need = min_rear_wet - raw[BAND_REAR_SVC]
            donors = [
                (BAND_SERVICE, 42.0),
                (BAND_PUBLIC, 54.0),
                (BAND_GF_SLEEPING, 80.0 if has_master_gf else 70.0),
            ]
            for db, floor_px in donors:
                if need <= 0.1:
                    break
                if db not in raw:
                    continue
                spare = raw[db] - floor_px
                if spare <= 0.1:
                    continue
                take = min(spare, need)
                raw[db] -= take
                raw[BAND_REAR_SVC] += take
                need -= take
            if need <= 0.1:
                warns.append(
                    "REAR WET CORE: depth balanced to keep common toilet/bath connected and usable."
                )

    # Final shell-fit guard: never let summed band heights exceed built-up height.
    # Prevents stretched-looking plans when programme pressure is very high.
    tot_final = sum(raw.values())
    if tot_final > built_h * 1.001:
        ratio = built_h / max(tot_final, 1.0)
        SOFT_FLOOR = {
            BAND_CORRIDOR: 40.0,   # keep minimum practical circulation (4'-0")
            BAND_ENTRANCE: 42.0,
            BAND_PUBLIC: 56.0,
            BAND_SERVICE: 42.0,
            BAND_GF_SLEEPING: 52.0,
            BAND_REAR_SVC: 52.0 if has_rear_wet else 38.0,
            BAND_BEDROOMS: 52.0,
            BAND_REAR: 48.0,
        }
        for k in list(raw.keys()):
            raw[k] = max(raw[k] * ratio, SOFT_FLOOR.get(k, 32.0))
        tot2 = sum(raw.values())
        if tot2 > built_h * 1.001:
            # Keep corridor practical; keep compact master-suite slab when present.
            hard_corr = 40.0 if BAND_CORRIDOR in raw else 0.0
            hard_sleep = 80.0 if (has_master_gf and BAND_GF_SLEEPING in raw) else 0.0
            hard_rear_wet = 52.0 if (has_rear_wet and BAND_REAR_SVC in raw) else 0.0
            if BAND_CORRIDOR in raw:
                raw[BAND_CORRIDOR] = max(raw[BAND_CORRIDOR], hard_corr)
            if BAND_GF_SLEEPING in raw and hard_sleep > 0.0:
                raw[BAND_GF_SLEEPING] = max(raw[BAND_GF_SLEEPING], hard_sleep)
            if BAND_REAR_SVC in raw and hard_rear_wet > 0.0:
                raw[BAND_REAR_SVC] = max(raw[BAND_REAR_SVC], hard_rear_wet)
            protected = {BAND_CORRIDOR}
            if hard_sleep > 0.0:
                protected.add(BAND_GF_SLEEPING)
            if hard_rear_wet > 0.0:
                protected.add(BAND_REAR_SVC)
            flex_keys = [k for k in raw.keys() if k not in protected]
            flex_total = sum(raw[k] for k in flex_keys)
            flex_budget = max(built_h - hard_corr - hard_sleep - hard_rear_wet, 1.0)
            ratio2 = min(1.0, flex_budget / max(flex_total, 1.0))
            for k in flex_keys:
                raw[k] *= ratio2
        warns.append(
            "SHELL FIT: band stack compressed to stay within built-up envelope "
            "(alignment preserved; avoids stretched output)."
        )

    # Final master-suite floor: if still too shallow, rebalance from donors.
    if has_master_gf and BAND_GF_SLEEPING in raw and raw[BAND_GF_SLEEPING] < 80.0:
        need = 80.0 - raw[BAND_GF_SLEEPING]
        donors = [
            (BAND_REAR_SVC, 34.0),
            (BAND_SERVICE, 40.0),
            (BAND_PUBLIC, 50.0),
        ]
        for db, floor_px in donors:
            if need <= 0.1:
                break
            if db not in raw:
                continue
            spare = raw[db] - floor_px
            if spare <= 0.1:
                continue
            take = min(spare, need)
            raw[db] -= take
            raw[BAND_GF_SLEEPING] += take
            need -= take
        if need <= 0.1:
            warns.append(
                "MASTER SUITE: final depth balancing applied for attached bath/WIC usability."
            )

    return raw


# ─── ROOM PLACEMENT IN BAND ───────────────────────────────────────────────────


def _tail_min_width_px(room: Dict) -> float:
    cat = _cat(str(room.get("name", "")), room)
    if cat in ("service_passage", "rear_passage", "passage"):
        return 18.0
    return max(_nbc(cat)[0] * SCALE * 0.80, 20.0)


def _is_staircase_landing_dict(r: Dict) -> bool:
    n = str(r.get("name", "")).lower()
    if "staircase_landing" in n or "stair_void" in n:
        return True
    return _cat(str(r.get("name", "")), r) == "staircase_landing"


def _align_staircase_landing_to_ground_axis(
    results: List[Tuple[Dict, Rect]],
    band_id: Optional[int],
    bx: float,
    tinset: float,
    avail_w: float,
    warns: List[str],
) -> List[Tuple[Dict, Rect]]:
    """
    For G+1+, snap first-floor staircase_landing to the same horizontal axis as the
    ground-floor staircase (parsed __staircase_anchor_* from visual_floor_plan).
    Remaining circulation rooms in the band fill the rest of the width without overlap.
    """
    if band_id != BAND_CORRIDOR or not results:
        return results
    left = bx + tinset
    right_edge = left + avail_w

    idx_land: Optional[int] = None
    for i, (r, _) in enumerate(results):
        if not _is_staircase_landing_dict(r):
            continue
        if r.get("__staircase_anchor_x_px") is None:
            continue
        idx_land = i
        break
    if idx_land is None:
        return results
    if idx_land > 0:
        warns.append(
            "STAIR_AXIS: skipped landing anchor (staircase_landing not leading cell in band)"
        )
        return results

    r_land, rect_land = results[idx_land]
    ax = float(r_land["__staircase_anchor_x_px"])
    aw_raw = r_land.get("__staircase_anchor_w_px")
    anchor_w = float(aw_raw) if aw_raw is not None else rect_land.w

    tail = list(results[idx_land + 1 :])
    min_tail = sum(_tail_min_width_px(r) for r, _ in tail) if tail else 0.0
    min_land = max(_nbc("staircase")[0] * SCALE * 0.80, 20.0)

    w_land = max(min(anchor_w, avail_w - min_tail), min_land)
    if w_land > avail_w - min_tail + 0.01:
        w_land = max(avail_w - min_tail, min_land)

    x_min = left
    x_max = right_edge - w_land - min_tail
    if x_max < x_min - 0.01:
        warns.append(
            "STAIR_AXIS: anchor does not fit circulation band; using left edge"
        )
        x_land = x_min
        w_land = min(max(w_land, min_land), avail_w - min_tail)
    else:
        x_land = min(max(ax, x_min), x_max)
    if abs(x_land - ax) > 1.0:
        warns.append(
            "STAIR_AXIS: landing nudged to fit corridor min width while tracking ground stair "
            f"(anchor x≈{ax:.0f}px → {x_land:.0f}px)."
        )

    new_land = Rect(x_land, rect_land.y, w_land, rect_land.h)
    out: List[Tuple[Dict, Rect]] = results[:idx_land] + [(r_land, new_land)]
    x_cursor = x_land + w_land
    rem = right_edge - x_cursor
    if rem < 0.5:
        warns.append("STAIR_AXIS: no width left after landing snap; keeping prior layout")
        return results
    if not tail:
        return out

    orig_ws = [max(rect.w, _tail_min_width_px(r)) for r, rect in tail]
    total_ow = sum(orig_ws)
    new_tail: List[Tuple[Dict, Rect]] = []
    if total_ow <= 0.01:
        piece = rem / len(tail)
        for r, rect in tail:
            nw = max(piece, _tail_min_width_px(r))
            new_tail.append((r, Rect(x_cursor, rect.y, nw, rect.h)))
            x_cursor += nw
    else:
        for k, ((r, rect), ow) in enumerate(zip(tail, orig_ws)):
            if k < len(tail) - 1:
                nw = max(rem * (ow / total_ow), _tail_min_width_px(r))
            else:
                nw = max(right_edge - x_cursor, _tail_min_width_px(r))
            new_tail.append((r, Rect(x_cursor, rect.y, nw, rect.h)))
            x_cursor += nw
    drift = right_edge - x_cursor
    if abs(drift) > 0.25 and new_tail:
        lr, lrect = new_tail[-1]
        new_tail[-1] = (lr, Rect(lrect.x, lrect.y, lrect.w + drift, lrect.h))
    return out + new_tail


# These rooms fill their band's full height (primary habitable rooms)
_FILL_H = {
    "drawing_room", "living_room", "master_bedroom", "parents_bedroom",
    "bedroom", "guest_bedroom", "kitchen", "wet_kitchen", "dry_kitchen",
    "servant_quarters", "family_lounge",
    "terrace", "balcony",   # fill BAND_REAR height (Guide Ch.5 — terrace ≥12ft)
    "service_passage", "rear_passage",
}

# Rooms that fill the FULL BAND WIDTH when alone (lounge/open spaces)
_FILL_BAND_WIDTH = {"terrace", "balcony"}  # family_lounge removed — caps at its own width

def _place_band(
    rooms: List[Dict],
    bx: float, by: float, bw: float, bh: float,
    facing: str, corridor_w: float,
    warns: List[str],
    band_id: Optional[int] = None,
    floor_index: int = 0,
    spatial_type: str = "traditional",
) -> List[Tuple[Dict, Rect]]:
    if not rooms:
        return []

    # Flush tiling on the structural grid — rooms share boundaries (no phantom interior gaps).
    tinset = 0.0
    avail_w = max(bw - tinset * 2, 10.0)
    avail_h = max(bh - tinset * 2, 10.0)

    # Sort by compass-aware column side, then area descending.
    # Prefer __col_side from compass_engine (facing-aware, Vastu-correct).
    # Fall back to _vastu_side() if compass_engine wasn't available.
    _col_order = {"left": 0, "center": 1, "right": 2}

    def _key(r: Dict) -> Tuple[int, int, float]:
        c = _cat(str(r.get("name", "")), r)
        # Use compass_engine output (__col_side) if available — AI controls positioning
        col_side = r.get("__col_side")
        if col_side in _col_order:
            side_num = _col_order[col_side]
        else:
            side_num = _vastu_side(c, facing)  # fallback for rooms without zone
        cr = _flow_rank(c, band_id, floor_index)
        return (side_num, cr, -float(r.get("area_sqft") or 0))

    rooms_sorted = sorted(rooms, key=_key)

    # If only one room in band and it's a fill-width type, give it full band width
    if len(rooms_sorted) == 1:
        cat_single = _cat(str(rooms_sorted[0].get("name", "")), rooms_sorted[0])
        if cat_single in _FILL_BAND_WIDTH:
            # Fill full band height — use avail_h which reflects expanded band (Guide Ch.5)
            # This ensures terrace/balcony fill the full BAND_REAR allocation
            room_h = avail_h
            rect = Rect(bx + tinset, by + tinset, avail_w, room_h)
            _nbc_warn(rooms_sorted[0], rect, warns)
            return [(rooms_sorted[0], rect)]

    # Target widths (+ subtle social-zone bias for open-plan: living/dining breathe)
    targets = []
    _open = str(spatial_type or "").lower() == "open_plan"
    for r in rooms_sorted:
        cat = _cat(str(r.get("name", "")), r)
        w_ft, _ = _dims(r)
        nbc_w, _ = _nbc(cat)
        t = max(w_ft * SCALE, nbc_w * SCALE)
        if _open and band_id == BAND_PUBLIC and floor_index == 0 and cat in (
            "living_room", "drawing_room",
        ):
            t *= 1.05
        if _open and band_id == BAND_SERVICE and floor_index == 0 and cat in (
            "dining_room", "kitchen", "wet_kitchen", "dry_kitchen",
        ):
            t *= 1.03
        targets.append(t)

    # Cap targets to max room width BEFORE scaling (Guide Ch.11 Fix 3)
    targets = [min(t, _MAX_ROOM_WIDTH_PX.get(_cat(str(r.get("name","")) , r), 9999.0))
               for r, t in zip(rooms_sorted, targets)]
    total_w = sum(targets)
    # Scale widths to fill avail_w exactly (Guide Ch.4)
    if abs(total_w - avail_w) < 0.5:
        widths = list(targets)
    else:
        ratio  = avail_w / max(total_w, 1.0)
        widths = []
        for r, t in zip(rooms_sorted, targets):
            rcat = _cat(str(r.get("name", "")), r)
            nbc_w, _ = _nbc(rcat)
            widths.append(max(t * ratio, nbc_w * SCALE * 0.85))
        # Last room absorbs remainder — with NBC guard (Guide Ch.4)
        total_placed = sum(widths[:-1])
        last_cat = _cat(str(rooms_sorted[-1].get("name","")), rooms_sorted[-1])
        widths[-1] = max(avail_w - total_placed, _nbc(last_cat)[0] * SCALE * 0.90, 20.0)

    # ── NBC OVERFLOW GUARD: steal from widest if any room below NBC min ──────
    # Fixes Root Cause 3 (Guide Ch.15): overflow silently crushes last room
    for i in range(len(widths)):
        rcat    = _cat(str(rooms_sorted[i].get("name","")), rooms_sorted[i])
        nbc_min = _nbc(rcat)[0] * SCALE * 0.85
        if widths[i] < nbc_min:
            deficit = nbc_min - widths[i]
            widths[i] = nbc_min
            best_j, best_surplus = -1, 0.0
            for k in range(len(widths)):
                if k == i: continue
                kcat    = _cat(str(rooms_sorted[k].get("name","")) , rooms_sorted[k])
                kmin    = _nbc(kcat)[0] * SCALE * 0.85
                surplus = widths[k] - kmin - deficit
                if surplus > best_surplus:
                    best_surplus, best_j = surplus, k
            if best_j >= 0:
                widths[best_j] -= deficit

    # Absolute floor: no room ever < 2ft (20px) (Guide Ch.4)
    widths = [max(w, 20.0) for w in widths]

    # ── FINAL REBALANCE: ensure widths sum exactly to avail_w ─────────────────
    # The overflow guard may have changed individual widths. Recompute the last
    # room to absorb any floating-point drift (C5 fix from audit).
    # Robust fit: after all min/cap guards, widths can still sum > avail_w.
    # Enforce exact fit to prevent any room spilling outside built-up.
    if len(widths) > 1:
        cats = [_cat(str(r.get("name","")), r) for r in rooms_sorted]
        mins = [max(_nbc(c)[0] * SCALE * 0.80, 20.0) for c in cats]
        total = sum(widths)
        if total > avail_w + 0.5:
            # Shrink proportionally above minima.
            excess = total - avail_w
            slack = sum(max(w - m, 0.0) for w, m in zip(widths, mins))
            if slack > 0.1:
                for i in range(len(widths)):
                    reducible = max(widths[i] - mins[i], 0.0)
                    if reducible <= 0:
                        continue
                    take = excess * (reducible / slack)
                    widths[i] = max(widths[i] - take, mins[i])
            # Final snap: last absorbs remaining drift.
            drift = avail_w - sum(widths)
            widths[-1] = max(widths[-1] + drift, mins[-1])

        # Last room absorbs any remaining drift within its hard max.
        final_sum = sum(widths[:-1])
        last_cat_r = cats[-1]
        nbc_last_r = _nbc(last_cat_r)[0] * SCALE * 0.80
        _last_max = _MAX_ROOM_WIDTH_PX.get(last_cat_r, 9999.0)
        widths[-1] = min(max(avail_w - final_sum, nbc_last_r, 20.0), _last_max)

    # POST-SCALE HARD WIDTH CAP: enforce MAX_ROOM_WIDTH_PX after all scaling
    # This prevents single-room bands from expanding a room beyond its design width.
    for idx_w, (room_w, room_s) in enumerate(zip(widths, rooms_sorted)):
        cat_w = _cat(str(room_s.get("name","")), room_s)
        hard_max = _MAX_ROOM_WIDTH_PX.get(cat_w, 9999.0)
        if room_w > hard_max:
            widths[idx_w] = hard_max

    # FINAL HARD FIT: after any caps/rebalances, enforce exact sum(avail_w).
    if len(widths) > 1:
        cats = [_cat(str(r.get("name","")), r) for r in rooms_sorted]
        mins = [max(_nbc(c)[0] * SCALE * 0.80, 20.0) for c in cats]
        total = sum(widths)
        if total > avail_w + 0.25:
            excess = total - avail_w
            slack = sum(max(w - m, 0.0) for w, m in zip(widths, mins))
            if slack > 0.1:
                for i in range(len(widths)):
                    reducible = max(widths[i] - mins[i], 0.0)
                    if reducible <= 0:
                        continue
                    take = excess * (reducible / slack)
                    widths[i] = max(widths[i] - take, mins[i])
        # Snap remainder into last (and if last would go below min, steal from widest).
        drift = avail_w - sum(widths)
        widths[-1] += drift
        if widths[-1] < mins[-1]:
            need = mins[-1] - widths[-1]
            widths[-1] = mins[-1]
            # steal from widest room with slack
            j = max(range(len(widths)-1), key=lambda k: widths[k] - mins[k])
            widths[j] = max(widths[j] - need, mins[j])

    # ── Corridor + stair: prevent corridor swallowing the entire band width ─────
    if band_id == BAND_CORRIDOR and len(rooms_sorted) >= 2:
        cats_order = [_cat(str(r.get("name", "")), r) for r in rooms_sorted]
        if "corridor" in cats_order and "staircase" in cats_order:
            ic = cats_order.index("corridor")
            ist = cats_order.index("staircase")
            max_corr_frac = 0.68
            cap_px = avail_w * max_corr_frac
            if widths[ic] > cap_px:
                dx = widths[ic] - cap_px
                widths[ic] = cap_px
                sw_min = _nbc("staircase")[0] * SCALE * 0.88
                widths[ist] = max(widths[ist] + dx, sw_min)
        if "corridor" in cats_order and "staircase_landing" in cats_order:
            ic = cats_order.index("corridor")
            il = cats_order.index("staircase_landing")
            max_corr_frac = 0.68
            cap_px = avail_w * max_corr_frac
            if widths[ic] > cap_px:
                dx = widths[ic] - cap_px
                widths[ic] = cap_px
                lw_min = _nbc("staircase")[0] * SCALE * 0.88
                widths[il] = max(widths[il] + dx, lw_min)

    # ── ABSOLUTE FINAL FIT (after any special-case adjustments) ───────────────
    # Ensures no room ever extends outside built-up due to width drift.
    if len(widths) > 1:
        cats_f = [_cat(str(r.get("name","")), r) for r in rooms_sorted]
        def _min_w_px(cat_name: str) -> float:
            if cat_name in ("service_passage", "rear_passage", "passage"):
                return 18.0  # allow skinny circulation strip
            return max(_nbc(cat_name)[0] * SCALE * 0.80, 20.0)
        mins_f = [_min_w_px(c) for c in cats_f]
        total_f = sum(widths)
        if total_f > avail_w + 0.25:
            excess = total_f - avail_w
            slack = sum(max(w - m, 0.0) for w, m in zip(widths, mins_f))
            if slack > 0.1:
                for i in range(len(widths)):
                    reducible = max(widths[i] - mins_f[i], 0.0)
                    if reducible <= 0:
                        continue
                    take = excess * (reducible / slack)
                    widths[i] = max(widths[i] - take, mins_f[i])
        drift = avail_w - sum(widths)
        widths[-1] += drift
        if widths[-1] < mins_f[-1]:
            need = mins_f[-1] - widths[-1]
            widths[-1] = mins_f[-1]
            j = max(range(len(widths)-1), key=lambda k: widths[k] - mins_f[k])
            widths[j] = max(widths[j] - need, mins_f[j])

    results: List[Tuple[Dict, Rect]] = []
    cur_x = bx + tinset

    for r, w_px in zip(rooms_sorted, widths):
        cat = _cat(str(r.get("name", "")), r)

        if cat in _FILL_H:
            room_h = avail_h
        elif cat in ("corridor", "passage"):
            # Corridor: use FULL band height (no WALL_INSET reduction) — Guide Ch.6
            # bh is already set to corridor_w*SCALE by _band_heights
            room_h = bh  # exact band height, no inset reduction
            share_band = len(rooms_sorted) > 1
            if not share_band:
                rect = Rect(bx + tinset, by, avail_w, room_h)
                _nbc_warn(r, rect, warns)
                results.append((r, rect))
                break
            rect = Rect(cur_x, by, max(w_px, 20.0), room_h)
            _nbc_warn(r, rect, warns)
            results.append((r, rect))
            cur_x += w_px
            continue
        elif cat == "staircase_landing":
            stair_w = max(float(r.get("width_ft", 6)) * SCALE, 50.0)
            room_h  = max(float(r.get("depth_ft", 10)) * SCALE, 80.0)
            room_h  = min(room_h, avail_h)
            rect    = Rect(cur_x, by + tinset, min(stair_w, w_px), room_h)
            _nbc_warn(r, rect, warns)
            results.append((r, rect))
            cur_x += w_px
            continue
        else:
            # One structural slab per band — schematic rooms meet full depth (no interior void strips).
            room_h = avail_h

        rect = Rect(cur_x, by + tinset, max(w_px, 20.0), room_h)
        _nbc_warn(r, rect, warns)
        results.append((r, rect))
        cur_x += w_px

    return _align_staircase_landing_to_ground_axis(
        results, band_id, bx, tinset, avail_w, warns,
    )


def _nbc_warn(room: Dict, rect: Rect, warns: List[str]) -> None:
    cat = _cat(str(room.get("name", "")), room)
    nw, nd = _nbc(cat)
    aw, ah = rect.w / SCALE, rect.h / SCALE
    if aw < nw * 0.75 or ah < nd * 0.75:
        warns.append(f"NBC: {room.get('name')} at {aw:.1f}×{ah:.1f}ft (min {nw}×{nd}ft)")


# ─── CARVING ─────────────────────────────────────────────────────────────────

def _carve(placed: List[Tuple[Dict, Rect]], children: List[Dict], warns: List[str]) -> List[Tuple[Dict, Rect]]:
    lookup: Dict[str, Rect] = {str(r.get("name","")).lower(): rect for r, rect in placed}
    by_parent: Dict[str, List[str]] = {}
    extra: List[Tuple[Dict, Rect]] = []

    def _resolve_parent(cn: str, child: Dict) -> Optional[str]:
        pname = None
        if cn.endswith("_bathroom"):
            cand = cn[:-len("_bathroom")]
            if cand in lookup:
                pname = cand
        if pname is None and ("walk_in_wardrobe" in cn or "wardrobe" in cn):
            for pn in lookup:
                if "master_bedroom" in pn and "_bathroom" not in pn:
                    pname = pn
                    break
        if pname is None:
            notes = (child.get("notes") or "").lower()
            if "attached to " in notes:
                cand = notes.split("attached to ")[1].split()[0].rstrip(",;.")
                if cand in lookup:
                    pname = cand
        return pname

    for child in children:
        cn = str(child.get("name","")).lower()
        pname = _resolve_parent(cn, child)
        if pname:
            by_parent.setdefault(pname, []).append(cn)

    for child in children:
        cn = str(child.get("name","")).lower()
        pname = _resolve_parent(cn, child)

        if pname is None:
            warns.append(f"CARVE: no parent for {cn}")
            continue

        pr = lookup[pname]
        cc = _cat(cn, child)
        cw_ft, cd_ft = _dims(child)
        nbc_w, nbc_d = _nbc(cc)
        has_wic = any(("walk_in_wardrobe" in n or "wardrobe" in n) for n in by_parent.get(pname, []))
        has_bath = any(("bath" in n or "toilet" in n) for n in by_parent.get(pname, []))
        suite_pair = ("master_bedroom" in pname) and has_wic and has_bath

        if suite_pair:
            # Structured right-side suite strip: top=WIC, bottom=bath.
            strip_w = max(cw_ft * SCALE, nbc_w * SCALE, pr.w * 0.30)
            strip_w = min(strip_w, pr.w * 0.42)
            cx = pr.x + pr.w - strip_w
            if "bath" in cn or "toilet" in cn:
                cd = max(cd_ft * SCALE, nbc_d * SCALE, pr.h * 0.40)
                cd = min(cd, pr.h * 0.52)
                cy = pr.y + pr.h - cd
                cw = strip_w
            else:  # wardrobe / WIC
                cd = max(cd_ft * SCALE, nbc_d * SCALE, pr.h * 0.40)
                cd = min(cd, pr.h * 0.52)
                cy = pr.y
                cw = strip_w
        else:
            cw = min(max(cw_ft * SCALE, nbc_w * SCALE), pr.w * 0.55)
            cd = min(max(cd_ft * SCALE, nbc_d * SCALE), pr.h * 0.55)
            if "bath" in cn or "toilet" in cn:
                cx, cy = pr.x + pr.w - cw, pr.y + pr.h - cd
            elif "walk_in_wardrobe" in cn or "wardrobe" in cn:
                cx, cy = pr.x + pr.w - cw, pr.y   # top-RIGHT so bed can use top-LEFT
            else:
                cx, cy = pr.x + pr.w - cw, pr.y

        extra.append((child, Rect(cx, cy, cw, cd)))

    return placed + extra


# ─── SERIALISE ───────────────────────────────────────────────────────────────

def _ser(room: Dict, rect: Rect, fl: int, layout_band: int = -1, facing: str = "east") -> Dict:
    wf = round(rect.w / SCALE, 1)
    hf = round(rect.h / SCALE, 1)
    _cat_v = _cat(str(room.get("name","")), room)
    lb = layout_band if layout_band >= 0 else -1
    hints = _experience_hints(_cat_v, lb, facing)
    out = {
        "name": room.get("name","?"), "floor": fl,
        "x": round(rect.x,1), "y": round(rect.y,1),
        "width": round(rect.w,1), "height": round(rect.h,1),
        "width_ft": wf, "depth_ft": hf, "area_sqft": round(wf*hf,1),
        "area_px": round(rect.w*rect.h,1),
        "windows":           room.get("windows", 1),
        "door_count":        room.get("door_count", 1),
        "attached_bathroom": room.get("attached_bathroom", False),
        "attached_balcony":  room.get("attached_balcony", False),
        "notes":             room.get("notes",""),
        "__cat":             _cat_v,
        "functional_zone":   _functional_zone(_cat_v),
        "daylight_tier":     hints["daylight_tier"],
        "circulation_role":  hints["circulation_role"],
        "aspect_hint":       hints["aspect_hint"],
        "__is_carved":       _is_attached_child(str(room.get("name",""))),
        # compass_engine outputs — passed through to svg_renderer + frontend
        "__vastu_zone":      room.get("__vastu_zone", ""),
        "__col_side":        room.get("__col_side",   ""),
    }
    if layout_band >= 0:
        out["layout_band"] = layout_band
    return out


def _resolve_layout_band(room: Dict, band_per_name: Dict[str, int]) -> int:
    """Resolve vertical band id for scoring (including carved baths/WIC)."""
    nm = str(room.get("name", "")).lower()
    if nm in band_per_name:
        return band_per_name[nm]
    if nm.endswith("_bathroom"):
        base = nm[: -len("_bathroom")]
        if base in band_per_name:
            return band_per_name[base]
        for key in band_per_name:
            if base and base in key:
                return band_per_name[key]
    if "wardrobe" in nm:
        for key in band_per_name:
            if "master_bedroom" in key and "_bathroom" not in key:
                return band_per_name[key]
    return -1


# ─── MAIN ────────────────────────────────────────────────────────────────────

def generate_layout(parsed: Dict[str, Any], floor_index: int = 0) -> Dict[str, Any]:
    warns: List[str] = []
    failed: List[str] = []

    b = compute_built_up_bounds(parsed)
    bx, by, bw, bh = b["built_up_x"], b["built_up_y"], b["built_up_w"], b["built_up_h"]
    pw, ph = b["plot_w_px"], b["plot_h_px"]

    facing = str(parsed.get("plot_facing") or "unknown").lower()
    if facing not in ("east","north","west","south"):
        facing = "east"

    corr_w_raw = float(parsed.get("corridor_width_ft") or 4.0)
    corr_w = _effective_corridor_width_ft(parsed, corr_w_raw, warns)

    floors_ct = int(parsed.get("floors", 1) or 1)

    # Read spatial_type to vary band proportions per family lifestyle
    _spatial = str(parsed.get("spatial_type") or "traditional").lower()
    _SPATIAL_MODS = {
        "open_plan":     {BAND_PUBLIC: 1.15, BAND_SERVICE: 0.90, BAND_REAR_SVC: 0.85},
        "traditional":   {},  # no modification — standard defaults
        # Corridor multiplier was 2.0 — reads as an oversized dead strip in plan view;
        # modest bump keeps courtyard programmes breathable without hallway dominance.
        "courtyard":     {BAND_CORRIDOR: 1.38, BAND_PUBLIC: 0.90, BAND_SERVICE: 0.90},
        "linear":        {
            BAND_PUBLIC: 0.85,
            BAND_SERVICE: 1.06,
            BAND_GF_SLEEPING: 1.18,
            BAND_BEDROOMS: 1.20,
            BAND_REAR: 0.80,
        },
        "split_private": {
            BAND_PUBLIC: 0.85,
            BAND_SERVICE: 1.08,
            BAND_GF_SLEEPING: 1.26,
            BAND_BEDROOMS: 1.30,
            BAND_REAR: 1.10,
        },
    }
    _spatial_band_mods = _SPATIAL_MODS.get(_spatial, {})

    all_rooms = parsed.get("rooms") or []

    indep = [r for r in all_rooms
             if not _is_ghost(str(r.get("name","")))
             and not _is_attached_child(str(r.get("name","")))
             and int(r.get("floor",0) or 0) == floor_index]
    carved = [r for r in all_rooms
              if _is_attached_child(str(r.get("name","")))
              and not _is_ghost(str(r.get("name","")))
              and int(r.get("floor",0) or 0) == floor_index]

    # ── Rear wet-core lobby spine (deterministic) ────────────────────────────
    # Adds a narrow passage strip aligned through GF sleeping + rear wet-core,
    # so common toilet/bath has a believable circulation access (not through bedroom).
    if floor_index == 0 and floors_ct <= 1:
        has_common = any(
            (_cat(str(r.get("name", "")), r) in ("common_bathroom", "guest_powder_room", "bathroom"))
            and ("master_bedroom" not in str(r.get("name", "")).lower())
            for r in indep
        )
        if has_common and not any(str(r.get("name","")).lower() == "service_passage" for r in indep):
            indep.append({
                "name": "service_passage",
                "floor": floor_index,
                "area_sqft": 36.0,
                "width_ft": 3.6,
                "depth_ft": 10.0,
                "windows": 0,
                "door_count": 0,
                "__category_hint": "service_passage",
                "__col_side": "left",
                "notes": "Circulation spine to rear wet core",
            })
            indep.append({
                "name": "rear_passage",
                "floor": floor_index,
                "area_sqft": 28.0,
                "width_ft": 3.6,
                "depth_ft": 8.0,
                "windows": 0,
                "door_count": 0,
                "__category_hint": "rear_passage",
                "__col_side": "left",
                "notes": "Rear wet-core lobby / passage",
            })
            warns.append(
                "CONNECTIVITY: added a small rear passage spine so common toilet/bath access is from circulation."
            )

    # ── Connect compass_engine: facing-aware Vastu zone assignment ────────────
    # Injects __vastu_zone + __col_side into each room dict.
    # __col_side drives LEFT/RIGHT column ordering within each band,
    # making the plan physically differ by plot facing.
    # East-facing: kitchen=right(SE), pooja=left(NE), master=right(SW)
    # North-facing: kitchen=right(SE), master=left(SW), pooja=right(NE)
    _floor_rooms_for_compass = [r for r in (indep + carved)]
    try:
        try:
            from app.services.compass_engine import assign_vastu_zones as _avz
        except ImportError:
            from compass_engine import assign_vastu_zones as _avz
        _avz(
            _floor_rooms_for_compass,
            plot_facing=facing,
            vastu_compliant=bool(parsed.get("vastu_compliant", True)),
            floors=int(parsed.get("floors", 1) or 1),
        )
        # assign_vastu_zones mutates rooms in-place — no reassignment needed
    except Exception:
        pass  # compass_engine unavailable — _vastu_side() fallback handles ordering

    if not indep and not carved:
        return {"rooms":[], "canvas_w": pw+MARGIN_PX*2, "canvas_h": ph+MARGIN_PX*2,
                "built_up_x":bx,"built_up_y":by,"built_up_w":bw,"built_up_h":bh,
                "plot_w_px":pw,"plot_h_px":ph,"warnings":warns,"failed_rooms":failed}

    # Single-storey: slightly narrower spine when no stair (landing loads corridor band)
    if floors_ct <= 1 and floor_index == 0:
        has_stair = any(_cat(str(r.get("name", "")), r) == "staircase" for r in indep)
        if not has_stair and corr_w > 4.25:
            corr_w = min(corr_w, 4.25)

    bua_ft2 = (bw / SCALE) * (bh / SCALE)
    plot_w_ft = float(parsed.get("plot_width_ft") or (pw / SCALE))
    indep = _hybrid_suite_service_merge(indep, bua_ft2, warns)
    fit_scale = _programme_fit_scale(indep, bua_ft2)
    if fit_scale < 0.99:
        warns.append(
            "PROGRAMME: compact-fit mode enabled for this shell "
            f"(pressure scale {fit_scale:.2f}); keeping composition while avoiding stretched rooms."
        )
    indep = _enforce_indian_program_targets(
        indep, bua_ft2, plot_w_ft, warns, min_scale=fit_scale
    )
    indep = _ensure_master_dominance(indep, floor_index, warns)
    indep = _bump_gf_sleeping_targets(indep, floors_ct, floor_index, warns)
    indep = _budget_check(indep, bw / SCALE, bh / SCALE, warns)
    indep = _enforce_indian_program_targets(
        indep, bua_ft2, plot_w_ft, warns, warn_on_touch=False, min_scale=fit_scale
    )
    indep = _ensure_master_dominance(indep, floor_index, warns)

    band_buckets: Dict[int, List[Dict]] = {i: [] for i in range(8)}
    for r in indep:
        cat = _cat(str(r.get("name", "")), r)
        bid = _placement_band(cat, floor_index, floors_ct)
        band_buckets[bid].append(r)

    occupied = {k:v for k,v in band_buckets.items() if v}
    _gf_compact = floors_ct <= 1 and floor_index == 0
    if _gf_compact and any(_cat(str(r.get("name", "")), r) == "dining_room" for r in indep):
        warns.append(
            "ZONING: single-storey meal cluster — dining grouped with kitchen/dry kitchen "
            "(service band); corridor follows meal zone then bedrooms."
        )
    heights  = _band_heights(
        occupied, bh, corr_w, warns, _spatial_band_mods,
        compact_gf_front=_gf_compact,
    )

    placed: List[Tuple[Dict, Rect]] = []
    band_per_name: Dict[str, int] = {}
    cur_y = by

    stack_order = _gf_band_stack_order(floor_index, floors_ct, list(occupied.keys()))
    for bid in stack_order:
        bh_now = heights.get(bid, 0.0)
        if bh_now < 5:
            continue
        new = _place_band(
            occupied[bid], bx, cur_y, bw, bh_now, facing, corr_w, warns,
            band_id=bid, floor_index=floor_index, spatial_type=_spatial,
        )
        placed_names = {str(r.get("name","")) for r,_ in new}
        for r in occupied[bid]:
            nm = str(r.get("name",""))
            if nm not in placed_names:
                failed.append(nm)
                warns.append(f"OVERFLOW: {nm} not placed")
        for r, rect in new:
            band_per_name[str(r.get("name", "")).lower()] = bid
        placed.extend(new)
        cur_y += bh_now

    placed = _carve(placed, carved, warns)

    # Dedup warnings
    if parsed.get("vastu_compliant"):
        pcats = {_cat(str(r.get("name",""))): True for r,_ in placed}
        # Only warn about missing pooja_room on GF (floor_index=0).
        # On FF the pooja_room is legitimately on GF — don't fire false positive.
        if floor_index == 0:
            has_pooja_placed = any(
                "pooja" in str(r.get("name","")).lower() or
                "prayer" in str(r.get("name","")).lower()
                for r,_ in placed
            )
            if not has_pooja_placed and parsed.get("pooja_room"):
                warns.append("VASTU CRITICAL: no Pooja room placed")

    seen, uniq = set(), []
    for w in warns:
        if w not in seen:
            seen.add(w); uniq.append(w)

    return {
        "rooms":        [
            _ser(r, rect, floor_index,
                 layout_band=_resolve_layout_band(r, band_per_name),
                 facing=facing)
            for r, rect in placed
        ],
        "canvas_w":     pw + MARGIN_PX*2,
        "canvas_h":     ph + MARGIN_PX*2,
        "built_up_x":   bx, "built_up_y": by,
        "built_up_w":   bw, "built_up_h": bh,
        "plot_w_px":    pw, "plot_h_px":  ph,
        "facing":       facing,
        "warnings":     uniq,
        "failed_rooms": failed,
    }