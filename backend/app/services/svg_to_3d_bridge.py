from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional
from xml.etree import ElementTree as ET

from app.services.ai_image_renderer import generate_ai_floor_plan_image
from app.services.three_d_renderer import render_3d_html


SVG_NS = "{http://www.w3.org/2000/svg}"


def _to_float(value: Optional[str], default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _to_int(value: Optional[str], default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _parse_viewbox(root: ET.Element) -> Dict[str, float]:
    vb = (root.attrib.get("viewBox") or "").strip()
    parts = re.split(r"\s+", vb) if vb else []
    if len(parts) == 4:
        return {
            "min_x": _to_float(parts[0], 0.0),
            "min_y": _to_float(parts[1], 0.0),
            "width": _to_float(parts[2], 1200.0),
            "height": _to_float(parts[3], 900.0),
        }
    return {"min_x": 0.0, "min_y": 0.0, "width": 1200.0, "height": 900.0}


def _extract_rooms(root: ET.Element) -> List[Dict[str, Any]]:
    rooms: List[Dict[str, Any]] = []
    all_groups = list(root.findall(f".//{SVG_NS}g")) + list(root.findall(".//g"))

    for g in all_groups:
        if g.attrib.get("data-editable") != "true":
            continue

        name = g.attrib.get("data-name") or "room"
        x_ft = _to_float(g.attrib.get("data-x-ft"), 0.0)
        y_ft = _to_float(g.attrib.get("data-y-ft"), 0.0)
        w_ft = _to_float(g.attrib.get("data-width-ft"), 0.0)
        d_ft = _to_float(g.attrib.get("data-depth-ft"), 0.0)

        # Fall back to rect pixel dimensions if ft attributes are missing.
        if w_ft <= 0.0 or d_ft <= 0.0:
            rect = g.find(f"{SVG_NS}rect") or g.find("rect")
            if rect is not None:
                w_ft = max(w_ft, _to_float(rect.attrib.get("width"), 0.0) / 10.0)
                d_ft = max(d_ft, _to_float(rect.attrib.get("height"), 0.0) / 10.0)

        if w_ft <= 0.0 or d_ft <= 0.0:
            continue

        rooms.append(
            {
                "name": name,
                "x_ft": x_ft,
                "y_ft": y_ft,
                "width_ft": w_ft,
                "depth_ft": d_ft,
                "area_sqft": _to_float(g.attrib.get("data-sqft"), w_ft * d_ft),
                "windows": 1,
                "door_count": 1,
                "attached_bathroom": False,
                "attached_balcony": False,
                "__cat": g.attrib.get("data-cat") or "",
                "__vastu_zone": g.attrib.get("data-vastu-zone") or "",
            }
        )

    return rooms


def parse_svg_to_layout(svg_content: str) -> Dict[str, Any]:
    root = ET.fromstring(svg_content)
    view = _parse_viewbox(root)
    floor = _to_int(root.attrib.get("data-floor"), 0)
    rooms = _extract_rooms(root)

    plot_w_px = view["width"]
    plot_h_px = view["height"]

    # Default simple built-up box from room extents.
    if rooms:
        x0 = min(r["x_ft"] for r in rooms)
        y0 = min(r["y_ft"] for r in rooms)
        x1 = max(r["x_ft"] + r["width_ft"] for r in rooms)
        y1 = max(r["y_ft"] + r["depth_ft"] for r in rooms)
        built_up_x = x0 * 10.0
        built_up_y = y0 * 10.0
        built_up_w = max(1.0, (x1 - x0) * 10.0)
        built_up_h = max(1.0, (y1 - y0) * 10.0)
    else:
        built_up_x = 80.0
        built_up_y = 120.0
        built_up_w = max(300.0, plot_w_px * 0.5)
        built_up_h = max(420.0, plot_h_px * 0.6)

    layout_rooms: List[Dict[str, Any]] = []
    for room in rooms:
        layout_rooms.append(
            {
                "name": room["name"],
                "x": room["x_ft"] * 10.0,
                "y": room["y_ft"] * 10.0,
                "width": room["width_ft"] * 10.0,
                "height": room["depth_ft"] * 10.0,
                "width_ft": room["width_ft"],
                "depth_ft": room["depth_ft"],
                "area_sqft": room["area_sqft"],
                "windows": room["windows"],
                "door_count": room["door_count"],
                "__cat": room["__cat"],
                "__vastu_zone": room["__vastu_zone"],
            }
        )

    return {
        "floor_index": floor,
        "canvas_w": int(plot_w_px),
        "canvas_h": int(plot_h_px),
        "plot_w_px": plot_w_px,
        "plot_h_px": plot_h_px,
        "built_up_x": built_up_x,
        "built_up_y": built_up_y,
        "built_up_w": built_up_w,
        "built_up_h": built_up_h,
        "scale": 10,
        "rooms": layout_rooms,
        "warnings": [],
        "failed_rooms": [],
    }


def _infer_parsed_from_layout(
    layout_data: Dict[str, Any],
    style: str = "modern",
    vastu_compliant: bool = False,
    plot_facing: str = "north",
) -> Dict[str, Any]:
    rooms = layout_data.get("rooms") or []
    bed_count = sum(1 for r in rooms if "bedroom" in str(r.get("name", "")).lower())
    bhk = f"{max(1, bed_count)}BHK"

    plot_w_ft = int(round(_to_float(str(layout_data.get("plot_w_px", 300))) / 10.0))
    plot_d_ft = int(round(_to_float(str(layout_data.get("plot_h_px", 500))) / 10.0))

    return {
        "bhk_type": bhk,
        "floors": 1,
        "style": style,
        "vastu_compliant": vastu_compliant,
        "plot_facing": plot_facing,
        "plot_width_ft": max(20, plot_w_ft),
        "plot_depth_ft": max(20, plot_d_ft),
        "rooms": [
            {
                "name": r.get("name", "room"),
                "floor": 0,
                "width_ft": r.get("width_ft", round(_to_float(str(r.get("width", 0))) / 10.0, 2)),
                "depth_ft": r.get("depth_ft", round(_to_float(str(r.get("height", 0))) / 10.0, 2)),
                "area_sqft": r.get("area_sqft", 0),
                "windows": r.get("windows", 1),
                "door_count": r.get("door_count", 1),
                "attached_bathroom": False,
                "attached_balcony": False,
            }
            for r in rooms
        ],
        "budget": 0,
        "budget_per_sqft": 0,
        "parking": {"car_spaces": 1},
    }


async def generate_3d_from_svg(
    svg_content: str,
    output_dir: str = "outputs/svg_bridge",
    style: str = "modern",
    vastu_compliant: bool = False,
    plot_facing: str = "north",
    include_ai_renders: bool = False,
) -> Dict[str, Any]:
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    layout_data = parse_svg_to_layout(svg_content)
    parsed = _infer_parsed_from_layout(
        layout_data=layout_data,
        style=style,
        vastu_compliant=vastu_compliant,
        plot_facing=plot_facing,
    )

    floor_label = "GROUND FLOOR (SVG IMPORT)"
    html_path = out_dir / "svg_import_3d.html"
    html = render_3d_html(
        layout_data=layout_data,
        parsed=parsed,
        score=None,
        floor_label=floor_label,
        output_path=str(html_path),
    )

    (out_dir / "svg_import_layout.json").write_text(
        json.dumps(layout_data, indent=2), encoding="utf-8"
    )
    (out_dir / "svg_import_parsed.json").write_text(
        json.dumps(parsed, indent=2), encoding="utf-8"
    )

    ai_renders: Dict[str, Any] = {}
    if include_ai_renders:
        exterior = await generate_ai_floor_plan_image(
            parsed_json=parsed,
            layout_data=layout_data,
            output_dir=str(out_dir),
            render_type="exterior",
        )
        interior = await generate_ai_floor_plan_image(
            parsed_json=parsed,
            layout_data=layout_data,
            output_dir=str(out_dir),
            render_type="interior",
            room_type="living_room",
        )
        ai_renders = {"exterior": exterior, "interior": interior}

    return {
        "pipeline": "svg_to_layout_to_3d",
        "html": html,
        "html_path": str(html_path),
        "layout_data": layout_data,
        "parsed_data": parsed,
        "camera_views_supported": [
            "isometric",
            "top_down",
            "front",
            "rear",
            "side",
            "exterior",
            "exploded",
            "walkthrough",
        ],
        "ai_renders": ai_renders,
    }
