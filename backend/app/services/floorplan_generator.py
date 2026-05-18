"""
floorplan_generator.py  —  synchronous wrapper for the visual floor plan pipeline
==================================================================================

Why this file exists:
  main.py has two synchronous endpoints (/generate-floorplan, /generate_floor_plan)
  that call generate_floor_plan(parsed_json). But the real pipeline in
  visual_floor_plan.py is async (uses asyncio for the optional AI render step).

  This module provides a synchronous interface that:
    1. Runs the full visual_floor_plan pipeline synchronously via asyncio.run()
    2. Returns a simplified dict compatible with the existing endpoint contract:
       { svg, per_floor_svgs, layout_data }

  Both synchronous endpoints are legacy. The preferred endpoint is
  POST /generate_visual_floor_plan which is already async and returns the full
  per_floor_svgs, per_floor_layouts, warnings, etc.

  This wrapper keeps backwards compatibility without duplicating pipeline logic.
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict


def generate_floor_plan(parsed_json: Dict[str, Any]) -> Dict[str, Any]:
    """
    Synchronous entry point for the floor plan pipeline.

    Runs the full async pipeline (layout_engine → svg_renderer → optional AI render)
    and returns a simplified dict.

    Returns:
        {
            "svg":          str   — ground floor SVG (primary 2D output)
            "per_floor_svgs": dict — all floors { "0": svg, "1": svg, ... }

            "layout_data":  dict  — ground floor layout data for the frontend editor
            "per_floor_layouts": dict — all floors layout data
            "warnings":     list  — any placement warnings
            "rooms_placed": int
            "rooms_failed": list
        }
    """
    from app.services.visual_floor_plan import generate_visual_floor_plan

    # Run the async pipeline synchronously.
    # SVG-only — no AI image generation. Use POST /generate for the full pipeline.
    # Python 3.12+: asyncio.get_event_loop() is deprecated and raises
    # DeprecationWarning (3.10+) or RuntimeError (3.12+) when no running loop.
    # Use asyncio.run() exclusively — it creates a fresh loop, runs, closes it.
    # Thread safety: if already inside a running loop (e.g. FastAPI lifespan,
    # pytest-asyncio), run in a separate thread to avoid "loop already running".
    try:
        import concurrent.futures
        loop = asyncio.get_running_loop()
        # Running inside an async context — delegate to thread pool
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(
                asyncio.run,
                generate_visual_floor_plan(
                    parsed_json=parsed_json,
                    output_dir="outputs/",
                    include_ai_render=False,
                )
            )
            result = future.result(timeout=120)
    except RuntimeError:
        # No running event loop — safe to use asyncio.run() directly
        result = asyncio.run(
            generate_visual_floor_plan(
                parsed_json=parsed_json,
                output_dir="outputs/",
                include_ai_render=False,
            )
        )

    # Return simplified contract-compatible dict
    return {
        # Primary SVG outputs
        "svg":               result.get("ground_floor_svg", ""),
        "per_floor_svgs":    result.get("per_floor_svgs",   {}),

        # Layout data for frontend room editor
        "layout_data":       result.get("layout_data",        {}),
        "per_floor_layouts": result.get("per_floor_layouts",  {}),

        # Stats + debug
        "warnings":          result.get("warnings",           []),
        "rooms_placed":      result.get("rooms_placed",        0),
        "rooms_failed":      result.get("rooms_failed",        []),
        "floors_generated":  result.get("floors_generated",    1),
    }