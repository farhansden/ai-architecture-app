"""pascal_router.py — FastAPI router for Pascal Editor scene export."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from typing import Any, Dict

from app.services.pascal_scene_converter import (
    layout_to_pascal_scene,
    single_layout_to_pascal,
    to_json,
)

router = APIRouter()


@router.post("/scene")
async def generate_pascal_scene(payload: Dict[str, Any]) -> Dict[str, Any]:
    layout = payload.get("layout")
    parsed = payload.get("parsed", {})
    floor_index = int(payload.get("floor_index", 0))
    if not layout:
        raise HTTPException(status_code=422, detail="Missing 'layout' in payload")
    return single_layout_to_pascal(layout, parsed, floor_index)


@router.post("/scene/multi")
async def generate_pascal_scene_multi(payload: Dict[str, Any]) -> Dict[str, Any]:
    per_floor_layouts = payload.get("per_floor_layouts")
    parsed = payload.get("parsed", {})
    project_name = payload.get("project_name", "Floor Plan")
    if not per_floor_layouts:
        raise HTTPException(status_code=422, detail="Missing 'per_floor_layouts' in payload")
    return layout_to_pascal_scene(per_floor_layouts, parsed, project_name)


@router.post("/scene/json")
async def generate_pascal_scene_json(payload: Dict[str, Any]) -> str:
    layout = payload.get("layout")
    parsed = payload.get("parsed", {})
    floor_index = int(payload.get("floor_index", 0))
    if not layout:
        raise HTTPException(status_code=422, detail="Missing 'layout' in payload")
    scene = single_layout_to_pascal(layout, parsed, floor_index)
    return to_json(scene)