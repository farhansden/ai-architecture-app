"""
POST /api/layout/render-preview  —  Re-run SVG (and optionally 3D HTML) from edited layout JSON.
Used by the Phase A layout editor below the static floor plan in the web UI.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.visual_floor_plan import _fix_parsed_rooms
from app.services.region_room_proposal import propose_room_in_region

router = APIRouter(tags=["layout"])

_FLOOR_LABELS = {
    0: "GROUND FLOOR",
    1: "FIRST FLOOR",
    2: "SECOND FLOOR",
    3: "THIRD FLOOR",
}


def _sync_ft_fields(layout: Dict[str, Any]) -> None:
    scale = float(layout.get("scale", 10) or 10)
    if scale <= 0:
        scale = 10.0
    for r in layout.get("rooms") or []:
        if not isinstance(r, dict):
            continue
        try:
            x = float(r.get("x", 0))
            y = float(r.get("y", 0))
            w = float(r.get("width", 0))
            h = float(r.get("height", 0))
            r["x_ft"] = round(x / scale, 2)
            r["y_ft"] = round(y / scale, 2)
            r["width_ft"] = round(w / scale, 2)
            r["depth_ft"] = round(h / scale, 2)
            if "area_sqft" in r:
                r["area_sqft"] = round((w / scale) * (h / scale), 1)
        except (TypeError, ValueError):
            continue


class LayoutPreviewRequest(BaseModel):
    """Same `parsed` / `project_data` shape as returned from /generate plus one floor layout."""

    parsed: Dict[str, Any] = Field(default_factory=dict)
    floor_index: int = Field(0, ge=0, le=3)
    layout: Dict[str, Any] = Field(..., description="Single-floor layout dict (rooms, built_up_*, plot_*, …)")
    include_3d: bool = Field(
        False,
        description="If true, also returns self-contained Three.js HTML (slower, larger payload).",
    )


@router.post("/api/layout/render-preview")
def render_layout_preview(body: LayoutPreviewRequest) -> Dict[str, Any]:
    parsed = _fix_parsed_rooms(dict(body.parsed))
    layout: Dict[str, Any] = dict(body.layout)
    fi = int(body.floor_index)
    floor_label = _FLOOR_LABELS.get(fi, f"FLOOR {fi}")

    _sync_ft_fields(layout)

    try:
        from app.services.svg_renderer import render_floor_plan_svg
    except ImportError as e:
        raise HTTPException(status_code=500, detail=f"svg_renderer unavailable: {e}") from e

    try:
        svg = render_floor_plan_svg(
            layout_data=layout,
            parsed=parsed,
            floor_index=fi,
            floor_label=floor_label,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"SVG render failed: {e}") from e

    out: Dict[str, Any] = {"svg": svg, "floor_index": fi, "ok": True}

    if body.include_3d:
        try:
            from app.services.three_d_renderer import render_3d_html
        except ImportError:
            out["html_3d"] = ""
            out["html_3d_error"] = "three_d_renderer not available"
            return out

        score: Optional[Dict[str, Any]] = None
        try:
            from app.services.plan_scorer import score_plan

            score = score_plan(layout, parsed)
        except Exception:
            pass

        all_floors: Optional[List[Dict[str, Any]]] = None
        try:
            html_3d = render_3d_html(
                layout_data=layout,
                parsed=parsed,
                score=score,
                floor_label=floor_label,
                floor_index=fi,
                all_floors=all_floors,
            )
            out["html_3d"] = html_3d
        except Exception as e:
            out["html_3d"] = ""
            out["html_3d_error"] = str(e)

    return out


class RegionRect(BaseModel):
    x: float = Field(..., description="Layout-space X (px), same as room `x` in JSON")
    y: float = Field(..., description="Layout-space Y (px)")
    width: float = Field(..., gt=0)
    height: float = Field(..., gt=0)


class ProposeRoomInRegionRequest(BaseModel):
    """Draw a rectangle over empty floor in the editor, then describe the desired room."""

    parsed: Dict[str, Any] = Field(default_factory=dict)
    floor_index: int = Field(0, ge=0, le=3)
    layout: Dict[str, Any] = Field(..., description="Single-floor layout dict")
    region: RegionRect
    user_prompt: str = Field(..., min_length=1, max_length=1200)


@router.post("/api/layout/propose-room-in-region")
def propose_room_in_region_endpoint(body: ProposeRoomInRegionRequest) -> Dict[str, Any]:
    """
    Append one room to the layout from a natural-language prompt + void rectangle.
    Uses OpenAI when ``OPENAI_API_KEY`` is set; otherwise keyword heuristics.
    """
    parsed = _fix_parsed_rooms(dict(body.parsed))
    layout: Dict[str, Any] = dict(body.layout)
    fi = int(body.floor_index)

    try:
        result = propose_room_in_region(
            parsed=parsed,
            layout=layout,
            floor_index=fi,
            region=body.region.model_dump(),
            user_prompt=body.user_prompt.strip(),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"propose_room_in_region failed: {e}") from e

    out_layout: Dict[str, Any] = result["layout"]
    _sync_ft_fields(out_layout)

    return {
        "ok": True,
        "floor_index": fi,
        "layout": out_layout,
        "room": result["room"],
        "reasoning": result["reasoning"],
        "overlap_fraction": result["overlap_fraction"],
        "used_llm": result["used_llm"],
        "inferred_base_name": result.get("inferred_base_name", ""),
    }
