"""
Infer a new room from a user prompt + target rectangle (void fill), merge into layout JSON.

Used by POST /api/layout/propose-room-in-region for the Phase A editor.
"""
from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List, Optional, Tuple

from app.services.layout_engine import _cat, _experience_hints, _functional_zone

# Canonical programme names (snake_case) — must stay aligned with ``svg_renderer.cat`` / layout_engine.
ALLOWED_PROGRAMME_NAMES: Tuple[str, ...] = (
    "car_porch",
    "sit_out",
    "foyer",
    "entrance_foyer",
    "living_room",
    "drawing_room",
    "dining_room",
    "family_lounge",
    "kitchen",
    "wet_kitchen",
    "dry_kitchen",
    "pooja_room",
    "utility_room",
    "store_room",
    "corridor",
    "passage",
    "service_passage",
    "rear_passage",
    "staircase",
    "staircase_landing",
    "master_bedroom",
    "parents_bedroom",
    "bedroom",
    "bedroom_2",
    "bedroom_3",
    "guest_bedroom",
    "guest_room",
    "home_office",
    "common_bathroom",
    "guest_powder_room",
    "bathroom",
    "servant_quarters",
    "servant_bathroom",
    "terrace",
    "balcony",
    "walk_in_wardrobe",
)

_ALLOWED_SET = frozenset(ALLOWED_PROGRAMME_NAMES)

# (regex pattern, canonical snake_case name) — first match wins; put ``bedroom`` last.
_HEURISTIC_ROOMS: Tuple[Tuple[str, str], ...] = (
    (r"\bmaster\s*(suite|bed)?\b", "master_bedroom"),
    (r"\b(primary|main)\s*bed(room)?\b", "master_bedroom"),
    (r"\bparents?\b.*\bbed(room)?\b", "parents_bedroom"),
    (r"\bguest\s*(room|bed|suite|quarters)\b", "guest_bedroom"),
    (r"\bspare\s*(bed)?(room)?\b", "guest_bedroom"),
    (r"\b(passage|lobby\s*spine|service\s*spine)\b", "passage"),
    (r"\b(corridor|hallway|gallery)\b", "corridor"),
    (r"\bstair(s|case|way|well)?\b", "staircase"),
    (r"\b(dining|breakfast\s*nook|meal\s*space|dining\s*area)\b", "dining_room"),
    (r"\b(drawing|formal\s*living)\b", "drawing_room"),
    (r"\bfamily\s*lounge\b", "family_lounge"),
    (r"\b(living|sitting\s*room|drawing\s*room)\b", "living_room"),
    (r"\blounge\b", "living_room"),
    (r"\b(kitchen|pantry\s*cook)\b", "kitchen"),
    (r"\b(prayer|pooja|puja|mandir|worship)\b", "pooja_room"),
    (r"\b(wfh|library|reading\s*room)\b", "home_office"),
    (r"\b(home\s*)?office\b", "home_office"),
    (r"\b(work\s*from\s*home|desk\s*space|study)\b", "home_office"),
    (r"\b(powder|guest\s*wc|half\s*bath)\b", "guest_powder_room"),
    (r"\b(wc|water\s*closet|toilet|bathroom|bath\s*room|restroom)\b", "common_bathroom"),
    (r"\b(store|storeroom|storage|pantry)\b", "store_room"),
    (r"\b(laundry|wash\s*area|utility)\b", "utility_room"),
    (r"\b(parking|car\s*porch|garage\s*bay)\b", "car_porch"),
    (r"\b(verandah|veranda|sit\s*out|porch)\b", "sit_out"),
    (r"\b(foyer|entry|vestibule)\b", "foyer"),
    (r"\b(terrace|deck)\b", "terrace"),
    (r"\b(balcony)\b", "balcony"),
    (r"\b(wardrobe|walk\s*in)\b", "walk_in_wardrobe"),
    (r"\b(kids?|child|children)\b.*\b(room|bed)\b", "bedroom_2"),
    (r"\bbed(room)?\b", "bedroom"),
)


def _norm_prompt(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def _stem_for_category(name: str) -> str:
    """Strip uniquifier ``_<digits>`` so ``dining_room_2`` → ``dining_room`` for ``_cat`` / furniture."""
    cur = (name or "").lower().strip()
    while True:
        m = re.fullmatch(r"(.+)_(\d+)$", cur)
        if not m:
            return cur
        nxt = m.group(1)
        if not nxt or nxt == cur:
            return cur
        cur = nxt


def _default_furniture_notes(programme: str) -> str:
    """Lightweight drawing hints so ``svg_renderer.furniture`` picks the right kit."""
    p = (programme or "").lower()
    hints = {
        "dining_room": "6-seater dining table, chairs around table perimeter, circulation clear around chairs",
        "living_room": "L-sofa layout, TV wall opposite seating, coffee table centre",
        "drawing_room": "luxury formal sofa, TV wall, wider seating for guests",
        "family_lounge": "sofa grouping, TV niche, family circulation",
        "kitchen": "modular L-counter, hob and sink on segregated wet wall, tall unit run",
        "corridor": "clear circulation spine, no furniture clutter",
        "passage": "narrow service circulation, no furniture clutter",
        "service_passage": "narrow service circulation spine",
        "rear_passage": "rear service circulation spine",
        "staircase": "tread run along long dimension, handrail side",
        "pooja_room": "altar platform toward NE wall, calm circulation",
        "home_office": "built-in shelves, desk run along long wall, task chair",
        "store_room": "shelving along one wall, clear floor for storage",
        "utility_room": "washing machine and dryer side by side, utility sink",
        "common_bathroom": "WC, wall-hung basin, shower zone with high sill",
        "guest_powder_room": "compact WC and basin, mirror above basin",
        "foyer": "entry mat zone, shoe storage along side wall",
        "sit_out": "outdoor seating chairs along façade",
        "car_porch": "single car bay manoeuvre clearance",
        "terrace": "open terrace hatch pattern, parapet ticks",
        "balcony": "slim outdoor zone, railing along outer edge",
        "master_bedroom": "queen bed, wardrobe run, ensuite door toward bath",
        "parents_bedroom": "queen bed, wardrobe run",
        "guest_bedroom": "queen bed, compact wardrobe",
        "guest_room": "queen bed, compact wardrobe",
        "bedroom": "queen bed, wardrobe run",
        "bedroom_2": "single bed, study desk along window wall",
        "bedroom_3": "single bed, compact wardrobe",
    }
    return hints.get(p, "User-defined void fill — keep centre clear for future fit-out")


def _infer_room_heuristic(user_prompt: str) -> Tuple[str, str, str]:
    """Returns (room_name_snake, notes, reasoning)."""
    t = _norm_prompt(user_prompt)
    if not t:
        t = "flex study"
    name = "home_office"
    for pat, nm in _HEURISTIC_ROOMS:
        if re.search(pat, t, re.I):
            name = nm
            break
    extra = _default_furniture_notes(name)
    notes = f"User-placed void fill: {user_prompt.strip()[:160] or 'unspecified'}. {extra}"
    reasoning = (
        f"Heuristic parser mapped the prompt to programme `{name}` (no LLM). "
        f"Tip: use words like dining, corridor, passage, guest room, kitchen, study, or set OPENAI_API_KEY for finer naming."
    )
    return name, notes, reasoning


def _coerce_llm_programme(raw: str) -> str:
    n = str(raw or "").strip().lower().replace(" ", "_").replace("-", "_")
    n = re.sub(r"[^a-z0-9_]+", "", n)
    if n in _ALLOWED_SET:
        return n
    stem = _stem_for_category(n)
    if stem in _ALLOWED_SET:
        return stem
    return ""


def _infer_room_openai(user_prompt: str, region_sqft: float, context: str) -> Optional[Tuple[str, str, str]]:
    key = (os.environ.get("OPENAI_API_KEY") or "").strip()
    if not key:
        return None
    try:
        from openai import OpenAI
    except ImportError:
        return None

    schema = {
        "name": "region_room",
        "strict": True,
        "schema": {
            "type": "object",
            "additionalProperties": False,
            "required": ["room_name_snake", "notes", "reasoning"],
            "properties": {
                "room_name_snake": {
                    "type": "string",
                    "description": "Exactly one allowed programme id (snake_case).",
                    "enum": list(ALLOWED_PROGRAMME_NAMES),
                },
                "notes": {
                    "type": "string",
                    "description": "Short drawing notes for SVG (furniture keywords per programme).",
                },
                "reasoning": {
                    "type": "string",
                    "description": "One or two sentences for the user.",
                },
            },
        },
    }

    client = OpenAI(api_key=key)
    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    user_block = (
        f"PROMPT: {user_prompt.strip()}\n"
        f"SELECTED_VOID_AREA_SQFT: {region_sqft:.1f}\n"
        f"NEIGHBOUR_SUMMARY:\n{context}\n\n"
        "Choose exactly ONE value from room_name_snake enum that best matches the user's request.\n"
        "Examples: guest room → guest_bedroom; passage / hallway → passage or corridor; "
        "dining → dining_room; drawing / formal living → drawing_room; "
        "living / lounge (not family lounge) → living_room; study / WFH → home_office; "
        "WC / toilet → common_bathroom; store / pantry → store_room; "
        "kitchen only if the neighbour summary does NOT already list a kitchen room.\n"
        "Notes must include furniture keywords recognised by the drawing engine "
        "(e.g. dining: '6-seater dining table'; living: 'L-sofa'; kitchen: 'modular L-counter'; "
        "corridor/passage: 'clear circulation spine, no furniture clutter')."
    )
    try:
        r = client.chat.completions.create(
            model=model,
            temperature=0.2,
            max_tokens=500,
            messages=[
                {
                    "role": "system",
                    "content": "You place one new room into a residential floor void. room_name_snake MUST be one of the enum strings — never invent new names.",
                },
                {"role": "user", "content": user_block},
            ],
            response_format={"type": "json_schema", "json_schema": schema},
        )
        raw = (r.choices[0].message.content or "").strip()
        data = json.loads(raw)
        if not isinstance(data, dict):
            return None
        n = str(data.get("room_name_snake", "")).strip().lower().replace(" ", "_").replace("-", "_")
        n = re.sub(r"[^a-z0-9_]+", "", n)
        if n not in _ALLOWED_SET:
            return None
        notes = str(data.get("notes", "")).strip()[:500]
        reasoning = str(data.get("reasoning", "")).strip()[:800]
        if not notes:
            notes = f"AI-placed void fill: {user_prompt.strip()[:120]}. {_default_furniture_notes(n)}"
        elif _default_furniture_notes(n) and len(notes) < 80:
            notes = f"{notes} {_default_furniture_notes(n)}"
        if not reasoning:
            reasoning = "Model did not return reasoning text."
        return n, notes, reasoning
    except Exception:
        return None


def _rect_intersection_area(ax: float, ay: float, aw: float, ah: float, bx: float, by: float, bw: float, bh: float) -> float:
    ix0 = max(ax, bx)
    iy0 = max(ay, by)
    ix1 = min(ax + aw, bx + bw)
    iy1 = min(ay + ah, by + bh)
    iw = max(0.0, ix1 - ix0)
    ih = max(0.0, iy1 - iy0)
    return iw * ih


def overlap_fraction_with_rooms(
    rx: float, ry: float, rw: float, rh: float, rooms: List[Dict[str, Any]]
) -> float:
    area = max(rw * rh, 1e-9)
    inter = 0.0
    for r in rooms:
        if not isinstance(r, dict):
            continue
        if r.get("__is_carved"):
            continue
        try:
            ax = float(r.get("x", 0))
            ay = float(r.get("y", 0))
            aw = float(r.get("width", 0))
            ah = float(r.get("height", 0))
        except (TypeError, ValueError):
            continue
        inter += _rect_intersection_area(rx, ry, rw, rh, ax, ay, aw, ah)
    return min(1.0, inter / area)


def _rect_gap(ax: float, ay: float, aw: float, ah: float, bx: float, by: float, bw: float, bh: float) -> float:
    """Separation between two rectangles; 0 if touching/overlapping."""
    dx = max(0.0, max(ax, bx) - min(ax + aw, bx + bw))
    dy = max(0.0, max(ay, by) - min(ay + ah, by + bh))
    return (dx * dx + dy * dy) ** 0.5


def _neighbour_summary(rooms: List[Dict[str, Any]], rx: float, ry: float, rw: float, rh: float, max_lines: int = 14) -> str:
    """Rooms that overlap the void pick, else nearest rooms by edge gap (for LLM / UX context)."""
    cx = rx + rw * 0.5
    cy = ry + rh * 0.5
    scored: List[Tuple[Any, str]] = []
    for r in rooms:
        if not isinstance(r, dict) or r.get("__is_carved"):
            continue
        nm = str(r.get("name", "?"))
        try:
            ax = float(r.get("x", 0))
            ay = float(r.get("y", 0))
            aw = float(r.get("width", 0))
            ah = float(r.get("height", 0))
        except (TypeError, ValueError):
            continue
        ov = _rect_intersection_area(rx, ry, rw, rh, ax, ay, aw, ah)
        gap = _rect_gap(rx, ry, rw, rh, ax, ay, aw, ah)
        dist = (cx - (ax + aw * 0.5)) ** 2 + (cy - (ay + ah * 0.5)) ** 2
        key = (-ov, gap, dist)
        scored.append((key, f"- {nm} ({aw:.0f}×{ah:.0f}px @ {ax:.0f},{ay:.0f}) gap≈{gap:.0f}px"))
    scored.sort(key=lambda t: t[0])
    lines = [t[1] for t in scored[:max_lines]]
    return "\n".join(lines) if lines else "(no rooms in layout)"


def _existing_names(rooms: List[Dict[str, Any]]) -> List[str]:
    out: List[str] = []
    for r in rooms:
        if isinstance(r, dict) and r.get("name"):
            out.append(str(r["name"]).lower())
    return out


def unique_room_name(base: str, existing_lower: List[str]) -> str:
    b = (base or "user_room").lower().strip().replace(" ", "_").replace("-", "_")
    b = re.sub(r"[^a-z0-9_]+", "", b) or "user_room"
    if b not in existing_lower:
        return b
    for i in range(2, 200):
        cand = f"{b}_{i}"
        if cand not in existing_lower:
            return cand
    return f"{b}_x"


def _has_kitchen(rooms: List[Dict[str, Any]]) -> bool:
    for r in rooms:
        if isinstance(r, dict) and str(r.get("name", "")).lower() == "kitchen":
            return True
    return False


def _sanitize_inferred_name(name: str, rooms: List[Dict[str, Any]]) -> str:
    """Never add a second `kitchen` via this tool."""
    n = (name or "").lower().strip().replace(" ", "_").replace("-", "_")
    n = re.sub(r"[^a-z0-9_]+", "", n) or "home_office"
    if n == "kitchen" and _has_kitchen(rooms):
        return "utility_room"
    return n


def build_room_record(
    *,
    name: str,
    floor_index: int,
    x: float,
    y: float,
    width: float,
    height: float,
    scale: float,
    parsed: Dict[str, Any],
    notes: str,
) -> Dict[str, Any]:
    sc = float(scale or 10)
    if sc <= 0:
        sc = 10.0
    wf = round(width / sc, 1)
    hf = round(height / sc, 1)
    stem = _stem_for_category(name)
    room_stub: Dict[str, Any] = {"name": stem, "notes": notes}
    cat_v = _cat(stem, room_stub)
    facing = str(parsed.get("plot_facing", "unknown") or "unknown").lower()
    hints = _experience_hints(cat_v, -1, facing)
    return {
        "name": name,
        "floor": int(floor_index),
        "x": round(x, 1),
        "y": round(y, 1),
        "width": round(width, 1),
        "height": round(height, 1),
        "width_ft": wf,
        "depth_ft": hf,
        "area_sqft": round(wf * hf, 1),
        "area_px": round(width * height, 1),
        "windows": 1,
        "door_count": 1,
        "attached_bathroom": False,
        "attached_balcony": False,
        "notes": notes,
        "__cat": cat_v,
        "functional_zone": _functional_zone(cat_v),
        "daylight_tier": hints["daylight_tier"],
        "circulation_role": hints["circulation_role"],
        "aspect_hint": hints["aspect_hint"],
        "plot_facing": hints.get("plot_facing", facing),
        "__is_carved": False,
        "__vastu_zone": "",
        "__col_side": "",
    }


def propose_room_in_region(
    *,
    parsed: Dict[str, Any],
    layout: Dict[str, Any],
    floor_index: int,
    region: Dict[str, float],
    user_prompt: str,
    max_overlap_fraction: float = 0.28,
) -> Dict[str, Any]:
    """
    Returns dict with keys: layout (mutated copy), room, reasoning, overlap_fraction, used_llm
    """
    layout = dict(layout)
    rooms_in = list(layout.get("rooms") or [])
    if not isinstance(rooms_in, list):
        rooms_in = []

    bx = float(layout.get("built_up_x") or 0)
    by = float(layout.get("built_up_y") or 0)
    bw = float(layout.get("built_up_w") or 1)
    bh = float(layout.get("built_up_h") or 1)
    scale = float(layout.get("scale") or 10)

    rx = float(region.get("x", 0))
    ry = float(region.get("y", 0))
    rw = float(region.get("width", 0))
    rh = float(region.get("height", 0))

    min_px = max(18.0, scale * 2.5)
    if rw < min_px or rh < min_px:
        raise ValueError(f"Selected area is too small (min ~{min_px:.0f}px along each side).")

    rx = max(bx, min(rx, bx + bw - min_px))
    ry = max(by, min(ry, by + bh - min_px))
    rw = max(min_px, min(rw, bx + bw - rx))
    rh = max(min_px, min(rh, by + bh - ry))

    ov = overlap_fraction_with_rooms(rx, ry, rw, rh, rooms_in)
    if ov > max_overlap_fraction:
        raise ValueError(
            f"That rectangle overlaps existing rooms by ~{ov * 100:.0f}% of its area. "
            "Drag a box mostly over empty floor, then try again."
        )

    region_sqft = (rw / scale) * (rh / scale)
    ctx = _neighbour_summary(rooms_in, rx, ry, rw, rh)

    used_llm = False
    spec = _infer_room_openai(user_prompt, region_sqft, ctx)
    if spec:
        used_llm = True
        raw_name, notes, reasoning = spec
    else:
        raw_name, notes, reasoning = _infer_room_heuristic(user_prompt)

    pre_sanitize = raw_name
    raw_name = _sanitize_inferred_name(raw_name, rooms_in)
    if raw_name not in _ALLOWED_SET:
        raw_name = _coerce_llm_programme(raw_name) or "home_office"
        reasoning = f"{reasoning} (Programme normalised to `{raw_name}` — name was not on the allowlist.)"
    if pre_sanitize.lower() == "kitchen" and raw_name == "utility_room":
        base_note = (notes or "").strip()
        extra = "Treated as utility / dry support (single main kitchen on plan)."
        notes = f"{base_note} {extra}".strip() if base_note else extra

    existing = _existing_names(rooms_in)
    final_name = unique_room_name(raw_name, existing)

    room = build_room_record(
        name=final_name,
        floor_index=floor_index,
        x=rx,
        y=ry,
        width=rw,
        height=rh,
        scale=scale,
        parsed=parsed,
        notes=notes if final_name == raw_name else f"{notes} (renamed to `{final_name}` to stay unique.)",
    )

    if final_name != raw_name and used_llm:
        reasoning = reasoning + f" Exported as `{final_name}` because `{raw_name}` was already used."

    new_rooms = rooms_in + [room]
    layout["rooms"] = new_rooms

    return {
        "layout": layout,
        "room": room,
        "reasoning": reasoning,
        "overlap_fraction": ov,
        "used_llm": used_llm,
        "inferred_base_name": raw_name,
    }
