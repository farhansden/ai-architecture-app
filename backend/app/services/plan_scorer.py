"""
plan_scorer.py — Quantified plan quality scoring.

Takes layout_engine output and parsed JSON.
Returns score 0-100 with per-dimension breakdown.

Dimensions (weighted):
  Vastu compliance      25pts — zone correctness for each room
  Adjacency quality     20pts — intended adjacencies achieved  
  Circulation logic     20pts — corridor efficiency, no dead-ends
  Area accuracy         15pts — rooms at intended size (not squished)
  Privacy gradient      10pts — public/private separation
  Natural light         10pts — bedroom/living on preferred walls
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple
import math

SCALE = 10.0  # px per ft — must match layout_engine

# ── Vastu zone map for east-facing ────────────────────────────────────────────
# For east-facing: front=east, left=north, right=south
# Vastu correct zones mapped to SVG positions (top-left origin, y increases down)
# Band mapping: FRONT(top)=entrance, PUBLIC=upper, SERVICE=middle, REAR=lower
# Column mapping: LEFT=north side, RIGHT=south side

_VASTU_IDEAL: Dict[str, Dict[str, str]] = {
    # (band, col) tuples for each room — depends on plot_facing
    "east": {
        "pooja_room":      ("public",  "left"),    # NE = top-left
        "living_room":     ("public",  "left"),    # N  = top-left  
        "dining_room":     ("public",  "left"),    # N  = top-left
        "kitchen":         ("service", "right"),   # SE = middle-right
        "master_bedroom":  ("private", "right"),   # SW = bottom-right
        "staircase":       ("corridor", "right"),   # S  = circulation band, stair+spine
        "common_bathroom": ("private", "left"),    # NW = bottom-left
        "servant_quarters":("private", "right"),   # S  = bottom-right
        "store_room":      ("private", "right"),   # S  = bottom
    },
    "north": {
        "pooja_room":      ("public",  "right"),   # NE = top-right
        "living_room":     ("public",  "center"),  # N  = top
        "dining_room":     ("public",  "right"),   # NE = top-right
        "kitchen":         ("private", "right"),   # SE = bottom-right
        "master_bedroom":  ("private", "left"),    # SW = bottom-left
        "staircase":       ("corridor", "center"), # circulation band (not kitchen band)
        "common_bathroom": ("service", "left"),    # NW = middle-left
        "servant_quarters":("private", "center"),  # S  = bottom
    },
}

# ── Band assignment map (mirrors layout_engine) ────────────────────────────────
# Mirrors layout_engine band ids (GF sleeping = 3 private band; FF beds = 6)
_BAND_NAMES = {
    0: "front",
    1: "public",
    2: "corridor",
    3: "private",
    4: "service",
    5: "rear_svc",
    6: "private",
    7: "rear",
}

def _band_of_room(room: Dict, built_up_y: float, built_up_h: float) -> str:
    """Map room y-position to its functional band."""
    ry = float(room.get("y", 0)) + float(room.get("height", 0)) / 2
    relative = (ry - built_up_y) / max(built_up_h, 1)
    if relative < 0.15:   return "front"
    if relative < 0.35:   return "public"
    if relative < 0.50:   return "corridor"
    if relative < 0.65:   return "service"
    if relative < 0.80:   return "rear_svc"
    if relative < 0.92:   return "private"
    return "rear"

def _col_of_room(room: Dict, built_up_x: float, built_up_w: float) -> str:
    """Map room x-position to left/center/right column."""
    rx = float(room.get("x", 0)) + float(room.get("width", 0)) / 2
    relative = (rx - built_up_x) / max(built_up_w, 1)
    if relative < 0.33:  return "left"
    if relative < 0.67:  return "center"
    return "right"

def _is_wet_core_room(name: str) -> bool:
    """WC / bath / powder — adjacency-sensitive."""
    n = (name or "").lower()
    if any(k in n for k in ("bathroom", "powder_room", "powder")):
        return True
    if "toilet" in n:
        return True
    return False


def _rooms_share_wall(r1: Dict, r2: Dict, tolerance: float = 8.0) -> bool:
    """Return True if r1 and r2 share a wall (within tolerance px)."""
    x1,y1,w1,h1 = r1.get("x",0), r1.get("y",0), r1.get("width",0), r1.get("height",0)
    x2,y2,w2,h2 = r2.get("x",0), r2.get("y",0), r2.get("width",0), r2.get("height",0)
    # Horizontal overlap
    h_overlap = min(x1+w1, x2+w2) - max(x1, x2) > tolerance
    # Vertical overlap  
    v_overlap = min(y1+h1, y2+h2) - max(y1, y2) > tolerance
    # Touching edges
    top_touch    = abs((y1+h1) - y2) < tolerance and h_overlap
    bottom_touch = abs((y2+h2) - y1) < tolerance and h_overlap
    left_touch   = abs((x1+w1) - x2) < tolerance and v_overlap
    right_touch  = abs((x2+w2) - x1) < tolerance and v_overlap
    return top_touch or bottom_touch or left_touch or right_touch


def _vertical_stack_overlap(r_upper: Dict, r_lower: Dict, tol: float = 12.0) -> float:
    """
    r_upper sits above r_lower on plan (smaller y). Returns horizontal overlap / min width
    when the bottom edge of upper meets top edge of lower — arrival→social stacking.
    """
    x1 = float(r_upper.get("x", 0)); y1 = float(r_upper.get("y", 0))
    w1 = float(r_upper.get("width", 0)); h1 = float(r_upper.get("height", 0))
    x2 = float(r_lower.get("x", 0)); y2 = float(r_lower.get("y", 0))
    w2 = float(r_lower.get("width", 0)); h2 = float(r_lower.get("height", 0))
    if abs((y1 + h1) - y2) > tol:
        return 0.0
    overlap = min(x1 + w1, x2 + w2) - max(x1, x2)
    if overlap <= 0:
        return 0.0
    return overlap / max(min(w1, w2), 1.0)


def score_plan(layout: Dict[str, Any], parsed: Dict[str, Any]) -> Dict[str, Any]:
    """
    Score a placed floor plan layout.
    
    Args:
        layout: output from layout_engine.generate_layout()
        parsed: output from llm_parser (full JSON)
    
    Returns:
        {
          "total": 0-100,
          "grade": "A/B/C/D/F",
          "breakdown": {dim: score},
          "issues": [str],
          "strengths": [str],
        }
    """
    rooms = layout.get("rooms", [])
    if not rooms:
        return {"total": 0, "grade": "F", "breakdown": {}, "issues": ["No rooms placed"], "strengths": []}
    
    facing  = str(parsed.get("plot_facing", "east")).lower()
    vastu   = bool(parsed.get("vastu_compliant", False))
    bx      = float(layout.get("built_up_x", 0))
    by_     = float(layout.get("built_up_y", 0))
    bw      = float(layout.get("built_up_w", 300))
    bh      = float(layout.get("built_up_h", 400))
    
    by_name: Dict[str, Dict] = {str(r.get("name","")).lower(): r for r in rooms}
    issues: List[str] = []
    strengths: List[str] = []
    
    # ── 1. VASTU COMPLIANCE (25 pts) ─────────────────────────────────────────
    vastu_score = 25
    if vastu:
        ideal = _VASTU_IDEAL.get(facing, _VASTU_IDEAL["east"])
        # layout_engine.BAND_SERVICE == 4: meal cluster (dining + kitchens) on single-storey GF
        MEAL_BAND = 4
        for room_name, (ideal_band, ideal_col) in ideal.items():
            r = by_name.get(room_name)
            if not r:
                continue
            lb = r.get("layout_band")
            # Dining deliberately sits in the service/meal strip with kitchens — skip rigid band rule
            if room_name == "dining_room" and lb == MEAL_BAND:
                strengths.append(
                    "Vastu-aware compromise: dining in meal/service strip adjoining kitchen "
                    "(preferred over textbook-only public-band placement)"
                )
                continue
            if isinstance(lb, int) and lb >= 0 and lb in _BAND_NAMES:
                actual_band = _BAND_NAMES[lb]
            else:
                actual_band = _band_of_room(r, by_, bh)
            actual_col  = _col_of_room(r, bx, bw)
            band_ok = actual_band == ideal_band
            col_ok  = actual_col  == ideal_col or ideal_col == "center"
            if not band_ok:
                penalty = 5 if room_name in ("kitchen","master_bedroom","pooja_room") else 2
                vastu_score -= penalty
                issues.append(f"Vastu: {room_name} in {actual_band} (want {ideal_band})")
            elif band_ok and col_ok:
                strengths.append(f"Vastu: {room_name} correctly in {actual_band}/{actual_col}")
    vastu_score = max(0, vastu_score)
    
    # ── 2. ADJACENCY QUALITY (20 pts) ─────────────────────────────────────────
    adj_score = 20
    required_adj = [
        ("kitchen", "dining_room", 5, "Kitchen↔Dining pass door"),
        ("corridor", "master_bedroom", 3, "Corridor↔Master access"),
        ("corridor", "bedroom_2", 3, "Corridor↔Bedroom2 access"),
        ("staircase", "corridor", 3, "Stair↔Corridor connection"),
    ]
    forbidden_adj = [
        ("kitchen", "common_bathroom", 6, "Kitchen shares wall with bathroom"),
        ("kitchen", "servant_quarters", 4, "Kitchen shares wall with servant quarters"),
        ("master_bedroom", "servant_quarters", 4, "Master bedroom adjacent to servant quarters"),
    ]
    for r1n, r2n, points, label in required_adj:
        r1, r2 = by_name.get(r1n), by_name.get(r2n)
        if r1 and r2:
            if _rooms_share_wall(r1, r2):
                strengths.append(f"Adjacency: {label} ✓")
            else:
                adj_score -= points
                issues.append(f"Missing adjacency: {label}")

    # Social anchor ↔ dining: living OR formal drawing must touch dining (connector rule)
    din0 = by_name.get("dining_room")
    if din0:
        liv0 = by_name.get("living_room")
        drw0 = by_name.get("drawing_room")
        anchor_ok = (liv0 and _rooms_share_wall(liv0, din0)) or (
            drw0 and _rooms_share_wall(drw0, din0)
        )
        if anchor_ok:
            strengths.append("Adjacency: social anchor ↔ dining (integrated composition) ✓")
        elif liv0 or drw0:
            adj_score -= 4
            issues.append(
                "Composition: dining not wall-connected to living/drawing — weak social connector"
            )

    # Arrival stacks into social core (foyer band above public living band on plan)
    foyer_r = by_name.get("foyer") or by_name.get("entrance_foyer")
    liv_anchor = by_name.get("living_room") or by_name.get("drawing_room")
    if foyer_r and liv_anchor:
        stack_ratio = _vertical_stack_overlap(foyer_r, liv_anchor)
        if stack_ratio >= 0.22:
            strengths.append("Arrival: foyer transitions into social anchor (vertical alignment) ✓")
        else:
            adj_score -= 3
            issues.append(
                "Entry: foyer weakly aligned with living/drawing — strengthen arrival→social overlap"
            )

    # Service-core integration
    kit0 = by_name.get("kitchen")
    ut0 = by_name.get("utility_room")
    if kit0 and ut0 and _rooms_share_wall(kit0, ut0):
        strengths.append("Service core: kitchen ↔ utility clustered ✓")

    # Dining touches circulation spine — connector behaviour
    corr0 = by_name.get("corridor")
    if din0 and corr0 and _rooms_share_wall(din0, corr0):
        strengths.append("Circulation: dining bridges spine ✓")

    # FF lounge feeds private wing
    flounge = by_name.get("family_lounge")
    if flounge and corr0 and _rooms_share_wall(flounge, corr0):
        strengths.append("Upper floor: family lounge ↔ corridor (integrated bedrooms approach) ✓")
    for r1n, r2n, penalty, label in forbidden_adj:
        r1, r2 = by_name.get(r1n), by_name.get(r2n)
        if r1 and r2 and _rooms_share_wall(r1, r2):
            adj_score -= penalty
            issues.append(f"Bad adjacency: {label}")

    din = by_name.get("dining_room")
    if din:
        for rn, rr in by_name.items():
            if rn == "dining_room":
                continue
            if _is_wet_core_room(rn) and _rooms_share_wall(din, rr):
                adj_score -= 7
                issues.append("Bad adjacency: dining shares wall with toilet/bath — block with service core")
                break
    puja_nm = next((nm for nm in by_name if "pooja" in nm or "prayer" in nm), None)
    if puja_nm:
        pr = by_name[puja_nm]
        for rn, rr in by_name.items():
            if rn == puja_nm or not _is_wet_core_room(rn):
                continue
            if _rooms_share_wall(pr, rr):
                adj_score -= 6
                issues.append(f"Bad adjacency: {puja_nm} shares wall with wet room")
                break
    adj_score = max(0, adj_score)
    
    # ── 3. CIRCULATION LOGIC (20 pts) ─────────────────────────────────────────
    circ_score = 20
    corr = by_name.get("corridor")
    if not corr:
        circ_score -= 10
        issues.append("No corridor — rooms may be inaccessible")
    else:
        # Corridor should span most of the building width
        corr_width_ft = float(corr.get("width_ft", corr.get("width",0)/SCALE))
        bw_ft = bw / SCALE
        coverage = corr_width_ft / max(bw_ft, 1)
        if coverage < 0.60:
            circ_score -= 5
            issues.append(f"Corridor only {corr_width_ft:.0f}ft wide ({coverage*100:.0f}% of building)")
        else:
            strengths.append(f"Corridor spans {coverage*100:.0f}% of building width")

        built_px = max(bw * bh, 1.0)
        corr_px = float(corr.get("width", 0) or 0) * float(corr.get("height", 0) or 0)
        if corr_px / built_px > 0.13:
            circ_score -= 4
            issues.append(
                f"Corridor band consumes {corr_px/built_px*100:.0f}% of built-up — likely dead circulation strip"
            )
    # Staircase present
    if "staircase" not in by_name:
        circ_score -= 8
        issues.append("No staircase on this floor")
    circ_score = max(0, circ_score)
    
    # ── 4. AREA ACCURACY (15 pts) ─────────────────────────────────────────────
    area_score = 15
    parsed_rooms = {str(r.get("name","")).lower(): r for r in (parsed.get("rooms") or [])}
    total_sqft_delta = 0
    checked = 0
    for name, placed_r in by_name.items():
        orig = parsed_rooms.get(name)
        if not orig:
            continue
        orig_area  = float(orig.get("area_sqft", 0) or 0)
        placed_area = float(placed_r.get("area_sqft", orig_area))
        if orig_area > 0:
            delta = abs(placed_area - orig_area) / orig_area
            total_sqft_delta += delta
            checked += 1
    if checked > 0:
        avg_delta = total_sqft_delta / checked
        if avg_delta > 0.30:
            area_score -= 10
            issues.append(f"Rooms 30%+ off target size (avg {avg_delta*100:.0f}% deviation)")
        elif avg_delta > 0.15:
            area_score -= 5
            issues.append(f"Rooms somewhat off target size (avg {avg_delta*100:.0f}% deviation)")
        else:
            strengths.append(f"Rooms close to intended size (avg {avg_delta*100:.0f}% deviation)")
    area_score = max(0, area_score)
    
    # ── 5. PRIVACY GRADIENT (10 pts) ─────────────────────────────────────────
    priv_score = 10
    # Bedrooms should be in back half (high y), public rooms in front half
    bedrooms = [r for n,r in by_name.items() if "bedroom" in n and "_bathroom" not in n]
    living   = [r for n,r in by_name.items() if n in ("living_room","dining_room")]
    if bedrooms and living:
        avg_bed_y  = sum(r.get("y",0)+r.get("height",0)/2 for r in bedrooms) / len(bedrooms)
        avg_live_y = sum(r.get("y",0)+r.get("height",0)/2 for r in living)   / len(living)
        if avg_bed_y > avg_live_y:
            strengths.append("Privacy gradient: bedrooms behind public areas ✓")
        else:
            priv_score -= 6
            issues.append("Privacy issue: bedrooms in front of public areas")

    layout_band_entrance = 0
    for nm, rr in by_name.items():
        if "_bathroom" in nm:
            continue
        if "bedroom" not in nm:
            continue
        fl = int(rr.get("floor", 0) or 0)
        lb = rr.get("layout_band")
        if fl == 0 and lb == layout_band_entrance:
            priv_score -= 7
            issues.append(f"Privacy: bedroom '{nm}' in entrance/public approach band")
            break
    priv_score = max(0, priv_score)
    
    # ── 6. NATURAL LIGHT (10 pts) ─────────────────────────────────────────────
    light_score = 10
    # For east-facing: living should be in left (north) column for diffuse light
    # Master bedroom should be in far column for privacy
    living_r = by_name.get("living_room") or by_name.get("drawing_room")
    if living_r and int(living_r.get("windows", 0) or 0) >= 2:
        strengths.append("Social anchor: multiple window openings — daylight / cross-vent intent ✓")

    if living_r and facing == "east":
        col = _col_of_room(living_r, bx, bw)
        if col == "left":
            strengths.append("Living room in north zone — diffuse light ✓")
        else:
            light_score -= 4
            issues.append("Living room not in north zone — will get harsh light")
    light_score = max(0, light_score)
    
    # ── TOTAL ─────────────────────────────────────────────────────────────────
    total = vastu_score + adj_score + circ_score + area_score + priv_score + light_score
    grade = "A" if total >= 85 else "B" if total >= 70 else "C" if total >= 55 else "D" if total >= 40 else "F"
    
    return {
        "total":     total,
        "grade":     grade,
        "breakdown": {
            "vastu_compliance":  vastu_score,
            "adjacency_quality": adj_score,
            "circulation":       circ_score,
            "area_accuracy":     area_score,
            "privacy_gradient":  priv_score,
            "natural_light":     light_score,
        },
        "max_possible": 100,
        "issues":    issues[:8],
        "strengths": strengths[:6],
    }


if __name__ == "__main__":
    # Quick self-test
    mock_layout = {
        "built_up_x": 50, "built_up_y": 100, "built_up_w": 300, "built_up_h": 400,
        "rooms": [
            {"name": "living_room",  "x": 50,  "y": 130, "width": 180, "height": 130, "width_ft": 18, "depth_ft": 13, "area_sqft": 234},
            {"name": "kitchen",      "x": 260, "y": 230, "width": 90,  "height": 100, "width_ft": 9,  "depth_ft": 10, "area_sqft": 90},
            {"name": "dining_room",  "x": 50,  "y": 265, "width": 140, "height": 90,  "width_ft": 14, "depth_ft": 9,  "area_sqft": 126},
            {"name": "corridor",     "x": 50,  "y": 370, "width": 300, "height": 50,  "width_ft": 30, "depth_ft": 5,  "area_sqft": 150},
            {"name": "master_bedroom","x":200, "y": 420, "width": 150, "height": 130, "width_ft": 15, "depth_ft": 13, "area_sqft": 195},
            {"name": "staircase",    "x": 50,  "y": 420, "width": 50,  "height": 100, "width_ft": 5,  "depth_ft": 10, "area_sqft": 50},
            {"name": "pooja_room",   "x": 50,  "y": 130, "width": 70,  "height": 70,  "width_ft": 7,  "depth_ft": 7,  "area_sqft": 49},
        ]
    }
    mock_parsed = {"plot_facing": "east", "vastu_compliant": True,
                   "rooms": [{"name":"living_room","area_sqft":234},
                              {"name":"kitchen","area_sqft":90}]}
    result = score_plan(mock_layout, mock_parsed)
    print(f"Test score: {result['total']}/100 Grade: {result['grade']}")
    print(f"Breakdown: {result['breakdown']}")
    print(f"Issues: {result['issues']}")
    print(f"Strengths: {result['strengths']}")
