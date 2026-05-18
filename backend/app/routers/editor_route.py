"""
editor_route.py  —  /editor  +  /api/editor-state
==================================================
Drop into:  app/routes/editor_route.py
Register:   app.include_router(editor_router) in main.py  (2 lines)
"""
from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from app.services.layout_engine import generate_layout
from app.services.pascal_editor_bridge import layout_to_editor_state

router = APIRouter(tags=["editor"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/editor", response_class=HTMLResponse)
async def editor_page(request: Request):
    """
    Serve the Pascal Editor.
    - If sessionStorage carries a state (set by the frontend after /generate),
      the editor JS picks it up automatically.
    - Can also be pre-seeded via query param ?parsed=<url-encoded JSON> for
      deep-linking from the generate response page.
    """
    return templates.TemplateResponse(
        "editor.html",
        {"request": request, "initial_state": None},
    )


@router.post("/api/editor-state")
async def editor_state(request: Request) -> JSONResponse:
    """
    Accept the same parsed JSON body as /generate_floor_plan.
    Returns: Pascal Editor state JSON (floors, rooms, furniture, walk position).

    Typical call sequence:
      POST /generate_floor_plan  →  get layout_data in response
      POST /api/editor-state     →  same body → get editor state
      GET  /editor               →  open editor (state pre-loaded via sessionStorage)

    Or combine: pass result["editor_state"] back from /generate_floor_plan directly
    (see PASCAL_INTEGRATION.md Step 5).
    """
    parsed = await request.json()
    num_floors = int(parsed.get("floors", 2) or 2)

    per_floor: dict = {}
    for fi in range(min(num_floors, 4)):
        per_floor[str(fi)] = generate_layout(parsed, floor_index=fi)

    state = layout_to_editor_state(per_floor, parsed)
    return JSONResponse(state)


@router.post("/api/editor-state-from-layout")
async def editor_state_from_layout(request: Request) -> JSONResponse:
    """
    Shortcut: accepts { "per_floor_layouts": {...}, "parsed": {...} }
    so the caller can pass already-computed layout_data (no re-computation).
    Use this if your /generate endpoint already ran generate_layout().
    """
    body = await request.json()
    per_floor = body.get("per_floor_layouts", body.get("layout_data", {}))
    parsed    = body.get("parsed", {})
    state = layout_to_editor_state(per_floor, parsed)
    return JSONResponse(state)