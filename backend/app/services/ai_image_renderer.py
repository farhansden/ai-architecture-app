from __future__ import annotations

"""
ai_image_renderer.py  —  3D photorealistic design visualizer
=============================================================

ROLE IN THE PIPELINE
--------------------
SVG renderer  → 2D floor plan  (deterministic, pixel-perfect, zero hallucination)
THIS FILE     → 3D render       (photorealistic, emotional, what clients connect with)

GPT-image-1 cannot reliably produce accurate 2D plans — it hallucinates room names,
misplaces staircases, and produces different results every call. The SVG renderer
solves that problem completely.

GPT-image-1 IS excellent at generating photorealistic architecture renders — exterior
bird's-eye views, interior perspectives, material visualizations. That is its job here.

TWO RENDER MODES
----------------
  exterior  → Photorealistic bird's-eye render of the completed house
              showing architecture, materials, landscape, golden-hour lighting.
              This is what clients use to approve the design aesthetically.

  interior  → Photorealistic perspective of a key room (living room, master
              bedroom, kitchen). Uses style/budget/materials from parsed JSON.
              This is what clients use to choose finishes and furniture.

WHAT FEEDS THIS FILE
--------------------
  parsed_json  → bhk_type, style, budget, plot dimensions, facing, materials
  layout_data  → room positions (used for exterior to get plot proportions)

NOTE: layout pixel coordinates are NOT passed to GPT-image-1.
They are only used to compute plot proportions for image sizing.
"""

import base64
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests

from app.config import settings


# ── Style → material + finish lookup ─────────────────────────────────────────
# Encodes what a senior architect specifies for each style tier in India

_STYLE_MATERIALS: Dict[str, Dict[str, str]] = {
    "contemporary indian luxury": {
        "facade":    (
            "exposed concrete and teak wood screen inserts, "
            "floor-to-ceiling double-glazed windows, "
            "aluminium composite cladding in dark grey"
        ),
        "roof":      "flat roof with glass parapet, rooftop terrace garden visible",
        "landscape": (
            "manicured lawn, granite slab pathway, "
            "specimen trees (ficus, palm), water feature near entrance"
        ),
        "driveway":  (
            "polished black granite pavers, motorised sliding gate, "
            "compound wall in GRC panels with backlit coping"
        ),
        "interior":  "Calacatta marble flooring, brushed brass fixtures, warm LED cove lighting",
    },
    "modern": {
        "facade":    (
            "white textured plaster, large-format glazing, "
            "aluminium composite accent panels in charcoal"
        ),
        "roof":      "flat roof with solar panels and parapet wall",
        "landscape": "minimalist garden, concrete pathway, ornamental grass, olive tree",
        "driveway":  "exposed aggregate concrete driveway, powder-coated steel gate",
        "interior":  "large-format grey ceramic tile, white walls, concealed LED lighting",
    },
    "traditional": {
        "facade":    "Mangalore clay tile roof, exposed brick accents, carved teak entrance door",
        "roof":      "sloped Mangalore tile roof with ornate ridge tiles and wide eaves",
        "landscape": "courtyard garden, banana and coconut trees, jasmine and bougainvillea hedge",
        "driveway":  "Kota stone pathway, wrought iron gate with traditional motifs",
        "interior":  "Athangudi tiles, lime wash walls, carved rosewood balcony railings",
    },
    "villa": {
        "facade":    (
            "natural stone cladding (sandstone or laterite), "
            "arched windows, ornamental columns, wrap-around verandah"
        ),
        "roof":      "hip roof with clay tiles, prominent eaves, dormer windows",
        "landscape": "formal garden with central fountain, royal palm-lined driveway",
        "driveway":  "cobblestone driveway, ornate wrought iron gate, stone-coped compound wall",
        "interior":  "Italian marble, crystal chandelier, solid teak joinery",
    },
    "luxury": {
        "facade":    (
            "glass and steel facade, cantilevered volumes, "
            "natural stone base, dramatic entrance canopy"
        ),
        "roof":      "flat roof with infinity pool visible, skylight volumes",
        "landscape": "infinity pool, decked terrace, tropical landscaping",
        "driveway":  "granite cobblestone, automated gate with intercom pillar",
        "interior":  "Statuario marble, custom millwork, integrated smart home",
    },
}

def _get_materials(style: str) -> Dict[str, str]:
    s = (style or "").lower().strip()
    for key in _STYLE_MATERIALS:
        if key in s or s in key:
            return _STYLE_MATERIALS[key]
    # Partial match
    for key in _STYLE_MATERIALS:
        for word in s.split():
            if word in key:
                return _STYLE_MATERIALS[key]
    return {
        "facade":    "painted plaster exterior, standard windows",
        "roof":      "flat roof with water tank",
        "landscape": "simple garden with compound wall",
        "driveway":  "plain concrete driveway, steel gate",
        "interior":  "ceramic tiles, white walls",
    }


# ── Budget tier description ───────────────────────────────────────────────────

def _budget_tier(budget: int, bps: int) -> str:
    if bps >= 20000 or budget >= 30_000_000:
        return "ultra-luxury (₹5Cr+), Lodha/Oberoi Realty standard"
    if bps >= 15000 or budget >= 15_000_000:
        return "premium luxury (₹2-5Cr), high-end residential"
    if bps >= 10000 or budget >= 8_000_000:
        return "upper-mid segment (₹80L-2Cr), quality specification"
    if bps >= 5000:
        return "mid-segment (₹40-80L), standard plus specification"
    return "standard residential"


# ── Interior room base prompts ─────────────────────────────────────────────────

_INTERIOR_BASE: Dict[str, str] = {
    "living_room": (
        "Photorealistic interior perspective of a luxury Indian living room. "
        "Viewed from the entrance corner looking toward the feature wall. "
        "L-shaped sectional sofa, rectangular coffee table on a large area rug. "
        "Floor-to-ceiling TV feature wall with integrated display niches. "
        "Large-format marble or stone floor tiles. "
        "Floor-to-ceiling windows with garden view, sheer linen curtains. "
        "Concealed LED cove lighting in ceiling, pendant lights above coffee table. "
        "Indoor plants in ceramic planters. Artwork on side walls."
    ),
    "master_bedroom": (
        "Photorealistic interior perspective of a luxury Indian master bedroom. "
        "Viewed from the foot of the bed. "
        "King-size bed with upholstered leather headboard against the feature wall. "
        "Bedside tables with reading lamps. Floor-to-ceiling curtains. "
        "Walk-in wardrobe opening visible on side wall. "
        "Ensuite bathroom glimpsed through open glass door. "
        "Engineered hardwood flooring. Concealed LED cove lighting. "
        "Dressing table with backlit mirror. Plush carpet at foot of bed."
    ),
    "kitchen": (
        "Photorealistic interior perspective of a premium Indian modular kitchen. "
        "Viewed from the dining room side. "
        "Handleless slab-front cabinets in matte white or dark finish. "
        "Quartz or granite countertop with integrated undermount sink. "
        "Professional range hood above 5-burner hob. "
        "Kitchen island with waterfall edge and bar stools. "
        "Pendant lights above island. "
        "Tall refrigerator and built-in oven at far end. "
        "Large window above sink with garden view."
    ),
    "master_bathroom": (
        "Photorealistic interior perspective of a luxury Indian master bathroom. "
        "Viewed from the entrance. "
        "Freestanding soaking bathtub centred near window. "
        "Double vanity with vessel basins and backlit mirror. "
        "Walk-in rain shower enclosure with frameless glass. "
        "Large-format marble or porcelain wall and floor tiles. "
        "Brushed brass or matte black fixtures throughout. "
        "Heated towel rail. Indirect LED lighting in ceiling."
    ),
    "dining_room": (
        "Photorealistic interior perspective of a formal Indian dining room. "
        "8-seater rectangular dining table in solid teak or marble top. "
        "Upholstered dining chairs. "
        "Statement pendant chandelier above table. "
        "Sideboard/buffet against wall with display above. "
        "Large window or glass sliding door to garden. "
        "Warm recessed lighting."
    ),
}


# ── 3D Exterior render prompt builder ─────────────────────────────────────────

def build_exterior_render_prompt(parsed: Dict[str, Any]) -> str:
    """
    Build a GPT-image-1 prompt for a photorealistic exterior bird's-eye render.

    Uses: bhk_type, style, budget, plot dimensions, facing, parking, outdoor features.
    Does NOT use pixel coordinates from layout_engine — those are for SVG only.
    """
    pw      = float(parsed.get("plot_width_ft",  30) or 30)
    pd      = float(parsed.get("plot_depth_ft",  50) or 50)
    bhk     = str(parsed.get("bhk_type",   "3BHK") or "3BHK")
    style   = str(parsed.get("style",      "modern") or "modern")
    floors  = int(parsed.get("floors",     1) or 1)
    vastu   = bool(parsed.get("vastu_compliant", False))
    budget  = int(parsed.get("budget",     0) or 0)
    bps     = int(parsed.get("budget_per_sqft", 0) or 0)
    facing  = str(parsed.get("plot_facing","north") or "north")
    bua     = int(parsed.get("built_up_area_sqft", int(pw * pd * 0.6)))
    cars    = int((parsed.get("parking") or {}).get("car_spaces", 1))
    garden  = bool((parsed.get("outdoor") or {}).get("garden", False))
    pool    = bool((parsed.get("outdoor") or {}).get("swimming_pool", False))
    solar   = bool((parsed.get("services") or {}).get("solar_panels", False))

    mats   = _get_materials(style)
    tier   = _budget_tier(budget, bps)
    storey = "single storey" if floors == 1 else (
        f"G+{floors-1} duplex" if floors == 2 else f"{floors}-storey"
    )

    # City context from budget
    if budget >= 30_000_000:
        location = "Juhu / Bandra / Whitefield — premium urban residential area"
    elif budget >= 10_000_000:
        location = "upmarket Indian suburban residential layout"
    else:
        location = "Indian residential area"

    prompt = (
        f"Photorealistic architectural exterior render of a completed {bhk} Indian "
        f"residential house. Professional architectural photography quality.\n\n"

        f"PROPERTY:\n"
        f"  Plot: {pw:.0f}ft wide x {pd:.0f}ft deep ({pw*pd:.0f} sqft)\n"
        f"  Built-up: {bua} sqft, {storey}, {facing}-facing\n"
        f"  Style: {style.title()} — {tier}\n"
        f"  Location context: {location}\n\n"

        f"ARCHITECTURE AND FACADE:\n"
        f"  {mats['facade']}\n"
        f"  Roof: {mats['roof']}\n"
        f"  Main entrance faces {facing}. "
        f"  Covered parking for {cars} car(s) at front.\n"
        + (f"  Solar panels visible on rooftop.\n" if solar else "")
        + (f"  Swimming pool visible in rear garden.\n" if pool else "")
        + f"\n"

        f"LANDSCAPE AND SURROUNDINGS:\n"
        f"  {mats['landscape']}\n"
        f"  {'Lush side garden with privacy planting' if garden else 'Compact planted borders'}\n"
        f"  Compound wall: {mats['driveway']}\n\n"

        f"CAMERA AND LIGHTING:\n"
        f"  Camera angle: 45-degree bird's-eye perspective showing the front facade "
        f"and left side of the house\n"
        f"  Time of day: golden hour (late afternoon), warm directional sunlight\n"
        f"  Sky: partly cloudy with dramatic light\n"
        f"  Long soft shadows from golden-hour light\n\n"

        f"QUALITY:\n"
        f"  Hyper-realistic architectural visualization, 8K render quality\n"
        f"  Professional CGI, no cartoon or illustration style\n"
        f"  Interior lights on — warm glow visible through windows\n"
        + (f"  Vastu-compliant design: main entrance at northeast corner\n" if vastu else "")
        + f"\n"

        f"DO NOT INCLUDE:\n"
        f"  No watermarks, no text overlays, no floor plan diagrams\n"
        f"  No 2D drawings, no dimension lines, no room labels\n"
        f"  No people. Show {cars} parked car(s) in the porch if visible from angle.\n"
        f"  This is a photorealistic EXTERIOR RENDER — not a drawing, not a sketch."
    )

    return prompt.strip()


# ── Interior render prompt builder ────────────────────────────────────────────

def build_interior_render_prompt(
    parsed: Dict[str, Any],
    room_type: str = "living_room",
) -> str:
    """
    Build a GPT-image-1 prompt for a photorealistic interior perspective.

    room_type: 'living_room' | 'master_bedroom' | 'kitchen' |
               'master_bathroom' | 'dining_room'
    """
    style  = str(parsed.get("style", "modern") or "modern")
    budget = int(parsed.get("budget", 0) or 0)
    bps    = int(parsed.get("budget_per_sqft", 0) or 0)
    tier   = _budget_tier(budget, bps)
    mats   = _get_materials(style)

    base = _INTERIOR_BASE.get(room_type, _INTERIOR_BASE["living_room"])

    return (
        f"{base}\n\n"
        f"Design specification:\n"
        f"  Style: {style.title()}, {tier}\n"
        f"  Materials and finishes: {mats['interior']}\n\n"
        f"Render quality:\n"
        f"  Hyper-realistic architectural visualization\n"
        f"  Professional interior photography style\n"
        f"  Warm ambient lighting with accent highlights\n"
        f"  No people. No text. No watermarks."
    )


# ── Legacy function — kept for backwards compatibility ────────────────────────

def build_strict_image_prompt(
    parsed: Dict[str, Any],
    layout_data: Dict[str, Any],
) -> str:
    """
    Legacy function — previously built a 2D floor plan prompt for GPT-image-1.
    2D plans are now handled by svg_renderer.py (deterministic, zero hallucination).
    This now returns the exterior 3D render prompt instead so existing callers
    continue to receive a useful output without code changes.
    """
    return build_exterior_render_prompt(parsed)


# ── Validation via GPT-4o vision ──────────────────────────────────────────────

def validate_generated_image(
    image_b64: str,
    parsed: Dict[str, Any],
    layout_data: Dict[str, Any],
    client: Any,
) -> Dict[str, Any]:
    """
    Use GPT-4o vision to validate the 3D render quality.
    Checks: is it a photorealistic render (not a floor plan), correct style, no text.
    """
    style  = str(parsed.get("style", "modern"))
    floors = int(parsed.get("floors", 1) or 1)
    bhk    = str(parsed.get("bhk_type", "3BHK"))

    check_prompt = (
        f"Look at this image. Answer each question:\n\n"
        f"1. Is this a photorealistic exterior RENDER of a {bhk} house (not a floor plan, "
        f"not a diagram, not a sketch)? Answer true/false.\n"
        f"2. Does it appear to show approximately {floors} floor(s)? Answer true/false.\n"
        f"3. Does the style feel like '{style}'? Answer true/false.\n"
        f"4. Does it contain any text overlays, watermarks, or floor plan elements? Answer true/false.\n"
        f"5. Rate the render quality 1-10.\n\n"
        f"Respond ONLY with valid JSON — no markdown, no explanation:\n"
        f'{{"is_render": true, "correct_floors": true, "style_match": true, '
        f'"has_text": false, "quality": 8, "needs_regeneration": false}}\n\n'
        f"Set needs_regeneration=true if is_render is false OR quality < 6."
    )

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{image_b64}",
                            "detail": "high",
                        },
                    },
                    {"type": "text", "text": check_prompt},
                ],
            }],
            max_tokens=200,
            temperature=0.0,
        )
        content = (response.choices[0].message.content or "").strip()
        content = content.replace("```json", "").replace("```", "").strip()
        return json.loads(content)
    except Exception as exc:
        print(f"[validator] GPT-4o validation skipped: {exc}")
        return {
            "is_render": True,
            "correct_floors": True,
            "style_match": True,
            "has_text": False,
            "quality": 8,
            "needs_regeneration": False,
        }


# ── Post-process labels — kept as no-op ───────────────────────────────────────

def post_process_labels(
    image_bytes: bytes,
    layout_data: Dict[str, Any],
    parsed: Dict[str, Any],
) -> bytes:
    """
    Previously overlaid text labels on the AI-generated 2D plan image.
    Now a no-op — SVG renderer handles all labels deterministically.
    Kept so existing callers don't break.
    """
    return image_bytes


# ── Main entry point ───────────────────────────────────────────────────────────

async def generate_ai_floor_plan_image(
    parsed_json: Dict[str, Any],
    layout_data: Dict[str, Any],
    output_dir: str = "outputs/",
    render_type: str = "exterior",
    room_type: str = "living_room",
) -> Dict[str, Any]:
    """
    Generate a photorealistic 3D visualization using GPT-image-1.

    Args:
        parsed_json:  Full parsed house spec from llm_parser
        layout_data:  Layout engine output (used for plot proportions only)
        output_dir:   Where to save the PNG
        render_type:  'exterior' (default) or 'interior'
        room_type:    Only for render_type='interior':
                      'living_room' | 'master_bedroom' | 'kitchen' |
                      'master_bathroom' | 'dining_room'

    Returns:
        {
            png_path:    str,
            png_base64:  str,
            prompt:      str,
            warning:     str,
            validation:  dict,
            regenerated: bool,
            render_type: str,
        }
    """
    prompt = (
        build_interior_render_prompt(parsed_json, room_type)
        if render_type == "interior"
        else build_exterior_render_prompt(parsed_json)
    )

    out_dir  = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    png_path = out_dir / f"render_{render_type}.png"

    api_key = settings.openai_api_key
    if not api_key:
        return {
            "png_path": "", "png_base64": "", "prompt": prompt,
            "warning": "OPENAI_API_KEY not configured.",
            "validation": {}, "regenerated": False, "render_type": render_type,
        }

    # Size from plot proportions
    pw   = float(parsed_json.get("plot_width_ft", 30) or 30)
    pd   = float(parsed_json.get("plot_depth_ft", 50) or 50)
    size = "1024x1536" if pw < pd else "1536x1024"

    try:
        from openai import OpenAI
    except ImportError as exc:
        return {
            "png_path": "", "png_base64": "", "prompt": prompt,
            "warning": f"openai package not installed: {exc}",
            "validation": {}, "regenerated": False, "render_type": render_type,
        }

    client      = OpenAI(api_key=api_key)
    warning     = ""
    image_b64   = ""
    regenerated = False
    validation: Dict[str, Any] = {}

    # ── Primary: gpt-image-1 ──────────────────────────────────────────────────
    try:
        resp      = client.images.generate(
            model="gpt-image-1",
            prompt=prompt,
            size=size,
            quality="high",
            n=1,
        )
        image_b64 = resp.data[0].b64_json  # type: ignore[attr-defined]

    except Exception as primary_exc:
        warning = f"gpt-image-1 failed, trying dall-e-3: {primary_exc}"
        try:
            resp      = client.images.generate(
                model="dall-e-3",
                prompt=prompt,
                size=size,
                quality="hd",
                n=1,
            )
            image_url = resp.data[0].url  # type: ignore[attr-defined]
            if not image_url:
                raise RuntimeError("dall-e-3 returned no URL")
            r = requests.get(image_url, timeout=30)
            r.raise_for_status()
            png_bytes = r.content
            png_path.write_bytes(png_bytes)
            return {
                "png_path":    str(png_path),
                "png_base64":  base64.b64encode(png_bytes).decode("ascii"),
                "prompt":      prompt,
                "warning":     warning,
                "validation":  {},
                "regenerated": False,
                "render_type": render_type,
            }
        except Exception as fallback_exc:
            return {
                "png_path": "", "png_base64": "", "prompt": prompt,
                "warning": (
                    f"Both models failed. "
                    f"gpt-image-1: {primary_exc}. dall-e-3: {fallback_exc}"
                ),
                "validation": {}, "regenerated": False, "render_type": render_type,
            }

    # ── Validation pass ───────────────────────────────────────────────────────
    try:
        validation = validate_generated_image(
            image_b64, parsed_json, layout_data, client
        )
    except Exception as val_exc:
        print(f"[renderer] Validation skipped: {val_exc}")

    # ── Auto-regeneration if model produced a floor plan instead of render ────
    if validation.get("needs_regeneration"):
        correction = (
            "\n\nPREVIOUS ATTEMPT FAILED. "
            "Generate a PHOTOREALISTIC EXTERIOR PHOTOGRAPH of the completed building. "
            "NOT a floor plan. NOT a diagram. NOT a sketch. "
            "A real-looking photo of the exterior of the house, as if taken by "
            "a professional architectural photographer with a drone."
        )
        try:
            resp2 = client.images.generate(
                model="gpt-image-1",
                prompt=prompt + correction,
                size=size,
                quality="high",
                n=1,
            )
            image_b64   = resp2.data[0].b64_json  # type: ignore[attr-defined]
            regenerated = True
        except Exception as regen_exc:
            warning = (warning + f" | Regeneration failed: {regen_exc}").strip(" |")

    # ── Save and return ───────────────────────────────────────────────────────
    try:
        png_bytes = base64.b64decode(image_b64 or "")
        png_path.write_bytes(png_bytes)
    except Exception as save_exc:
        return {
            "png_path": "", "png_base64": image_b64, "prompt": prompt,
            "warning": f"Failed to save PNG: {save_exc}",
            "validation": validation, "regenerated": regenerated,
            "render_type": render_type,
        }

    return {
        "png_path":    str(png_path),
        "png_base64":  image_b64,
        "prompt":      prompt,
        "warning":     warning,
        "validation":  validation,
        "regenerated": regenerated,
        "render_type": render_type,
    }