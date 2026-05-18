from __future__ import annotations

"""
floor_plan_generator.py  — orchestrator
========================================
No logic changes from original. Updated import paths to match refactored
layout_engine / svg_renderer, and improved PNG error reporting.
"""

import base64
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.services.layout_engine import generate_layout
from app.services.svg_renderer  import render_combined_svg, render_floor_svg


def _ensure_dir(path: str) -> str:
    Path(path).mkdir(parents=True, exist_ok=True)
    return path


def _write_text(path: str, text: str) -> None:
    Path(path).write_text(text, encoding="utf-8")


def _write_json(path: str, data: Any) -> None:
    Path(path).write_text(json.dumps(data, indent=2), encoding="utf-8")


def _svg_to_png(svg_text: str, *, dpi: int = 220) -> bytes:
    """
    Convert SVG → PNG bytes.  dpi=220 is presentation-grade; pass dpi=300 for print.
    Raises ImportError / other exception if CairoSVG / Cairo is unavailable.
    """
    import cairosvg  # type: ignore
    return cairosvg.svg2png(bytestring=svg_text.encode("utf-8"), dpi=dpi)


def generate_floor_plan(
    parsed_json: Dict[str, Any],
    output_dir:  str = "outputs/",
) -> Dict[str, Any]:
    """
    Entry point: accepts the validated JSON from llm_parser and produces
    SVG + PNG + JSON layout files.

    Returns a dict suitable for the FastAPI /generate_floor_plan response:
      svg_path, png_path, json_path,
      rooms_placed, rooms_failed, warnings,
      svg (full SVG string),
      png_base64 (empty string if Cairo unavailable),
      layout_data (per-floor layout dicts),
      [per_floor_svg]  — only present for multi-floor plans
    """
    out_dir = _ensure_dir(output_dir)
    floors  = int(parsed_json.get("floors", 1) or 1)

    warnings:     List[str] = []
    failed_total: List[str] = []

    # ── Single-storey ─────────────────────────────────────────────────────────
    if floors <= 1:
        layout = generate_layout(parsed_json, floor_index=0)
        warnings.extend(layout.get("warnings")    or [])
        failed_total.extend(layout.get("failed_rooms") or [])

        svg_text = render_floor_svg(parsed=parsed_json, layout=layout)
        svg_path  = str(Path(out_dir) / "floor_plan.svg")
        png_path  = str(Path(out_dir) / "floor_plan.png")
        json_path = str(Path(out_dir) / "floor_plan_data.json")

        _write_text(svg_path, svg_text)

        png_bytes: bytes = b""
        try:
            png_bytes = _svg_to_png(svg_text, dpi=220)
            Path(png_path).write_bytes(png_bytes)
        except Exception as exc:
            warnings.append(
                f"WARNING: PNG export skipped — CairoSVG/Cairo not available. ({exc})"
            )

        _write_json(json_path, {"floors": 1, "layouts": {"0": layout}})

        return {
            "svg_path":    svg_path,
            "png_path":    png_path if png_bytes else "",
            "json_path":   json_path,
            "rooms_placed":  len(layout.get("rooms") or []),
            "rooms_failed":  len(failed_total),
            "warnings":    warnings,
            "svg":         svg_text,
            "png_base64":  base64.b64encode(png_bytes).decode("ascii") if png_bytes else "",
            "layout_data": {"0": layout},
        }

    # ── Multi-storey ──────────────────────────────────────────────────────────
    per_floor: Dict[str, Dict[str, Any]] = {}
    floor_svgs: Dict[str, str] = {}

    for idx in range(min(floors, 4)):   # cap at 4 floors
        layout = generate_layout(parsed_json, floor_index=idx)
        per_floor[str(idx)] = layout
        warnings.extend(layout.get("warnings")    or [])
        failed_total.extend(layout.get("failed_rooms") or [])

        labels = {0: "GROUND FLOOR", 1: "FIRST FLOOR", 2: "SECOND FLOOR", 3: "THIRD FLOOR"}
        label  = labels.get(idx, f"FLOOR {idx}")
        names  = {0: "ground", 1: "first", 2: "second", 3: "third"}
        slug   = names.get(idx, str(idx))

        svg_text = render_floor_svg(parsed=parsed_json, layout=layout, floor_label=label)
        floor_svgs[str(idx)] = svg_text

        _write_text(str(Path(out_dir) / f"floor_plan_{slug}.svg"), svg_text)
        try:
            png_b = _svg_to_png(svg_text, dpi=220)
            Path(out_dir, f"floor_plan_{slug}.png").write_bytes(png_b)
        except Exception as exc:
            warnings.append(f"WARNING: PNG export skipped for floor {idx} — {exc}")

    # Combined side-by-side
    layout_pairs: List[Tuple[str, Dict[str, Any]]] = [
        (labels.get(i, f"FLOOR {i}"), per_floor[str(i)])
        for i in range(len(per_floor))
    ]
    combined_svg = render_combined_svg(parsed=parsed_json, layouts=layout_pairs)

    comb_svg_path  = str(Path(out_dir) / "floor_plan.svg")
    comb_png_path  = str(Path(out_dir) / "floor_plan.png")
    comb_json_path = str(Path(out_dir) / "floor_plan_data.json")

    _write_text(comb_svg_path, combined_svg)

    comb_png: bytes = b""
    try:
        comb_png = _svg_to_png(combined_svg, dpi=220)
        Path(comb_png_path).write_bytes(comb_png)
    except Exception as exc:
        warnings.append(f"WARNING: Combined PNG export skipped — {exc}")

    _write_json(comb_json_path, {"floors": floors, "layouts": per_floor})

    rooms_placed = sum(len(per_floor[k].get("rooms") or []) for k in per_floor)

    return {
        "svg_path":     comb_svg_path,
        "png_path":     comb_png_path if comb_png else "",
        "json_path":    comb_json_path,
        "rooms_placed": rooms_placed,
        "rooms_failed": len(failed_total),
        "warnings":     warnings,
        "svg":          combined_svg,
        "png_base64":   base64.b64encode(comb_png).decode("ascii") if comb_png else "",
        "layout_data":  per_floor,
        "per_floor_svg": floor_svgs,
    }