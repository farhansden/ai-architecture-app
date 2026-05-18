"""
architectural_rules.py  —  Indian Residential Architecture Knowledge Base
==========================================================================
Version: 2.0  —  All-India, All-Budget, Hindu Vastu baseline

SCOPE
-----
This module encodes what a licensed Indian architect knows — whether they are
designing a 200sqft rural homestead in a Rajasthan village on a ₹4 lakh budget,
or a 4000sqft Juhu villa at ₹6 crore. The rules scale across:

  BUDGET TIERS (construction cost per sqft, INR, 2025 rates):
    economy   :  < ₹1,200/sqft   (rural / village self-build, basic materials)
    standard  :  ₹1,200–2,500    (tier-3 / tier-2 town, good contractor)
    premium   :  ₹2,500–5,000    (tier-2 city / tier-1 suburban)
    luxury    :  ₹5,000–12,000   (tier-1 city, premium finishes)
    ultra     :  ₹12,000+        (Juhu / Bandra / Koramangala premium)

  PLOT SIZES:
    micro     :  < 600 sqft plot  (village, small town row house)
    small     :  600–1200 sqft    (20×30 to 30×40)
    medium    :  1200–2400 sqft   (30×40 to 40×60)
    large     :  2400–4000 sqft   (40×60 to 50×80)
    estate    :  4000+ sqft       (villa / farmhouse)

  RELIGION BASELINE: Hindu Vastu Shastra
    Future: Christian (Feng Shui-lite, no hard Vastu), Islamic (Qibla orientation)

STANDARDS REFERENCED
---------------------
  NBC India 2016 (National Building Code)
  IS:1725 (staircase construction)
  IS:11246 (accessibility)
  IS:1172 (plumbing)
  RERA 2016 (carpet area / super built-up definitions)
  Vastu Shastra (classical texts: Manasara, Mayamata)
  BIS SP:7 (general building design)
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional, Set, Tuple


# ══════════════════════════════════════════════════════════════════════════════
# CHAPTER 1: VASTU SHASTRA — HINDU BASELINE
# Classical Indian directional science.  Mandatory when vastu_compliant=True.
# ══════════════════════════════════════════════════════════════════════════════

# Absolute compass zone assignment per room type
# Source: Manasara Ch.9, Mayamata Ch.6, modern Vastu consultant consensus
VASTU_ZONES: Dict[str, str] = {

    # ── Eeshanya (NE) — Jal tatva (water), purity, divine energy ─────────────
    # Morning sun enters here. Keep open, light, sacred.
    "pooja_room":        "NE",
    "entrance_foyer":    "NE",
    "foyer":             "NE",
    "water_body":        "NE",   # underground sump, well, water feature
    "kids_study":        "NE",   # children face NE while studying = focus

    # ── Vayavya (NW) — Vayu tatva (air), movement, guests ────────────────────
    # Guests in NW don't overstay (air = movement). Bathrooms here = impurity
    # moves out with the air. Garage in NW = vehicles always move.
    "guest_bedroom":     "NW",
    "guest_room":        "NW",
    "common_bathroom":   "NW",
    "guest_bathroom":    "NW",
    "garage":            "NW",
    "parents_bedroom":   "NW",   # CORRECTED: parents/in-laws = NW, NOT SW
                                  # SW is owner's zone (heaviest). Parents in NW
                                  # = comfortable stay, not permanent anchor.

    # ── Agneya (SE) — Agni tatva (fire), cooking, electrical ─────────────────
    # Fire/heat belongs here. East morning light enters kitchen from right side.
    "kitchen":           "SE",
    "wet_kitchen":       "SE",
    "dry_kitchen":       "SE",
    "generator":         "SE",
    "electrical_room":   "SE",

    # ── Nairutya (SW) — Prithvi tatva (earth), stability, heaviness ──────────
    # The HEAVIEST zone. Master of the house sleeps here for stability,
    # authority, and grounded decision-making. Never keep it light or open.
    # This is the OWNER/MASTER zone exclusively.
    "master_bedroom":    "SW",

    # ── Uttara (N) — Kubera (wealth), prosperity, cool light ─────────────────
    # North = no direct harsh sunlight. Best for spaces needing calm/wealth.
    # Living room in North = family gathers in prosperity zone.
    # Home office facing North = wealth flows in (per Vastu belief).
    "living_room":       "N",
    "dining_room":       "N",    # adjacent to living, also north-ish acceptable
    "home_office":       "N",

    # ── Poorva (E) — Surya (sun), health, morning energy ─────────────────────
    # First light = health. Children's rooms facing east = positive start.
    "kids_bedroom":      "E",
    "bedroom_2":         "NE",   # second bedroom: prefer NE (children)
    "bedroom_3":         "E",
    "study":             "E",

    # ── Paschima (W) — afternoon rest, acceptable for bedrooms ───────────────
    "bedroom":           "W",    # generic bedroom not otherwise specified
    "bathroom":          "NW",   # all attached bathrooms → NW preferred

    # ── Dakshina (S) — Yama zone, heavy/inert, service area ──────────────────
    # South is the zone of rest, heaviness, and service. NOT for active living.
    "store_room":        "S",
    "staircase":         "S",    # SW also acceptable, never NE
    "servant_quarters":  "S",    # rear-south, service access
    "utility_room":      "S",

    # ── Brahmasthana (C) — Central void, must remain open ────────────────────
    # The central 1/9th of plot must NOT have a load-bearing room.
    # Corridor is acceptable (it's circulation, not a closed room).
    "corridor":          "C",
    "courtyard":         "C",
}

# ── Toilet placement rules ────────────────────────────────────────────────────
# CORRECTED: SE added to forbidden (fire zone + toilet = impurity in agni zone)
TOILET_FORBIDDEN_ZONES: Set[str] = {"NE", "SW", "N", "SE"}

# Acceptable toilet zones
TOILET_ACCEPTABLE_ZONES: Set[str] = {"NW", "W", "S"}

# Toilet seat direction while seated (facing direction)
# Never face N (wealth direction) or E (sacred/sun direction)
TOILET_SEAT_DIRECTION: List[str] = ["S", "W"]

# ── Water tank rules ──────────────────────────────────────────────────────────
# CORRECTED: SW removed from overhead tank zones.
# SW is master bedroom zone — water tank directly above master bed is
# inauspicious AND structurally heavy. Underground sump in SW is fine.
# Overhead tank: W only (or SW corner of terrace, away from bedroom below)
OVERHEAD_TANK_ZONES: Set[str]     = {"W"}   # overhead only
UNDERGROUND_SUMP_ZONES: Set[str]  = {"NE", "N"}  # underground only, NE corner
OVERHEAD_TANK_FORBIDDEN: Set[str] = {"NE", "N", "E", "SW"}

# ── Critical Vastu violations (must warn prominently in UI) ──────────────────
CRITICAL_VASTU_VIOLATIONS: List[str] = [
    "kitchen_in_NE",            # fire in water zone — very bad
    "kitchen_in_SW",            # fire in earth zone — bad for family health
    "toilet_in_NE",             # impurity in sacred zone — very bad
    "toilet_in_SW",             # impurity in master zone — very bad
    "toilet_in_SE",             # impurity in fire zone — bad
    "master_bedroom_not_SW",    # owner not in stability zone
    "staircase_in_NE",          # blocks positive energy / Eeshanya
    "entrance_in_S",            # south entrance = Yama (death) direction
    "pooja_room_missing",       # vastu_compliant=True with no pooja room
    "brahmasthana_blocked",     # solid room in center of plot
    "overhead_tank_in_NE",      # water tank above sacred zone
    "parents_bedroom_in_SW",    # parents in owner's zone = family tension
]

# ── Auspicious measurements (Vastu Shastra — Tala system) ────────────────────
# Room widths/lengths that are considered auspicious.
# Source: Manasara measurement system (not strictly enforced, advisory only)
AUSPICIOUS_DIMENSIONS_FT: List[float] = [
    # Based on Angula/Tala system converted to feet
    8.0, 9.0, 10.0, 11.0, 12.0, 13.0, 14.0, 15.0, 16.0,
    18.0, 20.0, 21.0, 24.0, 27.0, 30.0, 36.0
]


# ══════════════════════════════════════════════════════════════════════════════
# CHAPTER 2: ADJACENCY RULES
# What must be next to what, and what can never share a wall.
# These apply regardless of budget — basic architectural sense.
# ══════════════════════════════════════════════════════════════════════════════

# room_a MUST be adjacent to at least one room in the list
MUST_ADJACENT: Dict[str, List[str]] = {
    "kitchen":                  ["dining_room", "utility_room"],
    "dining_room":              ["kitchen", "living_room"],
    "utility_room":             ["kitchen", "servant_quarters"],
    "servant_quarters":         ["utility_room"],
    "master_bedroom":           ["master_bedroom_bathroom"],
    "master_bedroom_bathroom":  ["master_bedroom"],
    "walk_in_wardrobe":         ["master_bedroom"],
    "staircase":                ["corridor", "passage"],
    "staircase_landing":        ["corridor"],
    # Pooja room must open off living room, foyer, or dining — family visibility
    "pooja_room":               ["living_room", "dining_room", "foyer", "entrance_foyer"],
}

# These pairs must NEVER share a wall — hygiene, privacy, Vastu
MUST_NOT_ADJACENT: Dict[str, List[str]] = {
    "kitchen": [
        "bathroom", "common_bathroom", "toilet", "guest_powder_room",
        "master_bedroom", "bedroom", "parents_bedroom",
        "pooja_room",           # cooking smells entering sacred space
        "servant_quarters",     # only connected via utility
    ],
    "pooja_room": [
        "bathroom", "common_bathroom", "toilet", "guest_powder_room",
        "kitchen",              # cooking smells — impurity
        "servant_quarters",     # social hierarchy — Vastu rule
        "utility_room",
    ],
    "master_bedroom": [
        "servant_quarters",     # privacy + social hierarchy
        "kitchen",              # cooking smells into sleeping area
        "utility_room",         # machine noise
        "common_bathroom",      # shared bathroom next to master = privacy issue
    ],
    "bedroom": [
        "kitchen",
        "utility_room",
        "servant_quarters",
    ],
    "dining_room": [
        "bathroom", "common_bathroom", "toilet", "guest_powder_room",
        # Seeing toilet door from dining table = hygiene/etiquette violation
    ],
    # ADDED: living room must not share wall with service/utility areas
    "living_room": [
        "servant_quarters",     # guests should not see/hear servant area
        "utility_room",         # washing machine noise into living room
    ],
    "parents_bedroom": [
        "kitchen",
        "utility_room",
    ],
}

# Zone categories for three-zone separation (public / private / service)
ZONE_PUBLIC: Set[str] = {
    "living_room", "dining_room", "pooja_room",
    "foyer", "entrance_foyer",
    "car_porch", "sit_out",
    "home_office", "guest_bedroom", "guest_room",
    "family_lounge",
}
ZONE_PRIVATE: Set[str] = {
    "master_bedroom", "bedroom", "bedroom_2", "bedroom_3",
    "parents_bedroom", "kids_bedroom",
    "master_bedroom_bathroom", "bathroom",
    "walk_in_wardrobe", "terrace", "balcony",
}
ZONE_SERVICE: Set[str] = {
    "kitchen",
    "utility_room", "servant_quarters", "servant_bathroom",
    "store_room", "staircase",
    "common_bathroom", "guest_powder_room",
}

# Service rooms that need independent exterior access
# (no delivery or servant movement through living/dining)
SERVICE_NEEDS_REAR_ACCESS: Set[str] = {
    "servant_quarters", "utility_room", "kitchen",
}


# ══════════════════════════════════════════════════════════════════════════════
# CHAPTER 3: ROOM DIMENSION STANDARDS
# Three levels: NBC minimum (legal floor), standard (good contractor),
# luxury (premium finishes). All measurements in feet.
#
# NBC India 2016 references:
#   Clause 8.2.1: habitable room min 9.5 sqm (102 sqft), min side 2.4m (7.87ft)
#   Clause 8.2.3: kitchen min 5.0 sqm (53.8 sqft), min side 1.8m (5.9ft)
#   Clause 8.2.4: bathroom min 1.2m × 1.5m (3.94ft × 4.92ft)
#   Clause 8.6:   corridor min 1.0m (3.28ft) — but 1.2m (3.94ft) recommended
#   IS:1725:      stair min clear width 0.9m (2.95ft) private, 1.2m (3.94ft) recommended
# ══════════════════════════════════════════════════════════════════════════════

ROOM_DIMENSIONS: Dict[str, Dict[str, Any]] = {

    "living_room": {
        # NBC: min habitable room 9.5 sqm — living room typically 2× that
        "min_w": 10.0, "min_d": 10.0, "min_area": 120.0,
        # Standard: comfortably fits 3-seater sofa + TV unit + coffee table
        # 3-seater sofa (7ft) + 3.5ft clearance + TV wall = ~12ft min depth
        "standard_w": 14.0, "standard_d": 12.0, "standard_area": 168.0,
        # Luxury: accommodates L-shaped sofa, separate seating nook
        # CORRECTED from 288 → 360 (Indian luxury market 2025 baseline)
        "luxury_w": 20.0, "luxury_d": 18.0, "luxury_area": 360.0,
        "max_ratio": 1.6,
        "nbc_window_ratio": 0.10,   # window area ≥ 10% of floor area (NBC)
        # Budget scaling note: in a 20×30 village plot, 10×10 living room IS the
        # correct size. The standard/luxury targets are NOT imposed on small plots.
    },

    "master_bedroom": {
        # NBC: min habitable 9.5 sqm. Master gets at least 1.5× standard bedroom.
        "min_w": 10.0, "min_d": 10.0, "min_area": 120.0,
        # Standard: fits king bed (6×6.5ft) + 2.5ft clearance 3 sides + wardrobe
        "standard_w": 13.0, "standard_d": 12.0, "standard_area": 156.0,
        # Luxury: CORRECTED — Indian luxury market 2025 (Lodha/Oberoi benchmark)
        # 220–280sqft for master bedroom EXCLUDING attached bathroom
        "luxury_w": 16.0, "luxury_d": 14.0, "luxury_area": 224.0,
        "clear_area": 180.0,    # min area EXCLUDING attached bathroom
        "max_ratio": 1.5,
        "nbc_window_ratio": 0.10,
    },

    "bedroom": {
        # CORRECTED: NBC 2016 Clause 8.2.1 states 9.5 sqm (102 sqft) minimum
        # with minimum side 2.4m (7.87ft → use 8.0ft with imperial rounding)
        # Previous value of min_w:8, min_d:9 = 72sqft was BELOW NBC minimum.
        "min_w": 8.0, "min_d": 10.0, "min_area": 100.0,
        # Standard: fits double bed + wardrobe + study table
        "standard_w": 11.0, "standard_d": 11.0, "standard_area": 121.0,
        # Luxury: spacious secondary bedroom with attached bath possible
        "luxury_w": 13.0, "luxury_d": 12.0, "luxury_area": 156.0,
        "max_ratio": 1.5,
        "nbc_window_ratio": 0.10,
    },

    "parents_bedroom": {
        # Same as bedroom but with accessibility considerations
        # Parents/elderly need wider door (min 3ft) and turning radius inside
        "min_w": 10.0, "min_d": 10.0, "min_area": 120.0,
        "standard_w": 12.0, "standard_d": 12.0, "standard_area": 144.0,
        "luxury_w": 14.0, "luxury_d": 13.0, "luxury_area": 182.0,
        "max_ratio": 1.5,
        # Accessibility note: door min 3ft, no threshold step, grab bar space in bath
        "accessibility_door_min_ft": 3.0,
    },

    "kitchen": {
        # NBC Clause 8.2.3: min 5.0 sqm (53.8 sqft), min side 1.8m (5.9ft)
        # In practice, a functional kitchen needs platform + 3ft clear aisle min
        # = 6ft depth minimum for single-sided, 9ft for double-sided
        "min_w": 6.0, "min_d": 8.0, "min_area": 54.0,
        "standard_w": 10.0, "standard_d": 10.0, "standard_area": 100.0,
        "luxury_w": 12.0, "luxury_d": 12.0, "luxury_area": 144.0,
        # Functional clearances
        "min_aisle_between_counters": 3.5,   # ft — single person pass
        "comfortable_aisle":           4.0,   # ft — two people pass
        "island_clearance":            3.0,   # ft all sides of island
        "max_ratio": 2.0,
        # Village/economy note: 6×8ft kitchen with single counter is functional
    },

    "wet_kitchen": {
        # Heavy/messy cooking kitchen (South Indian / joint family homes)
        "min_w": 7.0, "min_d": 7.0, "min_area": 49.0,
        "standard_w": 8.0, "standard_d": 10.0, "standard_area": 80.0,
        "luxury_w": 10.0, "luxury_d": 10.0, "luxury_area": 100.0,
    },

    "dining_room": {
        # Must accommodate: table + 3ft chair pull-out on all 4 sides
        # 4-seater: 4ft table + 6ft clearance = 10ft min one direction
        "min_w": 8.0, "min_d": 8.0, "min_area": 80.0,
        "standard_w": 11.0, "standard_d": 10.0, "standard_area": 110.0,
        "luxury_w": 14.0, "luxury_d": 13.0, "luxury_area": 182.0,
        # Dining table sizing by occupant count
        "dining_4_min_w": 9.0,  "dining_4_min_d": 9.0,
        "dining_6_min_w": 11.0, "dining_6_min_d": 9.0,
        "dining_8_min_w": 13.0, "dining_8_min_d": 10.0,
        "max_ratio": 1.8,
    },

    "bathroom": {
        # NBC 8.2.4: min 1.2m × 1.5m = 3.94ft × 4.92ft
        # Practical minimum with WC + basin: 4ft × 6ft
        "min_w": 4.0, "min_d": 6.0, "min_area": 25.0,
        "standard_w": 5.0, "standard_d": 8.0, "standard_area": 40.0,
        "luxury_w": 7.0, "luxury_d": 10.0, "luxury_area": 70.0,
        # 3-fixture = WC + basin + shower/bath
        # 5-fixture = WC + double vanity + rain shower + bathtub + storage
    },

    "bathroom_master_standard": {
        "min_w": 5.0, "min_d": 8.0, "min_area": 45.0,
    },

    "bathroom_master_luxury": {
        # 5-fixture luxury: WC + double vanity + rain shower + freestanding tub + storage
        "min_w": 8.0, "min_d": 10.0, "min_area": 80.0,
        "bathtub_area": 13.75,   # 5.5ft × 2.5ft bathtub footprint
        "shower_min": 4.0,       # 4ft × 4ft rain shower minimum
        "vanity_min": 5.0,       # 5ft double vanity (2.5ft per person)
    },

    "common_bathroom": {
        # Shared bathroom for guests / children
        "min_w": 4.0, "min_d": 6.0, "min_area": 25.0,
        "standard_w": 5.0, "standard_d": 8.0, "standard_area": 40.0,
    },

    "guest_powder_room": {
        # Half-bath: WC + wash basin only. At entrance area.
        "min_w": 4.0, "min_d": 5.0, "min_area": 20.0,
        "standard_w": 5.0, "standard_d": 6.0, "standard_area": 30.0,
    },

    "corridor": {
        # CORRECTED: NBC 8.6 recommends 1.2m (3.94ft). 3.5ft is sub-NBC.
        # IS:11246 (accessibility): 1500mm (4.92ft) for wheelchair turn.
        "min_w": 4.0,          # NBC 2016 practical minimum
        "comfortable_w": 4.5,  # standard Indian residential
        "luxury_w": 5.0,       # luxury / wide corridor requirement
        "wheelchair_w": 5.0,   # IS:11246 wheelchair turning radius
        "max_length_no_window": 30.0,  # ft — beyond 30ft needs borrowed light
    },

    "staircase": {
        # IS:1725 + NBC 2016:
        #   min clear width private stair: 0.9m (2.95ft) — bare minimum
        #   recommended residential: 1.2m (3.94ft) → use 4.0ft
        # CORRECTED from 3.5ft to 4.0ft
        "min_w": 4.0,           # minimum residential clear width
        "comfortable_w": 4.5,   # standard Indian dog-leg stair
        "luxury_w": 5.0,        # feature staircase
        "footprint_w": 6.0,     # overall staircase well width (includes wall)
        "footprint_d": 10.0,    # overall staircase well depth (dog-leg on 40ft plot)
        # NBC / IS:1725 tread-riser rules
        "riser_max_in":    7.5,   # inches — NBC maximum
        "riser_optimal_in": 7.0,  # 7 inch riser = most comfortable Indian standard
        "tread_min_in":   10.0,   # inches — NBC minimum
        "tread_optimal_in": 11.0, # 11 inch tread = comfortable adult stride
        "headroom_min_ft":  7.0,  # ft clearance at any point along stair
        # For 10ft floor-to-floor height:
        # 10ft × 12in/ft ÷ 7in riser = 17.1 → 17 risers (odd number = auspicious)
        "steps_for_10ft_floor": 17,
        # Vastu: odd number of steps is auspicious
        "vastu_odd_steps": True,
    },

    "car_porch": {
        # CORRECTED: 1-car min should be 13ft, not 12ft
        # Sedan width (6.5ft) + door swing (3ft each side) = 12.5ft → 13ft safe
        # 2-car: 13ft + 10ft = 23ft min (not 22ft)
        "sedan_w_ft":    6.5,
        "sedan_l_ft":   16.0,
        "suv_w_ft":      7.0,
        "suv_l_ft":     18.0,   # SUV length corrected (Fortuner/Innova = 18ft)
        "door_clearance": 3.0,  # ft each side
        "1car_w":  13.0, "1car_d":  16.0,   # CORRECTED (was 12.0 × 14.0)
        "2car_w":  23.0, "2car_d":  16.0,   # CORRECTED (was 22.0 × 14.0)
        # Village/economy: even a 10ft wide porch fits a two-wheeler or small car (Alto)
        "economy_w": 10.0, "economy_d": 14.0,  # small car / Maruti Alto
    },

    "home_office": {
        "min_w": 8.0, "min_d": 8.0, "min_area": 64.0,
        "standard_w": 10.0, "standard_d": 10.0, "standard_area": 100.0,
        "luxury_w": 12.0, "luxury_d": 12.0, "luxury_area": 144.0,
        # Needs 2 windows for cross-ventilation (IT/WFH = 8hr/day usage)
        "min_windows": 2,
    },

    "pooja_room": {
        # From smallest (wall niche) to full room
        # Economy: pooja shelf/niche in living room (0 sqft — just a niche)
        # Standard: small dedicated room 5×5 = 25sqft
        # Luxury: dedicated room with mandir, seating, storage
        "min_w": 4.0, "min_d": 4.0, "min_area": 16.0,   # absolute minimum
        "standard_w": 5.0, "standard_d": 6.0, "standard_area": 30.0,
        "luxury_w": 8.0, "luxury_d": 8.0, "luxury_area": 64.0,
        # Must have east or north-facing opening (for morning light / Vastu)
        "opening_direction": ["E", "N", "NE"],
    },

    "walk_in_wardrobe": {
        "min_w": 5.0, "min_d": 5.0, "min_area": 25.0,
        "standard_w": 6.0, "standard_d": 6.0, "standard_area": 36.0,
        "luxury_w": 8.0, "luxury_d": 8.0, "luxury_area": 64.0,
        # Functional minimum: 2ft cabinet depth + 3ft swing space + 2ft opposite = 7ft
        # but 5×5 is acceptable for a small dressing room
        "min_usable_w": 5.0,
        "cabinet_depth": 2.0,
        "swing_clearance": 3.0,
    },

    "servant_quarters": {
        # NBC: habitable room ≥ 9.5 sqm. Servant room is habitable.
        # This is a person's home — minimum dignity standards apply.
        "min_w": 8.0, "min_d": 9.0, "min_area": 72.0,
        "standard_w": 9.0, "standard_d": 10.0, "standard_area": 90.0,
        # Servant quarters must always have:
        # - Independent access (not through main living area)
        # - Attached or nearby bathroom
        # - Natural ventilation (window)
        "requires_attached_bath": True,
        "requires_independent_access": True,
        "requires_window": True,
    },

    "utility_room": {
        # Washing machine (2×2ft) + drying space + storage
        "min_w": 5.0, "min_d": 5.0, "min_area": 25.0,
        "standard_w": 6.0, "standard_d": 8.0, "standard_area": 48.0,
        "luxury_w": 8.0, "luxury_d": 10.0, "luxury_area": 80.0,
    },

    "store_room": {
        "min_w": 4.0, "min_d": 4.0, "min_area": 16.0,
        "standard_w": 5.0, "standard_d": 6.0, "standard_area": 30.0,
        "luxury_w": 6.0, "luxury_d": 8.0, "luxury_area": 48.0,
    },

    "family_lounge": {
        # Upper floor lounge connecting bedrooms. Not needed on economy budget.
        "min_w": 8.0, "min_d": 8.0, "min_area": 64.0,
        "standard_w": 10.0, "standard_d": 10.0, "standard_area": 100.0,
        "luxury_w": 14.0, "luxury_d": 12.0, "luxury_area": 168.0,
    },

    "terrace": {
        # Open terrace — minimum usable size
        "min_area": 60.0,
        "standard_area": 100.0,
        "luxury_area": 200.0,
        # Parapet wall minimum 3ft height (NBC safety rule)
        "parapet_min_h_ft": 3.0,
    },

    "balcony": {
        # NBC: min depth 1.2m (3.94ft). Min width = room it serves.
        "min_w": 4.0, "min_d": 4.0, "min_area": 16.0,
        "standard_w": 5.0, "standard_d": 5.0, "standard_area": 25.0,
        "max_cantilever_ft": 5.0,    # NBC structural limit
        "parapet_min_h_ft": 3.5,     # NBC safety requirement
    },

    "sit_out": {
        # Front sit-out / verandah — very common in all Indian house types
        # Even in a village 20×30 plot, a 6×6 verandah is typical
        "min_w": 6.0, "min_d": 4.0, "min_area": 24.0,
        "standard_w": 10.0, "standard_d": 6.0, "standard_area": 60.0,
        "luxury_w": 14.0, "luxury_d": 8.0, "luxury_area": 112.0,
    },

    "foyer": {
        "min_w": 4.0, "min_d": 4.0, "min_area": 16.0,
        "standard_w": 6.0, "standard_d": 6.0, "standard_area": 36.0,
        "luxury_w": 10.0, "luxury_d": 10.0, "luxury_area": 100.0,
        # Double-height foyer starts at luxury tier
    },
}


# ══════════════════════════════════════════════════════════════════════════════
# CHAPTER 4: FURNITURE DIMENSIONS
# Standard Indian market furniture sizes (2025).
# Used to validate that rooms can physically fit their required furniture.
# ══════════════════════════════════════════════════════════════════════════════

FURNITURE_DIMS: Dict[str, Tuple[float, float]] = {
    # Beds (width × length in feet)
    "single_bed":           (3.5,  6.0),   # standard Indian single
    "double_bed":           (4.5,  6.5),   # standard Indian double
    "queen_bed":            (5.0,  6.5),   # queen (common in premium)
    "king_bed":             (6.0,  6.5),   # king
    "cot":                  (3.0,  6.0),   # economy — khatia/taat cot

    # Seating
    "sofa_2seater":         (5.0,  3.0),
    "sofa_3seater":         (7.0,  3.0),
    "sofa_l_shaped":        (9.0,  9.0),   # L-shaped, needs corner space
    "chair_wooden":         (2.0,  2.0),   # standard dining/study chair
    "chair_plastic":        (1.8,  1.8),   # economy plastic chair

    # Dining tables
    "dining_table_4":       (4.0,  3.0),   # 4-seater
    "dining_table_6":       (5.0,  3.0),   # 6-seater
    "dining_table_8":       (7.0,  3.5),   # 8-seater

    # Storage
    "wardrobe_2door":       (4.0,  2.0),   # standard 2-door steel/wood
    "wardrobe_3door":       (5.0,  2.0),
    "wardrobe_large":       (7.0,  2.0),   # large 4-door
    "almirah":              (3.0,  1.5),   # economy steel almirah (very common)

    # Kitchen
    "refrigerator_single":  (2.0,  2.5),   # small single-door (village/economy)
    "refrigerator_double":  (2.5,  3.0),   # double-door (standard)
    "refrigerator_french":  (3.0,  3.0),   # French door (luxury)

    # Desks & workspace
    "study_desk":           (4.0,  2.0),
    "office_desk":          (5.0,  2.5),

    # Appliances
    "washing_machine":      (2.0,  2.0),
    "bathtub_std":          (5.0,  2.5),   # standard built-in
    "bathtub_freestanding": (5.5,  2.5),   # luxury freestanding

    # Vehicles
    "car_small":            (5.5, 13.0),   # Maruti Alto / Wagon R
    "car_sedan":            (6.5, 15.0),   # Swift Dzire / Honda City
    "car_suv":              (7.0, 18.0),   # Fortuner / Innova (corrected length)
    "two_wheeler":          (2.5,  6.0),   # motorcycle / scooter

    # Misc
    "tv_unit_43inch":       (4.0,  1.5),
    "tv_unit_55inch":       (4.5,  1.5),
    "tv_unit_65inch":       (5.0,  1.5),
    "puja_mandir_small":    (2.0,  1.5),   # wall-mounted mandir
    "puja_mandir_large":    (4.0,  2.0),   # floor-standing mandir
}

# Minimum clearance around furniture for circulation (in feet)
FURNITURE_CLEARANCE: Dict[str, float] = {
    "bed":           2.5,   # ft — 3 sides (not headboard wall)
    "sofa":          3.5,   # ft in front (coffee table + walkway)
    "dining_chair":  3.0,   # ft behind (pull-out + walk-behind)
    "wardrobe":      3.0,   # ft in front (door swing + standing space)
    "car_door":      3.0,   # ft on driver/passenger side
    "car_front":     3.5,   # ft in front of car (walk around)
    "wc":            2.5,   # ft in front of toilet (NBC: 750mm = 2.46ft)
    "vanity":        2.5,   # ft in front of wash basin
    "kitchen_aisle": 3.5,   # ft between counters (single person comfortable)
}

# What furniture must fit in each room (minimum requirement by budget tier)
ROOM_FURNITURE_REQUIRED: Dict[str, Dict[str, List[str]]] = {
    "master_bedroom": {
        "economy":  ["cot", "almirah"],
        "standard": ["double_bed", "wardrobe_3door"],
        "luxury":   ["king_bed", "wardrobe_large"],
    },
    "bedroom": {
        "economy":  ["cot", "almirah"],
        "standard": ["double_bed", "wardrobe_2door"],
        "luxury":   ["queen_bed", "wardrobe_3door"],
    },
    "living_room": {
        "economy":  ["chair_plastic"],       # simple seating on economy
        "standard": ["sofa_2seater", "tv_unit_43inch"],
        "luxury":   ["sofa_3seater", "tv_unit_65inch"],
    },
    "dining_room": {
        "economy":  ["dining_table_4"],
        "standard": ["dining_table_6"],
        "luxury":   ["dining_table_8"],
    },
    "kitchen": {
        "economy":  [],                      # chulha/stove directly on floor — no furniture
        "standard": ["refrigerator_single"],
        "luxury":   ["refrigerator_double"],
    },
    "car_porch": {
        "economy":  ["two_wheeler"],
        "standard": ["car_sedan"],
        "luxury":   ["car_suv"],
    },
}


# ══════════════════════════════════════════════════════════════════════════════
# CHAPTER 5: PLUMBING STACK RULES
# IS:1172 — Code of Practice for Use of Building Services
# ══════════════════════════════════════════════════════════════════════════════

# Wet rooms must stack vertically floor-to-floor (plumbing efficiency)
WET_ROOMS: Set[str] = {
    "bathroom", "master_bedroom_bathroom", "bedroom_2_bathroom",
    "parents_bedroom_bathroom",
    "common_bathroom", "guest_powder_room",
    "kitchen", "wet_kitchen", "utility_room",
    "servant_bathroom", "servant_quarters",
}

# Maximum horizontal pipe run before vertical drop (IS:1172)
# Beyond 6m (20ft), self-cleansing velocity in drain drops too low
MAX_HORIZONTAL_PIPE_RUN: float = 20.0   # ft

# Toilets must not be directly above these rooms — IS:1172 + Vastu both agree
TOILET_NOT_ABOVE: Set[str] = {
    "pooja_room",
    "kitchen",
    "dining_room",
    "living_room",
}

# Minimum fall/gradient for drainage pipes
# 1:80 for pipes ≤ 100mm, 1:40 for smaller pipes
MIN_DRAIN_GRADIENT: float = 1.0 / 80.0


# ══════════════════════════════════════════════════════════════════════════════
# CHAPTER 6: STRUCTURAL RULES
# NBC India 2016 + BIS SP:7 + common RCC residential practice
# ══════════════════════════════════════════════════════════════════════════════

STRUCTURAL_RULES: Dict[str, Any] = {
    # RCC beam spans (without intermediate column)
    "max_beam_span_ft":            20.0,   # 6m — beyond this needs column or prestress
    "max_beam_span_economy_ft":    15.0,   # economy: shorter spans, smaller sections
    # Cantilever (balcony / chajja / sunshade)
    "max_cantilever_ft":            5.0,   # 1.5m — NBC limit
    "typical_chajja_ft":            2.0,   # sunshade over window
    # Column and wall sizes
    "min_column_size_in":           9.0,   # 9" × 9" minimum RCC column
    "standard_column_size_in":     12.0,   # 12" × 12" for G+1
    "external_wall_thickness_in":   9.0,   # 9" brick (230mm)
    "internal_wall_thickness_in":   4.5,   # 4.5" partition (115mm AAC block)
    # Slabs
    "slab_thickness_min_in":        4.5,   # 115mm minimum
    "slab_thickness_standard_in":   5.0,   # 125mm standard residential
    # Floor-to-floor heights
    "floor_height_economy_ft":      9.0,   # minimum for airiness
    "floor_height_standard_ft":    10.0,   # standard Indian residential
    "floor_height_luxury_ft":      11.0,   # premium residential
    "double_height_ft":            20.0,   # double height = 2 × 10ft
    # Wall alignment (structural integrity)
    "wall_alignment_tolerance_in":  6.0,   # walls must align floor-to-floor ± 6 inches
    # Footing depth by soil type
    "footing_depth_hard_soil_ft":   3.5,
    "footing_depth_medium_soil_ft": 5.0,
    "footing_depth_soft_soil_ft":   6.0,
}


# ══════════════════════════════════════════════════════════════════════════════
# CHAPTER 7: CLIMATE & PASSIVE DESIGN
# India spans 8°N to 37°N. Rules differ by climate zone.
# IS:3792 — Code for passive design in buildings
# ══════════════════════════════════════════════════════════════════════════════

# Sun exposure per wall direction — averaged for India's latitude band
SUN_EXPOSURE: Dict[str, Dict[str, str]] = {
    "N":  {
        "summer": "diffuse_low",
        "winter": "none",
        "recommendation": "Best wall for living rooms — consistent, glare-free light year-round",
        "ideal_for": ["living_room", "home_office", "dining_room"],
    },
    "S":  {
        "summer": "high_direct",
        "winter": "high_direct",
        "recommendation": "High sun all year. Good for warmth in cold climates (hills). "
                          "Use deep chajja (2ft+) as shade in hot regions.",
        "ideal_for": ["store_room", "staircase"],
    },
    "E":  {
        "summer": "gentle_morning",
        "winter": "gentle_morning",
        "recommendation": "Morning sun is gentle and healthy. Ideal for kitchen (breakfast light) "
                          "and pooja room (morning prayers face east).",
        "ideal_for": ["kitchen", "pooja_room", "bedroom_2"],
    },
    "W":  {
        "summer": "harsh_afternoon",
        "winter": "warm_afternoon",
        "recommendation": "Harsh afternoon sun in summer. Buffer with wardrobe wall or bathroom. "
                          "Never put a bedroom window facing west in coastal areas.",
        "ideal_for": ["bathroom", "walk_in_wardrobe"],
    },
    "NE": {
        "summer": "gentle_morning",
        "winter": "mild",
        "recommendation": "Best corner — morning light without afternoon heat. "
                          "Ideal for pooja room, children's room, study.",
        "ideal_for": ["pooja_room", "kids_bedroom", "foyer"],
    },
    "NW": {
        "summer": "afternoon_breeze",
        "winter": "cool_breeze",
        "recommendation": "Good cross-ventilation. Bathrooms here exhaust smells naturally. "
                          "Guest bedroom — guests don't stay too long (Vastu + reality).",
        "ideal_for": ["common_bathroom", "guest_bedroom", "parents_bedroom"],
    },
    "SE": {
        "summer": "warm_morning",
        "winter": "warm_pleasant",
        "recommendation": "Warm morning light. Perfect for kitchen — matches Vastu and climate both.",
        "ideal_for": ["kitchen", "wet_kitchen", "utility_room"],
    },
    "SW": {
        "summer": "harsh_afternoon",
        "winter": "warm",
        "recommendation": "Heaviest solar load in afternoon. Use wardrobe as thermal buffer "
                          "on SW wall of master bedroom. Never put a large window here.",
        "ideal_for": ["master_bedroom", "store_room"],
    },
}

# Indian climate zones (NBC 2016 Annex A)
CLIMATE_ZONES: Dict[str, Dict[str, Any]] = {
    "hot_dry": {
        "cities": ["Jaisalmer", "Bikaner", "Ahmedabad", "Nagpur", "Jodhpur"],
        "design_priority": "shade, thermal mass, small windows, courtyard",
        "ideal_window_size": "small — 8-10% of wall area",
        "roof_treatment": "thick slab + white coat / grass roof",
        "courtyard_recommended": True,
    },
    "hot_humid": {
        "cities": ["Mumbai", "Chennai", "Kochi", "Kolkata", "Goa", "Mangalore"],
        "design_priority": "cross-ventilation, shading, anti-fungal materials",
        "ideal_window_size": "large — 15-20% of wall area for breeze",
        "roof_treatment": "ventilated roof / sloped with air gap",
        "jali_recommended": True,    # perforated screens for airflow
    },
    "composite": {
        "cities": ["Delhi", "Jaipur", "Lucknow", "Bhopal", "Hyderabad", "Pune"],
        "design_priority": "balance — summer shade + winter sun + monsoon ventilation",
        "ideal_window_size": "medium — 12-15% of wall area",
        "roof_treatment": "5 inch RCC slab + lime plaster",
        "verandah_recommended": True,
    },
    "cold": {
        "cities": ["Shimla", "Mussoorie", "Ooty", "Darjeeling", "Leh"],
        "design_priority": "insulation, south-facing glazing, wind protection",
        "ideal_window_size": "south-facing large, north minimal",
        "roof_treatment": "sloped roof with insulation",
        "double_glazing_recommended": True,
    },
    "temperate": {
        "cities": ["Bangalore", "Mysore", "Pune", "Coimbatore"],
        "design_priority": "natural ventilation — climate is nearly ideal year-round",
        "ideal_window_size": "medium-large — 12-18%",
        "roof_treatment": "standard RCC slab sufficient",
    },
}

# Prevailing wind directions by Indian city (for cross-ventilation planning)
PREVAILING_WINDS: Dict[str, Dict[str, str]] = {
    "mumbai":     {"monsoon": "SW",  "summer": "SW",  "winter": "NW"},
    "bangalore":  {"monsoon": "W",   "summer": "SE",  "winter": "NW"},
    "chennai":    {"monsoon": "NE",  "summer": "SE",  "winter": "NE"},
    "delhi":      {"monsoon": "SE",  "summer": "W",   "winter": "NW"},
    "hyderabad":  {"monsoon": "SW",  "summer": "SW",  "winter": "N"},
    "pune":       {"monsoon": "SW",  "summer": "W",   "winter": "NW"},
    "kolkata":    {"monsoon": "SW",  "summer": "S",   "winter": "N"},
    "ahmedabad":  {"monsoon": "SW",  "summer": "SW",  "winter": "NE"},
    "jaipur":     {"monsoon": "SE",  "summer": "NW",  "winter": "NW"},
    "lucknow":    {"monsoon": "SE",  "summer": "W",   "winter": "N"},
    "kochi":      {"monsoon": "SW",  "summer": "SW",  "winter": "NE"},
    "surat":      {"monsoon": "SW",  "summer": "SW",  "winter": "NW"},
    "default":    {"monsoon": "SW",  "summer": "SW",  "winter": "N"},
}

ROOMS_NEEDING_VENTILATION: Set[str] = {
    "kitchen", "wet_kitchen", "utility_room",
    "common_bathroom", "bathroom", "bedroom", "master_bedroom",
    "servant_quarters",
}


# ══════════════════════════════════════════════════════════════════════════════
# CHAPTER 8: NBC SETBACKS BY PLOT SIZE
# Municipal building bylaws vary. These are NBC 2016 guidance values.
# Actual bylaws: BBMP (Bangalore), MCGM (Mumbai), NDMC (Delhi) etc.
# ══════════════════════════════════════════════════════════════════════════════

def get_required_setbacks(plot_area_sqft: float, floors: int = 1) -> Dict[str, float]:
    """
    Returns required setbacks in feet.
    Source: NBC India 2016 Table 11 + common municipal bylaw defaults.
    Note: For actual construction, always verify with local municipal authority.
    """
    # Plot area in sqm
    sqm = plot_area_sqft * 0.0929

    if sqm < 30:
        # Very small plot (< 320sqft) — row house / village plot
        return {"front": 3.0, "rear": 0.0, "left": 0.0, "right": 0.0}
    elif sqm < 50:
        # Small village / town plot
        return {"front": 3.0, "rear": 1.5, "left": 1.0, "right": 1.0}
    elif sqm < 100:
        # Standard small town plot (30×40 = 120sqm)
        return {"front": 5.0, "rear": 3.0, "left": 2.0, "right": 2.0}
    elif sqm < 200:
        # Medium plot (40×60 = 240sqm is in this band)
        return {"front": 5.0, "rear": 3.0, "left": 2.0, "right": 2.0}
    elif sqm < 500:
        # Large plot
        setbacks = {"front": 6.0, "rear": 4.0, "left": 3.0, "right": 3.0}
        if floors >= 2:
            setbacks = {"front": 8.0, "rear": 5.0, "left": 3.0, "right": 3.0}
        return setbacks
    else:
        # Estate / villa
        return {"front": 10.0, "rear": 6.0, "left": 4.5, "right": 4.5}


def get_max_ground_coverage(plot_area_sqft: float) -> float:
    """
    Maximum ground coverage allowed. NBC 2016 + typical municipal bylaws.
    """
    if plot_area_sqft < 600:
        return plot_area_sqft * 0.80    # small plots: up to 80% ground coverage
    elif plot_area_sqft < 1500:
        return plot_area_sqft * 0.70    # standard: 70%
    elif plot_area_sqft < 3000:
        return plot_area_sqft * 0.65    # medium: 65%
    else:
        return plot_area_sqft * 0.50    # large: 50%


def get_max_far(city: str, plot_area_sqft: float) -> float:
    """
    Floor Area Ratio (FAR) = total built-up area / plot area.
    Varies significantly by city. These are indicative values.
    """
    city_far: Dict[str, float] = {
        "mumbai":     1.33,
        "juhu":       2.0,      # premium Mumbai SRA zone
        "bandra":     1.5,
        "bangalore":  1.75,
        "koramangala": 2.5,     # high-density zone
        "delhi":      1.5,
        "hyderabad":  2.0,
        "chennai":    1.5,
        "pune":       1.5,
        "ahmedabad":  1.5,
        "kolkata":    1.5,
        "jaipur":     1.2,      # tier-2 city lower FAR
        "surat":      1.5,
        "default":    1.5,
    }
    return city_far.get(city.lower(), city_far["default"])


# ══════════════════════════════════════════════════════════════════════════════
# CHAPTER 9: SPECIAL REQUIREMENTS DECODER
# User says "double height", "home theater", "elderly parents" etc.
# These trigger specific architectural rules automatically.
# ══════════════════════════════════════════════════════════════════════════════

SPECIAL_REQUIREMENT_RULES: Dict[str, Dict[str, Any]] = {

    "elderly_parents": {
        "triggers": [
            "elderly", "senior", "aged", "parents", "in-laws", "in laws",
            "wheelchair", "disabled", "old age", "grandparents",
        ],
        "rules": {
            "accessibility":              True,
            "corridor_min_w_ft":          5.0,     # IS:11246 wheelchair turn
            "guest_bedroom_floor":        0,        # MUST be ground floor
            "no_steps_at_entrance":       True,
            "grab_bars_in_bathroom":      True,
            "ramp_at_threshold":          True,
            "bathroom_door_outswing":     True,     # opens outward for safety
            "non_slip_flooring":          True,
            "min_door_width_ft":          3.0,      # 3ft clear for wheelchair
        },
    },

    "home_theater": {
        "triggers": ["home theater", "home theatre", "theater room",
                     "cinema room", "screening room"],
        "rules": {
            "min_area_sqft":         200.0,   # 12ft × 17ft minimum
            "no_windows":            True,    # blackout required
            "screen_on_short_wall":  True,
            "acoustic_walls":        True,
            "floor_preference":      "ground",
            # CLARIFIED: home theater must not have bedrooms DIRECTLY ABOVE it
            # (noise travels up through slab — will disturb sleep above)
            "bedrooms_not_above":    True,
        },
    },

    "home_gym": {
        "triggers": ["gym", "home gym", "workout room", "exercise room", "fitness room"],
        "rules": {
            "min_area_sqft":          100.0,  # 10ft × 10ft minimum
            "rubber_flooring":        True,
            "extra_ventilation":      True,
            "ceiling_height_min_ft":  10.0,
            # Vibration from equipment — avoid above bedrooms
            "bedrooms_not_above":     True,
        },
    },

    "double_height": {
        "triggers": [
            "double height", "double-height", "2 storey high", "20ft ceiling",
            "double height foyer", "grand entrance", "soaring ceiling", "void",
        ],
        "rules": {
            "floor_slab_removed_above":     True,
            "structural_beam_required":     True,
            "mark_as_void_on_upper_floor":  True,
            "min_area_sqft":                80.0,
            "ceiling_height_ft":            20.0,
        },
    },

    "island_kitchen": {
        "triggers": ["island", "island counter", "kitchen island", "island kitchen"],
        "rules": {
            "min_kitchen_area_sqft":            130.0,
            "island_min_size":                  (4.0, 2.5),   # ft
            "min_clearance_around_island_ft":   3.0,
        },
    },

    "wet_dry_kitchen": {
        "triggers": [
            "wet kitchen", "dry kitchen", "show kitchen",
            "separate kitchen", "exhibition kitchen",
        ],
        "rules": {
            "requires_two_kitchen_rooms": True,
            "dry_kitchen_min_area":       90.0,   # show/display kitchen
            "wet_kitchen_min_area":       64.0,   # heavy cooking
            "must_be_adjacent":           True,
        },
    },

    "walk_in_wardrobe": {
        "triggers": [
            "walk-in wardrobe", "walk in wardrobe", "dressing room",
            "walk-in closet", "walk in closet", "wic",
        ],
        "rules": {
            "min_area_sqft":           48.0,
            "must_enter_from_bedroom": True,
            "wardrobe_on_3_walls":     True,
        },
    },

    "courtyard": {
        "triggers": ["courtyard", "inner courtyard", "chowk", "aangan", "angaan"],
        "rules": {
            "min_area_sqft":           100.0,   # 10ft × 10ft minimum
            "must_be_open_to_sky":     True,
            "vastu_zone":              "C",     # Brahmasthana — central
            "natural_light_to_rooms":  True,
        },
    },

    "acoustic_privacy": {
        "triggers": [
            "acoustic", "soundproof", "sound proof", "recording studio",
            "teenager", "privacy", "noise isolation", "music room",
        ],
        "rules": {
            "double_walls_with_air_gap": True,
            "floating_floor":            True,
            "solid_core_doors":          True,
            "no_shared_wall_with_bedroom": True,
        },
    },

    "separate_entrance_servant": {
        "triggers": [
            "separate entrance", "servant entrance", "service entrance",
            "rear entrance", "staff entrance", "back door",
        ],
        "rules": {
            "servant_quarters_separate_entrance": True,
            "service_entry_not_through_main":     True,
            "rear_side_access_required":          True,
        },
    },

    "vastu_strict": {
        "triggers": [
            "strict vastu", "100% vastu", "vastu strict", "pure vastu",
            "no vastu compromise",
        ],
        "rules": {
            "vastu_compliant":          True,
            "no_south_entrance":        True,
            "brahmasthana_open":        True,
            "auspicious_dimensions":    True,
            "pooja_room_mandatory":     True,
        },
    },
}


# ══════════════════════════════════════════════════════════════════════════════
# CHAPTER 10: BUDGET TIERS — ALL-INDIA, ALL-BUDGET
#
# CORRECTED THRESHOLDS (2025 construction cost per sqft, INR):
#   Previous file had luxury starting at ₹15,000/sqft — this was wrong for 2025.
#   ₹15,000/sqft is mid-premium in tier-1 cities, standard in tier-2.
#
# These tiers determine:
#   - Room size targets (which ROOM_DIMENSIONS tier to use)
#   - Furniture requirements
#   - Which special features are expected
#   - Quality of finishes expected in the design
# ══════════════════════════════════════════════════════════════════════════════

BUDGET_TIERS: Dict[str, Dict[str, Any]] = {

    "economy": {
        "construction_cost_per_sqft_inr": (0, 1200),
        "description": "Village self-build / basic contractor, tier-3 towns",
        "typical_plot": "20×30 to 30×40",
        "typical_budget_total": "₹5L to ₹30L",
        "materials": "local brick, RCC slab, basic tiles, MS windows",
        "finishes": "lime plaster, OBD paint, local tile flooring",
        # Room size targets: use NBC minimum
        "room_size_target": "min",
        "expected_features": [],
        "ceiling_height_ft": 9.0,
        "main_door_min_ft": 3.5,
    },

    "standard": {
        "construction_cost_per_sqft_inr": (1200, 2500),
        "description": "Good contractor, tier-2 / tier-3 city, solid middle-class home",
        "typical_plot": "30×40 to 40×50",
        "typical_budget_total": "₹30L to ₹1.5Cr",
        "materials": "burnt brick / AAC block, vitrified tiles, UPVC windows",
        "finishes": "gypsum plaster, emulsion paint, vitrified flooring",
        "room_size_target": "standard",
        "expected_features": ["car_porch", "pooja_room", "sit_out"],
        "ceiling_height_ft": 10.0,
        "main_door_min_ft": 4.0,
    },

    "premium": {
        "construction_cost_per_sqft_inr": (2500, 5000),
        "description": "Premium contractor, tier-1 suburban / tier-2 city premium",
        "typical_plot": "40×60 to 50×80",
        "typical_budget_total": "₹1.5Cr to ₹4Cr",
        "materials": "AAC block, granite/marble, aluminium windows, RCC staircase",
        "finishes": "imported tiles, modular kitchen, gypsum false ceiling",
        "room_size_target": "standard+",   # between standard and luxury
        "expected_features": [
            "car_porch", "pooja_room", "sit_out", "utility_room",
            "servant_quarters", "home_office",
        ],
        "ceiling_height_ft": 10.0,
        "main_door_min_ft": 4.0,
    },

    "luxury": {
        # CORRECTED: was ₹15,000 — now correctly ₹5,000+
        "construction_cost_per_sqft_inr": (5000, 12000),
        "description": "Premium builder, tier-1 city, architect-designed",
        "typical_plot": "40×60 to 60×90",
        "typical_budget_total": "₹4Cr to ₹10Cr",
        "materials": "Kajaria/RAK tiles, Italian marble, teak wood, glass railing",
        "finishes": "POP ceiling, modular kitchen, home automation conduit",
        "room_size_target": "luxury",
        "expected_features": [
            "car_porch_2", "pooja_room", "sit_out", "utility_room",
            "servant_quarters", "home_office", "family_lounge",
            "walk_in_wardrobe", "guest_powder_room",
        ],
        "ceiling_height_ft": 11.0,
        "main_door_min_ft": 4.5,
    },

    "ultra": {
        # CORRECTED: was ₹50,000 — now correctly ₹12,000+ (Juhu/Bandra level)
        "construction_cost_per_sqft_inr": (12000, 999999),
        "description": "Architect + interior designer, Juhu/Bandra/Koramangala/Jubilee Hills",
        "typical_plot": "50×80 to 100×100+",
        "typical_budget_total": "₹10Cr+",
        "materials": "Calacatta marble, solid teak, Miele kitchen, Grohe fittings",
        "finishes": "designer interiors, smart home, custom joinery, feature walls",
        "room_size_target": "luxury",   # same sizing, but quality multiplied
        "expected_features": [
            "car_porch_2plus", "double_height_foyer", "island_kitchen",
            "wet_dry_kitchen", "pooja_room", "sit_out_pergola",
            "utility_room", "servant_quarters_attached_bath",
            "home_office", "family_lounge", "walk_in_wardrobe",
            "5_fixture_master_bath", "guest_powder_room",
            "private_terrace_master", "feature_staircase",
        ],
        "ceiling_height_ft": 11.0,
        "main_door_min_ft": 5.0,    # double-leaf main door
    },
}

# Legacy compatibility: LUXURY_INDICATORS kept for existing code that imports it
LUXURY_INDICATORS: Dict[str, Any] = {
    # CORRECTED thresholds
    "min_budget_per_sqft_luxury":  5000,    # INR — was wrong at 15000
    "min_budget_per_sqft_premium": 2500,    # INR
    "min_budget_per_sqft_ultra":   12000,   # INR — was wrong at 50000

    # Luxury design standards (tier = luxury / ultra)
    "living_room_min_sqft":       300,      # for luxury tier
    "master_bedroom_min_sqft":    200,      # EXCLUDING bathroom
    "master_bathroom_min_sqft":    70,      # 5-fixture
    "corridor_min_w_ft":           5.0,
    "ceiling_height_min_ft":      10.0,
    "ceiling_height_luxury_ft":   11.0,

    # Features expected at luxury budget (not economy/standard)
    "luxury_features": [
        "double_height_foyer",
        "walk_in_wardrobe",
        "5_fixture_master_bath",
        "island_kitchen",
        "separate_wet_kitchen",
        "family_lounge",
        "private_terrace_from_master",
        "feature_staircase",
    ],

    # Sightline rules (what should and should not be seen from entrance)
    "from_entrance_should_see":   ["staircase", "living_room"],
    "from_entrance_must_not_see": [
        "bedroom_door", "toilet_door", "kitchen_sink",
        "utility_room", "servant_quarters",
    ],
}


def get_budget_tier(budget_per_sqft_inr: float) -> str:
    """
    Return the budget tier string for a given construction cost per sqft.
    Used by LLM parser to select appropriate room sizes and features.
    """
    for tier_name, tier_data in BUDGET_TIERS.items():
        lo, hi = tier_data["construction_cost_per_sqft_inr"]
        if lo <= budget_per_sqft_inr < hi:
            return tier_name
    return "standard"   # safe default


# ══════════════════════════════════════════════════════════════════════════════
# CHAPTER 11: VALIDATION ENGINE
# Called by llm_parser.py to validate and correct room sizes.
# ══════════════════════════════════════════════════════════════════════════════

def validate_room_size(
    room_name: str,
    width_ft: float,
    depth_ft: float,
    is_luxury: bool = False,
    occupants: int = 0,
    special: Optional[List[str]] = None,
    budget_per_sqft: int = 0,
) -> Dict[str, Any]:
    """
    Validate a room's dimensions against NBC minimum and tier standards.
    Returns: { valid, warnings, corrected_w, corrected_d, area_sqft }
    """
    n       = room_name.lower()
    dims    = None
    for key, d in ROOM_DIMENSIONS.items():
        if key in n or n.startswith(key):
            dims = d
            break

    if not dims:
        return {
            "valid": True, "warnings": [],
            "corrected_w": width_ft, "corrected_d": depth_ft,
            "area_sqft": width_ft * depth_ft,
        }

    warnings    = []
    corrected_w = width_ft
    corrected_d = depth_ft

    min_w    = float(dims.get("min_w",    0))
    min_d    = float(dims.get("min_d",    0))
    min_area = float(dims.get("min_area", 0))
    lux_w    = float(dims.get("luxury_w", min_w))
    lux_d    = float(dims.get("luxury_d", min_d))

    # NBC minimum check
    if width_ft < min_w:
        warnings.append(
            f"{room_name}: width {width_ft:.1f}ft < NBC minimum {min_w}ft"
        )
        corrected_w = min_w

    if depth_ft < min_d:
        warnings.append(
            f"{room_name}: depth {depth_ft:.1f}ft < NBC minimum {min_d}ft"
        )
        corrected_d = min_d

    area = width_ft * depth_ft
    if area < min_area:
        warnings.append(
            f"{room_name}: area {area:.0f}sqft < NBC minimum {min_area:.0f}sqft"
        )

    # Luxury standard check
    if is_luxury or budget_per_sqft >= LUXURY_INDICATORS["min_budget_per_sqft_luxury"]:
        if width_ft < lux_w:
            warnings.append(
                f"{room_name}: width {width_ft:.1f}ft below luxury standard {lux_w}ft"
            )
        if depth_ft < lux_d:
            warnings.append(
                f"{room_name}: depth {depth_ft:.1f}ft below luxury standard {lux_d}ft"
            )

    # Proportion check
    if min(width_ft, depth_ft) > 0:
        ratio     = max(width_ft, depth_ft) / min(width_ft, depth_ft)
        max_ratio = float(dims.get("max_ratio", 2.0))
        if ratio > max_ratio:
            warnings.append(
                f"{room_name}: room proportion {ratio:.1f}:1 exceeds max {max_ratio}:1. "
                f"Furniture won't fit properly."
            )

    # Occupant-based dining check
    if "dining" in n and occupants > 0:
        if occupants >= 8:
            req_w = float(dims.get("dining_8_min_w", 13.0))
            req_d = float(dims.get("dining_8_min_d", 10.0))
        elif occupants >= 6:
            req_w = float(dims.get("dining_6_min_w", 11.0))
            req_d = float(dims.get("dining_6_min_d", 9.0))
        else:
            req_w = float(dims.get("dining_4_min_w", 9.0))
            req_d = float(dims.get("dining_4_min_d", 9.0))
        if width_ft < req_w or depth_ft < req_d:
            warnings.append(
                f"dining_room: {occupants} occupants need {req_w}ft × {req_d}ft "
                f"(table + 3ft pull-out). Current: {width_ft}ft × {depth_ft}ft"
            )

    # Special requirements
    if special:
        for spec in special:
            spec_rules = SPECIAL_REQUIREMENT_RULES.get(spec, {}).get("rules", {})
            spec_min   = spec_rules.get("min_area_sqft")
            if spec_min and area < spec_min:
                warnings.append(
                    f"{room_name}: special requirement '{spec}' needs "
                    f"{spec_min:.0f}sqft minimum. Current: {area:.0f}sqft"
                )

    valid = len(warnings) == 0 or all("luxury" in w for w in warnings)
    return {
        "valid":       valid,
        "warnings":    warnings,
        "corrected_w": corrected_w,
        "corrected_d": corrected_d,
        "area_sqft":   corrected_w * corrected_d,
    }


def check_vastu_violations(
    rooms: List[Dict[str, Any]],
    plot_facing: str,
    vastu_compliant: bool,
) -> List[str]:
    """
    Check placed rooms for Vastu violations. Returns list of violation strings.

    Checks performed:
      1. Pooja room present (mandatory)
      2. Toilet forbidden zones (NE, SW, N, SE)
      3. Staircase not in NE
      4. Kitchen in correct zone (SE preferred)
      5. Master bedroom in SW
      6. Parents bedroom NOT in SW
      7. Brahmasthana: central zone must not have a load-bearing closed room
      8. Plumbing stack: toilets must not be directly above pooja/kitchen/dining/living
      9. Sightline: servant quarters / utility must not be visible from entrance
    """
    if not vastu_compliant:
        return []

    violations: List[str] = []

    # ── Null guard: empty rooms = placement failed, not a Vastu violation ──────
    if not rooms:
        return []

    # ── 1. Pooja room mandatory ───────────────────────────────────────────────
    has_pooja = any(
        "pooja" in str(r.get("name", "")).lower() or
        "prayer" in str(r.get("name", "")).lower()
        for r in rooms
    )
    if not has_pooja:
        violations.append("VASTU CRITICAL: Vastu-compliant plan has no Pooja room")

    # Build maps for multi-check use
    room_map: Dict[str, Dict[str, Any]] = {}
    by_floor: Dict[int, List[Dict[str, Any]]] = {}
    for room in rooms:
        name  = str(room.get("name", "")).lower()
        floor = int(room.get("floor", 0) or 0)
        room_map[name] = room
        by_floor.setdefault(floor, []).append(room)

    for room in rooms:
        name = str(room.get("name", "")).lower()
        zone = room.get("__vastu_zone", "")
        if not zone:
            continue

        # ── 2. Toilet forbidden zones ─────────────────────────────────────────
        if ("bath" in name or "toilet" in name) and zone in TOILET_FORBIDDEN_ZONES:
            violations.append(
                f"VASTU CRITICAL: {name} in {zone} zone. "
                f"Toilets forbidden in {TOILET_FORBIDDEN_ZONES}."
            )

        # ── 3. Staircase must not be in NE ────────────────────────────────────
        if "staircase" in name and "_landing" not in name and zone == "NE":
            violations.append(
                "VASTU CRITICAL: Staircase in NE (Eeshanya) zone — blocks divine energy. "
                "Move to S or SW."
            )

        # ── 4. Kitchen zone ───────────────────────────────────────────────────
        if "kitchen" in name and "bathroom" not in name and zone not in {"SE", "E", "S"}:
            violations.append(
                f"VASTU CRITICAL: Kitchen in {zone} zone. "
                f"Should be SE (Agneya/fire corner) for Vastu compliance."
            )

        # ── 5. Master bedroom must be SW ──────────────────────────────────────
        if "master_bedroom" in name and "_bathroom" not in name and zone not in {"SW", "S", "W"}:
            violations.append(
                f"VASTU: Master bedroom in {zone} zone. "
                f"Should be SW (Nairutya/earth — stability and authority)."
            )

        # ── 6. Parents bedroom must NOT be SW ────────────────────────────────
        if "parents_bedroom" in name and zone == "SW":
            violations.append(
                "VASTU: Parents bedroom in SW (owner's zone). "
                "Should be NW (Vayavya) — parents are guests, not owners."
            )

    # ── 7. Brahmasthana check ─────────────────────────────────────────────────
    # The central 1/9th of the built-up area must be open or a corridor.
    # A solid room in the center blocks the Brahmasthana (cosmic energy center).
    # We approximate: rooms whose x-center and y-center both fall in the middle
    # third of the built-up area are considered Brahmasthana occupants.
    floor0_rooms = by_floor.get(0, [])
    if floor0_rooms:
        all_x = [float(r.get("x", 0)) for r in floor0_rooms]
        all_y = [float(r.get("y", 0)) for r in floor0_rooms]
        all_rw = [float(r.get("width", 0)) for r in floor0_rooms]
        all_rh = [float(r.get("height", 0)) for r in floor0_rooms]
        if all_x and all_rw:
            min_x = min(all_x)
            max_x = max(x + w for x, w in zip(all_x, all_rw))
            min_y = min(all_y)
            max_y = max(y + h for y, h in zip(all_y, all_rh))
            cx_lo = min_x + (max_x - min_x) / 3
            cx_hi = min_x + (max_x - min_x) * 2 / 3
            cy_lo = min_y + (max_y - min_y) / 3
            cy_hi = min_y + (max_y - min_y) * 2 / 3

            _CENTRAL_OK = {"corridor", "passage", "courtyard", "staircase_landing"}
            for room in floor0_rooms:
                name = str(room.get("name", "")).lower()
                rx   = float(room.get("x", 0))
                ry   = float(room.get("y", 0))
                rw   = float(room.get("width", 0))
                rh   = float(room.get("height", 0))
                rcx  = rx + rw / 2
                rcy  = ry + rh / 2
                # Room center falls in middle third of both axes = Brahmasthana
                if (cx_lo <= rcx <= cx_hi and cy_lo <= rcy <= cy_hi
                        and not any(ok in name for ok in _CENTRAL_OK)):
                    violations.append(
                        f"VASTU: {name} occupies Brahmasthana (central 1/9th zone). "
                        f"This zone must remain open. Use corridor or courtyard here."
                    )

    # ── 8. Plumbing stack — toilet must not be above sacred/living rooms ──────
    # For multi-floor buildings: floor=1 bathrooms must not be directly above
    # floor=0 pooja_room, kitchen, dining_room, or living_room.
    # "Directly above" = horizontal overlap > 50% of the smaller room's footprint.
    floor1_rooms = by_floor.get(1, [])
    if floor1_rooms and floor0_rooms:
        for r1 in floor1_rooms:
            n1 = str(r1.get("name", "")).lower()
            if "bath" not in n1 and "toilet" not in n1:
                continue
            x1  = float(r1.get("x", 0))
            w1  = float(r1.get("width", 1))
            y1  = float(r1.get("y", 0))
            h1  = float(r1.get("height", 1))
            for r0 in floor0_rooms:
                n0 = str(r0.get("name", "")).lower()
                if not any(k in n0 for k in TOILET_NOT_ABOVE):
                    continue
                x0  = float(r0.get("x", 0))
                w0  = float(r0.get("width", 1))
                # Check horizontal overlap
                overlap_x = max(0.0, min(x1+w1, x0+w0) - max(x1, x0))
                if overlap_x > min(w0, w1) * 0.5:
                    violations.append(
                        f"VASTU + PLUMBING: {n1} (floor 1) is directly above "
                        f"{n0} (floor 0). Toilet above {n0} violates both "
                        f"Vastu purity rules and IS:1172 plumbing code."
                    )

    # ── 9. Sightline from entrance ────────────────────────────────────────────
    # From the main entrance (foyer/sit_out on entrance side), the user must NOT
    # have a direct sightline to: servant quarters, utility room, kitchen sink.
    # We check: if servant_quarters / utility_room are in the same screen column
    # (same x-band) as the foyer, flag it.
    _MUST_NOT_SEE = {"servant_quarters", "utility_room"}
    entrance_rooms = [r for r in floor0_rooms
                      if any(k in str(r.get("name","")).lower()
                             for k in ("foyer","sit_out","entrance"))]
    if entrance_rooms:
        ent_x_centers = [float(r.get("x",0)) + float(r.get("width",0))/2
                         for r in entrance_rooms]
        ent_x_lo = min(ent_x_centers) - 30   # 3ft tolerance band
        ent_x_hi = max(ent_x_centers) + 30
        for room in floor0_rooms:
            n = str(room.get("name", "")).lower()
            if any(k in n for k in _MUST_NOT_SEE):
                rcx = float(room.get("x",0)) + float(room.get("width",0))/2
                if ent_x_lo <= rcx <= ent_x_hi:
                    violations.append(
                        f"SIGHTLINE: {n} is visible from entrance (same column). "
                        f"Guests should not see service areas from the main door. "
                        f"Add a screen wall or move {n} to rear zone."
                    )

    return violations


def check_adjacency_violations(
    rooms: List[Dict[str, Any]],
    layout_data: Dict[str, Any],
) -> List[str]:
    """Check for anti-adjacency violations using layout coordinates."""
    violations: List[str] = []
    tolerance  = 8.0   # px — INT_WALL is 4px, need > 4px to detect rooms sharing a wall

    placed   = layout_data.get("rooms", [])
    room_map = {str(r.get("name", "")): r for r in placed}

    def shares_wall(r1: Dict, r2: Dict) -> bool:
        x1, y1, w1, h1 = r1["x"], r1["y"], r1["width"], r1["height"]
        x2, y2, w2, h2 = r2["x"], r2["y"], r2["width"], r2["height"]
        h_adj    = abs((x1+w1) - x2) < tolerance or abs((x2+w2) - x1) < tolerance
        v_overlap = not (y1+h1 <= y2 or y2+h2 <= y1)
        v_adj    = abs((y1+h1) - y2) < tolerance or abs((y2+h2) - y1) < tolerance
        h_overlap = not (x1+w1 <= x2 or x2+w2 <= x1)
        return (h_adj and v_overlap) or (v_adj and h_overlap)

    for room_a, forbidden_list in MUST_NOT_ADJACENT.items():
        ra = room_map.get(room_a)
        if not ra:
            continue
        for room_b in forbidden_list:
            for name_b, rb in room_map.items():
                if room_b in name_b and shares_wall(ra, rb):
                    violations.append(
                        f"ADJACENCY: {room_a} shares wall with {name_b}. "
                        f"These must NOT be adjacent (hygiene/Vastu/privacy)."
                    )

    return violations


def decode_special_requirements(
    special_requirements: List[str],
    prompt_text: str = "",
) -> Dict[str, Any]:
    """Parse special requirements text and return active rules dict."""
    combined = " ".join(special_requirements + [prompt_text]).lower()
    active: Dict[str, Any] = {}
    for req_name, req_data in SPECIAL_REQUIREMENT_RULES.items():
        if any(t in combined for t in req_data.get("triggers", [])):
            active[req_name] = req_data["rules"]
    return active


def get_room_size_for_budget(
    room_name: str,
    budget_per_sqft: int,
    occupants: int = 4,
) -> Tuple[float, float]:
    """
    Return appropriate (width_ft, depth_ft) for a room based on budget tier.
    This is the main function called by llm_parser to set sensible defaults.
    """
    n    = room_name.lower()
    dims = None
    for key, d in ROOM_DIMENSIONS.items():
        if key in n or n.startswith(key):
            dims = d
            break

    if not dims:
        return (10.0, 10.0)

    tier = get_budget_tier(float(budget_per_sqft))

    if tier in ("ultra", "luxury"):
        w = float(dims.get("luxury_w",   dims.get("standard_w", dims.get("min_w", 10.0))))
        d = float(dims.get("luxury_d",   dims.get("standard_d", dims.get("min_d", 10.0))))
    elif tier == "premium":
        # Midpoint between standard and luxury
        std_w = float(dims.get("standard_w", dims.get("min_w", 8.0)))
        std_d = float(dims.get("standard_d", dims.get("min_d", 8.0)))
        lux_w = float(dims.get("luxury_w",   std_w))
        lux_d = float(dims.get("luxury_d",   std_d))
        w     = (std_w + lux_w) / 2
        d     = (std_d + lux_d) / 2
    elif tier == "standard":
        w = float(dims.get("standard_w", dims.get("min_w", 8.0)))
        d = float(dims.get("standard_d", dims.get("min_d", 8.0)))
    else:
        # Economy: use NBC minimums
        w = float(dims.get("min_w", 8.0))
        d = float(dims.get("min_d", 8.0))

    # Scale dining room to occupants
    if "dining" in n:
        if occupants >= 8:
            w = max(w, float(dims.get("dining_8_min_w", 13.0)))
            d = max(d, float(dims.get("dining_8_min_d", 10.0)))
        elif occupants >= 6:
            w = max(w, float(dims.get("dining_6_min_w", 11.0)))
            d = max(d, float(dims.get("dining_6_min_d",  9.0)))

    return (round(w, 1), round(d, 1))


# ══════════════════════════════════════════════════════════════════════════════
# SELF-TEST
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys
    PASS  = True
    fails = []

    def check(condition: bool, label: str) -> None:
        global PASS
        status = "✅" if condition else "❌"
        print(f"  {status} {label}")
        if not condition:
            PASS = False
            fails.append(label)

    print("\n── Vastu Zone Corrections ──")
    check(VASTU_ZONES["parents_bedroom"] == "NW",
          "parents_bedroom → NW (not SW)")
    check("SE" in TOILET_FORBIDDEN_ZONES,
          "SE in TOILET_FORBIDDEN_ZONES")
    check("SW" not in OVERHEAD_TANK_ZONES,
          "SW removed from OVERHEAD_TANK_ZONES (overhead)")

    print("\n── Adjacency ──")
    check("living_room" in MUST_NOT_ADJACENT,
          "living_room has anti-adjacency rules")
    check("servant_quarters" in MUST_NOT_ADJACENT["living_room"],
          "living_room must not be adjacent to servant_quarters")

    print("\n── Room Dimensions — NBC Corrections ──")
    check(ROOM_DIMENSIONS["bedroom"]["min_area"] >= 100.0,
          "bedroom min_area ≥ 100sqft (NBC 2016)")
    check(ROOM_DIMENSIONS["corridor"]["min_w"] >= 4.0,
          "corridor min_w ≥ 4.0ft (NBC 2016)")
    check(ROOM_DIMENSIONS["staircase"]["min_w"] >= 4.0,
          "staircase min_w ≥ 4.0ft (NBC 2016)")
    check(ROOM_DIMENSIONS["car_porch"]["1car_w"] >= 13.0,
          "car_porch 1-car width ≥ 13ft")

    print("\n── Luxury Dimensions — Market Correction ──")
    check(ROOM_DIMENSIONS["living_room"]["luxury_area"] >= 360.0,
          "living_room luxury_area ≥ 360sqft (Lodha/Oberoi benchmark)")
    check(ROOM_DIMENSIONS["master_bedroom"]["luxury_area"] >= 220.0,
          "master_bedroom luxury_area ≥ 220sqft (Indian luxury 2025)")

    print("\n── Budget Tier Thresholds ──")
    check(LUXURY_INDICATORS["min_budget_per_sqft_luxury"] == 5000,
          "luxury tier starts at ₹5,000/sqft (corrected from ₹15,000)")
    check(LUXURY_INDICATORS["min_budget_per_sqft_ultra"] == 12000,
          "ultra tier starts at ₹12,000/sqft (corrected from ₹50,000)")
    check(get_budget_tier(1000) == "economy",   "₹1,000/sqft → economy")
    check(get_budget_tier(2000) == "standard",  "₹2,000/sqft → standard")
    check(get_budget_tier(4000) == "premium",   "₹4,000/sqft → premium")
    check(get_budget_tier(8000) == "luxury",    "₹8,000/sqft → luxury")
    check(get_budget_tier(25000) == "ultra",    "₹25,000/sqft → ultra")

    print("\n── get_room_size_for_budget ──")
    w, d = get_room_size_for_budget("living_room", 1000)
    check(w >= 10.0 and d >= 10.0, f"economy living room {w}×{d}ft ≥ 10×10ft")
    w, d = get_room_size_for_budget("living_room", 8000)
    check(w >= 18.0 and d >= 16.0, f"luxury living room {w}×{d}ft ≥ 18×16ft")
    w, d = get_room_size_for_budget("dining_room", 2000, occupants=8)
    check(w >= 13.0 and d >= 9.0,  f"8-seater dining {w}×{d}ft ≥ 13×9ft")

    print("\n── Validate Room Size ──")
    r = validate_room_size("master_bedroom", 8.0, 8.0)
    check(not r["valid"], "master_bedroom 8×8ft fails NBC (< 100sqft)")
    r = validate_room_size("master_bedroom", 13.0, 12.0)
    check(r["valid"] or all("luxury" in w for w in r["warnings"]),
          "master_bedroom 13×12ft passes NBC")
    r = validate_room_size("corridor", 3.5, 20.0)
    check(len(r["warnings"]) > 0, "corridor 3.5ft width triggers warning")

    print(f"\n{'='*50}")
    if PASS:
        print("  ✅ ALL CHECKS PASSED")
    else:
        print("  ❌ FAILURES:")
        for f in fails:
            print(f"     — {f}")
    print(f"{'='*50}\n")
    sys.exit(0 if PASS else 1)