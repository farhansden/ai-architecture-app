from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple

import svgwrite
from shapely.geometry import LineString, Polygon, box

# ──────────────────────────────────────────────────────────────
# Constants (per spec)
# ──────────────────────────────────────────────────────────────

SCALE: float = 10.0  # px/ft (layout_engine contract)
MARGIN: float = 80.0
TITLE_H: float = 60.0

EXT_WALL_T: float = 7.5  # 0.75ft * 10px/ft
INT_WALL_T: float = 4.0  # 3.75px rounded to 4px

BG_PAPER: str = "#F5F0E8"
SETBACK_TINT: str = "#EDE8DC"


ROOM_BASE_COLORS: Dict[str, str] = {
    "living_room": "#FDF6E3",
    "dining_room": "#FDF6E3",
    "master_bedroom": "#E8EEF8",
    "parents_bedroom": "#E8EEF8",
    "bedroom": "#E8EEF8",
    "kitchen": "#E8F5EC",
    "bathroom": "#E0F2F8",
    "pooja_room": "#FDF0DC",
    "corridor": "#F5F5EE",
    "car_porch": "#EEEBD8",
    "sit_out": "#E8F2E8",
    "utility_room": "#F0F0EC",
    "store_room": "#EDEDED",
    "default": "#FAFAFA",
}

ABBREV: Dict[str, str] = {
    "bathroom": "BATH",
    "pooja_room": "POOJA",
    "store_room": "STORE",
    "utility_room": "UTIL",
}


@dataclass(frozen=True)
class Rect:
    x: float
    y: float
    w: float
    h: float

    @property
    def right(self) -> float:
        return self.x + self.w

    @property
    def bottom(self) -> float:
        return self.y + self.h

    @property
    def cx(self) -> float:
        return self.x + self.w / 2.0

    @property
    def cy(self) -> float:
        return self.y + self.h / 2.0

    def poly(self) -> Polygon:
        return box(self.x, self.y, self.right, self.bottom)

    def inset(self, pad: float) -> "Rect":
        return Rect(self.x + pad, self.y + pad, max(self.w - 2 * pad, 0.0), max(self.h - 2 * pad, 0.0))


def _room_rect(r: Dict[str, Any]) -> Rect:
    return Rect(float(r["x"]), float(r["y"]), float(r["width"]), float(r["height"]))


def _cat_from_name(name: str) -> str:
    n = (name or "").lower()
    if "living_room" in n:
        return "living_room"
    if "dining_room" in n:
        return "dining_room"
    if "master_bedroom" in n:
        return "master_bedroom"
    if "parents_bedroom" in n:
        return "parents_bedroom"
    if "bedroom" in n or "guest" in n:
        return "bedroom"
    if "kitchen" in n:
        return "kitchen"
    if "bath" in n or "toilet" in n:
        return "bathroom"
    if "pooja" in n:
        return "pooja_room"
    if "corridor" in n:
        return "corridor"
    if "car_porch" in n or "car porch" in n:
        return "car_porch"
    if "sit_out" in n or "sit out" in n or "verandah" in n or "veranda" in n:
        return "sit_out"
    if "utility" in n:
        return "utility_room"
    if "store" in n:
        return "store_room"
    return "default"


def _room_category(r: Dict[str, Any]) -> str:
    return str(r.get("category") or _cat_from_name(str(r.get("name", ""))) or "default")


def _base_color_for_room(r: Dict[str, Any]) -> str:
    cat = _room_category(r)
    if cat in ROOM_BASE_COLORS:
        return ROOM_BASE_COLORS[cat]
    return ROOM_BASE_COLORS["default"]


def _fmt_name(name: str) -> str:
    return (name or "").replace("_", " ").upper().strip() or "ROOM"


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _feet_inches_str(ft: float) -> str:
    inches_total = float(ft) * 12.0
    feet = int(inches_total // 12)
    inches = int(round(inches_total - feet * 12))
    if inches == 12:
        feet += 1
        inches = 0
    return f"{feet}'-{inches}\""


def _shared_boundary(a: Rect, b: Rect, tol: float = 1.0) -> Optional[LineString]:
    inter = a.poly().boundary.intersection(b.poly().boundary)
    if inter.is_empty:
        return None
    lines: List[LineString] = []
    if isinstance(inter, LineString):
        lines = [inter]
    else:
        try:
            for g in inter.geoms:  # type: ignore[attr-defined]
                if isinstance(g, LineString):
                    lines.append(g)
        except Exception:
            lines = []
    if not lines:
        return None
    lines = [ln for ln in lines if ln.length >= tol]
    if not lines:
        return None
    return max(lines, key=lambda ln: ln.length)


def _is_vertical(ln: LineString, eps: float = 0.5) -> bool:
    (x1, y1), (x2, y2) = ln.coords[0], ln.coords[-1]
    return abs(x1 - x2) <= eps and abs(y1 - y2) > eps


def _is_horizontal(ln: LineString, eps: float = 0.5) -> bool:
    (x1, y1), (x2, y2) = ln.coords[0], ln.coords[-1]
    return abs(y1 - y2) <= eps and abs(x1 - x2) > eps


def _add_defs(dwg: svgwrite.Drawing) -> None:
    # Filters: build via svgwrite primitives for maximum compatibility
    # across svgwrite versions (avoid Raw injection).
    #
    # plotGlow: subtle outer glow/shadow around plot boundary.
    plot_f = dwg.defs.add(dwg.filter(id="plotGlow", x="-15%", y="-15%", width="130%", height="130%"))
    plot_f.feGaussianBlur(in_="SourceAlpha", stdDeviation=2, result="blur")
    plot_f.feOffset(in_="blur", dx=0, dy=0, result="offsetBlur")
    # Merge shadow behind the source.
    plot_f.feMerge(layernames=["offsetBlur", "SourceGraphic"])

    # extWallShadow: depth under external wall group.
    wall_f = dwg.defs.add(dwg.filter(id="extWallShadow", x="-20%", y="-20%", width="140%", height="140%"))
    wall_f.feGaussianBlur(in_="SourceAlpha", stdDeviation=3, result="blur")
    wall_f.feOffset(in_="blur", dx=2, dy=3, result="offsetBlur")
    wall_f.feMerge(layernames=["offsetBlur", "SourceGraphic"])

    # Per-room hatch patterns: base fill + diagonal lines at 4px spacing, 0.3 opacity.
    for cat, base in ROOM_BASE_COLORS.items():
        pid = f"pat_{cat}"
        pat = dwg.pattern(
            id=pid,
            size=(4, 4),
            patternUnits="userSpaceOnUse",
            patternTransform="rotate(45)",
        )
        pat.add(dwg.rect(insert=(0, 0), size=(4, 4), fill=base, stroke="none"))
        pat.add(dwg.line(start=(0, 0), end=(0, 4), stroke="#000000", stroke_width=0.6, opacity=0.30))
        dwg.defs.add(pat)


def _draw_canvas_background(dwg: svgwrite.Drawing, canvas_w: float, canvas_h: float) -> svgwrite.container.Group:
    g = dwg.g(id="bg")
    g.add(dwg.rect(insert=(0, 0), size=(canvas_w, canvas_h), fill=BG_PAPER, stroke="none"))
    return g


def _draw_plot_outline(dwg: svgwrite.Drawing, plot_w: float, plot_h: float) -> svgwrite.container.Group:
    g = dwg.g(id="plot")
    g.add(
        dwg.rect(
            insert=(MARGIN, MARGIN),
            size=(plot_w, plot_h),
            fill="none",
            stroke="#AAAAAA",
            stroke_width=0.5,
            filter="url(#plotGlow)",
        )
    )
    return g


def _draw_setbacks_and_builtup(
    dwg: svgwrite.Drawing,
    *,
    plot_w: float,
    plot_h: float,
    built: Rect,
    parsed: Dict[str, Any],
) -> Tuple[svgwrite.container.Group, svgwrite.container.Group]:
    g_setbacks = dwg.g(id="setbacks")
    g_built = dwg.g(id="built_up_boundary")

    sb = parsed.get("setbacks") or {}
    front_px = float(sb.get("front", 0.0) or 0.0) * SCALE
    rear_px = float(sb.get("rear", 0.0) or 0.0) * SCALE
    left_px = float(sb.get("left", 0.0) or 0.0) * SCALE
    right_px = float(sb.get("right", 0.0) or 0.0) * SCALE

    # 4 setback strips in plot coords (origin at plot top-left).
    if front_px > 0:
        g_setbacks.add(dwg.rect(insert=(MARGIN, MARGIN), size=(plot_w, front_px), fill=SETBACK_TINT, stroke="none"))
    if rear_px > 0:
        g_setbacks.add(
            dwg.rect(
                insert=(MARGIN, MARGIN + plot_h - rear_px),
                size=(plot_w, rear_px),
                fill=SETBACK_TINT,
                stroke="none",
            )
        )
    if left_px > 0:
        g_setbacks.add(
            dwg.rect(
                insert=(MARGIN, MARGIN + front_px),
                size=(left_px, max(plot_h - front_px - rear_px, 0.0)),
                fill=SETBACK_TINT,
                stroke="none",
            )
        )
    if right_px > 0:
        g_setbacks.add(
            dwg.rect(
                insert=(MARGIN + plot_w - right_px, MARGIN + front_px),
                size=(right_px, max(plot_h - front_px - rear_px, 0.0)),
                fill=SETBACK_TINT,
                stroke="none",
            )
        )

    # Built-up boundary (dashed)
    g_built.add(
        dwg.rect(
            insert=(MARGIN + built.x, MARGIN + built.y),
            size=(built.w, built.h),
            fill="none",
            stroke="#888888",
            stroke_width=1.0,
            stroke_dasharray="6,3",
        )
    )
    return g_setbacks, g_built


def _draw_room_fills(dwg: svgwrite.Drawing, rooms: List[Dict[str, Any]]) -> svgwrite.container.Group:
    g = dwg.g(id="room_fills")
    for r in rooms:
        rr = _room_rect(r)
        cat = _room_category(r)
        pid = f"pat_{cat if cat in ROOM_BASE_COLORS else 'default'}"
        g.add(
            dwg.rect(
                insert=(MARGIN + rr.x, MARGIN + rr.y),
                size=(rr.w, rr.h),
                fill=f"url(#{pid})",
                stroke="#2A2A2A",
                stroke_width=1.5,
            )
        )
    return g


def _iter_room_pairs(rooms: List[Dict[str, Any]]) -> Iterable[Tuple[Dict[str, Any], Rect, Dict[str, Any], Rect]]:
    rects = [(r, _room_rect(r)) for r in rooms]
    for i in range(len(rects)):
        for j in range(i + 1, len(rects)):
            yield rects[i][0], rects[i][1], rects[j][0], rects[j][1]


def _draw_internal_walls(dwg: svgwrite.Drawing, rooms: List[Dict[str, Any]]) -> svgwrite.container.Group:
    g = dwg.g(id="int_walls")
    for _, ra, __, rb in _iter_room_pairs(rooms):
        ln = _shared_boundary(ra, rb, tol=8.0)
        if ln is None:
            continue
        (x1, y1), (x2, y2) = ln.coords[0], ln.coords[-1]
        if _is_vertical(ln):
            x = x1 - INT_WALL_T / 2.0
            y = min(y1, y2)
            h = abs(y2 - y1)
            g.add(dwg.rect(insert=(MARGIN + x, MARGIN + y), size=(INT_WALL_T, h), fill="#3C3C3C", stroke="none"))
        elif _is_horizontal(ln):
            x = min(x1, x2)
            y = y1 - INT_WALL_T / 2.0
            w = abs(x2 - x1)
            g.add(dwg.rect(insert=(MARGIN + x, MARGIN + y), size=(w, INT_WALL_T), fill="#3C3C3C", stroke="none"))
    return g


def _draw_external_walls(dwg: svgwrite.Drawing, built: Rect) -> svgwrite.container.Group:
    g = dwg.g(id="ext_walls", filter="url(#extWallShadow)")
    x0 = MARGIN + built.x
    y0 = MARGIN + built.y
    x1 = MARGIN + built.right
    y1 = MARGIN + built.bottom

    # 4 wall strips
    g.add(dwg.rect(insert=(x0 - EXT_WALL_T, y0 - EXT_WALL_T), size=(built.w + 2 * EXT_WALL_T, EXT_WALL_T), fill="#1E1E1E", stroke="none"))  # top
    g.add(dwg.rect(insert=(x0 - EXT_WALL_T, y1), size=(built.w + 2 * EXT_WALL_T, EXT_WALL_T), fill="#1E1E1E", stroke="none"))  # bottom
    g.add(dwg.rect(insert=(x0 - EXT_WALL_T, y0), size=(EXT_WALL_T, built.h), fill="#1E1E1E", stroke="none"))  # left
    g.add(dwg.rect(insert=(x1, y0), size=(EXT_WALL_T, built.h), fill="#1E1E1E", stroke="none"))  # right
    return g


def _room_area_sqft(room: Dict[str, Any]) -> float:
    try:
        return float(room.get("area_sqft", 0.0) or 0.0)
    except Exception:
        return 0.0


def _add_to_group(g: svgwrite.container.Group, el: svgwrite.base.BaseElement) -> None:
    g.add(el)


def _rotated_group(dwg: svgwrite.Drawing, cx: float, cy: float, angle_deg: float) -> svgwrite.container.Group:
    """
    Create a rotated SVG group.
    cx, cy must be FINAL SVG coordinates (already including any MARGIN offset).
    Do NOT add MARGIN here — the caller is responsible for passing the correct coords.
    Previous bug: this function added MARGIN internally, double-applying it when
    callers also added MARGIN before passing cx/cy.
    """
    grp = dwg.g()
    grp.rotate(angle_deg, center=(cx, cy))
    return grp


def _furniture_common_style() -> Dict[str, Any]:
    return {"stroke": "#999999", "stroke_width": 0.75}


def _draw_furniture(dwg: svgwrite.Drawing, rooms: List[Dict[str, Any]]) -> svgwrite.container.Group:
    g = dwg.g(id="furniture")
    style = _furniture_common_style()
    for room in rooms:
        rr = _room_rect(room)
        if _room_area_sqft(room) < 60.0:
            continue
        pad = 10.0
        inner = rr.inset(pad)
        if inner.w < 30 or inner.h < 30:
            continue

        name = str(room.get("name", "")).lower()
        cat = _room_category(room)
        rotate = 90.0 if rr.h > rr.w else 0.0
        grp = _rotated_group(dwg, rr.cx, rr.cy, rotate) if rotate != 0.0 else dwg.g()

        def rrect(x: float, y: float, w: float, h: float, **kw: Any) -> None:
            _add_to_group(
                grp,
                dwg.rect(
                    insert=(MARGIN + x, MARGIN + y),
                    size=(w, h),
                    **kw,
                ),
            )

        def circ(x: float, y: float, r: float, **kw: Any) -> None:
            _add_to_group(grp, dwg.circle(center=(MARGIN + x, MARGIN + y), r=r, **kw))

        # Bedrooms (master/parents)
        if cat in ("master_bedroom", "parents_bedroom") and _room_area_sqft(room) >= 130.0:
            # Bed centered
            bed_w, head_h, matt_h = 55.0, 8.0, 72.0
            bed_x = inner.cx - bed_w / 2.0
            bed_y = inner.y + 6.0
            # Fit check
            if bed_y + head_h + matt_h <= inner.bottom - 6.0:
                rrect(bed_x, bed_y, bed_w, head_h, fill="#C5D5E8", stroke="#8AAAC8", stroke_width=0.9)
                rrect(bed_x, bed_y + head_h, bed_w, matt_h, fill="#C5D5E8", stroke="#8AAAC8", stroke_width=0.9)
                circ(bed_x + 15.0, bed_y + head_h + 12.0, 7.0, fill="#FFFFFF", stroke="none")
                circ(bed_x + bed_w - 15.0, bed_y + head_h + 12.0, 7.0, fill="#FFFFFF", stroke="none")
                # Side tables
                st = 14.0
                rrect(bed_x - st - 4.0, bed_y + 2.0, st, st, fill="#D4C4A8", **style)
                rrect(bed_x + bed_w + 4.0, bed_y + 2.0, st, st, fill="#D4C4A8", **style)

            # Wardrobe along side wall (right preferred)
            ww, wh = 65.0, 18.0
            wx = inner.right - ww
            wy = inner.bottom - wh - 6.0
            if wx >= inner.x and wy >= inner.y:
                rrect(wx, wy, ww, wh, fill="#C8B89A", **style)
                # 2 dividers (3 panels)
                for k in (1, 2):
                    xk = wx + ww * k / 3.0
                    _add_to_group(
                        grp,
                        dwg.line(
                            start=(MARGIN + xk, MARGIN + wy),
                            end=(MARGIN + xk, MARGIN + wy + wh),
                            stroke="#999999",
                            stroke_width=0.75,
                        ),
                    )

            g.add(grp)
            continue

        # Other bedrooms / guest
        if cat == "bedroom" and _room_area_sqft(room) >= 100.0:
            bed_w, bed_h = 42.0, 65.0
            bx = inner.cx - bed_w / 2.0
            by = inner.cy - bed_h / 2.0
            if bx >= inner.x and by >= inner.y and bx + bed_w <= inner.right and by + bed_h <= inner.bottom:
                rrect(bx, by, bed_w, bed_h, fill="#C5D5E8", **style)
            ww, wh = 52.0, 16.0
            wx, wy = inner.right - ww, inner.y + 6.0
            if wx >= inner.x and wy + wh <= inner.bottom:
                rrect(wx, wy, ww, wh, fill="#C8B89A", **style)
            g.add(grp)
            continue

        # Living room
        if cat == "living_room":
            sx, sy = inner.x + 6.0, inner.y + inner.h - 32.0 - 6.0
            if sy >= inner.y:
                rrect(sx, sy, 85.0, 32.0, fill="#C8BAB0", stroke="#A8988E", stroke_width=0.9)
                # seat cushions
                for k in (1, 2, 3):
                    xk = sx + 85.0 * k / 3.0
                    _add_to_group(
                        grp,
                        dwg.line(
                            start=(MARGIN + xk, MARGIN + sy),
                            end=(MARGIN + xk, MARGIN + sy + 32.0),
                            stroke="#A8988E",
                            stroke_width=0.6,
                        ),
                    )
                # extension
                ex, ey = sx + 85.0 - 16.0, sy - 56.0
                if ey >= inner.y:
                    rrect(ex, ey, 56.0, 32.0, fill="#C8BAB0", stroke="#A8988E", stroke_width=0.9)
                # coffee table
                cx, cy = inner.cx - 22.0, inner.cy - 14.0
                rrect(cx, cy, 44.0, 28.0, fill="#B8A888", rx=4, ry=4, **style)
                # TV unit
                tvx, tvy = inner.cx - 36.0, inner.y + 6.0
                rrect(tvx, tvy, 72.0, 14.0, fill="#A8988A", **style)
                rrect(tvx + 28.0, tvy - 10.0, 16.0, 10.0, fill="#666666", stroke="none")
            g.add(grp)
            continue

        # Dining room
        if cat == "dining_room":
            tx, ty = inner.cx - 26.0, inner.cy - 18.0
            rrect(tx, ty, 52.0, 36.0, fill="#C4B08A", rx=6, ry=6, **style)
            chair_w, chair_h = 14.0, 12.0
            # 6 chairs around: two each long side, one each short
            chairs = [
                (tx - chair_w - 4.0, ty + 4.0),
                (tx - chair_w - 4.0, ty + 20.0),
                (tx + 52.0 + 4.0, ty + 4.0),
                (tx + 52.0 + 4.0, ty + 20.0),
                (tx + 18.0, ty - chair_h - 4.0),
                (tx + 18.0, ty + 36.0 + 4.0),
            ]
            for cx0, cy0 in chairs:
                rrect(cx0, cy0, chair_w, chair_h, fill="#B09870", rx=2, ry=2, **style)
            g.add(grp)
            continue

        # Kitchen
        if cat == "kitchen":
            # top counter full width x 18
            rrect(inner.x, inner.y, inner.w, 18.0, fill="#D8D0C4", stroke="#B8B0A4", stroke_width=0.8)
            # side counter right wall: 18 x 50% height
            rrect(inner.right - 18.0, inner.y, 18.0, inner.h * 0.5, fill="#D8D0C4", stroke="#B8B0A4", stroke_width=0.8)
            # sink (left side)
            sx, sy = inner.x + 8.0, inner.y + 2.0
            rrect(sx, sy, 20.0, 14.0, fill="#D8D0C4", stroke="#B8B0A4", stroke_width=0.6)
            rrect(sx + 2.0, sy + 2.0, 16.0, 10.0, fill="#E0E6EA", stroke="#AAB4BC", stroke_width=0.6)
            # stove (right side)
            stx, sty = inner.right - 8.0 - 28.0, inner.y + 2.0
            rrect(stx, sty, 28.0, 24.0, fill="#CCCCCC", stroke="#999999", stroke_width=0.8)
            for dx in (8.0, 20.0):
                for dy in (8.0, 18.0):
                    circ(stx + dx, sty + dy, 4.0, fill="#EEEEEE", stroke="#888888", stroke_width=0.6)
            g.add(grp)
            continue

        # Bathroom
        if cat == "bathroom" and _room_area_sqft(room) >= 35.0:
            wcx, wcy = inner.x + 6.0, inner.y + 6.0
            rrect(wcx, wcy, 18.0, 24.0, fill="#D8EAEF", rx=6, ry=6, **style)
            circ(wcx + 9.0, wcy - 4.0, 5.0, fill="#D8EAEF", stroke="#999999", stroke_width=0.6)
            shx, shy = wcx + 24.0, wcy
            rrect(shx, shy, 24.0, 38.0, fill="#C8E0E8", **style)
            _add_to_group(
                grp,
                dwg.line(
                    start=(MARGIN + shx, MARGIN + shy),
                    end=(MARGIN + shx + 24.0, MARGIN + shy + 38.0),
                    stroke="#9BB0BC",
                    stroke_width=0.8,
                ),
            )
            _add_to_group(
                grp,
                dwg.line(
                    start=(MARGIN + shx + 24.0, MARGIN + shy),
                    end=(MARGIN + shx, MARGIN + shy + 38.0),
                    stroke="#9BB0BC",
                    stroke_width=0.8,
                ),
            )
            vx, vy = inner.right - 24.0 - 6.0, inner.bottom - 14.0 - 6.0
            rrect(vx, vy, 24.0, 14.0, fill="#D8D0C8", **style)
            g.add(grp)
            continue

        # Pooja
        if cat == "pooja_room":
            ax, ay = inner.x + 10.0, inner.y + 6.0
            aw = max(inner.w - 20.0, 0.0)
            if aw >= 20.0:
                rrect(ax, ay, aw, 18.0, fill="#ECD090", stroke="#C8A840", stroke_width=0.9)
                circ(inner.cx, ay - 6.0, 5.0, fill="#F5C030", stroke="none")
                rrect(ax, ay + 20.0, aw, 3.0, fill="#E8D9A8", stroke="none")
                rrect(ax, ay + 24.0, aw, 3.0, fill="#E8D9A8", stroke="none")
            g.add(grp)
            continue

        # Car porch
        if cat == "car_porch":
            body_w, body_h = 56.0, 100.0
            bx, by = inner.cx - body_w / 2.0, inner.cy - body_h / 2.0
            if bx >= inner.x and by >= inner.y and bx + body_w <= inner.right and by + body_h <= inner.bottom:
                rrect(bx, by, body_w, body_h, fill="#CCCCBB", rx=8, ry=8, **style)
                rrect(bx + 5.0, by + 10.0, 46.0, 14.0, fill="#AACCDD", rx=2, ry=2, stroke="none")
                rrect(bx + 5.0, by + body_h - 24.0, 46.0, 14.0, fill="#AACCDD", rx=2, ry=2, stroke="none")
                # wheels
                wheels = [
                    (bx - 8.0, by + 14.0),
                    (bx + body_w, by + 14.0),
                    (bx - 8.0, by + body_h - 30.0),
                    (bx + body_w, by + body_h - 30.0),
                ]
                for wx, wy in wheels:
                    rrect(wx, wy, 8.0, 16.0, fill="#555555", rx=2, ry=2, stroke="none")
            g.add(grp)
            continue

        # Sit out
        if cat == "sit_out":
            circ(inner.x + 18.0, inner.cy, 12.0, fill="#C8B898", **style)
            circ(inner.right - 18.0, inner.cy, 12.0, fill="#C8B898", **style)
            circ(inner.cx, inner.cy, 8.0, fill="#B8A880", **style)
            g.add(grp)
            continue

    return g


def _external_edges(room: Rect, built: Rect, tol: float = 2.0) -> List[Tuple[str, Tuple[float, float, float, float]]]:
    edges: List[Tuple[str, Tuple[float, float, float, float]]] = []
    if abs(room.y - built.y) <= tol:
        edges.append(("top", (room.x, room.y, room.right, room.y)))
    if abs(room.bottom - built.bottom) <= tol:
        edges.append(("bottom", (room.x, room.bottom, room.right, room.bottom)))
    if abs(room.x - built.x) <= tol:
        edges.append(("left", (room.x, room.y, room.x, room.bottom)))
    if abs(room.right - built.right) <= tol:
        edges.append(("right", (room.right, room.y, room.right, room.bottom)))
    return edges


def _draw_windows(
    dwg: svgwrite.Drawing,
    rooms: List[Dict[str, Any]],
    built: Rect,
) -> Tuple[svgwrite.container.Group, svgwrite.container.Group]:
    g_gaps = dwg.g(id="win_gaps")
    g = dwg.g(id="windows")
    opening = 38.0
    for r in rooms:
        cnt = int(r.get("windows", 0) or 0)
        if cnt <= 0:
            continue
        rr = _room_rect(r)
        edges = _external_edges(rr, built)
        if not edges:
            continue

        # Distribute windows across *each* external edge evenly, but capped by cnt.
        # If multiple edges, split count approximately.
        per_edge = max(1, int(math.ceil(cnt / max(len(edges), 1))))
        remaining = cnt

        for side, (x1, y1, x2, y2) in edges:
            if remaining <= 0:
                break
            local_n = min(per_edge, remaining)
            remaining -= local_n

            length = math.hypot(x2 - x1, y2 - y1)
            if length < opening + 10:
                continue
            for k in range(local_n):
                t = (k + 1) / (local_n + 1)
                cx = x1 + (x2 - x1) * t
                cy = y1 + (y2 - y1) * t

                if side in ("top", "bottom"):
                    sx = cx - opening / 2.0
                    sy = cy - EXT_WALL_T / 2.0
                    # gap
                    g_gaps.add(dwg.rect(insert=(MARGIN + sx, MARGIN + sy), size=(opening, EXT_WALL_T), fill=BG_PAPER, stroke="none"))
                    # glazing lines perpendicular -> vertical short lines across thickness, so draw horizontal lines inside opening
                    for off, col, sw, dashed in (
                        (-3.0, "#555555", 1.5, False),
                        (0.0, "#8899AA", 0.75, True),
                        (3.0, "#555555", 1.5, False),
                    ):
                        kwargs: Dict[str, Any] = {
                            "start": (MARGIN + sx, MARGIN + cy + off),
                            "end": (MARGIN + sx + opening, MARGIN + cy + off),
                            "stroke": col,
                            "stroke_width": sw,
                        }
                        if dashed:
                            kwargs["stroke_dasharray"] = "4,3"
                        g.add(dwg.line(**kwargs))
                else:
                    sx = cx - EXT_WALL_T / 2.0
                    sy = cy - opening / 2.0
                    g_gaps.add(dwg.rect(insert=(MARGIN + sx, MARGIN + sy), size=(EXT_WALL_T, opening), fill=BG_PAPER, stroke="none"))
                    for off, col, sw, dashed in (
                        (-3.0, "#555555", 1.5, False),
                        (0.0, "#8899AA", 0.75, True),
                        (3.0, "#555555", 1.5, False),
                    ):
                        kwargs = {
                            "start": (MARGIN + cx + off, MARGIN + sy),
                            "end": (MARGIN + cx + off, MARGIN + sy + opening),
                            "stroke": col,
                            "stroke_width": sw,
                        }
                        if dashed:
                            kwargs["stroke_dasharray"] = "4,3"
                        g.add(dwg.line(**kwargs))
    return g_gaps, g


def _find_corridor_room(rooms: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    for r in rooms:
        if _room_category(r) == "corridor" or str(r.get("name", "")).lower() == "corridor":
            return r
    return None


def _door_width_px_for_room(name: str) -> float:
    n = name.lower()
    if "bath" in n:
        return 24.0
    if "kitchen" in n or "utility" in n:
        return 28.0
    return 32.0  # bedroom doors


def _draw_doors(
    dwg: svgwrite.Drawing,
    rooms: List[Dict[str, Any]],
    built: Rect,
    parsed: Dict[str, Any],
) -> Tuple[svgwrite.container.Group, svgwrite.container.Group]:
    g_gaps = dwg.g(id="door_gaps")
    g = dwg.g(id="doors")

    corridor_room = _find_corridor_room(rooms)
    corridor_rect = _room_rect(corridor_room) if corridor_room else None

    def add_door_at(side: str, cx: float, cy: float, door_w: float) -> None:
        # 1) gap cutout
        if side in ("top", "bottom"):
            g_gaps.add(
                dwg.rect(
                    insert=(MARGIN + cx - door_w / 2.0, MARGIN + cy - EXT_WALL_T),
                    size=(door_w, EXT_WALL_T * 2.0),
                    fill=BG_PAPER,
                    stroke="none",
                )
            )
            # 2) door leaf
            g.add(
                dwg.rect(
                    insert=(MARGIN + cx - door_w / 2.0, MARGIN + cy - 1.5),
                    size=(door_w, 3.0),
                    fill="#888888",
                    stroke="none",
                )
            )
            # 3) swing arc (dashed)
            r = door_w
            if side == "top":
                d = f"M {MARGIN + cx - door_w/2:.1f} {MARGIN + cy:.1f} A {r:.1f} {r:.1f} 0 0 1 {MARGIN + cx + door_w/2:.1f} {MARGIN + cy + r:.1f}"
            else:
                d = f"M {MARGIN + cx + door_w/2:.1f} {MARGIN + cy:.1f} A {r:.1f} {r:.1f} 0 0 1 {MARGIN + cx - door_w/2:.1f} {MARGIN + cy - r:.1f}"
            g.add(dwg.path(d=d, fill="none", stroke="#666666", stroke_width=1.0, stroke_dasharray="3,2"))
        else:
            g_gaps.add(
                dwg.rect(
                    insert=(MARGIN + cx - EXT_WALL_T, MARGIN + cy - door_w / 2.0),
                    size=(EXT_WALL_T * 2.0, door_w),
                    fill=BG_PAPER,
                    stroke="none",
                )
            )
            g.add(
                dwg.rect(
                    insert=(MARGIN + cx - 1.5, MARGIN + cy - door_w / 2.0),
                    size=(3.0, door_w),
                    fill="#888888",
                    stroke="none",
                )
            )
            r = door_w
            if side == "left":
                d = f"M {MARGIN + cx:.1f} {MARGIN + cy - door_w/2:.1f} A {r:.1f} {r:.1f} 0 0 1 {MARGIN + cx + r:.1f} {MARGIN + cy + door_w/2:.1f}"
            else:
                d = f"M {MARGIN + cx:.1f} {MARGIN + cy + door_w/2:.1f} A {r:.1f} {r:.1f} 0 0 1 {MARGIN + cx - r:.1f} {MARGIN + cy - door_w/2:.1f}"
            g.add(dwg.path(d=d, fill="none", stroke="#666666", stroke_width=1.0, stroke_dasharray="3,2"))

    # Main entrance door (built-up perimeter)
    entrance = str(parsed.get("entrance_location", "north") or "").lower()
    main_w = float(parsed.get("main_door_width_ft", 4.0) or 4.0) * SCALE
    if "northeast" in entrance:
        side = "top"
        cx, cy = built.x + built.w * 0.35, built.y  # left-of-center
    elif "north" in entrance or "front" in entrance:
        side = "top"
        cx, cy = built.x + built.w * 0.5, built.y
    elif "east" in entrance:
        side = "right"
        cx, cy = built.right, built.y + built.h * 0.25
    elif "west" in entrance:
        side = "left"
        cx, cy = built.x, built.y + built.h * 0.25
    else:  # south/rear
        side = "bottom"
        cx, cy = built.x + built.w * 0.5, built.bottom
    add_door_at(side, cx, cy, main_w)

    # Interior doors: for each room (except corridor), place on shared wall with corridor.
    if corridor_rect is not None:
        for room in rooms:
            if room is corridor_room:
                continue
            rr = _room_rect(room)
            ln = _shared_boundary(rr, corridor_rect, tol=8.0)
            if ln is None:
                continue
            (x1, y1), (x2, y2) = ln.coords[0], ln.coords[-1]
            # determine side and pick point at ~1/3 along the segment (center-left-ish)
            door_w = _door_width_px_for_room(str(room.get("name", "")))
            if abs(x1 - x2) < 0.5:  # vertical shared edge
                x = x1
                ya = min(y1, y2)
                yb = max(y1, y2)
                cy = ya + (yb - ya) * 0.35
                cx = x
                side = "left" if abs(rr.x - x) < 1.0 else "right"
                add_door_at(side, cx, cy, door_w)
            elif abs(y1 - y2) < 0.5:  # horizontal
                y = y1
                xa = min(x1, x2)
                xb = max(x1, x2)
                cx = xa + (xb - xa) * 0.35
                cy = y
                side = "top" if abs(rr.y - y) < 1.0 else "bottom"
                add_door_at(side, cx, cy, door_w)

    return g_gaps, g


def _draw_labels(dwg: svgwrite.Drawing, rooms: List[Dict[str, Any]]) -> svgwrite.container.Group:
    g = dwg.g(id="labels")
    for i, r in enumerate(rooms):
        rr = _room_rect(r)
        name = _fmt_name(str(r.get("name", "")))
        w_ft = float(r.get("width_ft", rr.w / SCALE))
        d_ft = float(r.get("depth_ft", rr.h / SCALE))
        area = float(r.get("area_sqft", (rr.w / SCALE) * (rr.h / SCALE)))

        clip_id = f"clip_{i}"
        clip = dwg.clipPath(id=clip_id)
        clip.add(dwg.rect(insert=(MARGIN + rr.x, MARGIN + rr.y), size=(rr.w, rr.h)))
        dwg.defs.add(clip)

        grp = dwg.g(clip_path=f"url(#{clip_id})")
        if area < 50.0:
            abbr = ABBREV.get(_room_category(r), name[:6])
            grp.add(
                dwg.text(
                    abbr,
                    insert=(MARGIN + rr.cx, MARGIN + rr.cy),
                    text_anchor="middle",
                    dominant_baseline="middle",
                    font_family="Arial, Helvetica, sans-serif",
                    font_size=6.5,
                    font_weight=700,
                    fill="#1A1A1A",
                )
            )
        else:
            fs1 = _clamp(rr.w / 9.0, 7.0, 10.0)
            fs2 = _clamp(rr.w / 12.0, 5.5, 8.0)
            grp.add(
                dwg.text(
                    name,
                    insert=(MARGIN + rr.cx, MARGIN + rr.cy - fs1 * 0.6),
                    text_anchor="middle",
                    dominant_baseline="middle",
                    font_family="Arial, Helvetica, sans-serif",
                    font_size=fs1,
                    font_weight=700,
                    fill="#1A1A1A",
                    letter_spacing="0.3px",
                )
            )
            grp.add(
                dwg.text(
                    f"{w_ft:.0f}' × {d_ft:.0f}'  •  {area:.0f} sqft",
                    insert=(MARGIN + rr.cx, MARGIN + rr.cy + fs2 * 1.2),
                    text_anchor="middle",
                    dominant_baseline="middle",
                    font_family="Arial, Helvetica, sans-serif",
                    font_size=fs2,
                    font_weight=400,
                    fill="#666666",
                    font_style="italic",
                )
            )
        g.add(grp)
    return g


def _has_room_directly_above(target: Rect, rooms: List[Rect], tol: float = 2.0) -> bool:
    for r in rooms:
        if abs(r.bottom - target.y) <= tol:
            # overlap in x range?
            if not (r.right <= target.x + 1.0 or r.x >= target.right - 1.0):
                return True
    return False


def _has_room_directly_left(target: Rect, rooms: List[Rect], tol: float = 2.0) -> bool:
    for r in rooms:
        if abs(r.right - target.x) <= tol:
            if not (r.bottom <= target.y + 1.0 or r.y >= target.bottom - 1.0):
                return True
    return False


def _draw_tick_dim(
    dwg: svgwrite.Drawing,
    g: svgwrite.container.Group,
    *,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    text: str,
    text_x: float,
    text_y: float,
    rotate: Optional[float] = None,
    bold: bool = False,
) -> None:
    g.add(dwg.line(start=(x1, y1), end=(x2, y2), stroke="#777777", stroke_width=0.75))
    # ticks 7px
    if abs(y1 - y2) < 0.5:  # horizontal
        for x in (x1, x2):
            g.add(dwg.line(start=(x, y1 - 3.5), end=(x, y1 + 3.5), stroke="#777777", stroke_width=1.0))
    else:  # vertical
        for y in (y1, y2):
            g.add(dwg.line(start=(x1 - 3.5, y), end=(x1 + 3.5, y), stroke="#777777", stroke_width=1.0))

    txt = dwg.text(
        text,
        insert=(text_x, text_y),
        fill="#555555",
        font_family="Arial, Helvetica, sans-serif",
        font_size=9.0 if bold else 7.0,
        font_weight=700 if bold else 400,
        text_anchor="middle",
        dominant_baseline="middle",
    )
    if rotate is not None:
        txt.rotate(rotate, center=(text_x, text_y))
    g.add(txt)


def _draw_dimensions(
    dwg: svgwrite.Drawing,
    rooms: List[Dict[str, Any]],
    plot_w: float,
    plot_h: float,
) -> svgwrite.container.Group:
    g = dwg.g(id="dims")
    rects = [_room_rect(r) for r in rooms]
    for r, rr in zip(rooms, rects):
        area = float(r.get("area_sqft", 0.0) or 0.0)
        if area < 80.0:
            continue
        # outermost only: draw horizontal if no room directly above; vertical if no room directly left
        if not _has_room_directly_above(rr, rects):
            y = MARGIN + rr.y - 16.0
            _draw_tick_dim(
                dwg,
                g,
                x1=MARGIN + rr.x,
                y1=y,
                x2=MARGIN + rr.right,
                y2=y,
                text=_feet_inches_str(float(r.get("width_ft", rr.w / SCALE))),
                text_x=MARGIN + rr.cx,
                text_y=y - 8.0,
            )
        if not _has_room_directly_left(rr, rects):
            x = MARGIN + rr.x - 16.0
            _draw_tick_dim(
                dwg,
                g,
                x1=x,
                y1=MARGIN + rr.y,
                x2=x,
                y2=MARGIN + rr.bottom,
                text=_feet_inches_str(float(r.get("depth_ft", rr.h / SCALE))),
                text_x=x - 10.0,
                text_y=MARGIN + rr.cy,
                rotate=-90.0,
            )

    # overall plot dims
    # width above everything
    y = MARGIN - 35.0
    _draw_tick_dim(
        dwg,
        g,
        x1=MARGIN,
        y1=y,
        x2=MARGIN + plot_w,
        y2=y,
        text=_feet_inches_str(plot_w / SCALE),
        text_x=MARGIN + plot_w / 2.0,
        text_y=y - 10.0,
        bold=True,
    )
    # depth left of everything
    x = MARGIN - 35.0
    _draw_tick_dim(
        dwg,
        g,
        x1=x,
        y1=MARGIN,
        x2=x,
        y2=MARGIN + plot_h,
        text=_feet_inches_str(plot_h / SCALE),
        text_x=x - 12.0,
        text_y=MARGIN + plot_h / 2.0,
        rotate=-90.0,
        bold=True,
    )
    return g


def _draw_compass(dwg: svgwrite.Drawing, canvas_w: float) -> svgwrite.container.Group:
    g = dwg.g(id="compass")
    cx = canvas_w - MARGIN / 2.0 - 27.0
    cy = MARGIN / 2.0 + 27.0
    g.add(dwg.circle(center=(cx, cy), r=26.0, fill="white", stroke="#888888", stroke_width=1.0))
    g.add(dwg.polygon(points=[(cx, cy - 22.0), (cx - 5.0, cy - 4.0), (cx + 5.0, cy - 4.0)], fill="#1A1A1A"))
    g.add(
        dwg.polygon(
            points=[(cx, cy + 22.0), (cx - 5.0, cy + 4.0), (cx + 5.0, cy + 4.0)],
            fill="white",
            stroke="#1A1A1A",
            stroke_width=1.0,
        )
    )
    g.add(dwg.circle(center=(cx, cy), r=4.0, fill="#333333", stroke="none"))
    for lbl, x, y, anchor in (
        ("N", cx, cy - 28.0, "middle"),
        ("S", cx, cy + 32.0, "middle"),
        ("E", cx + 30.0, cy + 3.0, "start"),
        ("W", cx - 30.0, cy + 3.0, "end"),
    ):
        g.add(
            dwg.text(
                lbl,
                insert=(x, y),
                text_anchor=anchor,
                dominant_baseline="middle",
                font_family="Arial, Helvetica, sans-serif",
                font_size=9.0,
                font_weight="bold",
                fill="#1A1A1A",
            )
        )
    return g


def _draw_title_block(dwg: svgwrite.Drawing, canvas_w: float, canvas_h: float, parsed: Dict[str, Any]) -> svgwrite.container.Group:
    g = dwg.g(id="title")
    y0 = canvas_h - TITLE_H
    g.add(dwg.rect(insert=(0, y0), size=(canvas_w, TITLE_H), fill="#FFFFFF", stroke="#333333", stroke_width=1.5))

    x1 = canvas_w * 0.35
    x2 = canvas_w * 0.68
    g.add(dwg.line(start=(x1, y0), end=(x1, y0 + TITLE_H), stroke="#CCCCCC", stroke_width=0.75))
    g.add(dwg.line(start=(x2, y0), end=(x2, y0 + TITLE_H), stroke="#CCCCCC", stroke_width=0.75))

    bhk = str(parsed.get("bhk_type", "") or "").upper() or "BHK"
    floors = int(parsed.get("floors", 1) or 1)
    style = str(parsed.get("style", "modern") or "").upper()
    pw = float(parsed.get("plot_width_ft", 0.0) or 0.0)
    pd = float(parsed.get("plot_depth_ft", 0.0) or 0.0)
    bua = int(parsed.get("built_up_area_sqft", 0) or 0)
    budget = int(parsed.get("budget", 0) or 0)
    vastu = bool(parsed.get("vastu_compliant", False))

    # col 1
    pad = 12.0
    g.add(
        dwg.text(
            "RESIDENTIAL FLOOR PLAN",
            insert=(pad, y0 + 20.0),
            font_family="Arial, Helvetica, sans-serif",
            font_size=11.0,
            font_weight=700,
            fill="#111111",
        )
    )
    g.add(
        dwg.text(
            f"{bhk}  ·  {floors} STOREY  ·  {style}",
            insert=(pad, y0 + 35.0),
            font_family="Arial, Helvetica, sans-serif",
            font_size=7.5,
            fill="#555555",
        )
    )

    # col 2
    cx = (x1 + x2) / 2.0
    g.add(
        dwg.text(
            f"Plot {pw:.0f}'-0\" × {pd:.0f}'-0\"",
            insert=(cx, y0 + 20.0),
            text_anchor="middle",
            font_family="Arial, Helvetica, sans-serif",
            font_size=8.5,
            font_weight=600,
            fill="#222222",
        )
    )
    g.add(
        dwg.text(
            f"Built-up: {bua} sq ft  |  Scale 1:100",
            insert=(cx, y0 + 35.0),
            text_anchor="middle",
            font_family="Arial, Helvetica, sans-serif",
            font_size=7.0,
            fill="#555555",
        )
    )

    # col 3
    col3_cx = (x2 + canvas_w) / 2.0
    if vastu:
        bw, bh = 120.0, 22.0
        bx, by = col3_cx - bw / 2.0, y0 + 10.0
        g.add(dwg.rect(insert=(bx, by), size=(bw, bh), rx=4.0, ry=4.0, fill="#E8F5E9", stroke="#4CAF50", stroke_width=1.0))
        g.add(
            dwg.text(
                "✓ VASTU COMPLIANT",
                insert=(col3_cx, by + 15.0),
                text_anchor="middle",
                dominant_baseline="middle",
                font_family="Arial, Helvetica, sans-serif",
                font_size=8.0,
                font_weight=600,
                fill="#2E7D32",
            )
        )
    if budget > 0:
        lakhs = budget / 100000.0
        g.add(
            dwg.text(
                f"Budget: ₹{lakhs:.0f} Lakhs",
                insert=(col3_cx, y0 + 42.0),
                text_anchor="middle",
                font_family="Arial, Helvetica, sans-serif",
                font_size=8.0,
                fill="#444444",
            )
        )
    return g


def render_enhanced_svg(*, parsed: Dict[str, Any], layout: Dict[str, Any]) -> str:
    """
    Pure-SVG professional architectural renderer.

    Inputs:
      - parsed: full JSON from llm_parser
      - layout: output from layout_engine (room rects in px)
    Returns:
      - SVG string
    """
    # ── Schema adapter: handles both old nested format and new flat format ──
    # Old: layout["plot"]["width_px"], layout["built_up"]["x"]
    # New: layout["plot_w_px"], layout["built_up_x"]  (layout_engine v5+)
    _plot  = layout.get("plot") or {}
    _built = layout.get("built_up") or {}
    plot_w = float(layout.get("plot_w_px") or _plot.get("width_px")  or 400)
    plot_h = float(layout.get("plot_h_px") or _plot.get("height_px") or 600)
    built = Rect(
        float(layout.get("built_up_x") or _built.get("x",      20)),
        float(layout.get("built_up_y") or _built.get("y",      50)),
        float(layout.get("built_up_w") or _built.get("width",  360)),
        float(layout.get("built_up_h") or _built.get("height", 520)),
    )
    rooms: List[Dict[str, Any]] = list(layout.get("rooms") or [])

    canvas_w = plot_w + MARGIN * 2.0
    canvas_h = plot_h + MARGIN * 2.0 + TITLE_H

    dwg = svgwrite.Drawing(size=(canvas_w, canvas_h), viewBox=f"0 0 {canvas_w} {canvas_h}")
    dwg.attribs["shape-rendering"] = "geometricPrecision"

    _add_defs(dwg)

    # ── Layer order (bottom to top) per spec ───────────────────────────────
    g_bg = _draw_canvas_background(dwg, canvas_w, canvas_h)
    g_plot = _draw_plot_outline(dwg, plot_w, plot_h)
    g_setbacks, g_built = _draw_setbacks_and_builtup(dwg, plot_w=plot_w, plot_h=plot_h, built=built, parsed=parsed)
    g_room_fills = _draw_room_fills(dwg, rooms)
    g_furniture = _draw_furniture(dwg, rooms)
    g_int = _draw_internal_walls(dwg, rooms)
    g_ext = _draw_external_walls(dwg, built)
    g_win_gaps, g_windows = _draw_windows(dwg, rooms, built)
    g_door_gaps, g_doors = _draw_doors(dwg, rooms, built, parsed)
    g_labels = _draw_labels(dwg, rooms)
    g_dims = _draw_dimensions(dwg, rooms, plot_w, plot_h)
    g_compass = _draw_compass(dwg, canvas_w)
    g_title = _draw_title_block(dwg, canvas_w, canvas_h, parsed)

    for layer in [
        g_bg,
        g_plot,
        g_setbacks,
        g_room_fills,
        g_furniture,
        g_int,
        g_ext,
        g_win_gaps,
        g_windows,
        g_door_gaps,
        g_doors,
        g_labels,
        g_dims,
        g_compass,
        g_title,
        g_built,  # built-up dashed boundary can sit on top or bottom; spec lists it in setbacks section
    ]:
        dwg.add(layer)

    return dwg.tostring()