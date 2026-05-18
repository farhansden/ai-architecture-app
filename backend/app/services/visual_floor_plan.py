from __future__ import annotations

"""
visual_floor_plan.py  —  multi-floor visual pipeline
======================================================

What this file does
-------------------
Orchestrates the full journey from parsed JSON → professional SVG floor plan(s)
+ optional 3D HTML viewer.

  1.  Pre-process parsed JSON
        • Fix family_lounge floor assignment (LLM bug: always places it on floor 0
          even for G+1 plans where it connects first-floor bedrooms).
        • Extend room category hints for rooms layout_engine doesn't know:
          guest_powder_room, home_office, family_lounge,
          walk_in_wardrobe, foyer, servant_quarters.

  2.  For EACH floor (0 to floors-1):
        a. generate_layout(floor_index=N)  →  pixel-accurate room layout
        b. check_architectural_rules()     →  Vastu + NBC compliance
        c. render_floor_plan_svg()         →  2D SVG output
        d. render_floor_plan_dxf()         →  AutoCAD DXF output
        e. render_3d_html()               →  Three.js 3D interactive viewer
        f. score_plan()                   →  0-100 quality score

  3.  Return complete results dict.

Phase 1: SVG (deterministic, zero API cost).
Phase 2: Three.js 3D (procedural, zero API cost).
Phase 3: GPT-image-1 photorealistic render (optional, Phase 2+ only).
"""

import base64
import copy
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.services.layout_engine import generate_layout

# ── Optional renderer imports (all try/except — never hard-fail) ──────────────

# SVG renderer — deterministic 2D floor plan
try:
    from app.services.svg_renderer import render_floor_plan_svg, render_all_floors
    _SVG_RENDERER_AVAILABLE = True
except ImportError:
    _SVG_RENDERER_AVAILABLE = False

# DXF renderer — AutoCAD/SketchUp compatible output
try:
    from app.services.dxf_renderer import render_floor_plan_dxf
    _DXF_RENDERER_AVAILABLE = True
except ImportError:
    _DXF_RENDERER_AVAILABLE = False

# Three.js 3D renderer — interactive procedural 3D viewer
try:
    from app.services.three_d_renderer import render_3d_html
    _3D_RENDERER_AVAILABLE = True
except Exception as _3d_import_err:
    _3D_RENDERER_AVAILABLE = False
    print(f"[visual_floor_plan] WARNING: three_d_renderer import failed: {_3d_import_err}")

# Plan scorer — 0-100 quality score with dimension breakdown
try:
    from app.services.plan_scorer import score_plan
    _SCORER_AVAILABLE = True
except ImportError:
    _SCORER_AVAILABLE = False

# AI image renderer — Phase 2+ only, disabled in Phase 1
_AI_RENDERER_AVAILABLE = False


# ── Floor labels ───────────────────────────────────────────────────────────────
_FLOOR_LABELS = {
    0: "GROUND FLOOR",
    1: "FIRST FLOOR",
    2: "SECOND FLOOR",
    3: "THIRD FLOOR",
}

_FLOOR_SLUGS = {
    0: "ground",
    1: "first",
    2: "second",
    3: "third",
}


# ── Room pre-processing ────────────────────────────────────────────────────────

_CATEGORY_OVERRIDES: Dict[str, str] = {
    "guest_powder_room":  "guest_powder_room",
    "powder_room":        "guest_powder_room",
    "dry_kitchen":        "dry_kitchen",
    "wet_kitchen":        "wet_kitchen",
    "foyer":              "foyer",
    "entrance_foyer":     "foyer",
    "staircase_landing":  "staircase_landing",
    "stair_void":         "staircase_landing",
    "staircase":          "staircase",
    "terrace":            "terrace",
}

_FORCE_UPPER_FLOOR: set = {
    "walk_in_wardrobe",
    "wardrobe",
    "terrace",
}

_FORCE_GROUND_FLOOR: set = {
    "foyer",
    "entrance_foyer",
    "guest_powder_room",
    "powder_room",
    "home_office",
    "servant_quarters",
    "servant_bathroom",
}


def _fix_parsed_rooms(parsed: Dict[str, Any]) -> Dict[str, Any]:
    """
    Return a deep-copied parsed dict with corrected room floor assignments
    and injected __category_hint fields for unusual room names.

    Architectural rules applied:
      1. walk_in_wardrobe → same floor as master_bedroom (always).
      2. terrace → floor=1 when floors >= 2.
      3. servant_quarters + servant_bathroom → floor=0 always.
      4. home_office, foyer, guest_powder_room → floor=0 always.
      5. family_lounge / lounge → TRUST LLM's floor assignment.
      6. STAIRCASE LANDING INJECTION — mandatory for multi-floor plans.
      7. Structural room guarantees (car_porch, sit_out, pooja_room, etc.)
      8. Single-kitchen policy — same as llm_parser (strip wet/dry kitchen rooms for any JSON source).
      9. G+1 efficiency: inject first-floor study when shell is wide and no FF work zone exists;
         default terrace sizing favours balcony+terrace split over one anonymous outdoor slab.
    """
    out = copy.deepcopy(parsed)

    try:
        from app.services.llm_parser import _strip_secondary_kitchen_programme

        out = _strip_secondary_kitchen_programme(out)
    except Exception as exc:
        print(f"[vfp] Secondary kitchen strip skipped: {exc}")

    # ── Structural room guarantees ─────────────────────────────────────────────
    _rooms  = out.get("rooms") or []
    _names  = {r.get("name", "") for r in _rooms}
    _cars   = int((out.get("parking") or {}).get("car_spaces", 0))
    _vastu  = bool(out.get("vastu_compliant", False))
    _floors = int(out.get("floors", 1) or 1)
    _sb     = out.get("setbacks") or {}
    _pw     = float(out.get("plot_width_ft", 40))
    _bw     = _pw - float(_sb.get("left", 2)) - float(_sb.get("right", 2))
    _bps    = int(out.get("budget_per_sqft", 0) or 0)

    # 1. car_porch
    if _cars >= 1 and not any("car_porch" in n for n in _names):
        _cp_w = round(min(26.0 if _cars >= 2 else 13.0, _bw * 0.72), 1)
        _rooms.insert(0, {
            "name": "car_porch", "floor": 0,
            "width_ft": _cp_w, "depth_ft": 13.0, "area_sqft": round(_cp_w * 13.0, 1),
            "windows": 0, "door_count": 0, "attached_bathroom": False, "attached_balcony": False,
            "notes": "covered parking 2 cars" if _cars >= 2 else "covered parking 1 car",
        })
        print(f"[vfp] Guaranteed car_porch {_cp_w}ft wide")

    # 2. sit_out (Vastu mandatory)
    if _vastu and not any("sit_out" in n for n in _names):
        _rooms.insert(1, {
            "name": "sit_out", "floor": 0,
            "width_ft": 8.0, "depth_ft": 5.0, "area_sqft": 40.0,
            "windows": 0, "door_count": 1, "attached_bathroom": False, "attached_balcony": False,
            "notes": "vastu verandah at entrance, northeast zone, covered sit-out",
        })
        print("[vfp] Guaranteed sit_out")

    # 3. pooja_room (Vastu mandatory)
    if _vastu and not any("pooja" in n or "prayer" in n for n in _names):
        _rooms.insert(2, {
            "name": "pooja_room", "floor": 0,
            "width_ft": 8.0, "depth_ft": 8.0, "area_sqft": 64.0,
            "windows": 1, "door_count": 1,
            "attached_bathroom": False, "attached_balcony": False,
            "notes": "northeast Vastu zone, pooja altar",
        })
        print("[vfp] Guaranteed pooja_room in NE zone")

    # 4. family_lounge (mandatory every G+1)
    if _floors >= 2 and not any("family_lounge" in n for n in _names):
        _rooms.append({
            "name": "family_lounge", "floor": 1,
            "width_ft": 12.0, "depth_ft": 8.0, "area_sqft": 96.0,
            "windows": 2, "door_count": 1, "attached_bathroom": False, "attached_balcony": False,
            "notes": "first floor family lounge connecting bedrooms",
        })
        print("[vfp] Guaranteed family_lounge on FF")
        _names = {r.get("name", "") for r in _rooms}

    # 4b. First-floor study (G+1 — fills FF public band instead of leaving half a plate outdoor-only)
    if _floors >= 2 and _bw >= 22.0:

        def _ff_has_work_zone(rr: Dict[str, Any]) -> bool:
            nm = str(rr.get("name", "")).lower()
            fl = int(rr.get("floor", 0) or 0)
            if fl != 1:
                return False
            return any(k in nm for k in ("study", "library", "home_office", "office", "work"))

        if not any(_ff_has_work_zone(r) for r in _rooms):
            _sw = round(min(11.0, max(8.5, _bw * 0.28)), 1)
            _sd = 9.0
            _rooms.append({
                "name": "study", "floor": 1,
                "width_ft": _sw, "depth_ft": _sd,
                "area_sqft": round(_sw * _sd, 1),
                "windows": 1, "door_count": 1,
                "attached_bathroom": False, "attached_balcony": False,
                "notes": "first-floor study off lounge/corridor — keeps G+1 plate efficient",
            })
            print("[vfp] Guaranteed study on FF (G+1 built width programme fill)")
            _names = {r.get("name", "") for r in _rooms}

    # 5. terrace (mandatory every G+1) — cap default width so rear band can share with balcony
    if _floors >= 2 and not any("terrace" in n for n in _names):
        _tw = round(min(_bw, max(14.0, _bw * 0.58)), 1)
        _td = min(12.0, max(8.5, _bw * 0.22))
        _rooms.append({
            "name": "terrace", "floor": 1,
            "width_ft": _tw, "depth_ft": round(_td, 1),
            "area_sqft": round(_tw * _td, 1),
            "windows": 0, "door_count": 1, "attached_bathroom": False, "attached_balcony": False,
            "notes": "open terrace, accessible from first floor corridor",
        })
        print("[vfp] Guaranteed terrace on FF")
        _names = {r.get("name", "") for r in _rooms}
        if _bw >= 24.0 and not any("balcony" in str(nn).lower() for nn in _names):
            _bw_ft = round(min(6.5, max(4.5, _bw * 0.14)), 1)
            _bd = round(min(11.0, max(7.5, _td + 1.0)), 1)
            _rooms.append({
                "name": "balcony", "floor": 1,
                "width_ft": _bw_ft, "depth_ft": _bd,
                "area_sqft": round(_bw_ft * _bd, 1),
                "windows": 0, "door_count": 1, "attached_bathroom": False, "attached_balcony": True,
                "notes": "slim service balcony or utility drying — splits outdoor band from one mega-void",
            })
            print("[vfp] Guaranteed balcony on FF alongside terrace (G+1)")

    # 6. master_bedroom_bathroom + walk_in_wardrobe
    for _br in list(_rooms):
        if _br.get("name") == "master_bedroom":
            _has_wic = any("walk_in_wardrobe" in r.get("name", "") for r in _rooms)
            if not _has_wic and _bps >= 5000:
                _rooms.append({
                    "name": "walk_in_wardrobe",
                    "floor": int(_br.get("floor", 1)),
                    "area_sqft": 64.0, "width_ft": 8.0, "depth_ft": 8.0,
                    "attached_bathroom": False, "attached_balcony": False,
                    "windows": 0, "door_count": 1,
                    "notes": "walk-in wardrobe attached to master bedroom suite",
                })
                print("[vfp] Guaranteed walk_in_wardrobe")
        if _br.get("name") == "master_bedroom" and _br.get("attached_bathroom"):
            _has_mb_bath = any("master_bedroom_bathroom" in r.get("name", "") for r in _rooms)
            if not _has_mb_bath:
                _b_w = 8.0 if _bps >= 5000 else 5.5
                _b_d = 10.0 if _bps >= 5000 else 8.0
                _rooms.append({
                    "name": "master_bedroom_bathroom",
                    "floor": int(_br.get("floor", 1)),
                    "area_sqft": round(_b_w * _b_d, 1), "width_ft": _b_w, "depth_ft": _b_d,
                    "attached_bathroom": False, "attached_balcony": False,
                    "windows": 1, "door_count": 1,
                    "notes": "luxury 5-fixture bath" if _bps >= 5000 else "standard 3-fixture bathroom",
                })
                print("[vfp] Guaranteed master_bedroom_bathroom")

    out["rooms"] = _rooms

    # ── Floor assignment corrections ───────────────────────────────────────────
    floors  = int(out.get("floors", 1) or 1)
    rooms: List[Dict[str, Any]] = out.get("rooms") or []

    master_floor = next(
        (int(r.get("floor", 0)) for r in rooms
         if "master_bedroom" in str(r.get("name", "")) and "_bathroom" not in str(r.get("name", ""))),
        1 if floors >= 2 else 0,
    )

    for room in rooms:
        name = str(room.get("name", "")).lower()
        current_floor = int(room.get("floor", 0) or 0)

        # Category hint injection
        if "family_lounge" in name or ("lounge" in name and "family" in name):
            room["__category_hint"] = "family_lounge" if (floors >= 2 and current_floor == 1) else "living_room"
        elif "servant_bathroom" in name or ("servant" in name and "bath" in name):
            room["__category_hint"] = "bathroom"
        elif "staircase_landing" in name or "stair_void" in name:
            room["__category_hint"] = "staircase_landing"
        elif "lounge" in name and "family" not in name:
            room["__category_hint"] = "living_room"
        else:
            # Longer fragments first so "staircase_landing" is not swallowed by "staircase".
            for fragment, cat in sorted(
                _CATEGORY_OVERRIDES.items(), key=lambda kv: -len(kv[0])
            ):
                if fragment in name:
                    room["__category_hint"] = cat
                    break

        # Force ground floor rooms
        for fragment in _FORCE_GROUND_FLOOR:
            if fragment in name:
                room["floor"] = 0
                break

        # Force upper floor rooms (multi-floor only)
        if floors >= 2:
            for fragment in _FORCE_UPPER_FLOOR:
                if fragment in name:
                    room["floor"] = 1
                    break
            if "walk_in_wardrobe" in name or ("wardrobe" in name and "walk_in" in name):
                room["floor"] = master_floor

    # ── Staircase landing injection (architecturally mandatory for G+1) ────────
    if floors >= 2:
        ground_staircase = next(
            (r for r in rooms
             if "staircase" in str(r.get("name", "")).lower()
             and "_landing" not in str(r.get("name", "")).lower()
             and int(r.get("floor", 0) or 0) == 0),
            None,
        )
        has_landing = any(
            "staircase_landing" in str(r.get("name", "")).lower()
            or ("staircase" in str(r.get("name", "")).lower() and int(r.get("floor", 0) or 0) >= 1)
            for r in rooms
        )
        if ground_staircase and not has_landing:
            for upper_floor in range(1, floors):
                stair_w = float(ground_staircase.get("width_ft",  6))
                stair_d = float(ground_staircase.get("depth_ft", 10))
                rooms.append({
                    "name":              "staircase_landing",
                    "floor":             upper_floor,
                    "area_sqft":         stair_w * stair_d,
                    "width_ft":          stair_w,
                    "depth_ft":          stair_d,
                    "attached_bathroom": False,
                    "attached_balcony":  False,
                    "windows":           0,
                    "door_count":        1,
                    "notes":             "staircase void/opening in slab — same position as ground floor stair",
                    "__category_hint":   "staircase_landing",
                })

    # ── Foyer injection (luxury builds) ───────────────────────────────────────
    has_foyer     = any("foyer" in str(r.get("name", "")).lower() for r in rooms)
    style_str     = str(out.get("style", "")).lower()
    budget_val    = int(out.get("budget", 0) or 0)
    budget_per_sqft = int(out.get("budget_per_sqft", 0) or 0)
    is_luxury = (
        budget_per_sqft >= 2500 or budget_val >= 2000000 or
        any(kw in style_str for kw in ("luxury", "premium", "high-end", "duplex", "villa"))
    )
    if not has_foyer and is_luxury:
        foyer_w = 10.0 if budget_per_sqft >= 5000 else 8.0
        foyer_d = 10.0 if budget_per_sqft >= 5000 else 9.0
        rooms.insert(0, {
            "name": "foyer", "floor": 0,
            "area_sqft": round(foyer_w * foyer_d, 1),
            "width_ft": foyer_w, "depth_ft": foyer_d,
            "attached_bathroom": False, "attached_balcony": False,
            "windows": 1, "door_count": 1,
            "notes": "entrance foyer, northeast Vastu zone",
            "__category_hint": "foyer",
        })

    out["rooms"] = rooms
    return out


# ── Per-floor parsed context builder ──────────────────────────────────────────

def _build_floor_context(
    parsed: Dict[str, Any],
    floor_index: int,
) -> Dict[str, Any]:
    """Build a modified parsed dict scoped to a single floor."""
    ctx = copy.deepcopy(parsed)
    ctx["_floor_label"]  = _FLOOR_LABELS.get(floor_index, f"FLOOR {floor_index}")
    ctx["_floor_index"]  = floor_index
    ctx["_floors_total"] = int(parsed.get("floors", 1) or 1)
    ctx["rooms"] = [
        r for r in (parsed.get("rooms") or [])
        if int(r.get("floor", 0) or 0) == floor_index
    ]
    return ctx


# ── Main pipeline ──────────────────────────────────────────────────────────────

async def generate_visual_floor_plan(
    parsed_json: Dict[str, Any],
    output_dir: str = "outputs/",
    include_ai_render: bool = False,   # DEPRECATED — always False. Phase 2 handles 3D.
) -> Dict[str, Any]:
    """
    Multi-floor floor plan pipeline.

    Phase 1: SVG (deterministic, zero API cost).
    Phase 2: Three.js 3D HTML (procedural, zero API cost).

    For each floor:
      1. generate_layout(floor_index)   →  pixel-accurate room placement
      2. check_architectural_rules()   →  Vastu + NBC compliance check
      3. render_floor_plan_svg()        →  semantic SVG with data-* attributes
      4. render_floor_plan_dxf()        →  AutoCAD DXF export
      5. render_3d_html()               →  Three.js 3D interactive viewer
      6. score_plan()                   →  0-100 plan quality score

    Returns:
      per_floor_svgs     : Dict[str, str]   — SVG per floor keyed "0","1",...
      per_floor_3d       : Dict[str, str]   — 3D HTML per floor keyed "0","1",...
      per_floor_layouts  : Dict[str, Dict]  — room placement data per floor
      per_floor_scores   : Dict[str, Dict]  — quality scores per floor
      rooms_placed       : int
      rooms_failed       : list
      warnings           : list
    """
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # ── 1. Pre-process: fix floor assignments + inject category hints ──────────
    parsed = _fix_parsed_rooms(parsed_json)

    floors = int(parsed.get("floors", 1) or 1)
    floors = max(1, min(floors, 4))

    # Debug: log room→floor assignments
    _floor_summary: Dict[int, List[str]] = {}
    for _r in parsed.get("rooms") or []:
        _f = int(_r.get("floor", 0) or 0)
        _floor_summary.setdefault(_f, []).append(str(_r.get("name", "")))
    for _fi, _rnames in sorted(_floor_summary.items()):
        print(f"[visual_floor_plan] Floor {_fi} ({len(_rnames)} rooms): {_rnames}")

    all_warnings:      List[str] = []
    all_failed:        List[str] = []
    per_floor_layouts: Dict[str, Dict[str, Any]] = {}
    per_floor_svgs:    Dict[str, str] = {}
    per_floor_3d:      Dict[str, str] = {}
    per_floor_scores:  Dict[str, Dict[str, Any]] = {}

    # ── 2. Per-floor loop ──────────────────────────────────────────────────────
    for floor_idx in range(floors):
        label     = _FLOOR_LABELS.get(floor_idx, f"FLOOR {floor_idx}")
        slug      = _FLOOR_SLUGS.get(floor_idx, str(floor_idx))
        floor_out = out_dir / f"floor_{slug}"
        floor_out.mkdir(parents=True, exist_ok=True)

        # ── 2a. Staircase continuity anchor for upper floors ───────────────────
        if floor_idx > 0:
            ground_layout = per_floor_layouts.get("0", {})
            ground_stair  = next(
                (r for r in ground_layout.get("rooms", [])
                 if "staircase" in str(r.get("name", "")).lower()
                 and "_landing" not in str(r.get("name", "")).lower()),
                None,
            )
            if ground_stair:
                for r in parsed.get("rooms") or []:
                    if ("staircase_landing" in str(r.get("name", "")).lower()
                            and int(r.get("floor", 0) or 0) == floor_idx):
                        r["__staircase_anchor_x_px"] = ground_stair["x"]
                        r["__staircase_anchor_y_px"] = ground_stair["y"]
                        r["__staircase_anchor_w_px"] = ground_stair["width"]
                        r["__staircase_anchor_h_px"] = ground_stair["height"]
                        r["width_ft"] = ground_stair["width_ft"]
                        r["depth_ft"] = ground_stair["depth_ft"]

        # ── 2b. Layout engine ──────────────────────────────────────────────────
        layout = generate_layout(parsed, floor_index=floor_idx)
        all_warnings.extend(layout.get("warnings") or [])
        all_failed.extend(layout.get("failed_rooms") or [])
        per_floor_layouts[str(floor_idx)] = layout

        # ── 2c. Architectural rules check ──────────────────────────────────────
        try:
            from app.services.architectural_rules import (
                check_adjacency_violations,
                check_vastu_violations as check_vastu_arch,
            )
            adj_violations = check_adjacency_violations(
                layout.get("rooms", []), layout
            )
            if adj_violations:
                all_warnings.extend(adj_violations)

            if parsed.get("vastu_compliant"):
                vastu_violations = check_vastu_arch(
                    layout.get("rooms", []),
                    str(parsed.get("plot_facing", "unknown")),
                    bool(parsed.get("vastu_compliant", False)),
                )
                if vastu_violations:
                    all_warnings.extend(vastu_violations)
        except ImportError:
            pass

        # Persist layout JSON
        try:
            (floor_out / "layout_data.json").write_text(
                json.dumps(layout, indent=2), encoding="utf-8"
            )
        except Exception:
            pass

        rooms_this_floor = layout.get("rooms") or []
        if not rooms_this_floor:
            all_warnings.append(f"WARNING: No rooms placed for {label} — skipping render.")
            per_floor_svgs[str(floor_idx)] = ""
            per_floor_3d[str(floor_idx)]   = ""
            continue

        # ── 2d. Plan scorer ────────────────────────────────────────────────────
        floor_score: Dict[str, Any] = {}
        if _SCORER_AVAILABLE:
            try:
                floor_score = score_plan(layout, parsed)
                per_floor_scores[str(floor_idx)] = floor_score
                print(
                    f"[visual_floor_plan] Score for {label}: "
                    f"{floor_score.get('total', 0)}/100 Grade {floor_score.get('grade', '?')}"
                )
            except Exception as score_exc:
                all_warnings.append(f"Scorer failed for {label}: {score_exc}")
        else:
            all_warnings.append("plan_scorer not found — add plan_scorer.py to app/services/")

        # ── 2e. SVG renderer — PRIMARY 2D output ──────────────────────────────
        floor_svg = ""
        if _SVG_RENDERER_AVAILABLE:
            try:
                floor_svg = render_floor_plan_svg(
                    layout_data=layout,
                    parsed=parsed,
                    floor_index=floor_idx,
                    floor_label=label,
                )
                svg_file = floor_out / f"floor_plan_{slug}.svg"
                svg_file.write_text(floor_svg, encoding="utf-8")
                per_floor_svgs[str(floor_idx)] = floor_svg
                print(
                    f"[visual_floor_plan] SVG generated for {label}: "
                    f"{len(rooms_this_floor)} rooms, {len(floor_svg)} chars"
                )
            except Exception as svg_exc:
                all_warnings.append(f"SVG render failed for {label}: {svg_exc}")
                per_floor_svgs[str(floor_idx)] = ""
        else:
            all_warnings.append("svg_renderer not found — add svg_renderer.py to app/services/")
            per_floor_svgs[str(floor_idx)] = ""

        # ── 2f. DXF renderer ──────────────────────────────────────────────────
        if _DXF_RENDERER_AVAILABLE:
            try:
                dxf_path = str(floor_out / f"floor_plan_{slug}.dxf")
                render_floor_plan_dxf(
                    layout_data=layout,
                    parsed=parsed,
                    floor_index=floor_idx,
                    floor_label=label,
                    output_path=dxf_path,
                )
                print(f"[visual_floor_plan] DXF generated for {label}: {dxf_path}")
            except Exception as dxf_exc:
                all_warnings.append(f"DXF render failed for {label}: {dxf_exc}")

        # ── 2g. Three.js 3D renderer ───────────────────────────────────────────
        if _3D_RENDERER_AVAILABLE:
            try:
                three_d_path = str(floor_out / f"3d_{slug}.html")
                three_d_html = render_3d_html(
                    layout_data=layout,
                    parsed=parsed,
                    score=floor_score if floor_score else None,
                    floor_label=label,
                    output_path=three_d_path,
                    floor_index=floor_idx,
                )
                per_floor_3d[str(floor_idx)] = three_d_html
                print(
                    f"[visual_floor_plan] 3D HTML generated for {label}: "
                    f"{len(three_d_html)} chars -> {three_d_path}"
                )
            except Exception as td_exc:
                import traceback
                all_warnings.append(f"3D render failed for {label}: {td_exc}")
                print(f"[visual_floor_plan] 3D render EXCEPTION for {label}:")
                traceback.print_exc()
        else:
            all_warnings.append(
                "three_d_renderer not found — add three_d_renderer.py to app/services/"
            )
            per_floor_3d[str(floor_idx)] = ""

    # ── 3. Persist combined layout JSON ───────────────────────────────────────
    try:
        (out_dir / "all_floors_layout.json").write_text(
            json.dumps({"floors": floors, "layouts": per_floor_layouts}, indent=2),
            encoding="utf-8",
        )
    except Exception:
        pass

    # ── 4. Assemble return dict ────────────────────────────────────────────────
    ground_svg   = per_floor_svgs.get("0", "")
    ground_3d    = per_floor_3d.get("0", "")
    total_placed = sum(
        len(per_floor_layouts.get(str(i), {}).get("rooms") or [])
        for i in range(floors)
    )

    return {
        # ── SVG outputs — primary 2D plan ──────────────────────────────────────
        "per_floor_svgs":    per_floor_svgs,
        "ground_floor_svg":  ground_svg,
        "svg_renderer_used": _SVG_RENDERER_AVAILABLE,
        # backwards compat alias
        "enhanced_svg":      ground_svg,

        # ── 3D outputs — Three.js interactive viewer ───────────────────────────
        "per_floor_3d":      per_floor_3d,
        "ground_floor_3d":   ground_3d,
        "renderer_3d_used":  _3D_RENDERER_AVAILABLE,

        # ── Plan scores ────────────────────────────────────────────────────────
        "per_floor_scores":  per_floor_scores,
        "ground_floor_score": per_floor_scores.get("0", {}),
        "scorer_used":        _SCORER_AVAILABLE,

        # ── Layout data for React canvas editor ────────────────────────────────
        "per_floor_layouts": per_floor_layouts,
        "layout_data":       per_floor_layouts.get("0", {}),

        # ── Stats ──────────────────────────────────────────────────────────────
        "floors_generated":  floors,
        "rooms_placed":      total_placed,
        "rooms_failed":      all_failed,
        "warnings":          all_warnings,

        # ── Parsed data for frontend ───────────────────────────────────────────
        "parsed_data":       None,   # set by caller in main.py
    }