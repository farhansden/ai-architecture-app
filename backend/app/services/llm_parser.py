from __future__ import annotations

"""
llm_parser.py  —  GPT-4o structured-output parser
====================================================
Architecture:
  1. GPT-4o with response_format=json_schema  →  schema-enforced JSON (zero field hallucination)
  2. _normalise()                              →  type coercion & defaults
  3. _postprocess()                            →  10 deterministic business-logic fixers

Why structured outputs replace most fixers:
  - GPT-4o with json_schema CANNOT omit required fields or invent new ones.
  - The model is constrained at the token level to match the schema exactly.
  - Fixers now handle business logic only (vastu rules, room injection, floor
    assignment) — not JSON cleanup, which was their main job before.
"""

import copy
import json
import math
import re
from typing import Any, Dict, List, Optional, Tuple

from openai import OpenAI

def _build_rules_context() -> str:
    """
    Build canonical architectural rules context from architectural_rules.py.
    Single source of truth — LLM receives actual rules, not hardcoded assumptions.
    Tries multiple import paths so it works in dev, test, and production.
    """
    try:
        # Try production path first, then dev fallback
        try:
            from app.services.architectural_rules import (
                VASTU_ZONES, MUST_ADJACENT, MUST_NOT_ADJACENT,
                ROOM_DIMENSIONS, LUXURY_INDICATORS, get_budget_tier
            )
        except ImportError:
            import importlib.util as _ilu, os as _os
            _candidates = [
                _os.path.join(_os.path.dirname(__file__), "architectural_rules.py"),
                "/mnt/user-data/uploads/architectural_rules.py",
            ]
            _mod = None
            for _p in _candidates:
                if _os.path.exists(_p):
                    _s = _ilu.spec_from_file_location("architectural_rules", _p)
                    _mod = _ilu.module_from_spec(_s); _s.loader.exec_module(_mod)
                    break
            if _mod is None:
                return ""
            VASTU_ZONES      = _mod.VASTU_ZONES
            MUST_ADJACENT    = _mod.MUST_ADJACENT
            MUST_NOT_ADJACENT = _mod.MUST_NOT_ADJACENT
            ROOM_DIMENSIONS  = _mod.ROOM_DIMENSIONS
            LUXURY_INDICATORS = _mod.LUXURY_INDICATORS
        lines = ["\n══════ CANONICAL RULES (from architectural_rules.py) ══════\n"]

        lines.append("VASTU ZONES (compass → room):")
        for room, zone in sorted(VASTU_ZONES.items(), key=lambda x: x[1]):
            lines.append(f"  {room:<28} → {zone}")

        lines.append("\nMUST BE ADJACENT:")
        for room, adj in MUST_ADJACENT.items():
            lines.append(f"  {room} → {adj}")

        lines.append("\nMUST NOT SHARE WALL:")
        for room, forbidden in MUST_NOT_ADJACENT.items():
            lines.append(f"  {room} → NEVER adjacent to {forbidden}")

        lines.append("\nROOM SIZES (min | standard | luxury in ft, area sqft):")
        for room, d in ROOM_DIMENSIONS.items():
            mn = f"{d.get('min_w',0):.0f}×{d.get('min_d',0):.0f}={d.get('min_area',0):.0f}"
            lx = f"{d.get('luxury_w',d.get('min_w',0)):.0f}×{d.get('luxury_d',d.get('min_d',0)):.0f}={d.get('luxury_area',d.get('min_area',0)):.0f}"
            lines.append(f"  {room:<25} min:{mn}  lux:{lx}")

        lines.append(f"\nLUXURY THRESHOLD: ≥ ₹{LUXURY_INDICATORS['min_budget_per_sqft_luxury']:,}/sqft")
        lines.append(f"ULTRA THRESHOLD:  ≥ ₹{LUXURY_INDICATORS['min_budget_per_sqft_ultra']:,}/sqft")

        return "\n".join(lines)
    except ImportError:
        return ""   # architectural_rules.py not available — use inline rules in SYSTEM_PROMPT


_RULES_CONTEXT = _build_rules_context()



from app.config import settings


# ===========================================================================
# JSON Schema  (OpenAI Structured Outputs — strict mode)
# All fields are required; additionalProperties=false at every level.
# ===========================================================================

_ROOM_SCHEMA = {
    "type": "object",
    "properties": {
        "name":               {"type": "string"},
        "floor":              {"type": "integer"},
        "area_sqft":          {"type": "number"},
        "width_ft":           {"type": "number"},
        "depth_ft":           {"type": "number"},
        "attached_bathroom":  {"type": "boolean"},
        "attached_balcony":   {"type": "boolean"},
        "windows":            {"type": "integer"},
        "door_count":         {"type": "integer"},
        "notes":              {"type": "string"},
    },
    "required": [
        "name", "floor", "area_sqft", "width_ft", "depth_ft",
        "attached_bathroom", "attached_balcony", "windows", "door_count", "notes",
    ],
    "additionalProperties": False,
}

# Maket-grade narrative bundle (strict schema — every field required; use "" only if impossible)
_MAKET_DELIVERABLE_KEYS: Tuple[str, ...] = (
    "prose_before_geometry",
    "design_moves",
    "spatial_concept",
    "zoning_diagram_words",
    "room_table_markdown",
    "wet_core_drainage",
    "opening_schedule_markdown",
    "door_discipline",
    "guest_walkthrough",
    "family_walkthrough",
    "circulation_critique",
    "risks_mitigations",
    "anti_template_statement",
)
_MAKET_DELIVERABLE_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {k: {"type": "string"} for k in _MAKET_DELIVERABLE_KEYS},
    "required": list(_MAKET_DELIVERABLE_KEYS),
    "additionalProperties": False,
}

FLOOR_PLAN_SCHEMA = {
    "name": "floor_plan",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "plot_area_sqft":        {"type": "integer"},
            "built_up_area_sqft":    {"type": "integer"},
            "plot_width_ft":         {"type": "number"},
            "plot_depth_ft":         {"type": "number"},
            "plot_facing":           {"type": "string"},
            "setbacks": {
                "type": "object",
                "properties": {
                    "front": {"type": "number"},
                    "rear":  {"type": "number"},
                    "left":  {"type": "number"},
                    "right": {"type": "number"},
                },
                "required": ["front", "rear", "left", "right"],
                "additionalProperties": False,
            },
            "floors":                {"type": "integer"},
            "floor_height_ft":       {"type": "number"},
            "building_height_ft":    {"type": "number"},
            "basement":              {"type": "boolean"},
            "basement_area_sqft":    {"type": "integer"},
            "terrace":               {"type": "boolean"},
            "staircase_type":        {"type": "string"},
            "staircase_location":    {"type": "string"},
            "bhk_type":              {"type": "string"},
            "bedrooms":              {"type": "integer"},
            "bathrooms":             {"type": "integer"},
            "attached_bathrooms":    {"type": "integer"},
            "common_bathrooms":      {"type": "integer"},
            "toilets":               {"type": "integer"},
            "occupants":             {"type": "integer"},
            "style":                 {"type": "string"},
            "location":              {"type": "string"},
            "spatial_type":          {"type": "string"},
            "vastu_compliant":       {"type": "boolean"},
            "vastu_notes":           {"type": "array", "items": {"type": "string"}},
            "budget":                {"type": "integer"},
            "budget_per_sqft":       {"type": "integer"},
            "rooms":                 {"type": "array", "items": _ROOM_SCHEMA},
            "entrance_location":     {"type": "string"},
            "main_door_width_ft":    {"type": "number"},
            "corridor_width_ft":     {"type": "number"},
            "lift":                  {"type": "boolean"},
            "utility_areas":         {"type": "array", "items": {"type": "string"}},
            "parking": {
                "type": "object",
                "properties": {
                    "car_spaces":         {"type": "integer"},
                    "two_wheeler_spaces": {"type": "integer"},
                    "covered":            {"type": "boolean"},
                    "location":          {"type": "string"},
                },
                "required": ["car_spaces", "two_wheeler_spaces", "covered", "location"],
                "additionalProperties": False,
            },
            "outdoor": {
                "type": "object",
                "properties": {
                    "garden":          {"type": "boolean"},
                    "garden_area_sqft":{"type": "integer"},
                    "swimming_pool":   {"type": "boolean"},
                    "courtyard":       {"type": "boolean"},
                    "sit_out":         {"type": "boolean"},
                    "deck":            {"type": "boolean"},
                    "compound_wall":   {"type": "boolean"},
                    "gate_width_ft":   {"type": "number"},
                },
                "required": [
                    "garden", "garden_area_sqft", "swimming_pool",
                    "courtyard", "sit_out", "deck", "compound_wall", "gate_width_ft",
                ],
                "additionalProperties": False,
            },
            "services": {
                "type": "object",
                "properties": {
                    "overhead_tank":        {"type": "boolean"},
                    "sump":                 {"type": "boolean"},
                    "solar_panels":         {"type": "boolean"},
                    "generator_room":       {"type": "boolean"},
                    "electrical_room":      {"type": "boolean"},
                    "water_treatment":      {"type": "boolean"},
                    "septic_tank_location": {"type": "string"},
                },
                "required": [
                    "overhead_tank", "sump", "solar_panels",
                    "generator_room", "electrical_room",
                    "water_treatment", "septic_tank_location",
                ],
                "additionalProperties": False,
            },
            "special_requirements": {"type": "array", "items": {"type": "string"}},
            "accessibility":         {"type": "boolean"},
            "home_office":           {"type": "boolean"},
            "home_gym":              {"type": "boolean"},
            "home_theater":          {"type": "boolean"},
            "study_room":            {"type": "boolean"},
            "servant_quarters":      {"type": "boolean"},
            "pooja_room":            {"type": "boolean"},
            "guest_room":            {"type": "boolean"},
            "store_room":            {"type": "boolean"},
            "maket_deliverable":     _MAKET_DELIVERABLE_SCHEMA,
        },
        "required": [
            "plot_area_sqft", "built_up_area_sqft", "plot_width_ft", "plot_depth_ft",
            "plot_facing", "setbacks", "floors", "floor_height_ft", "building_height_ft",
            "basement", "basement_area_sqft", "terrace", "staircase_type",
            "staircase_location", "bhk_type", "bedrooms", "bathrooms",
            "attached_bathrooms", "common_bathrooms", "toilets", "occupants",
            "style", "vastu_compliant", "vastu_notes", "budget", "budget_per_sqft",
            "rooms", "entrance_location", "main_door_width_ft", "corridor_width_ft",
            "lift", "utility_areas", "parking", "outdoor", "services",
            "special_requirements", "accessibility", "home_office", "home_gym",
            "home_theater", "study_room",             "servant_quarters", "pooja_room",
            "guest_room", "store_room", "maket_deliverable",
            "location", "spatial_type",
        ],
        "additionalProperties": False,
    },
}


# ===========================================================================
# System prompt  (architect-grade, exhaustive)
# ===========================================================================

SYSTEM_PROMPT = """You are a licensed senior Indian residential architect with 25 years of practice.
You have designed homes across every budget — from a ₹8 lakh village house in Rajasthan
to a ₹12 crore villa in Juhu. You know NBC 2016, MCGM bylaws, Vastu Shastra, and Indian
family lifestyle from first principles — not from lookup tables.

You compete with premium tools like Maket: every plan is ONE bespoke composition for THIS family,
THIS climate band, THIS plot, THIS budget — never a template grid of mirror bedrooms or hotel corridors.

{rules_context}
══════════════════════════════════════════════════════════════
NON-NEGOTIABLE PRODUCT RULES (Indian premium residential)
══════════════════════════════════════════════════════════════
• SINGLE KITCHEN ONLY: exactly ONE room named "kitchen" is the cook space. NEVER emit separate
  dry_kitchen, wet_kitchen, second_kitchen, or duplicate cook rooms. Heavy Indian cooking =
  segregated wet zone + tall wall INSIDE the same kitchen + utility_room (wash/laundry/dry only).
• NO TEMPLATE GRID: forbid mirror-image bedroom clones and identical strip bedrooms; vary shapes
  with daylight, privacy, structure, or outdoor edge logic in notes + maket_deliverable.
• ZONING GRADIENT: PUBLIC (parking/porch/foyer/drawing) → SEMI-PRIVATE (dining, pooja from family space)
  → PRIVATE (bedrooms) → SERVICE (kitchen/utility/store/rear baths). Never bedroom doors off parking line;
  never pooja trapped on the kitchen smoke path without a buffer.
• DOOR / WINDOW INTENT: document in maket_deliverable (openings + door discipline); WC = shaft/frosted/high sill;
  typical internal door 3ft where load-bearing, min ~2ft-6in landing in front of swing; no WC door opening
  toward dining head or pooja primary view.
• MASTER SUITE + SERVICE: master_bedroom gets its own door into master_bedroom_bathroom; if store_room is in the
  programme, describe a direct bedroom-to-store door (storage is not reached only via the ensuite). Common /
  family toilets: circulation-first entry (passage/corridor), not off a bedroom façade as the main opening.
• WET SPINE: cluster kitchen + utility + baths along ONE service spine; mention duct/loft shaft location
  if future G+1 is plausible.

══════════════════════════════════════════════════════════════
YOUR PROCESS — follow this exactly, every time
══════════════════════════════════════════════════════════════

STEP 1 — SITE-SPECIFIC PROSE (stored in JSON field maket_deliverable.prose_before_geometry)
Write 3–6 sentences: WHO lives here, climate/locust logic, the 6–10 bullet "design moves" summary is
expanded in maket_deliverable.design_moves (not generic packing).

STEP 2 — SPATIAL CONCEPT
Put one sentence in maket_deliverable.spatial_concept (not a hotel-suite cliché unless brief demands it).

STEP 3 — MAKET DELIVERABLE BUNDLE (same JSON object — contractor-grade)
Fill EVERY key in maket_deliverable with real prose (markdown tables allowed inside string fields):
  zoning_diagram_words (N/E/S/W anchors), room_table_markdown (name|approx L×W|area|adjacency|furniture),
  wet_core_drainage, opening_schedule_markdown, door_discipline, numbered guest_walkthrough + family_walkthrough,
  circulation_critique, three risks_mitigations, anti_template_statement (what you refused to do).

STEP 4 — VALIDATE YOUR ROOM LIST (before finalising JSON)
Check ELITE SPATIAL-PLANNING ENGINE + ADJACENCY RULES below:
  - kitchen adjacent to dining_room? dining BETWEEN living and kitchen in intent? ✓
  - pooja_room opens off living_room or foyer? no toilet adjacency in notes? ✓
  - master_bedroom_bathroom adjacent to master_bedroom? ✓
  - If store_room exists: state direct suite access from master_bedroom (not only through ensuite WC);
    common_bathroom / family toilet opens only from passage/corridor — never a bedroom as primary entry ✓
  - no toilet above pooja_room/kitchen (duplex)? ✓
  - servant_quarters has rear access, not through living? ✓
  - zoning gradient PUBLIC → SEMI-PRIVATE → PRIVATE honoured (see engine)? ✓
  - NO extra kitchen room types ✓
If any fail, fix them before outputting JSON.

STEP 5 — OUTPUT THE JSON
STOREY COUNT (non-negotiable): Set "floors" to 1 unless the ORIGINAL BRIEF explicitly asks for more than
one storey (e.g. duplex, triplex, G+1 / G+2, two-storey / two-story, second floor, upper floor, maisonette).
If the user only specifies plot size, BHK, style, or rooms without multi-storey language, floors MUST be 1.

Every room "notes" field is a drawing instruction. Use EXACT keywords — the SVG renderer
matches on these precisely:

  KITCHEN:   "island counter"       → island with bar stools drawn
             "u-shaped"             → U-layout with 3 counters
  BATHROOM:  "freestanding soaking tub" → luxury tub drawn
             "double vanity"        → twin basins drawn
             "rain shower"          → rain shower head drawn
             (ALL THREE required for full 5-fixture luxury bath)
  BEDROOM:   "king bed"             → king-size bed drawn
             "queen bed"            → queen-size bed drawn
             "single bed"           → narrow single bed drawn
  LIVING:    "l-sofa"               → L-shaped sofa layout
             "luxury"               → wider TV unit + larger sofa
  DINING:    "8-seater"             → 8-chair table
             "6-seater"             → 6-chair table
  OFFICE:    "built-in shelves"     → bookshelf wall drawn
  FOYER:     "double height"        → diagonal void markers drawn
  PARKING:   "2-car"                → 2 car symbols drawn

Also always include: Vastu zone, quality tier (luxury/standard), adjacency relationships.
Example: "southeast Vastu fire zone, modular island counter with seating, high-end appliances, pass door to dining on south wall"

══════════════════════════════════════════════════════════════
INDIAN CIRCULATION & PRIVACY (industry standard — follow on every project)
══════════════════════════════════════════════════════════════
APPROACH SEQUENCE (ground floor, front → back):
  1) Vehicle / entry: car_porch → sit_out (verandah) → foyer — guests never walk through
     bedrooms; parking does not open directly into kitchen or pooja.
  2) Social core: living_room is the hub; dining_room is adjacent to living and between
     living and kitchen (shortest servery path). First-time visitor path: foyer →
     living → dining → (glance) kitchen; not through wet areas.
  3) Sacred: pooja_room opens from living or foyer (visible from family space, not from
     bathroom or kitchen). Notes must say "opens from living" or "opens from foyer".
  4) Service rear: ONE kitchen (SE) + utility appendage in sequence; store and utility
     near kitchen; bathrooms / powder room clustered for wetwall efficiency — powder
     near entry for guests, family baths away from kitchen/pooja.
  5) Stairs: staircase(0) sits in the circulation band — next to or opening from
     corridor / foyer, not inside kitchen. Connects to family_lounge or FF corridor.
UPPER FLOOR: staircase_landing → family_lounge or corridor → bedrooms. Bedrooms are
  never entered from parking or kitchen below; they are private off the hall.
WINDOWS (notes per room): living/dining: prefer north/east light; kitchen: east+
  southeast vent; toilets: high sill/frosted toward shaft or NW; bedrooms: one opening
  to exterior façade, cross-ventilate where budget allows.

══════════════════════════════════════════════════════════════
ELITE SPATIAL-PLANNING ENGINE (architect-grade — never random placement)
══════════════════════════════════════════════════════════════
Treat every brief as structural + circulation + plumbing + behaviour first.

BEFORE emitting room JSON, reason in this inward order:
  (1) Entry flow   (2) Zoning tiers   (3) Circulation spine   (4) Service/wet core
  (5) Staircase tied to foyer/corridor   (6) Public   (7) Semi-private   (8) Private

══════════════════════════════════════════════════════════════
UNIFIED COMPOSITION — ONE HOME, NOT RECTANGLE PACKING
══════════════════════════════════════════════════════════════
The house is ONE architectural composition. Your programme must not read as disconnected boxes.

Mandatory narrative discipline (echoed by the deterministic engine):
  • Buildable footprint → zoning → circulation spine + stair → living/drawing as PRIMARY SOCIAL ANCHOR
    → dining as CONNECTOR (living↔kitchen + spine) → compact kitchen+utility+storage CLUSTER
    → bedrooms emerging from FF lounge/corridor hierarchy → daylight & cross-vent notes per habitable room
    → privacy layering → Vastu polish WITHOUT sacrificing flow, structure, or ventilation.

  • foyer / entrance_foyer: notes MUST tie arrival to living or drawing (sight-line control, transition);
    avoid orphan entry pockets with no stated relationship to the social core.

  • dining_room: notes MUST state bridge role between gathering space and kitchen/service — never a
    leftover strip or corridor mimic; keep corridor_width_ft modest unless luxury/courtyard brief.

  • Single-storey (floors==1): deterministic layout places dining with the single kitchen in one
    horizontal meal band directly under living/drawing — programme dining+kitchen as one service meal
    zone; corridor follows that band, then bedrooms (not between dining and kitchen).

  • FF bedrooms: reached via family_lounge / corridor story — not arbitrary blocks pasted at the edge.

ZONE MAP — enforce privacy TRANSITION street → dwelling (never invert):
  PUBLIC:        foyer, living_room (= drawing-room / guest-facing buffer near entry)
                 Car/sit-out are pre-foyer approach only — bedrooms never peel off parking line.
  SEMI-PRIVATE:  dining_room, pooja_room, family_lounge (family ritual + meals, not “leftover strips”)
  PRIVATE:       bedrooms, quiet study zones, sleeping-related spaces
  SERVICE:       kitchen (sole cook room) + utility_room, toilets, storage, servant if any

MANDATORY INTENT PER SPACE:
  ENTRY / FOYER   — Welcomes; shields bedrooms and WCs from first sight-line.
  LIVING ROOM     — Near entrance band; daylight; NOT consumed as pointless passage; sofas fit.
  DINING ROOM     — Near kitchen; acts as SERVERY node — NOT elongated fake-corridor footprint.
  KITCHEN         — Touches dining + utility; ventilation explicit in notes; SE/E preference when vastu —
                    never maroon an island programme without dining touch.
  UTILITY         — Direct kitchen connection + practical drainage wording in notes.
  MASTER SUITE    — Max privacy SW/W tendency when vastu; avoid gratuitous PRIMARY wall with living;
                     attached bath in program.
  ELDERS BEDROOM  — Ground floor preference when occupants elderly; WC reach; minimise stair dependence.
  KIDS ROOMS      — Quieter zone; daylight; sensible furniture depth in sizing.
  PUJA ROOM       — Calm NE/E; never “circulation leftovers”; forbid toilet-share-wall language in notes.
  TOILETS         — Wet-wall stacking across floors where duplex; ventilation; no boast opening straight
                     into dining view in notes/layout intent.
  STAIRCASE       — Efficient circulation; opens off foyer/spine — never hack through usable room middles.
  CORRIDORS       — Min dead-end slivers; purposeful width (NBC min); halls feed bedrooms cleanly.
  PARKING/CAR_PORCH — Realistic manoeuvre widths in notes when 2-car; gate-to-car clearance.

OUTPUT MUST FEEL: walkable, furnishable for Indian households, plausible wet stacks, daylight logic,
climate-aware openings, socially correct privacy gradient — NEVER random boxes or disconnected zones.

VASTU: Prefer SE kitchen, SW master FF, NE pooja, N/E gathering light — but NEVER violate circulation,
usable spans (NBC min), usability, ventilation, or plumbing practicality for symbolism alone.

══════════════════════════════════════════════════════════════
SCHEMA RULES (arithmetic must be correct)
══════════════════════════════════════════════════════════════

built_up_area_sqft = (plot_width - left_sb - right_sb) × (plot_depth - front_sb - rear_sb) × floors
budget_per_sqft    = budget ÷ built_up_area_sqft

FLOOR ASSIGNMENTS for G+1 duplex:
  floor=0: living_room, dining_room, kitchen, home_office, pooja_room,
           car_porch, sit_out, foyer, staircase, corridor, servant_quarters,
           servant_bathroom, utility_room, store_room, common_bathroom, guest_powder_room
  floor=1: ALL bedrooms + attached bathrooms, walk_in_wardrobe, corridor, family_lounge,
           terrace, balcony, staircase_landing
  G+1 SPACE USE (senior practice): Avoid a single empty terrace or void consuming >35% of a floor plate.
    On floor=1 when built width ≥24ft, include study(1) OR library(1) off the family lounge/corridor spine.
    Split large outdoor into balcony + smaller terrace in JSON (two rooms) rather than one anonymous slab.

MANDATORY ROOMS — never omit:
  Always:          living_room(0), kitchen(0), store_room(0)
  2BHK+:           dining_room(0)
  vastu=true:      sit_out(0), pooja_room(0)
  floors≥2:        staircase(0), corridor(0), corridor(1), family_lounge(1)
  cars≥2:          car_porch(0) at 26ft width (fits 2 SUVs in 36ft built-up)
  servant:         servant_quarters(0) + servant_bathroom(0)
  luxury+:         walk_in_wardrobe(1), enlarged kitchen+utility wet narrative on notes, foyer(0) at 10×10ft
  ultra:           all luxury + double_height_foyer, private terrace from master

area_sqft = width_ft × depth_ft  (always verify this arithmetic)

location: City/area name extracted from brief. e.g. "Juhu Mumbai", "Koramangala Bangalore".
  CRITICAL: use "Juhu Mumbai" not just "Mumbai" — area name drives setback rules.
spatial_type: open_plan | traditional | courtyard | linear | split_private
  Choose based on family lifestyle. Default: "traditional".
"""

USER_PROMPT_TEMPLATE = (
    "### DESIGN BRIEF\n\n{prompt}\n\n"
    "Generate the complete JSON schema. Apply every rule in SYSTEM + Elite Spatial-Planning Engine — "
    "no random layouts; zoning PUBLIC→SEMI-PRIVATE→PRIVATE; dining as circulation node toward kitchen.\n"
    "Populate maket_deliverable fully (Maket-grade narrative + tables in markdown strings). "
    "Use exactly one kitchen room; express wet prep + tall wall + utility in kitchen/utility notes — "
    "never add dry_kitchen or wet_kitchen rooms.\n\n"
)


# ===========================================================================
# Room sizing lookup — budget-tier aware
# Format: (area_sqft, width_ft, depth_ft, windows, doors)
# These are STANDARD TIER defaults. Economy and luxury are applied by
# _fix_rooms() using get_room_size_for_budget() from architectural_rules.
# ===========================================================================

_ROOM_SIZING: Dict[str, tuple] = {
    # Standard tier (₹1,200–2,500/sqft) — used as default fallback
    "master_bedroom":       (156.0, 13.0, 12.0, 2, 2),
    "master_bathroom":      (40.0,   5.0,  8.0, 1, 1),
    "master_bedroom_bathroom": (40.0, 5.0, 8.0, 1, 1),
    "parents_bedroom":      (144.0, 12.0, 12.0, 2, 2),
    "parents_bedroom_bathroom": (40.0, 5.0, 8.0, 1, 1),
    "parents_bathroom":     (40.0,   5.0,  8.0, 1, 1),
    "bedroom":              (121.0, 11.0, 11.0, 2, 1),
    "bathroom":             (40.0,   5.0,  8.0, 1, 1),
    "living_room":          (168.0, 14.0, 12.0, 3, 2),
    "drawing_room":        (154.0, 13.0, 11.8, 2, 2),
    "dining_room":          (110.0, 11.0, 10.0, 1, 1),
    "kitchen":              (100.0, 10.0, 10.0, 2, 1),
    "wet_kitchen":          (64.0,   8.0,  8.0, 1, 1),
    "dry_kitchen":          (90.0,   9.0, 10.0, 2, 1),
    "pooja_room":           (30.0,   5.0,  6.0, 1, 1),
    "store_room":           (30.0,   5.0,  6.0, 0, 1),
    "utility_room":         (48.0,   6.0,  8.0, 1, 1),
    "corridor":             (55.0,   4.5, 12.0, 0, 0),
    "sit_out":              (60.0,  10.0,  6.0, 0, 1),
    "car_porch":            (160.0, 13.0, 12.0, 0, 0),
    "balcony":              (40.0,   8.0,  5.0, 0, 1),
    "staircase":            (60.0,   6.0, 10.0, 0, 2),
    "common_bathroom":      (40.0,   5.0,  8.0, 1, 1),
    "guest_room":           (121.0, 11.0, 11.0, 2, 1),
    "guest_bedroom":        (121.0, 11.0, 11.0, 2, 1),
    "study":                (100.0, 10.0, 10.0, 1, 1),
    "home_office":          (100.0, 10.0, 10.0, 2, 1),
    "servant_quarters":     (90.0,   9.0, 10.0, 1, 1),
    "servant_bathroom":     (25.0,   4.0,  6.0, 1, 1),
    "family_lounge":        (100.0, 10.0, 10.0, 2, 1),
    "guest_powder_room":    (30.0,   5.0,  6.0, 1, 1),
    "walk_in_wardrobe":     (36.0,   6.0,  6.0, 0, 1),
    "terrace":              (100.0, 10.0, 10.0, 0, 1),
    "foyer":                (36.0,   6.0,  6.0, 0, 1),
    "entrance_foyer":       (36.0,   6.0,  6.0, 0, 1),
}

_GROUND_FLOOR_ROOMS = {
    # Public / social / service zone — always ground floor
    "living_room", "dining_room", "kitchen", "pooja_room", "utility_room",
    "store_room", "car_porch", "sit_out", "common_bathroom", "staircase",
    # Servant / guest — always ground floor
    "servant_quarters", "guest_room",
    # Special-use rooms that belong on ground floor (study can be floor=1 — see SYSTEM G+1 rules)
    "home_office", "guest_powder_room", "powder_room",
    "foyer", "entrance_foyer",
    # NOTE: family_lounge / lounge intentionally NOT here.
    # LLM correctly assigns floor based on user intent:
    #   "reading nook connecting bedrooms" → floor=1 ✓
    #   "ground floor sitting area"        → floor=0 ✓
}
_UPPER_FLOOR_ROOMS = {
    # Named bedroom variants the LLM explicitly produces
    "master_bedroom", "parents_bedroom", "bedroom",
    # Attached bathrooms — must follow their parent bedroom to upper floor
    "master_bathroom", "parents_bathroom",
    # NOTE: "corridor" intentionally REMOVED from this set.
    # Corridors now exist on EVERY floor (G+1 needs corridor on floor=0 AND floor=1).
    # _fix_floor_assignments must preserve the floor number the LLM assigned.
    # Forcing all corridors to floor=1 breaks the GF circulation spine.
    "balcony",
    # Walk-in wardrobe always goes with master bedroom — CRITICAL for luxury suites
    "walk_in_wardrobe", "wardrobe",
    # Terrace accessible from upper floor — always floor=1 for G+1
    "terrace",
    # Family lounge connecting bedrooms — LLM assigns this correctly
    # DO NOT add here; trust LLM assignment (see _fix_floor_assignments comments)
}

CORE_DEFAULTS: Dict[str, Any] = {
    "plot_area_sqft":       1200,
    "built_up_area_sqft":   720,
    "plot_width_ft":        30.0,
    "plot_depth_ft":        40.0,
    "plot_facing":          "unknown",
    "setbacks":             {"front": 5.0, "rear": 3.0, "left": 2.0, "right": 2.0},
    "floors":               1,
    "floor_height_ft":      10.0,
    "building_height_ft":   10.0,
    "basement":             False,
    "basement_area_sqft":   0,
    "terrace":              False,
    "staircase_type":       "none",
    "staircase_location":   "none",
    "bhk_type":             "2BHK",
    "bedrooms":             2,
    "bathrooms":            2,
    "attached_bathrooms":   1,
    "common_bathrooms":     1,
    "toilets":              0,
    "occupants":            4,
    "style":                "modern",
    "location":     "",
    "spatial_type": "traditional",
    "vastu_compliant":      False,
    "vastu_notes":          [],
    "budget":               0,
    "budget_per_sqft":      0,
    "rooms":                [],
    "entrance_location":    "front_center",
    "main_door_width_ft":   4.0,
    "corridor_width_ft":    4.0,    # NBC 2016 minimum (corrected from 3.5ft)
    "lift":                 False,
    "utility_areas":        ["washing_area", "drying_yard"],
    "parking":  {"car_spaces": 1, "two_wheeler_spaces": 0, "covered": True, "location": "front"},
    "outdoor":  {
        "garden": False, "garden_area_sqft": 0, "swimming_pool": False,
        "courtyard": False, "sit_out": True, "deck": False,
        "compound_wall": True, "gate_width_ft": 12.0,
    },
    "services": {
        "overhead_tank": True, "sump": True, "solar_panels": False,
        "generator_room": False, "electrical_room": False,
        "water_treatment": False, "septic_tank_location": "rear_right",
    },
    "special_requirements": [],
    "accessibility":        False,
    "home_office":          False,
    "home_gym":             False,
    "home_theater":         False,
    "study_room":           False,
    "servant_quarters":     False,
    "pooja_room":           False,
    "guest_room":           False,
    "store_room":           False,
    "maket_deliverable":    {k: "" for k in _MAKET_DELIVERABLE_KEYS},
}

_FULL_VASTU_NOTES = [
    "bathrooms_northwest",
    "entrance_northeast",
    "kitchen_southeast",
    "living_room_north",
    "master_bedroom_southwest",
    "parents_bedroom_northwest",
    "pooja_room_northeast",
    "staircase_south_or_southwest",
    "store_south",
]


# ===========================================================================
# Public API
# ===========================================================================

def parse_architecture_prompt(prompt: str) -> Dict[str, Any]:
    if not isinstance(prompt, str) or not prompt.strip():
        return {"error": "Prompt must be a non-empty string"}
    prompt = prompt.strip()

    result = _parse_with_openai(prompt)
    if result is not None:
        return result

    return {"error": "Parsing failed — OpenAI API unavailable or returned invalid data"}



# ===========================================================================
# GPT-4o backend — Three-call senior architect pipeline
# Call 1: Free reasoning (architect thinks, no schema constraint)
# Call 2: Structured JSON (schema-enforced, informed by Call 1)
# Call 3: Validation (architect checks own work, Python fixes critical errors)
# ===========================================================================

_REASONING_SYSTEM = """You are a senior Indian architect with 25 years of practice.
Given a house brief, think through it as a professional — not as a form-filler.

Compute first:
  footprint = (plot_w - left_sb - right_sb) × (plot_d - front_sb - rear_sb)
  built_up  = footprint × floors
  budget_per_sqft = budget ÷ built_up
  tier = economy(<1200) | standard(1200-2500) | premium(2500-5000) | luxury(5000-12000) | ultra(12000+)

Apply the elite spatial-planning sequence BEFORE budgeting rooms:
 (1)→entry flow (2)→PUBLIC/SEMI-PRIVATE/PRIVATE/SERVICE tiers (3)→circulation spine
 (4)→service core (5)→stair landing logic (6)→public placement (7)→semi-private (8)→private.

Then reason:
1. WHO is this family? (lifestyle, daily routine, entertaining habits — from budget+location)
2. WHAT ARE THE 3 NON-NEGOTIABLE DESIGN MOVES for this plot, facing, and family?
3. WHAT WOULD YOU NEVER COMPROMISE on at this budget tier?
4. WHAT DOES THE NOTES FIELD NEED TO SAY for each key room? (notes drive what gets drawn)
5. CIRCULATION: spell "approach → foyer → living → dining → kitchen/service" plus FF hall privacy.
   Dining must read as NODE not corridor; toilets not visible from dining in intent.
6. WHERE are wet zones (baths, kitchen) stacked or aligned relative to pooja and entry?
7. ELDERS / KIDS: ground-floor elder bedroom? quieter kids zone? staircase dependency called out?
8. MAKET NARRATIVE: outline maket_deliverable — prose_before_geometry, design_moves bullets,
   walkthroughs (guest vs family), opening + door discipline, wet spine + drainage story,
   circulation_critique, three risks, anti-template refusal.

Be specific. A senior architect has a point of view.
9. SPATIAL TYPE — decide one: open_plan | traditional | courtyard | linear | split_private
   open_plan for modern entertaining families. traditional for joint/Vastu-strict families.
   Include spatial_type in your reasoning so Call 2 uses it correctly.
Output: 280-450 words of professional reasoning covering zoning tiers, circulation spine, elderly/kids placement,
and Maket-style narrative scaffolding. NO JSON here."""

_VALIDATION_SYSTEM = """You are a licensed NBC 2016 inspector and Vastu consultant.
Check the room program against these exact rules:

VASTU (when vastu_compliant=true):
  pooja_room → NE zone (top-left for east-facing). NEVER in SE or S.
  kitchen → SE zone. NEVER in NE, SW, or N.
  master_bedroom → SW zone (first floor, bottom-right for east-facing).
  staircase → S or SW. NEVER NE.
  toilet → NEVER in NE, SW, N, or SE zones.
  toilet on floor=1 → NEVER directly above pooja_room or kitchen on floor=0.

ADJACENCY + ZONING (non-negotiable):
  kitchen → must touch dining_room (shared wall with pass door)
  dining_room → logically between living-room buffer and kitchen (servery / meal node intent)
  living_room → public buffer — narrative must NOT place WC/bedroom as first interior hit from entry
  master_bedroom → must have master_bedroom_bathroom attached; if store_room in programme, notes must
    describe a separate door from the sleeping zone to storage (not implied access only through the WC)
  common_bathroom / family toilet → primary door from corridor/passage/rear spine only (never bedroom-first)
  pooja_room → must open off living_room or foyer (not isolated); forbid toilet-wall adjacency wording
  servant_quarters → must NOT share wall with master_bedroom
  kitchen → must NOT share wall with pooja_room
  utility_room → must articulate connection to kitchen in room notes/program

QUALITY BAR (reject incoherent programs):
  Any bedroom or WC opening directly off car_porch storyline? corridor-only dining footprint?
  stair not linked to foyer/circulation spine? duplexer toilets not stacked without justification?

NBC 2016 MINIMUMS:
  habitable room: min 100sqft, min side 8ft
  kitchen: min 54sqft
  corridor: min 4ft width
  bathroom: min 25sqft

MANDATORY ROOMS (floors≥2):
  corridor on floor=0 AND floor=1
  family_lounge on floor=1
  staircase on floor=0

Reply in EXACTLY this format:
ISSUES: <issue1>, <issue2> OR "NONE"
FIX: <the single most critical fix> OR "NONE"
SEVERITY: CRITICAL | WARNING | NONE"""


def _apply_validation_fixes(result: dict, validation: str) -> dict:
    """
    Apply critical geometric fixes from Call 3 validation output.
    CRITICAL severity → runs full emergency injection safety net.
    WARNING severity  → logged only (design decisions stay with LLM).
    """
    if not validation.strip() or "NONE" in validation:
        return result

    # CRITICAL: run full emergency injection as safety net
    if "CRITICAL" in validation:
        print("[parser] Validation CRITICAL — running emergency injection safety net")
        result = _emergency_inject_missing_rooms(result)

    rooms  = result.get("rooms", [])
    floors = int(result.get("floors", 1))

    # Fix: missing corridor on any floor
    if "corridor" in validation.lower() and "missing" in validation.lower():
        for fl_idx in range(floors):
            has_corr = any(
                "corridor" in r.get("name","")
                and int(r.get("floor",0)) == fl_idx
                for r in rooms
            )
            if not has_corr:
                sb  = result.get("setbacks") or {}
                bw  = float(result.get("plot_width_ft",36)) - float(sb.get("left",2)) - float(sb.get("right",2))
                cw  = max(float(result.get("corridor_width_ft",5.0)), 5.0)
                rooms.append({
                    "name": "corridor", "floor": fl_idx,
                    "width_ft": round(bw,1), "depth_ft": cw,
                    "area_sqft": round(bw*cw,1),
                    "attached_bathroom": False, "attached_balcony": False,
                    "windows": 0, "door_count": 0,
                    "notes": f"floor {fl_idx} corridor — added by validation pass",
                })
                print(f"[parser] Validation fix: added corridor on floor {fl_idx}")

    # Fix: missing family_lounge for G+1
    names = {r.get("name","") for r in rooms}
    if floors >= 2 and "family_lounge" not in names:
        rooms.append({
            "name": "family_lounge", "floor": 1,
            "area_sqft": 120.0, "width_ft": 12.0, "depth_ft": 10.0,
            "attached_bathroom": False, "attached_balcony": False,
            "windows": 2, "door_count": 1,
            "notes": "first floor family lounge — added by validation pass",
        })
        print("[parser] Validation fix: added family_lounge on floor 1")

    result["rooms"] = rooms
    return result


_MULTI_STOREY_HINT_RE = re.compile(
    r"\b(?:"
    r"g\s*\+\s*[1-9]|g\s*plus\s*[1-9]|g\s*\.\s*[1-9]|"
    r"duplex|triplex|"
    r"multi(?:[\s-]?storey|[\s-]?story)|"
    r"(?:two|three|2|3)[\s-]?(?:storey|story|storied)|"
    r"(?:first|second|upper)\s+floor|upper\s+(?:floor|level)|"
    r"(?:two|2)[\s-]?(?:level|tier)s?\s+(?:home|house)|"
    r"double\s+floor|additional\s+floor|extra\s+floor|"
    r"maisonette|stacked\s+floors?|split\s+levels?"
    r")\b",
    re.I,
)


def _user_explicit_multi_storey(user_prompt: str) -> bool:
    return bool(user_prompt and _MULTI_STOREY_HINT_RE.search(user_prompt.strip()))


def _clamp_single_floor_if_implicit(user_prompt: Optional[str], out: Dict[str, Any]) -> Dict[str, Any]:
    """
    Unless the brief explicitly requests multi-storey, force floors=1 and drop upper-floor +
    staircase programme pieces so layouts stay single-level.
    """
    if not user_prompt or not isinstance(user_prompt, str):
        return out
    if _user_explicit_multi_storey(user_prompt):
        return out
    floors = int(out.get("floors", 1) or 1)
    if floors <= 1:
        out["floors"] = 1
        return out
    out = copy.deepcopy(out)
    out["floors"] = 1
    kept: List[Dict[str, Any]] = []
    for r in out.get("rooms") or []:
        name = str(r.get("name", "")).lower()
        fl = int(r.get("floor", 0) or 0)
        if fl >= 1:
            continue
        if "staircase" in name or "stair_void" in name:
            continue
        rr = dict(r)
        rr["floor"] = 0
        kept.append(rr)
    out["rooms"] = kept
    print(
        "[parser] Brief did not request multi-storey - floors collapsed to 1; "
        "upper-floor rooms and stairs removed."
    )
    return out


def _parse_with_openai(prompt: str) -> Optional[Dict[str, Any]]:
    """
    Three-call senior architect pipeline.
    Call 1 — architect THINKS (free text, no schema, temperature=0.3)
    Call 2 — architect OUTPUTS (schema JSON, temperature=0.0, informed by Call 1)
    Call 3 — architect CHECKS (validation, Python applies geometric fixes)
    """
    api_key = settings.openai_api_key or ""
    if not api_key:
        print("[parser] ERROR: OPENAI_API_KEY not set in environment")
        return None
    if getattr(settings, "use_local_llm", False):
        print(
            "[parser] Note: USE_LOCAL_LLM is set but parse_architecture_prompt requires "
            "OpenAI structured outputs (json_schema + maket_deliverable); Ollama path is not implemented."
        )
    try:
        client = OpenAI(api_key=api_key)
        model  = settings.openai_model  # gpt-4o

        # ── CALL 1: Architect THINKS (no schema, free reasoning) ─────────────
        print("[parser] Call 1: architect reasoning...")
        # Inject live rules from architectural_rules.py if available
        rules_suffix = ("\n\n" + _RULES_CONTEXT) if _RULES_CONTEXT else ""
        design_reasoning = ""
        try:
            r1 = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": _REASONING_SYSTEM + rules_suffix},
                    {"role": "user", "content":
                        "DESIGN BRIEF:\n" + prompt + "\n\n"
                        "Compute budget_per_sqft, identify the tier, then reason through "
                        "the 3 non-negotiable design moves and what the notes field must say "
                        "for each key room to get the right furniture/fixtures drawn."},
                ],
                temperature=0.3,
                max_tokens=1000,
            )
            design_reasoning = (r1.choices[0].message.content or "").strip()
            print(f"[parser] Reasoning ({len(design_reasoning)} chars): {design_reasoning[:150]}...")
        except Exception as call1_exc:
            # Non-fatal: Call 1 failed. Call 2 proceeds without reasoning context.
            # Quality degrades slightly — LLM uses SYSTEM_PROMPT alone.
            print(f"[parser] Call 1 failed (non-fatal): {call1_exc}. Proceeding to Call 2.")

        # ── CALL 2: Architect OUTPUTS (schema-enforced JSON) ──────────────────
        print("[parser] Call 2: generating room program...")
        r2 = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT.replace("{rules_context}", _RULES_CONTEXT or "")},
                {"role": "user", "content":
                    "ORIGINAL BRIEF:\n" + prompt + "\n\n"
                    "YOUR ARCHITECTURAL REASONING:\n" + design_reasoning + "\n\n"
                    "Generate the complete JSON room programme + maket_deliverable bundle.\n"
                    "maket_deliverable must be filled with contractor-grade prose (markdown tables inside strings are OK).\n"
                    "Every room notes field is a drawing instruction — be specific: "
                    "Vastu zone, furniture, fixtures, quality level, adjacency. "
                    "Kitchen example: 'southeast Vastu fire zone, single modular kitchen, "
                    "L-counter + hob + sink on segregated wet wall, tall unit run, pass door to dining, "
                    "utility door to wash/laundry — NOT a second kitchen'"},
            ],
            temperature=0.0,
            max_tokens=8192,
            response_format={
                "type": "json_schema",
                "json_schema": FLOOR_PLAN_SCHEMA,
            },
        )
        content = (r2.choices[0].message.content or "").strip()
        raw = json.loads(content)
        if not isinstance(raw, dict):
            print("[parser] OpenAI returned non-dict JSON")
            return None

        result = _postprocess(_normalise(raw), brief_prompt=prompt)

        # ── CALL 3: Architect VALIDATES their own work ────────────────────────
        print("[parser] Call 3: validation check...")
        rooms_summary = "\n".join(
            "  " + str(r.get("name","?")) + " fl=" + str(r.get("floor",0)) + " "
            + str(r.get("width_ft",0)) + "x" + str(r.get("depth_ft",0)) + "ft "
            + "= " + str(r.get("area_sqft",0)) + "sqft | " + str(r.get("notes",""))[:60]
            for r in result.get("rooms", [])
        )
        r3 = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": _VALIDATION_SYSTEM},
                {"role": "user", "content":
                    "BRIEF: " + prompt + "\n"
                    + "PLOT: " + str(result.get("plot_width_ft")) + "x" + str(result.get("plot_depth_ft")) + "ft "
                    + str(result.get("plot_facing","")) + " facing, "
                    + "floors=" + str(result.get("floors",1)) + ", "
                    + "budget_per_sqft=Rs" + str(result.get("budget_per_sqft",0)) + "\n\n"
                    + "ROOM PROGRAM:\n" + rooms_summary},
            ],
            temperature=0.0,
            max_tokens=300,
        )
        validation = (r3.choices[0].message.content or "").strip()
        print(f"[parser] Validation: {validation}")

        # Store reasoning + validation for debugging / frontend display
        result["_design_reasoning"] = design_reasoning
        result["_validation"]       = validation

        # Apply geometric fixes the validator identified
        result = _apply_validation_fixes(result, validation)
        result = _clamp_single_floor_if_implicit(prompt, result)
        result = _fix_plot(result)
        result = _fix_floors_staircase(result)
        result = _fix_floor_assignments(result)
        result = _fix_accessibility(result)
        result = _fix_area_budget(result)

        return result

    except Exception as exc:
        print(f"[parser] OpenAI error: {exc}")
        return None

# ===========================================================================
# Normalise: type-coerce raw dict into typed Python dict with defaults
# ===========================================================================

def _coerce_maket_deliverable(val: Any) -> Dict[str, str]:
    base: Dict[str, str] = {k: "" for k in _MAKET_DELIVERABLE_KEYS}
    if not isinstance(val, dict):
        return base
    for k in _MAKET_DELIVERABLE_KEYS:
        v = val.get(k)
        if isinstance(v, str) and v.strip():
            base[k] = v.strip()
    return base


def _normalise(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    With structured outputs the model cannot deviate from the schema,
    so normalise is now lightweight: start from defaults, overlay LLM values
    with type coercion as a safety net only.
    """
    out: Dict[str, Any] = copy.deepcopy(CORE_DEFAULTS)

    INT_KEYS   = {"plot_area_sqft","built_up_area_sqft","basement_area_sqft","floors",
                  "bedrooms","bathrooms","attached_bathrooms","common_bathrooms",
                  "toilets","occupants","budget","budget_per_sqft"}
    FLOAT_KEYS = {"plot_width_ft","plot_depth_ft","building_height_ft","floor_height_ft",
                  "main_door_width_ft","corridor_width_ft"}
    BOOL_KEYS  = {"basement","terrace","lift","vastu_compliant","accessibility",
                  "home_office","home_gym","home_theater","study_room",
                  "servant_quarters","pooja_room","guest_room","store_room"}
    STR_KEYS   = {"plot_facing","staircase_type","staircase_location","bhk_type",
                  "style","entrance_location"}
    LIST_KEYS  = {"vastu_notes","utility_areas","special_requirements"}

    for key, value in data.items():
        k = key.lower()
        if   k in INT_KEYS:    out[k] = _ci(value, CORE_DEFAULTS.get(k, 0))
        elif k in FLOAT_KEYS:  out[k] = _cf(value, CORE_DEFAULTS.get(k, 0.0))
        elif k in BOOL_KEYS:   out[k] = _cb(value)
        elif k in STR_KEYS:    out[k] = str(value).strip() if value else CORE_DEFAULTS.get(k, "")
        elif k in LIST_KEYS:   out[k] = _cls(value)
        elif k == "setbacks":  out["setbacks"] = _merge_setbacks(value)
        elif k == "parking":   out["parking"]  = _merge_parking(value)
        elif k == "outdoor":   out["outdoor"]  = _merge_outdoor(value)
        elif k == "services":  out["services"] = _merge_services(value)
        elif k == "rooms":     out["rooms"]    = _coerce_rooms(value)
        elif k == "maket_deliverable":
            out["maket_deliverable"] = _coerce_maket_deliverable(value)
        else:                  out[key]        = value
    out["maket_deliverable"] = _coerce_maket_deliverable(out.get("maket_deliverable"))
    return out


# ===========================================================================
# POST-PROCESSOR — business-logic fixers
# ===========================================================================

_SECONDARY_KITCHEN_TOKENS = ("dry_kitchen", "wet_kitchen")


def _is_secondary_kitchen_room(name: str) -> bool:
    n = (name or "").lower().strip()
    if not n:
        return False
    for tok in _SECONDARY_KITCHEN_TOKENS:
        if n == tok or n.startswith(tok + "_"):
            return True
    return False


def _strip_secondary_kitchen_programme(out: Dict[str, Any]) -> Dict[str, Any]:
    """
    Product rule: exactly ONE kitchen room type. wet_kitchen / dry_kitchen are removed;
    area rolls into the primary kitchen footprint and notes carry wet-zone intent.
    """
    rooms_in = list(out.get("rooms") or [])
    absorbed_area = 0.0
    absorbed_notes: List[str] = []
    kept: List[Dict[str, Any]] = []
    for r in rooms_in:
        nm = str(r.get("name", ""))
        if _is_secondary_kitchen_room(nm):
            w = float(r.get("width_ft") or 0)
            d = float(r.get("depth_ft") or 0)
            a = float(r.get("area_sqft") or 0) or (w * d if w and d else 0.0)
            absorbed_area += max(a, 0.0)
            note = str(r.get("notes") or "").strip()
            if note:
                absorbed_notes.append(f"[merged from {nm}] {note}")
            print(f"[parser] Single-kitchen policy: removed room '{nm}' from programme.")
            continue
        kept.append(r)

    if absorbed_area <= 0.01 and not absorbed_notes:
        out["rooms"] = kept
        return out

    kitchen_idx = next(
        (i for i, r in enumerate(kept) if str(r.get("name", "")).lower().strip() == "kitchen"),
        None,
    )
    policy = (
        "single Indian kitchen only: integrated segregated wet zone (sink/wash/drainage wall) "
        "+ tall-unit wall inside this kitchen; utility_room is laundry/wash appendage — not a second cook space."
    )
    merge_tail = "; ".join(absorbed_notes + ([policy] if policy else []))

    if kitchen_idx is not None:
        k = dict(kept[kitchen_idx])
        w = max(float(k.get("width_ft") or 9), 8.5)
        d = max(float(k.get("depth_ft") or 9), 8.0)
        a0 = float(k.get("area_sqft") or 0) or (w * d)
        a1 = a0 + absorbed_area
        d_new = round(a1 / w, 2)
        k["depth_ft"] = max(d_new, d)
        k["area_sqft"] = round(w * float(k["depth_ft"]), 1)
        kn = str(k.get("notes") or "").strip()
        k["notes"] = (kn + "; " + merge_tail).strip("; ") if merge_tail else kn
        kept[kitchen_idx] = k
    else:
        util_idx = next(
            (i for i, r in enumerate(kept) if "utility" in str(r.get("name", "")).lower()),
            None,
        )
        if util_idx is not None:
            u = dict(kept[util_idx])
            wu = max(float(u.get("width_ft") or 6), 6.0)
            du = max(float(u.get("depth_ft") or 6), 5.5)
            au = float(u.get("area_sqft") or 0) or (wu * du) + absorbed_area
            u["depth_ft"] = round(au / wu, 2)
            u["area_sqft"] = round(wu * float(u["depth_ft"]), 1)
            un = str(u.get("notes") or "").strip()
            u["notes"] = (un + "; " + merge_tail).strip("; ") if merge_tail else un
            kept[util_idx] = u

    out["rooms"] = kept
    return out


def _postprocess(out: Dict[str, Any], brief_prompt: Optional[str] = None) -> Dict[str, Any]:
    """
    Geometric safety rails only.
    Design decisions (room program, sizes, style, Vastu) are made by the LLM.
    These fixers only correct math errors and enforce hard geometric constraints.
    """
    out = _strip_secondary_kitchen_programme(out)
    # Cultural system enrichment (adds design context, non-destructive)
    try:
        from app.services.cultural_design_systems import enrich_parsed_with_cultural_data
        out = enrich_parsed_with_cultural_data(out)
    except ImportError:
        pass

    out = _clamp_single_floor_if_implicit(brief_prompt, out)

    # GEOMETRIC SAFETY RAILS — order matters
    out = _fix_plot(out)               # 1. Recompute BUA + budget_per_sqft (math check)
    out = _fix_floors_staircase(out)   # 2. Type-coerce staircase fields
    out = _fix_bhk_type(out)           # 3. Normalize BHK label
    out = _ensure_bhk_bedrooms(out)    # 4. Ensure required bedroom programme count
    out = _fix_sump_overhead(out)      # 5. overhead_tank + sump always True
    out = _fix_accessibility(out)      # 6. Corridor width for disability, grab bars
    out = _fix_floor_assignments(out)  # 7. Hard floor assignment safety net
    out = _fix_area_budget(out)        # 8. Geometric overflow prevention (MUST be last)
    return out


def _fix_plot(out: Dict[str, Any]) -> Dict[str, Any]:
    """Compute correct BUA (footprint × floors) and budget_per_sqft. Never trust LLM math."""
    area = out.get("plot_area_sqft", 0)
    w    = out.get("plot_width_ft",  0.0)
    d    = out.get("plot_depth_ft",  0.0)
    if area and not w:
        w = round(math.sqrt(area / 1.5), 1)
        d = round(area / w, 1)
        out["plot_width_ft"] = w
        out["plot_depth_ft"] = d
    elif w and d and not area:
        out["plot_area_sqft"] = round(w * d)
        area = out["plot_area_sqft"]
    if not area:
        out.update({"plot_area_sqft": 1200, "plot_width_ft": 30.0, "plot_depth_ft": 40.0})

    # ── Location-aware setback enforcement (must run BEFORE footprint calc) ──
    # LLM frequently uses default setbacks even for premium zones like Juhu.
    # This ensures MCGM / BBMP / NDMC minimums are applied.
    location = str(out.get("location") or out.get("plot_facing") or "").lower()
    _sb_raw  = out.get("setbacks") or {}

    _MUMBAI_PREMIUM = ["juhu","bandra","worli","khar","santacruz","versova",
                       "andheri west","four bungalows","seven bungalows","juhu tara"]
    _BANGALORE_PREMIUM = ["koramangala","indiranagar","whitefield","hsr","jp nagar"]
    _DELHI_PREMIUM = ["lutyens","vasant vihar","defence colony","golf links","jor bagh"]

    if any(z in location for z in _MUMBAI_PREMIUM):
        # MCGM premium zone minimums
        _sb_raw["front"] = max(float(_sb_raw.get("front", 5)), 10.0)
        _sb_raw["rear"]  = max(float(_sb_raw.get("rear",  3)),  5.0)
        _sb_raw["left"]  = max(float(_sb_raw.get("left",  2)),  4.5)
        _sb_raw["right"] = max(float(_sb_raw.get("right", 2)),  4.5)
        out["setbacks"]  = _sb_raw
    elif any(z in location for z in _BANGALORE_PREMIUM):
        # BBMP premium zone minimums
        _sb_raw["front"] = max(float(_sb_raw.get("front", 5)),  6.0)
        _sb_raw["rear"]  = max(float(_sb_raw.get("rear",  3)),  3.0)
        _sb_raw["left"]  = max(float(_sb_raw.get("left",  2)),  3.0)
        _sb_raw["right"] = max(float(_sb_raw.get("right", 2)),  3.0)
        out["setbacks"]  = _sb_raw

    # Correct BUA: footprint × floors (NOT plot_area × 0.60)
    sb     = out.get("setbacks") or {}
    pw     = float(out.get("plot_width_ft", 30))
    pd     = float(out.get("plot_depth_ft", 40))
    l_sb   = float(sb.get("left",  2) or 2)
    r_sb   = float(sb.get("right", 2) or 2)
    f_sb   = float(sb.get("front", 5) or 5)
    re_sb  = float(sb.get("rear",  3) or 3)
    footprint = max((pw - l_sb - r_sb) * (pd - f_sb - re_sb), 1.0)
    floors    = int(out.get("floors", 1) or 1)
    correct_bua = round(footprint * floors)
    # ALWAYS override — our math is correct, LLM's never is for multi-storey
    out["built_up_area_sqft"] = correct_bua

    # Always recompute budget_per_sqft from correct BUA
    budget = int(out.get("budget", 0) or 0)
    out["budget_per_sqft"] = round(budget / correct_bua) if budget > 0 else 0

    # ── Car porch size fix ────────────────────────────────────────────────────
    cars = int((out.get("parking") or {}).get("car_spaces", 1))
    bw   = pw - l_sb - r_sb   # built-up width
    for room in (out.get("rooms") or []):
        if str(room.get("name","")).lower() == "car_porch":
            # 2 cars → 26ft (fits 2 Innova Crystas: each 7ft + 3ft door swing each side)
            # Use 90% of built-up width as cap — car porch spans almost full width
            ideal_w   = 26.0 if cars >= 2 else 13.0
            correct_w = min(ideal_w, bw * 0.90)
            if float(room.get("width_ft", 0) or 0) < correct_w:
                room["width_ft"]  = round(correct_w, 1)
                room["depth_ft"]  = max(float(room.get("depth_ft",13) or 13), 13.0)
                room["area_sqft"] = round(room["width_ft"] * room["depth_ft"], 1)

    # ── Vastu notes normalization ────────────────────────────────────────────
    # LLM sometimes sends free text ("east facing plot, kitchen in southeast")
    # instead of the required underscore format ("kitchen_southeast").
    # Always override with the canonical set — never trust LLM format here.
    if out.get("vastu_compliant"):
        out["vastu_notes"] = sorted(set(_FULL_VASTU_NOTES))

    # ── Entrance location normalization ──────────────────────────────────────
    # LLM sends "front" — should be "northeast" for vastu-compliant east-facing
    if out.get("vastu_compliant") and out.get("entrance_location") in ("front","front_center",""):
        facing = str(out.get("plot_facing","")).lower()
        if facing == "east":
            out["entrance_location"] = "northeast"
        elif facing == "north":
            out["entrance_location"] = "northeast"

    return out


def _fix_floors_staircase(out: Dict[str, Any]) -> Dict[str, Any]:
    floors = int(out.get("floors", 1) or 1)
    # Pure single-storey programmes must not carry staircase volumes (reads as false G+)
    if floors <= 1:
        rooms_sf = []
        for r in out.get("rooms") or []:
            n = str(r.get("name", "")).lower()
            if "staircase" in n or "stair_void" in n:
                continue
            rr = dict(r)
            rr["floor"] = 0
            rooms_sf.append(rr)
        out["rooms"] = rooms_sf

    needs = floors > 1 or out.get("terrace") or out.get("basement")
    if not needs:
        out["staircase_type"]     = "none"
        out["staircase_location"] = "none"
    else:
        # Normalize LLM variants to layout_engine canonical values
        _st = str(out.get("staircase_type") or "").lower()
        if _st in ("none", "", "null") or not _st:
            out["staircase_type"] = "dog_leg"
        elif _st not in ("dog_leg", "open_well", "straight"):
            out["staircase_type"] = "dog_leg"

        _sl = str(out.get("staircase_location") or "").lower()
        if _sl in ("none", "", "null", "center", "central", "middle") or not _sl:
            out["staircase_location"] = "rear_center"
        elif _sl not in ("rear_center", "rear_left", "rear_right", "front_left",
                         "front_right", "left", "right"):
            out["staircase_location"] = "rear_center"

    # ── Guarantee corridor on EVERY floor (geometric necessity) ─────────────
    # The layout engine needs at least one corridor per floor.
    # This is a hard structural requirement — without it, bedrooms have no access.
    if floors >= 2:
        rooms = out.get("rooms") or []
        sb    = out.get("setbacks") or {}
        pw    = float(out.get("plot_width_ft", 36))
        bw    = pw - float(sb.get("left",2)) - float(sb.get("right",2))
        cw    = max(float(out.get("corridor_width_ft", 5.0)), 5.0)
        for fl_idx in range(floors):
            has_corr = any(
                ("corridor" in str(r.get("name","")).lower() or
                 "passage" in str(r.get("name","")).lower())
                and int(r.get("floor",0) or 0) == fl_idx
                for r in rooms
            )
            if not has_corr:
                rooms.append({
                    "name": "corridor", "floor": fl_idx,
                    "width_ft": round(bw,1), "depth_ft": cw,
                    "area_sqft": round(bw*cw,1),
                    "attached_bathroom": False, "attached_balcony": False,
                    "windows": 0, "door_count": 0,
                    "notes": f"floor {fl_idx} corridor — auto-injected by geometric rail",
                })
        out["rooms"] = rooms
    out["building_height_ft"] = round(
        out.get("floors", 1) * out.get("floor_height_ft", 10.0), 1
    )
    return out


def _fix_bhk_type(out: Dict[str, Any]) -> Dict[str, Any]:
    beds = out.get("bedrooms", 2)
    area = out.get("plot_area_sqft", 0)
    if out.get("bhk_type", "").lower() == "villa" and (area < 3000 or beds < 4):
        out["bhk_type"] = f"{beds}BHK"
    elif out.get("bhk_type") in ("", None):
        out["bhk_type"] = {1:"1BHK",2:"2BHK",3:"3BHK",4:"4BHK"}.get(beds, f"{beds}BHK")
    return out


def _ensure_bhk_bedrooms(out: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ensure independent bedroom count matches bhk_type intent (e.g. 2BHK -> 2 bedrooms).
    Only injects missing bedrooms; never deletes existing rooms.
    """
    rooms = out.get("rooms", []) or []
    bhk = str(out.get("bhk_type") or "").upper()
    m = re.search(r"(\d+)\s*BHK", bhk)
    if not m:
        return out
    req = max(1, int(m.group(1)))

    def _is_indep_bedroom(name: str) -> bool:
        n = (name or "").lower()
        if "bathroom" in n or "wardrobe" in n:
            return False
        # LLM frequently emits variants like "second_bedroom" / "kids_bedroom".
        # Count any independent bedroom token, excluding carved children.
        if "master_bedroom" in n or "parents_bedroom" in n or "guest_bedroom" in n:
            return True
        return "bedroom" in n

    have = sum(1 for r in rooms if _is_indep_bedroom(str(r.get("name", ""))))
    if have >= req:
        out["bedrooms"] = max(int(out.get("bedrooms", 0) or 0), req)
        return out

    floors = int(out.get("floors", 1) or 1)
    inject_floor = 0 if floors <= 1 else 1
    existing = {str(r.get("name", "")).lower() for r in rooms}
    idx = 2
    for _ in range(req - have):
        while f"bedroom_{idx}" in existing:
            idx += 1
        nm = f"bedroom_{idx}"
        rooms.append({
            "name": nm,
            "floor": inject_floor,
            "width_ft": 10.0,
            "depth_ft": 10.0,
            "area_sqft": 100.0,
            "attached_bathroom": False,
            "attached_balcony": False,
            "windows": 1,
            "door_count": 1,
            "notes": "auto-injected to satisfy BHK bedroom count",
        })
        existing.add(nm)
        idx += 1
    out["rooms"] = rooms
    out["bedrooms"] = req
    return out


def _fix_bathrooms(out: Dict[str, Any]) -> Dict[str, Any]:
    beds     = out.get("bedrooms", 2)
    has_par  = any("parent" in r.get("name","") for r in out.get("rooms",[]))
    attached = 1
    if beds >= 3 or has_par or out.get("accessibility"):
        attached = 2
    attached = min(attached, beds)
    common   = max(math.ceil(max(beds - attached, 0) / 2), 1)
    out["attached_bathrooms"] = attached
    out["common_bathrooms"]   = common
    out["bathrooms"]          = attached + common
    out["toilets"]            = 0
    return out


def _fix_sump_overhead(out: Dict[str, Any]) -> Dict[str, Any]:
    svc = out.get("services", {})
    svc["overhead_tank"] = True
    svc["sump"]          = True
    if not svc.get("septic_tank_location"):
        svc["septic_tank_location"] = "rear_right"
    out["services"] = svc
    return out


def _fix_parking(out: Dict[str, Any]) -> Dict[str, Any]:
    p    = out.get("parking", {})
    cars = p.get("car_spaces", 1)
    if cars >= 1:
        p["covered"] = True
        min_gate = float(max(cars * 9, 10))
        if out["outdoor"].get("gate_width_ft", 0) < min_gate:
            out["outdoor"]["gate_width_ft"] = min_gate
    out["outdoor"]["compound_wall"] = True
    out["parking"] = p
    return out


def _fix_vastu(out: Dict[str, Any]) -> Dict[str, Any]:
    if not out.get("vastu_compliant"):
        return out
    # Always start with the canonical full note set — do not trust LLM's notes format
    # LLM sometimes sends free-text ("east facing plot, kitchen in southeast")
    # instead of underscore format ("kitchen_southeast"). We just override with canonical.
    out["vastu_notes"] = sorted(set(_FULL_VASTU_NOTES))
    out["outdoor"]["sit_out"] = True
    if out.get("entrance_location") in ("front_center", "", None):
        out["entrance_location"] = "northeast"
    if out.get("main_door_width_ft", 4.0) < 4.0:
        out["main_door_width_ft"] = 4.0
    return out


def _fix_accessibility(out: Dict[str, Any]) -> Dict[str, Any]:
    bps      = out.get("budget_per_sqft", 0) or 0
    # Corridor width tiers:
    #   accessibility=true → 4.5ft (wheelchair turn needs 5ft but 4.5ft is practical)
    #   luxury (>₹15k/sqft) → 5.0ft (generous luxury standard)
    #   standard → 3.5ft (NBC minimum)
    if out.get("accessibility"):
        min_corr = 5.0
    elif bps >= 5000:   # luxury tier starts at ₹5,000/sqft (corrected from ₹15,000)
        min_corr = 5.0
    elif bps >= 2500:   # premium tier
        min_corr = 4.5
    else:
        min_corr = 4.0  # economy/standard — NBC 2016 minimum (corrected from 3.5ft)

    if out.get("corridor_width_ft", 4.0) < min_corr:
        out["corridor_width_ft"] = min_corr

    for room in out.get("rooms", []):
        rname = str(room.get("name",""))
        rnotes = str(room.get("notes","")).lower()
        if "parent" in rname or "elderly" in rnotes or "accessibility" in rnotes:
            out["accessibility"] = True
            room["attached_bathroom"] = True
            if "grab bar" not in rnotes:
                room["notes"] = (room.get("notes","").strip("; ") + "; grab bars in attached bathroom").strip("; ")
    return out


def _emergency_inject_missing_rooms(out: Dict[str, Any]) -> Dict[str, Any]:
    """
    Emergency safety net: inject mandatory rooms the LLM omitted.

    NOT called in normal pipeline — the LLM handles room injection via SYSTEM_PROMPT.
    Called only when post-validation finds critical failures (zero rooms, missing
    corridor on every floor, etc.) that would cause layout_engine to crash.

    MONITORING: Every injection = evidence the SYSTEM_PROMPT needs improvement.
    In production, watch for [PROMPT_FAILURE] log lines. If any fires repeatedly,
    fix the prompt — don't add more Python.
    """
    _injections: list = []  # accumulate injection names for logging
    _rooms_before = 0  # set after initial rooms load
    rooms  = out.get("rooms", [])
    _rooms_before = len(rooms)
    floors = out.get("floors", 1)
    beds   = out.get("bedrooms", 2)
    cars   = out.get("parking", {}).get("car_spaces", 0)
    vastu  = out.get("vastu_compliant", False)
    occs   = out.get("occupants", beds * 2)
    names  = {r["name"] for r in rooms}

    def _has(kw: str) -> bool:
        return any(kw in n for n in names)

    def _sz(name: str) -> tuple:
        if name in _ROOM_SIZING:
            return _ROOM_SIZING[name]
        for key, val in _ROOM_SIZING.items():
            if name.startswith(key) or key.startswith(name):
                return val
        return _ROOM_SIZING["bedroom"]

    def _add(name: str, floor: int = 0, notes: str = "",
             ab: bool = False) -> None:
        if _has(name):
            return
        s = _sz(name)
        rooms.append({
            "name": name, "floor": floor,
            "area_sqft": s[0], "width_ft": s[1], "depth_ft": s[2],
            "attached_bathroom": ab, "attached_balcony": False,
            "windows": s[3], "door_count": s[4], "notes": notes,
        })
        names.add(name)

    _add("living_room",  0, "main family gathering space")
    if beds >= 2:
        _add("dining_room", 0, "adjacent to kitchen")
    _add("kitchen", 0, "southeast corner" if vastu else "")

    # Attached bathroom objects
    for br in [r for r in rooms if "bedroom" in r["name"]]:
        if br.get("attached_bathroom"):
            bath_name = br["name"] + "_bathroom"
            if not _has(bath_name):
                notes = f"attached to {br['name']}"
                if "parent" in br["name"]:
                    notes += "; grab bars recommended"
                rooms.append({
                    "name": bath_name, "floor": br.get("floor", 0),
                    "area_sqft": 50.0, "width_ft": 5.0, "depth_ft": 10.0,
                    "attached_bathroom": False, "attached_balcony": False,
                    "windows": 1, "door_count": 1, "notes": notes,
                })
                names.add(bath_name)

    # Common bathrooms
    common = out.get("common_bathrooms", 1)
    for i in range(1, common + 1):
        bname = "common_bathroom" if common == 1 else f"common_bathroom_{i}"
        _add(bname, 0, "northwest corner" if vastu else "shared bathroom")

    if beds >= 2:
        c_floor = 1 if floors > 1 else 0
        _add("corridor", c_floor, "connects all bedrooms")

    if occs >= 3:
        _add("utility_room", 0, "washing machine, drying area")
    _add("store_room", 0, "south zone" if vastu else "general storage")

    if out.get("pooja_room") and not _has("pooja_room"):
        _add("pooja_room", 0, "northeast corner" if vastu else "")

    if cars >= 1 and not _has("car_porch"):
        area_v  = 320.0 if cars >= 2 else 160.0
        w_v     = 24.0  if cars >= 2 else 13.0
        d_v     = 14.0  if cars >= 2 else 12.5
        rooms.append({
            "name": "car_porch", "floor": 0,
            "area_sqft": area_v, "width_ft": w_v, "depth_ft": d_v,
            "attached_bathroom": False, "attached_balcony": False,
            "windows": 0, "door_count": 0,
            "notes": f"covered parking for {cars} car(s), front of plot",
        })
        names.add("car_porch")

    if vastu and not _has("sit_out"):
        _add("sit_out", 0, "vastu verandah at entrance")

    if out.get("staircase_type") not in ("none","",None) and not _has("staircase"):
        rooms.append({
            "name": "staircase", "floor": 0,
            "area_sqft": 60.0, "width_ft": 6.0, "depth_ft": 10.0,
            "attached_bathroom": False, "attached_balcony": False,
            "windows": 0, "door_count": 2,
            "notes": out.get("staircase_location", "rear_center"),
        })
        names.add("staircase")

    # ── Servant quarters injection ────────────────────────────────────────────
    if out.get("servant_quarters") and not _has("servant_quarters"):
        rooms.append({
            "name": "servant_quarters", "floor": 0,
            "area_sqft": 90.0, "width_ft": 9.0, "depth_ft": 10.0,
            "attached_bathroom": True, "attached_balcony": False,
            "windows": 1, "door_count": 1,
            "notes": "near utility area, separate entrance preferred",
        })
        names.add("servant_quarters")
        if not _has("servant_bathroom"):
            rooms.append({
                "name": "servant_bathroom", "floor": 0,
                "area_sqft": 30.0, "width_ft": 4.0, "depth_ft": 7.5,
                "attached_bathroom": False, "attached_balcony": False,
                "windows": 1, "door_count": 1,
                "notes": "attached to servant quarters",
            })
            names.add("servant_bathroom")

    # ── Walk-in wardrobe injection ─────────────────────────────────────────────
    # Inject when mentioned anywhere in the parsed data but not yet in rooms list.
    # walk_in_wardrobe always goes on the same floor as master_bedroom.
    master_floor = next(
        (int(r.get("floor", 1)) for r in rooms
         if "master_bedroom" in str(r.get("name","")) and "_bathroom" not in str(r.get("name",""))),
        1 if floors > 1 else 0,
    )
    _all_text = " ".join([
        " ".join(str(s) for s in out.get("special_requirements", [])),
        " ".join(str(r.get("notes","")) for r in rooms),
    ]).lower()
    _want_wardrobe = any(kw in _all_text for kw in
                         ["walk-in", "walk_in", "walk in wardrobe", "dressing room",
                          "walk in closet", "walkin", "wardrobe"])
    # Also inject for luxury/ultra budget — walk-in wardrobe is expected
    # at ₹5,000+/sqft regardless of whether the LLM explicitly mentioned it
    bps_check = int(out.get("budget_per_sqft", 0) or 0)
    if bps_check >= 5000 and _has("master_bedroom"):
        _want_wardrobe = True
    if _want_wardrobe and not _has("walk_in_wardrobe"):
        rooms.append({
            "name": "walk_in_wardrobe", "floor": master_floor,
            "area_sqft": 64.0, "width_ft": 8.0, "depth_ft": 8.0,
            "attached_bathroom": False, "attached_balcony": False,
            "windows": 0, "door_count": 1,
            "notes": "walk-in wardrobe attached to master bedroom suite",
        })
        names.add("walk_in_wardrobe")

    # ── Terrace injection ──────────────────────────────────────────────────────
    # Inject when terrace=true or mentioned in text, for multi-floor buildings.
    _want_terrace = (
        out.get("terrace") or
        any(kw in _all_text for kw in ["terrace", "private terrace", "roof terrace"])
    )
    if _want_terrace and not _has("terrace") and floors > 1:
        rooms.append({
            "name": "terrace", "floor": master_floor,
            "area_sqft": 120.0, "width_ft": 12.0, "depth_ft": 10.0,
            "attached_bathroom": False, "attached_balcony": False,
            "windows": 0, "door_count": 1,
            "notes": "private terrace accessible from master bedroom",
        })
        names.add("terrace")

    # ── Master bathroom sizing by corrected budget tier ──────────────────────
    # economy   (< ₹1,200/sqft):  25sqft, 4'×6'  — basic 2-fixture
    # standard  (₹1,200–2,500):   40sqft, 5'×8'  — 3-fixture
    # premium   (₹2,500–5,000):   55sqft, 5.5'×10' — 4-fixture
    # luxury    (₹5,000–12,000):  70sqft, 7'×10' — 5-fixture luxury
    # ultra     (₹12,000+):       80sqft, 8'×10' — 5-fixture with bathtub
    bps = out.get("budget_per_sqft", 0) or 0
    if bps >= 12000:
        _bath_min, _bath_w, _bath_d = 80.0, 8.0, 10.0
    elif bps >= 5000:
        _bath_min, _bath_w, _bath_d = 70.0, 7.0, 10.0
    elif bps >= 2500:
        _bath_min, _bath_w, _bath_d = 55.0, 5.5, 10.0
    elif bps >= 1200:
        _bath_min, _bath_w, _bath_d = 40.0, 5.0, 8.0
    else:
        _bath_min, _bath_w, _bath_d = 25.0, 4.0, 6.0

    # Hard cap + hard floor for ALL bathroom rooms.
    # This runs BEFORE _fix_area_budget so the correct sizes are set.
    # _fix_area_budget excludes bathrooms from scaling (they are carved children).
    _bath_max   = 80.0
    _bath_max_w = 8.0
    _bath_max_d = 10.0
    # Attached bedroom bathrooms (bedroom_2_bathroom etc.)
    _attached_bath_max  = 60.0
    _attached_bath_w    = 5.5
    _attached_bath_d    = 11.0

    for room in rooms:
        rname = str(room.get("name",""))
        area  = float(room.get("area_sqft", 0) or 0)
        w     = float(room.get("width_ft",  0) or 0)

        if "master_bedroom_bathroom" in rname or "master_bathroom" in rname:
            # Hard reset to tier-correct size — never let LLM dimensions through
            room["area_sqft"] = _bath_min
            room["width_ft"]  = _bath_w
            room["depth_ft"]  = _bath_d

        elif "_bathroom" in rname and rname not in ("servant_bathroom","common_bathroom"):
            # Attached bedroom bath: cap at 60sqft
            if area > _attached_bath_max or w > _attached_bath_w * 1.5:
                room["area_sqft"] = _attached_bath_max
                room["width_ft"]  = _attached_bath_w
                room["depth_ft"]  = _attached_bath_d

    # ── Architectural rules validation — all tiers premium+ ──────────────────
    # CRITICAL: exclude _bathroom names — "bedroom" is a substring of
    # "master_bedroom_bathroom", which caused bathroom to get bedroom dimensions.
    if bps >= 2500:   # premium tier and above
        try:
            from app.services.architectural_rules import get_room_size_for_budget
            for room in rooms:
                n = room.get("name", "")
                # Skip any room that is a bathroom, wardrobe, or service room
                if "_bathroom" in n or "wardrobe" in n or "bath" in n:
                    continue
                if any(kw in n for kw in ("bedroom","living_room","kitchen","dining_room")):
                    occ = out.get("occupants", 4)
                    w_rec, d_rec = get_room_size_for_budget(n, int(bps), int(occ))
                    if room.get("width_ft", 0) < w_rec * 0.85:
                        room["width_ft"]  = w_rec
                        room["depth_ft"]  = d_rec
                        room["area_sqft"] = round(w_rec * d_rec, 1)
        except ImportError:
            pass

    out["rooms"] = rooms
    injected_count = len(rooms) - _rooms_before
    if injected_count > 0:
        injected_names = [r.get("name","?") for r in rooms[_rooms_before:]]
        print(
            f"[PROMPT_FAILURE] _emergency_inject_missing_rooms injected {injected_count} room(s): "
            f"{injected_names}. These should come from LLM — update SYSTEM_PROMPT."
        )
    return out


def _fix_floor_assignments(out: Dict[str, Any]) -> Dict[str, Any]:
    """
    Enforce correct floor numbers for every room.

    floors == 1  →  ALL rooms floor=0, no exceptions.
    floors >= 2  →  3-pass logic:
      Pass 1: prefix-match against _GROUND_FLOOR_ROOMS / _UPPER_FLOOR_ROOMS.
              Catches bedroom_2, bedroom_3, etc. via "bedroom" prefix in the set.
      Pass 2: attached bathrooms inherit parent bedroom's floor.
              servant_bathroom / common_bathroom → floor=0.
      Pass 3: catch-all → floor=0 for anything still unresolved.
    """
    floors = out.get("floors", 1)
    rooms  = out.get("rooms", [])

    if floors == 1:
        for room in rooms:
            room["floor"] = 0
        return out

    # Track bedroom name → floor so bathrooms can inherit the right floor
    bedroom_floors: Dict[str, int] = {}
    deferred: List[Dict[str, Any]] = []   # bathrooms resolved in pass 2

    # ── Pass 1 ────────────────────────────────────────────────
    for room in rooms:
        name = str(room.get("name", "")).lower().strip()

        # Ground floor check (prefix or exact match)
        if any(name == g or name.startswith(g) for g in _GROUND_FLOOR_ROOMS):
            room["floor"] = 0
            continue

        # Upper floor check
        if any(name == u or name.startswith(u) for u in _UPPER_FLOOR_ROOMS):
            room["floor"] = 1
            if "bedroom" in name and "_bathroom" not in name:
                bedroom_floors[name] = 1
            continue

        # Any bedroom variant not explicitly listed (bedroom_2, bedroom_3, guest_bedroom…)
        if "bedroom" in name and "_bathroom" not in name:
            room["floor"] = 1
            bedroom_floors[name] = 1
            continue

        # Defer bathrooms to pass 2 — we need bedroom_floors populated first
        if "_bathroom" in name or name.endswith("_bath"):
            deferred.append(room)
            continue

        # Pass-3 catch-all: PRESERVE the LLM's floor assignment for unknown rooms.
        # This is critical for rooms like family_lounge, lounge, walk_in_wardrobe, etc.
        # where the LLM correctly parsed the user's intent (e.g. "connecting bedrooms" = floor=1).
        # Only override to floor=0 if the room has NO floor assignment at all.
        if room.get("floor") is None:
            room["floor"] = 0
        # else: keep whatever the LLM assigned

    # ── Pass 2: bathrooms inherit parent bedroom floor ────────
    for room in deferred:
        name = str(room.get("name", "")).lower().strip()

        # Servant bathroom → ground floor (servant quarters are always ground floor)
        if "servant" in name:
            room["floor"] = 0
            continue

        # Common bathroom → ground floor
        if "common" in name:
            room["floor"] = 0
            continue

        # Find parent bedroom by stripping _bathroom suffix
        parent = name.replace("_bathroom", "").replace("_bath", "")
        if parent in bedroom_floors:
            room["floor"] = bedroom_floors[parent]
            continue

        # Generic attached bathroom with no explicit parent → follow bedrooms to upper floor
        if bedroom_floors:
            room["floor"] = 1
            continue

        # Final fallback
        room["floor"] = 0

    # ── Pass 3: guarantee no None floors remain ───────────────
    for room in rooms:
        if room.get("floor") is None:
            room["floor"] = 0

    out["rooms"] = rooms
    return out


def _fix_room_sizes(out: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate and correct room dimensions using architectural_rules.py.
    Ensures every room meets NBC minimums and luxury standards if budget warrants.
    Also corrects bathroom sizes and caps oversized rooms.
    """
    try:
        from app.services.architectural_rules import (
            validate_room_size, get_room_size_for_budget
        )
    except ImportError:
        # Fallback: rules module not yet installed — skip validation
        return out

    budget_per_sqft = int(out.get("budget_per_sqft", 0) or 0)
    is_luxury       = budget_per_sqft >= 5000   # corrected from 15000 — luxury tier starts at ₹5,000/sqft
    occupants       = int(out.get("occupants", 4) or 4)
    rooms           = out.get("rooms", [])
    special         = out.get("special_requirements", [])

    for room in rooms:
        name = str(room.get("name", ""))
        # Never validate bathroom sizes here — they are handled by the
        # hard-reset in _fix_rooms which runs before this fixer.
        # validate_room_size would inflate baths to luxury bedroom dimensions.
        if "_bathroom" in name or name.endswith("_bath"):
            continue
        w    = float(room.get("width_ft",  0) or 0)
        d    = float(room.get("depth_ft",  0) or 0)

        if w <= 0 or d <= 0:
            # Let _ROOM_SIZING defaults handle it — skip
            continue

        result = validate_room_size(
            room_name=name,
            width_ft=w,
            depth_ft=d,
            is_luxury=is_luxury,
            occupants=occupants,
            special=special,
        )

        # Apply corrections (NBC violations only — not luxury warnings)
        nbc_violations = [warn for warn in result["warnings"]
                          if "NBC" in warn or "minimum" in warn.lower()]
        if nbc_violations and result["corrected_w"] > w:
            room["width_ft"] = result["corrected_w"]
            room["area_sqft"] = round(result["corrected_w"] * d, 1)
        if nbc_violations and result["corrected_d"] > d:
            room["depth_ft"] = result["corrected_d"]
            room["area_sqft"] = round(room["width_ft"] * result["corrected_d"], 1)

        # Store any warnings in the room notes (useful for frontend warnings panel)
        if result["warnings"]:
            existing_notes = str(room.get("notes", "")).strip()
            size_warn = "; ".join(result["warnings"][:1])  # just the most important
            if size_warn not in existing_notes:
                room["notes"] = (existing_notes + "; " + size_warn).strip("; ")

    out["rooms"] = rooms
    return out


def _fix_area_budget(out: Dict[str, Any]) -> Dict[str, Any]:
    """
    Enforce per-floor area budget.

    This is the most important post-processor for layout correctness.
    The LLM generates room areas from training data — it has no spatial
    reasoning and will happily produce 2,200 sqft of rooms for a 1,872 sqft
    floor. The layout_engine has a soft budget check but by the time it runs,
    it's too late — it silently clips or drops rooms.

    We fix it here at the source: if rooms on a given floor exceed the
    built-up floor area by more than 5%, scale all rooms proportionally.
    Attached bathrooms and carved children (walk_in_wardrobe, servant_bathroom)
    are excluded from the budget since they are carved INSIDE parent rooms —
    counting them double would over-penalise large bedrooms.

    Built-up floor area = (plot_w - sb_left - sb_right) × (plot_d - sb_front - sb_rear)
    """
    pw = float(out.get("plot_width_ft",  30) or 30)
    pd = float(out.get("plot_depth_ft",  40) or 40)
    sb = out.get("setbacks") or {}
    l  = float(sb.get("left",  2) or 2)
    r  = float(sb.get("right", 2) or 2)
    f  = float(sb.get("front", 5) or 5)
    re = float(sb.get("rear",  3) or 3)

    floor_area = max((pw - l - r) * (pd - f - re), 1.0)
    # Allow 10% overrun — walls consume ~5–8% of area, and rooms can slightly overlap
    budget = floor_area * 1.10

    rooms  = out.get("rooms", [])
    floors = int(out.get("floors", 1) or 1)

    # Names of rooms that are carved INSIDE parents — exclude from floor budget
    # ALL bathrooms are excluded: they are carved inside parent rooms and
    # counting them toward the budget would cause double-penalisation.
    _bps_now = int(out.get("budget_per_sqft", 0) or 0)

    def _is_carved(name: str) -> bool:
        """Rooms excluded from proportional scaling — they have fixed physical requirements."""
        n = name.lower()
        # Carved sub-rooms (already inside parent room — double-penalising is wrong)
        if n.endswith("_bathroom") or n.endswith("_bath"):
            return True
        if "servant_bathroom" in n or "servant_bath" in n:
            return True
        if "walk_in_wardrobe" in n or "wardrobe" in n:
            return True
        # Circulation and structure — cannot scale below physical minimum
        # (corridor must fit a person, staircase treads have fixed NBC dimensions)
        if n in ("corridor", "staircase", "staircase_landing", "passage"):
            return True
        # Outdoor and parking — dimensions set by vehicle/human body size, not design
        # car_porch must fit a car, sit_out must fit chairs, terrace has parapet rules
        if n in ("car_porch", "sit_out", "terrace", "balcony", "courtyard"):
            return True
        # Luxury fixed sizes — foyer and pooja_room at premium budget
        if _bps_now >= 2500 and n in ("foyer", "entrance_foyer", "pooja_room"):
            return True
        return False

    for floor_idx in range(floors):
        floor_rooms = [
            r for r in rooms
            if int(r.get("floor", 0) or 0) == floor_idx
            and not _is_carved(str(r.get("name", "")))
        ]

        total = sum(float(r.get("area_sqft", 0) or 0) for r in floor_rooms)

        if total <= budget:
            continue   # fits — nothing to do

        # Scale down proportionally so total = floor_area × 0.95
        ratio = (floor_area * 0.95) / max(total, 1.0)

        for room in floor_rooms:
            old_area = float(room.get("area_sqft", 0) or 0)
            if old_area <= 0:
                continue
            sf     = math.sqrt(ratio)
            new_w  = round(float(room.get("width_ft", 0) or 0) * sf, 2)
            new_d  = round(float(room.get("depth_ft", 0) or 0) * sf, 2)
            new_area = round(new_w * new_d, 1)
            room["width_ft"]  = new_w
            room["depth_ft"]  = new_d
            room["area_sqft"] = new_area

    out["rooms"] = rooms
    return out


def _fix_special_requirements(out: Dict[str, Any]) -> Dict[str, Any]:
    """
    Decode special requirements and apply their rules to the parsed output.
    E.g. 'elderly parents' → accessibility=true, guest_bedroom on floor=0
    E.g. 'double height' → mark foyer as double_height in notes
    E.g. 'acoustic privacy' → add notes to relevant bedrooms
    """
    try:
        from app.services.architectural_rules import decode_special_requirements
    except ImportError:
        return out

    special  = out.get("special_requirements", [])
    prompt   = ""   # prompt text not available here — already parsed by LLM
    active   = decode_special_requirements(special, prompt)

    if not active:
        return out

    # Apply elderly_parents rules
    if "elderly_parents" in active:
        rules = active["elderly_parents"]
        out["accessibility"] = True
        corr_w = rules.get("corridor_min_w_ft", 5.0)
        if out.get("corridor_width_ft", 4.0) < corr_w:
            out["corridor_width_ft"] = corr_w
        # Ensure guest bedroom is on ground floor
        for room in out.get("rooms", []):
            if "guest" in str(room.get("name","")).lower() and "bedroom" in str(room.get("name","")).lower():
                room["floor"] = 0

    # Apply double_height rules
    if "double_height" in active:
        for room in out.get("rooms", []):
            name = str(room.get("name","")).lower()
            if "foyer" in name or "entrance" in name or "living" in name:
                notes = str(room.get("notes","")).strip()
                if "double height" not in notes.lower():
                    room["notes"] = (notes + "; DOUBLE HEIGHT — mark void on first floor").strip("; ")
                break

    # Apply island_kitchen rules
    if "island_kitchen" in active:
        rules = active["island_kitchen"]
        min_area = rules.get("min_kitchen_area_sqft", 130.0)
        for room in out.get("rooms", []):
            if "kitchen" in str(room.get("name","")).lower() and "wet" not in str(room.get("name","")).lower():
                if float(room.get("area_sqft", 0)) < min_area:
                    # Scale kitchen up to fit island
                    room["width_ft"]  = 12.0
                    room["depth_ft"]  = 11.0
                    room["area_sqft"] = 132.0
                    room["notes"]     = (str(room.get("notes","")) + "; island kitchen — enlarged").strip("; ")

    return out


# ===========================================================================
# Nested-object mergers  (type-safe defaults for nested structs)
# ===========================================================================

def _merge_setbacks(v: Any) -> Dict[str, float]:
    d = copy.deepcopy(CORE_DEFAULTS["setbacks"])
    if isinstance(v, dict):
        for s in ("front","rear","left","right"):
            if s in v:
                d[s] = _cf(v[s], d[s])
    return d


def _merge_parking(v: Any) -> Dict[str, Any]:
    d = copy.deepcopy(CORE_DEFAULTS["parking"])
    if isinstance(v, dict):
        if "car_spaces"         in v: d["car_spaces"]        = _ci(v["car_spaces"], 1)
        if "two_wheeler_spaces" in v: d["two_wheeler_spaces"] = _ci(v["two_wheeler_spaces"], 0)
        if "covered"            in v: d["covered"]            = _cb(v["covered"])
        if "location"           in v: d["location"]           = str(v["location"]).strip()
    return d


def _merge_outdoor(v: Any) -> Dict[str, Any]:
    d = copy.deepcopy(CORE_DEFAULTS["outdoor"])
    if isinstance(v, dict):
        for k2 in ("garden","swimming_pool","courtyard","sit_out","deck","compound_wall"):
            if k2 in v: d[k2] = _cb(v[k2])
        if "garden_area_sqft" in v: d["garden_area_sqft"] = _ci(v["garden_area_sqft"], 0)
        if "gate_width_ft"    in v: d["gate_width_ft"]    = _cf(v["gate_width_ft"], 10.0)
    return d


def _merge_services(v: Any) -> Dict[str, Any]:
    d = copy.deepcopy(CORE_DEFAULTS["services"])
    if isinstance(v, dict):
        for k2 in ("overhead_tank","sump","solar_panels","generator_room",
                   "electrical_room","water_treatment"):
            if k2 in v: d[k2] = _cb(v[k2])
        if "septic_tank_location" in v:
            loc = str(v["septic_tank_location"]).strip()
            d["septic_tank_location"] = loc if loc and loc != "unknown" else "rear_right"
    return d


def _coerce_rooms(value: Any) -> List[Dict[str, Any]]:
    if not isinstance(value, list):
        return []
    rooms: List[Dict[str, Any]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name","room")).strip().lower().replace(" ","_")
        # Drop ghost rooms (e.g. "master_bedroom_bathroom_bathroom")
        if name.count("_bathroom") > 1:
            continue
        s = _ROOM_SIZING.get(name, (100.0, 10.0, 10.0, 1, 1))
        # ── Zero-dimension guard ──────────────────────────────────────────
        # LLM sometimes gives area=0, depth=0 for staircase/corridor.
        # Use defaults from _ROOM_SIZING when LLM value is effectively zero.
        _raw_w = _cf(item.get("width_ft",  s[1]), s[1])
        _raw_d = _cf(item.get("depth_ft",  s[2]), s[2])
        _raw_a = _cf(item.get("area_sqft", s[0]), s[0])
        _w = _raw_w if _raw_w > 0.5 else s[1]
        _d = _raw_d if _raw_d > 0.5 else s[2]
        _a = _raw_a if _raw_a > 4.0 else round(_w * _d, 1)
        rooms.append({
            "name":              name,
            "floor":             _ci(item.get("floor", 0), 0),
            "area_sqft":         round(_a, 1),
            "width_ft":          round(_w, 1),
            "depth_ft":          round(_d, 1),
            "attached_bathroom": _cb(item.get("attached_bathroom", False)),
            "attached_balcony":  _cb(item.get("attached_balcony",  False)),
            "windows":           _ci(item.get("windows",   s[3]), s[3]),
            "door_count":        _ci(item.get("door_count", s[4]), s[4]),
            "notes":             str(item.get("notes","")).strip(),
        })
    # Deduplicate by (name, floor) — corridors exist on EVERY floor, so
    # "corridor" on floor=0 and "corridor" on floor=1 are DIFFERENT rooms.
    # Keep last occurrence per (name, floor) pair.
    seen: Dict[tuple, int] = {}
    for i, r in enumerate(rooms):
        key = (r["name"], int(r.get("floor", 0)))
        seen[key] = i
    rooms = [rooms[i] for i in sorted(seen.values())]

    # ── Deduplicate master bathroom variants ────────────────────────────────
    # LLM sometimes generates BOTH "master_bathroom" and "master_bedroom_bathroom".
    # Both get carved inside master_bedroom — leaves no space for the bed.
    # Rule: if master_bedroom_bathroom exists, drop master_bathroom.
    # If only master_bathroom exists, rename it to master_bedroom_bathroom
    # so the layout engine correctly carves it inside the master bedroom.
    names_list = [r["name"] for r in rooms]
    has_mb_bath  = "master_bedroom_bathroom" in names_list
    has_m_bath   = "master_bathroom" in names_list

    if has_mb_bath and has_m_bath:
        # Keep master_bedroom_bathroom (richer notes), drop master_bathroom
        # But if master_bedroom_bathroom has empty/generic notes and master_bathroom
        # has rich notes, merge the notes before dropping
        mb_bath  = next(r for r in rooms if r["name"] == "master_bedroom_bathroom")
        m_bath   = next(r for r in rooms if r["name"] == "master_bathroom")
        if len(str(m_bath.get("notes",""))) > len(str(mb_bath.get("notes",""))):
            # master_bathroom has richer notes — copy them over
            mb_bath["notes"] = m_bath["notes"]
        rooms = [r for r in rooms if r["name"] != "master_bathroom"]
        print("[normalise] Dropped duplicate master_bathroom — kept master_bedroom_bathroom")
    elif has_m_bath and not has_mb_bath:
        # Rename to canonical name so layout engine carves it correctly
        for r in rooms:
            if r["name"] == "master_bathroom":
                r["name"] = "master_bedroom_bathroom"
                print("[normalise] Renamed master_bathroom → master_bedroom_bathroom")
                break

    return rooms


# ===========================================================================
# Type coercers
# ===========================================================================

def _ci(v: Any, default: int) -> int:
    try:
        if v is None: return default
        return int(float(str(v).replace(",","")))
    except (TypeError, ValueError):
        return default

def _cf(v: Any, default: float) -> float:
    try:
        if v is None: return default
        return float(str(v).replace(",",""))
    except (TypeError, ValueError):
        return default

def _cb(v: Any) -> bool:
    if isinstance(v, bool): return v
    if isinstance(v, str):  return v.lower() in ("true","yes","1")
    if isinstance(v, int):  return bool(v)
    return False

def _cls(v: Any) -> List[str]:
    if v is None:           return []
    if isinstance(v, str):  return [v] if v.strip() else []
    if isinstance(v, list): return [str(x).strip() for x in v if x is not None and str(x).strip()]
    return [str(v)]