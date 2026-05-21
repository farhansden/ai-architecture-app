# app/main.py

import os

from fastapi import FastAPI, HTTPException, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, FileResponse, HTMLResponse
from pydantic import BaseModel, Field

from app.services.llm_parser import parse_architecture_prompt
from app.services.floorplan_generator import generate_floor_plan
from app.services.visual_floor_plan import generate_visual_floor_plan
from app.services.svg_to_3d_bridge import generate_3d_from_svg
from app.routers.pascal_router import router as pascal_router
from app.routers.editor_route import router as editor_router
from app.routers.layout_route import router as layout_router

# ── App init MUST come before include_router ──────────────────────────────────
app = FastAPI(
    title="AI Architecture Design API",
    description="Backend for AI architecture design prototype",
    version="2.0.0",
)

# ── Router registration (after app = FastAPI()) ───────────────────────────────
app.include_router(pascal_router, prefix="/api/pascal", tags=["pascal"])
app.include_router(editor_router)
app.include_router(layout_router)

def _cors_origins() -> list[str]:
    origins = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:3002",
        "http://localhost:3003",
        "http://localhost:3004",
        "http://localhost:3005",
        "http://localhost:5173",
        "http://localhost:8080",
    ]
    extra = os.getenv("ALLOWED_ORIGINS", "")
    for origin in extra.split(","):
        o = origin.strip()
        if o and o not in origins:
            origins.append(o)
    return origins


app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request / Response models ─────────────────────────────────────────────────

class ParsePromptRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=2000)


class VisualFloorPlanRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=2000)
    output_dir: str = "outputs/"


class GenerateRequest(BaseModel):
    prompt:     str = Field(..., min_length=1, max_length=4000)
    output_dir: str = Field(default="outputs/")


class ThreeDRequest(BaseModel):
    prompt:     str = Field(..., min_length=1, max_length=4000)
    floor:      int = Field(default=0, ge=0, le=3)
    output_dir: str = Field(default="outputs/")


class SvgTo3DRequest(BaseModel):
    svg: str = Field(..., min_length=10)
    output_dir: str = Field(default="outputs/svg_bridge")
    style: str = Field(default="modern")
    vastu_compliant: bool = Field(default=False)
    plot_facing: str = Field(default="north")
    include_ai_renders: bool = Field(default=False)


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {"message": "AI Architecture Design API", "status": "ok", "version": "2.0.0"}


@app.get("/health")
def health():
    return {"status": "healthy"}


# ── Parse only ────────────────────────────────────────────────────────────────

@app.post("/parse")
def parse_endpoint(body: ParsePromptRequest):
    return parse_architecture_prompt(body.prompt)


@app.post("/parse_prompt")
def parse_prompt_compat(body: ParsePromptRequest):
    return parse_architecture_prompt(body.prompt)


# ── Canonical generate endpoint ───────────────────────────────────────────────

@app.post("/generate", response_model=None)
async def generate_endpoint(body: GenerateRequest):
    parsed = parse_architecture_prompt(body.prompt)
    if isinstance(parsed, dict) and parsed.get("error"):
        raise HTTPException(status_code=400, detail=parsed["error"])

    result = await generate_visual_floor_plan(
        parsed_json=parsed,
        output_dir=body.output_dir,
        include_ai_render=False,
    )

    per_floor_layouts = {}
    for floor_str, layout in result.get("per_floor_layouts", {}).items():
        rooms_with_ft = []
        for room in layout.get("rooms", []):
            scale = layout.get("scale", 10)
            rooms_with_ft.append({
                **room,
                "x_ft":     round(room.get("x", 0) / scale, 2),
                "y_ft":     round(room.get("y", 0) / scale, 2),
                "width_ft": round(room.get("width", 0) / scale, 2),
                "depth_ft": round(room.get("height", 0) / scale, 2),
            })
        per_floor_layouts[floor_str] = {**layout, "rooms": rooms_with_ft}

    return {
        "floors":            result.get("per_floor_svgs", {}),
        "layout_data":       per_floor_layouts,
        "floors_3d":         result.get("per_floor_3d", {}),
        "ground_floor_3d":   result.get("ground_floor_3d", ""),
        "scores":            result.get("per_floor_scores", {}),
        "ground_score":      result.get("ground_floor_score", {}),
        "design_reasoning":  parsed.get("_design_reasoning", ""),
        "validation":        parsed.get("_validation", ""),
        "maket_deliverable": parsed.get("maket_deliverable") or {},
        "project_data":      {k: v for k, v in parsed.items() if not k.startswith("_")},
        "floors_generated":  result.get("floors_generated", 1),
        "rooms_placed":      result.get("rooms_placed", 0),
        "rooms_failed":      result.get("rooms_failed", []),
        "warnings":          result.get("warnings", []),
        "dxf_paths":         result.get("dxf_paths", {}),
    }


# ── 3D viewer endpoints ────────────────────────────────────────────────────────

@app.post("/3d", response_class=HTMLResponse)
async def three_d_post(body: ThreeDRequest):
    """Generate and return a self-contained Three.js 3D floor plan HTML viewer."""
    parsed = parse_architecture_prompt(body.prompt)
    if isinstance(parsed, dict) and parsed.get("error"):
        raise HTTPException(status_code=400, detail=parsed["error"])

    result = await generate_visual_floor_plan(
        parsed_json=parsed,
        output_dir=body.output_dir,
    )

    floor_str = str(body.floor)
    three_d   = result.get("per_floor_3d", {}).get(floor_str, "")

    if not three_d:
        raise HTTPException(
            status_code=500,
            detail=(
                f"3D render not available for floor {body.floor}. "
                "Ensure three_d_renderer.py is in app/services/ and the floor exists."
            ),
        )
    return HTMLResponse(content=three_d)


@app.get("/3d/{floor}", response_class=HTMLResponse)
async def three_d_get(floor: int = 0, prompt: str = ""):
    """GET version of the 3D viewer — pass prompt as query param."""
    if not prompt:
        raise HTTPException(status_code=400, detail="prompt query parameter required")

    parsed = parse_architecture_prompt(prompt)
    if isinstance(parsed, dict) and parsed.get("error"):
        raise HTTPException(status_code=400, detail=parsed["error"])

    result = await generate_visual_floor_plan(parsed_json=parsed)
    three_d = result.get("per_floor_3d", {}).get(str(floor), "")

    if not three_d:
        raise HTTPException(status_code=500, detail=f"3D render not available for floor {floor}.")
    return HTMLResponse(content=three_d)


@app.get("/3d/file/{floor}")
async def three_d_file(floor: int = 0, output_dir: str = "outputs/"):
    """Download the pre-generated 3D HTML file for a specific floor."""
    import os
    _SLUGS = {0: "ground", 1: "first", 2: "second", 3: "third"}
    slug      = _SLUGS.get(floor, str(floor))
    html_path = os.path.join(output_dir, f"floor_{slug}", f"3d_{slug}.html")

    if not os.path.exists(html_path):
        raise HTTPException(
            status_code=404,
            detail=f"3D file not found at {html_path}. Run POST /generate first.",
        )
    return FileResponse(
        path=html_path,
        media_type="text/html",
        filename=f"3d_floor_plan_{slug}.html",
    )


@app.post("/3d/from-svg", response_model=None)
async def three_d_from_svg(body: SvgTo3DRequest):
    """
    Additional pipeline: SVG string -> parsed layout -> interactive 3D HTML.
    Does not affect existing /generate flow.
    """
    try:
        result = await generate_3d_from_svg(
            svg_content=body.svg,
            output_dir=body.output_dir,
            style=body.style,
            vastu_compliant=body.vastu_compliant,
            plot_facing=body.plot_facing,
            include_ai_renders=body.include_ai_renders,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"SVG to 3D failed: {exc}")
    return result


@app.post("/3d/from-svg/upload", response_model=None)
async def three_d_from_svg_upload(
    file: UploadFile = File(...),
    output_dir: str = Form("outputs/svg_bridge"),
    style: str = Form("modern"),
    vastu_compliant: bool = Form(False),
    plot_facing: str = Form("north"),
    include_ai_renders: bool = Form(False),
):
    """
    Upload an SVG file and generate interactive 3D HTML + optional AI renders.
    This is additive and does not alter existing endpoints.
    """
    if not file.filename.lower().endswith(".svg"):
        raise HTTPException(status_code=400, detail="Only .svg upload is supported")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty SVG file")

    try:
        svg_text = content.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="SVG file must be UTF-8 text")

    try:
        result = await generate_3d_from_svg(
            svg_content=svg_text,
            output_dir=output_dir,
            style=style,
            vastu_compliant=vastu_compliant,
            plot_facing=plot_facing,
            include_ai_renders=include_ai_renders,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"SVG upload to 3D failed: {exc}")
    return result


@app.get("/3d-view/{job_id}", response_class=HTMLResponse)
async def three_d_view_by_job(job_id: str):
    """Render 3D HTML for a stored job by job_id."""
    # Replace load_layout / load_parsed / load_score with your actual storage logic
    try:
        layout = load_layout(job_id)
        parsed = load_parsed(job_id)
        score  = load_score(job_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found: {e}")

    from app.services.three_d_renderer import render_3d_html
    html = render_3d_html(layout, parsed, score, "GROUND FLOOR")
    return HTMLResponse(html)


# ── Legacy endpoints ──────────────────────────────────────────────────────────

@app.post("/generate-floorplan")
def generate_floorplan_endpoint(body: ParsePromptRequest):
    parsed = parse_architecture_prompt(body.prompt)
    if isinstance(parsed, dict) and parsed.get("error"):
        raise HTTPException(status_code=400, detail=parsed["error"])
    fp = generate_floor_plan(parsed)
    return {
        "parsed_data":    parsed,
        "floor_plan_svg": fp.get("svg", ""),
        "layout_data":    fp.get("layout_data", {}),
    }


@app.post("/generate_floor_plan")
def generate_floor_plan_endpoint(body: ParsePromptRequest):
    parsed = parse_architecture_prompt(body.prompt)
    if isinstance(parsed, dict) and parsed.get("error"):
        raise HTTPException(status_code=400, detail=parsed["error"])
    fp = generate_floor_plan(parsed)
    return {
        "parsed_data":    parsed,
        "floor_plan_svg": fp.get("svg", ""),
        "layout_data":    fp.get("layout_data", {}),
    }


@app.post("/generate_visual_floor_plan")
async def generate_visual_floor_plan_endpoint(body: VisualFloorPlanRequest):
    parsed = parse_architecture_prompt(body.prompt)
    if isinstance(parsed, dict) and parsed.get("error"):
        raise HTTPException(status_code=400, detail=parsed["error"])

    result = await generate_visual_floor_plan(
        parsed_json=parsed,
        output_dir=body.output_dir,
    )
    return {
        "parsed_data":        parsed,
        "design_reasoning":   parsed.get("_design_reasoning", ""),
        "validation":         parsed.get("_validation", ""),
        "maket_deliverable":  parsed.get("maket_deliverable") or {},
        "project_data":       {k: v for k, v in parsed.items() if not k.startswith("_")},
        "per_floor_svgs":     result.get("per_floor_svgs",    {}),
        "ground_floor_svg":   result.get("ground_floor_svg",  ""),
        "svg_renderer_used":  result.get("svg_renderer_used", False),
        "per_floor_3d":       result.get("per_floor_3d",      {}),
        "ground_floor_3d":    result.get("ground_floor_3d",   ""),
        "renderer_3d_used":   result.get("renderer_3d_used",  False),
        "per_floor_scores":   result.get("per_floor_scores",  {}),
        "ground_floor_score": result.get("ground_floor_score",{}),
        "scorer_used":        result.get("scorer_used",       False),
        "per_floor_layouts":  result.get("per_floor_layouts", {}),
        "dxf_paths":          result.get("dxf_paths",         {}),
        "floors_generated":   result.get("floors_generated",  1),
        "rooms_placed":       result.get("rooms_placed",      0),
        "rooms_failed":       result.get("rooms_failed",      []),
        "warnings":           result.get("warnings",          []),
    }


# ── Download endpoints ────────────────────────────────────────────────────────

@app.get("/download_dxf")
async def download_dxf(floor: int = 0, output_dir: str = "outputs/"):
    import os
    _SLUGS = {0: "ground", 1: "first", 2: "second", 3: "third"}
    slug     = _SLUGS.get(floor, str(floor))
    dxf_path = os.path.join(output_dir, f"floor_{slug}", f"floor_plan_{slug}.dxf")
    if not os.path.exists(dxf_path):
        raise HTTPException(status_code=404, detail=f"DXF not found at {dxf_path}. Run /generate first.")
    return FileResponse(
        path=dxf_path,
        media_type="application/dxf",
        filename=f"floor_plan_{slug}.dxf",
        headers={"Content-Disposition": f'attachment; filename="floor_plan_{slug}.dxf"'},
    )


@app.get("/download_svg")
async def download_svg(floor: int = 0, output_dir: str = "outputs/"):
    import os
    _SLUGS = {0: "ground", 1: "first", 2: "second", 3: "third"}
    slug     = _SLUGS.get(floor, str(floor))
    svg_path = os.path.join(output_dir, f"floor_{slug}", f"floor_plan_{slug}.svg")
    if not os.path.exists(svg_path):
        raise HTTPException(status_code=404, detail=f"SVG not found at {svg_path}. Run /generate first.")
    return FileResponse(path=svg_path, media_type="image/svg+xml", filename=f"floor_plan_{slug}.svg")


# ── Test endpoint ─────────────────────────────────────────────────────────────

@app.get("/test_plan")
async def test_plan():
    try:
        from app.services.architectural_plan import render_architectural_plan
        svg = render_architectural_plan({
            "bhk_type": "3BHK", "floors": 1, "style": "Modern",
            "plot_width_ft": 30, "plot_depth_ft": 50,
            "car_spaces": 2, "vastu_compliant": True, "budget": 5500000,
            "corridor_width_ft": 4.0, "main_door_width_ft": 4.0,
            "setbacks": {"front": 5, "rear": 3, "left": 2, "right": 2},
            "special_requirements": "big kitchen",
        })
        return Response(content=svg, media_type="image/svg+xml")
    except ImportError:
        raise HTTPException(status_code=501, detail="architectural_plan.py not found. Use /generate instead.")