"""
svg_renderer.py  —  Professional Architectural Floor Plan  v10
===============================================================
BLACK ON WHITE. No fills. Thick solid walls. Thin outline furniture.
Exactly matching the reference plan style.

WALL SYSTEM:
  External walls = 9px thick solid BLACK filled rect
  Internal walls = 4px thick solid BLACK filled rect
  Rooms = WHITE interior
  
DOOR SYSTEM:
  Gap punched in wall (white rect over wall)
  Thin arc inside room = door swing (0.8px)
  No door leaf line needed

FURNITURE (all thin outlines, no fill):
  Bed      = rect + small headboard rect + 2 pillow rects
  Sofa     = L-shape rects  
  Dining   = rect table + small chair rects touching edges
  Kitchen  = L-counter outline + double sink rects + hob circles
  WC       = cistern rect + D-shape oval + inner circle
  Basin    = rounded square
  Stair    = parallel tread lines + UP/DN arrow
  Car      = top-view rectangle + wheels circles
"""
from __future__ import annotations
import math
import re
from typing import Any, Dict, List, Optional, Tuple

SCALE   = 10        # 10px per foot = 1:100
MARGIN  = 80
DIM_SPC = 55
TITLE_H = 50
TITLE_GAP_BELOW_PLOT = 28   # gap between lowest geometry and title ribbon
TITLE_BOTTOM_PAD = 48       # room for graphic scale ticks below title block
SIDE_PAD = 56               # symmetric horizontal margin (centers plan on canvas)
SCALE_BAR_TEXT_DROP = 16    # metres labels extend below title rect

EXT_WALL = 9.0      # external wall thickness px
INT_WALL = 4.0      # internal wall thickness px
HALF_EXT = EXT_WALL / 2
HALF_INT = INT_WALL / 2

# Door / window drafting (reference sheet: jambs + leaf + swing arc; framed windows)
DOOR_LEAF_THK = 1.85   # plan view door leaf thickness (inches scaled at 1:100)
JAMB_TICK = 2.4      # short jamb return at opening corners
WIN_FRAME_IN = 0.9   # inset from wall cut for window frame stroke

BLACK  = "#1A1A1A"
WHITE  = "#FFFFFF"
PAPER  = "#FFFFFF"   # pure white — no tint
GRAY   = "#888888"   # for light dimension lines
FRN    = "#1A1A1A"   # furniture lines — same black
FRN_W  = 0.7         # furniture line weight
DIM_C  = "#555555"
LBL_C  = "#111111"


# ─── PRIMITIVES ──────────────────────────────────────────────────────────────

def R(x, y, w, h, fill=WHITE, stroke=BLACK, sw=1.0, rx=0):
    return (f'<rect x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="{h:.2f}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}" rx="{rx}"/>')

def L(x1, y1, x2, y2, c=BLACK, w=0.8, dash=""):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return (f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" '
            f'stroke="{c}" stroke-width="{w}"{d}/>')

def C(cx, cy, r, fill=WHITE, stroke=BLACK, w=0.7):
    return (f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="{r:.2f}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{w}"/>')

def T(x, y, text, size=8, weight="400", c=LBL_C, anchor="middle"):
    return (f'<text x="{x:.2f}" y="{y:.2f}" font-size="{size}" font-weight="{weight}" '
            f'fill="{c}" text-anchor="{anchor}" '
            f'font-family="Arial,Helvetica,sans-serif" dominant-baseline="middle">{text}</text>')

def clip_rect(cid, x, y, w, h, ins=6):
    """Clip rect for text labels — generous inset so labels never get cut."""
    return (f'<clipPath id="{cid}"><rect x="{x+ins:.1f}" y="{y+ins:.1f}" '
            f'width="{max(w-ins*2,4):.1f}" height="{max(h-ins*2,4):.1f}"/></clipPath>')

def fmt_ft(px):
    px = max(float(px), 0.0)  # Guard: never negative (Guide Ch.12 Fix 5)
    total_in = round((px / SCALE) * 12)
    ft, inch = divmod(total_in, 12)
    if inch == 0:
        return f"{ft}'-0\""
    return f"{ft}\'-{inch}\""


# ─── THICK WALL DRAWING ───────────────────────────────────────────────────────
# Walls are drawn as FILLED BLACK RECTANGLES, not stroked lines.
# This is the key to the architectural look.

def wall_h(x, y, length, thickness=INT_WALL):
    """Horizontal wall segment."""
    return R(x, y - thickness/2, length, thickness, fill=BLACK, stroke="none", sw=0)

def wall_v(x, y, length, thickness=INT_WALL):
    """Vertical wall segment."""
    return R(x - thickness/2, y, thickness, length, fill=BLACK, stroke="none", sw=0)


# ─── ROOM BOUNDARY WALLS ──────────────────────────────────────────────────────

def draw_room_walls(x, y, w, h, is_ext_top, is_ext_bot, is_ext_left, is_ext_right):
    """Draw 4 walls. Exterior walls draw INWARD from boundary. Internal walls centered on shared edge."""
    out = []
    t_top   = EXT_WALL if is_ext_top   else INT_WALL
    t_bot   = EXT_WALL if is_ext_bot   else INT_WALL
    t_left  = EXT_WALL if is_ext_left  else INT_WALL
    t_right = EXT_WALL if is_ext_right else INT_WALL
    # EXTERIOR walls draw INWARD from edge — no bleed outside building
    # INTERNAL walls stay centered on shared edge between rooms
    top_y   = y         if is_ext_top   else y   - t_top/2
    bot_y   = y+h-t_bot if is_ext_bot   else y+h - t_bot/2
    left_x  = x         if is_ext_left  else x   - t_left/2
    right_x = x+w-t_right if is_ext_right else x+w - t_right/2
    out.append(R(left_x,  top_y,  w,       t_top,   fill=BLACK, stroke="none", sw=0))
    out.append(R(left_x,  bot_y,  w,       t_bot,   fill=BLACK, stroke="none", sw=0))
    out.append(R(left_x,  top_y,  t_left,  h,       fill=BLACK, stroke="none", sw=0))
    out.append(R(right_x, top_y,  t_right, h,       fill=BLACK, stroke="none", sw=0))
    return "".join(out)


def _programme_name_stems(n: str) -> List[str]:
    """
    Programme ids for void-fill / editor may append ``_2``, ``_3`` for uniqueness.
    Try the full string first, then strip trailing ``_<digits>`` segments until ``cat`` resolves.
    """
    stems: List[str] = []
    cur = (n or "").lower().strip()
    if not cur:
        return stems
    seen = set()
    while cur and cur not in seen:
        seen.add(cur)
        stems.append(cur)
        m = re.fullmatch(r"(.+)_(\d+)$", cur)
        if not m:
            break
        cur = m.group(1)
    return stems


def _cat_core(n: str) -> str:
    """Resolve one snake_case programme fragment (already lowercased)."""
    if "car_porch" in n:
        return "car_porch"
    if "sit_out" in n or "verandah" in n or "veranda" in n:
        return "sit_out"
    if "foyer" in n:
        return "foyer"
    if "drawing_room" == n or ("drawing" in n and "room" in n):
        return "drawing_room"
    if n == "living_room":
        return "living_room"
    if n == "dining_room":
        return "dining_room"
    if "wet_kitchen" in n:
        return "wet_kitchen"
    if "dry_kitchen" in n:
        return "dry_kitchen"
    if "kitchen" in n:
        return "kitchen"
    if "pooja" in n:
        return "pooja_room"
    if "utility" in n:
        return "utility_room"
    if "store_room" in n or ("store" in n and "stair" not in n):
        return "store_room"
    if "staircase_landing" in n:
        return "staircase_landing"
    if n in ("service_passage", "rear_passage"):
        return "passage"
    if "corridor" in n:
        return "corridor"
    if "passage" in n:
        return "passage"
    if "common" in n and "bath" in n:
        return "common_bathroom"
    if "guest_powder" in n or "powder_room" in n:
        return "guest_powder_room"
    if "bath" in n or "toilet" in n:
        return "bathroom"
    if "master_bedroom" in n:
        return "master_bedroom"
    if "parents_bedroom" in n:
        return "parents_bedroom"
    if "guest_bedroom" in n or "guest_room" in n:
        return "guest_bedroom"
    if "bedroom" in n:
        return "bedroom"
    if "staircase" in n:
        return "staircase"
    if "balcony" in n:
        return "balcony"
    if "terrace" in n:
        return "terrace"
    if "home_office" in n or ("office" in n and "home" in n):
        return "home_office"
    if "servant" in n:
        return "servant_quarters"
    if "family_lounge" in n or ("lounge" in n and "family" in n):
        return "family_lounge"
    if "walk_in_wardrobe" in n or "wardrobe" in n:
        return "walk_in_wardrobe"
    return "generic"


def cat(name):
    """Map room ``name`` → furniture / tint category (handles uniquified ``*_2`` suffixes)."""
    n0 = (name or "").strip().lower()
    if not n0:
        return "generic"
    for cand in _programme_name_stems(n0):
        c = _cat_core(cand)
        if c != "generic":
            return c
    return "generic"


def room_label(name):
    n = name.lower(); c = cat(n)
    M = {
        "living_room":     "DRAWING ROOM", "dining_room":    "DINING",
        "drawing_room":    "DRAWING ROOM",
        "master_bedroom":  "M. BED ROOM",  "parents_bedroom":"PARENTS BED",
        "bedroom_2":       "BED ROOM",     "bedroom_3":      "BED ROOM",
        "bedroom":         "BED ROOM",     "guest_bedroom":  "GUEST BED",
        "kitchen":         "KITCHEN",      "wet_kitchen":    "WET KITCHEN",
        "dry_kitchen":     "DRY KITCHEN",  "pooja_room":     "PRAYER ROOM",
        "corridor":        "CORRIDOR",     "passage":        "PASSAGE",
        "car_porch":       "PARKING",      "sit_out":        "VERANDA",
        "utility_room":    "UTILITY",      "store_room":     "STORE",
        "staircase_landing":"STAIR",        "staircase":      "STAIR",
        "home_office":     "HOME OFFICE",  "family_lounge":  "FAMILY LOUNGE",
        "servant_quarters":"SERVANT BED",  "servant_bathroom":"BATH",
        "walk_in_wardrobe":"W.I.C",        "terrace":        "TERRACE",
        "balcony":         "BALCONY",      "foyer":          "FOYER",
        "common_bathroom": "TOILET",       "guest_powder_room":"TOILET",
        "bathroom":        "BATH",
    }
    if c in M: return M[c]
    for k, v in sorted(M.items(), key=lambda x: -len(x[0])):
        if k in n: return v
    return name.replace("_", " ").upper()

def is_carved(name):
    n = name.lower()
    cv = ("master_bedroom", "parents_bedroom", "bedroom_", "servant_quarters", "servant_")
    if n.endswith("_bathroom") and any(p in n for p in cv): return True
    if "servant" in n and "bath" in n: return True
    if "walk_in_wardrobe" in n: return True
    return False

def is_bedroom_cat(c):
    return c in ("master_bedroom", "bedroom", "parents_bedroom", "guest_bedroom")


# ─── EXTERIOR WALL DETECTION ─────────────────────────────────────────────────

def ext_walls_of(rx, ry, rw, rh, bx, by, bw, bh, ox, oy, T=10.0):
    """Which walls of this room are on the exterior boundary?"""
    abx = bx + ox; aby = by + oy
    return (
        abs(ry - aby)            < T,  # top
        abs((ry+rh) - (aby+bh)) < T,  # bottom
        abs(rx - abx)            < T,  # left
        abs((rx+rw) - (abx+bw)) < T,  # right
    )


# ─── DOOR: reference-style (wall cut + jambs + door leaf + quarter swing) ─────

def _door_leaf_poly_quad(x0: float, y0: float, x1: float, y1: float, th: float) -> str:
    """
    Thin filled quadrilateral for door leaf (plan view).
    Offset uses a 90° rotation of the leaf direction (dy, -dx) so thickness reads
    consistently on plan (matches reference leaf weight).
    """
    dx = x1 - x0
    dy = y1 - y0
    ln = math.hypot(dx, dy) or 1.0
    nx = dy / ln * th
    ny = -dx / ln * th
    return (
        f'<polygon points="{x0:.2f},{y0:.2f} {x1:.2f},{y1:.2f} '
        f"{x1+nx:.2f},{y1+ny:.2f} {x0+nx:.2f},{y0+ny:.2f}\" "
        f'fill="{WHITE}" stroke="{BLACK}" stroke-width="0.55" stroke-linejoin="miter"/>'
    )


def draw_door(
    rx,
    ry,
    rw,
    rh,
    name,
    ext_top=False,
    ext_bot=False,
    ext_left=False,
    ext_right=False,
    layout_band: int = -1,
    preferred_wall: str = "",
    width_override_px: float = 0.0,
):
    """
    Reference-sheet door: opening cut in wall, short jamb returns, door leaf (thin panel),
    quarter-circle swing arc into the room (never through exterior).

    Main entrance (large width_override): uneven pair — narrow active + wide active
    (reference \"Uneven door\" / main entry).
    """
    n = name.lower(); c = cat(n)
    if c in ("corridor", "passage", "staircase_landing", "car_porch",
             "terrace", "balcony", "staircase"):
        return ""

    out: List[str] = []
    gap_t = EXT_WALL * 2.0

    # Door width: NBC ~900 mm internal, ~1200 mm main; override for entry.
    if width_override_px and width_override_px > 1.0:
        dw = float(width_override_px)
    else:
        if rw < 60 or rh < 60:
            dw = max(min(rw * 0.38, 22.0), 14.0)
        else:
            dw = max(min(rw * 0.28, 32.0), 20.0)
        dw = min(dw, rw * 0.42, rh * 0.42)

    main_pair = bool(width_override_px and width_override_px >= 38.0)

    wall = ""
    if preferred_wall in ("top", "bot", "left", "right"):
        if (preferred_wall == "top" and not ext_top) or \
           (preferred_wall == "bot" and not ext_bot) or \
           (preferred_wall == "left" and not ext_left) or \
           (preferred_wall == "right" and not ext_right):
            wall = preferred_wall

    if not wall and c in ("kitchen", "wet_kitchen", "dry_kitchen", "utility_room",
                          "servant_quarters", "home_office"):
        wall = "left" if not ext_left else ("top" if not ext_top else "right")
    elif not wall and c in ("master_bedroom", "bedroom", "parents_bedroom", "guest_bedroom",
                            "family_lounge", "walk_in_wardrobe"):
        wall = "top" if not ext_top else ("left" if not ext_left else "right")
    elif not wall and c in ("bathroom", "common_bathroom", "guest_powder_room"):
        if layout_band == 5:
            wall = "left" if not ext_left else ("right" if not ext_right else ("top" if not ext_top else "bot"))
        else:
            wall = "top" if not ext_top else ("left" if not ext_left else "right")
    elif not wall and c in ("pooja_room", "store_room", "foyer"):
        wall = "top" if not ext_top else ("right" if not ext_right else "left")
    elif not wall:
        wall = "top" if not ext_top else ("left" if not ext_left else ("right" if not ext_right else "bot"))

    edge_pad = 16.0
    th = DOOR_LEAF_THK

    def _jambs_top(hx: float, wy: float, w: float) -> None:
        j = JAMB_TICK
        out.append(L(hx, wy, hx + j, wy, BLACK, 0.55))
        out.append(L(hx, wy, hx, wy + j, BLACK, 0.55))
        out.append(L(hx + w, wy, hx + w - j, wy, BLACK, 0.55))
        out.append(L(hx + w, wy, hx + w, wy + j, BLACK, 0.55))

    def _jambs_bot(hx: float, wy: float, w: float) -> None:
        j = JAMB_TICK
        out.append(L(hx, wy, hx + j, wy, BLACK, 0.55))
        out.append(L(hx, wy, hx, wy - j, BLACK, 0.55))
        out.append(L(hx + w, wy, hx + w - j, wy, BLACK, 0.55))
        out.append(L(hx + w, wy, hx + w, wy - j, BLACK, 0.55))

    def _jambs_left(wx: float, hy: float, d: float) -> None:
        j = JAMB_TICK
        out.append(L(wx, hy, wx, hy + j, BLACK, 0.55))
        out.append(L(wx, hy, wx + j, hy, BLACK, 0.55))
        out.append(L(wx, hy + d, wx, hy + d - j, BLACK, 0.55))
        out.append(L(wx, hy + d, wx + j, hy + d, BLACK, 0.55))

    def _jambs_right(wx: float, hy: float, d: float) -> None:
        j = JAMB_TICK
        out.append(L(wx, hy, wx, hy + j, BLACK, 0.55))
        out.append(L(wx, hy, wx - j, hy, BLACK, 0.55))
        out.append(L(wx, hy + d, wx, hy + d - j, BLACK, 0.55))
        out.append(L(wx, hy + d, wx - j, hy + d, BLACK, 0.55))

    # ── Kitchen: opening only — no leaf/swing ───────────────────────────────
    _kitchen_opening_only = c in ("kitchen", "wet_kitchen", "dry_kitchen")

    # ── TOP wall (swing into +Y) ─────────────────────────────────────────────
    if wall == "top":
        hx = rx + (rw - dw) * 0.5
        hx = max(rx + edge_pad, min(hx, rx + rw - edge_pad - dw))
        wy = ry
        out.append(R(hx, wy - EXT_WALL, dw, gap_t, fill=WHITE, stroke="none", sw=0))
        _jambs_top(hx, wy, dw)
        if _kitchen_opening_only:
            pass  # no leaf/swing for kitchen
        elif main_pair:
            wn = max(9.0, min(dw * 0.30, 20.0))
            wl = max(dw - wn - 1.0, 10.0)
            # Narrow leaf (hinge left), wide leaf (hinge right); both swing down.
            out.append(_door_leaf_poly_quad(hx, wy, hx, wy + wn, th))
            out.append(_door_leaf_poly_quad(hx + dw, wy, hx + dw, wy + wl, th))
            out.append(
                f'<path d="M {hx+wn:.2f} {wy:.2f} A {wn:.2f} {wn:.2f} 0 0 0 {hx:.2f} {wy+wn:.2f}" '
                f'fill="none" stroke="{BLACK}" stroke-width="0.7"/>'
            )
            out.append(
                f'<path d="M {hx+dw-wl:.2f} {wy:.2f} A {wl:.2f} {wl:.2f} 0 0 1 {hx+dw:.2f} {wy+wl:.2f}" '
                f'fill="none" stroke="{BLACK}" stroke-width="0.7"/>'
            )
        else:
            out.append(_door_leaf_poly_quad(hx, wy, hx, wy + dw, th))
            out.append(
                f'<path d="M {hx+dw:.2f} {wy:.2f} A {dw:.2f} {dw:.2f} 0 0 0 {hx:.2f} {wy+dw:.2f}" '
                f'fill="none" stroke="{BLACK}" stroke-width="0.7"/>'
            )
    elif wall == "bot":
        hx = rx + (rw - dw) * 0.5
        hx = max(rx + edge_pad, min(hx, rx + rw - edge_pad - dw))
        wy = ry + rh
        out.append(R(hx, wy - EXT_WALL, dw, gap_t, fill=WHITE, stroke="none", sw=0))
        _jambs_bot(hx, wy, dw)
        if _kitchen_opening_only:
            pass  # no leaf/swing for kitchen
        elif main_pair:
            wn = max(9.0, min(dw * 0.30, 20.0))
            wl = max(dw - wn - 1.0, 10.0)
            out.append(_door_leaf_poly_quad(hx, wy, hx, wy - wn, th))
            out.append(_door_leaf_poly_quad(hx + dw, wy, hx + dw, wy - wl, th))
            out.append(
                f'<path d="M {hx+wn:.2f} {wy:.2f} A {wn:.2f} {wn:.2f} 0 0 1 {hx:.2f} {wy-wn:.2f}" '
                f'fill="none" stroke="{BLACK}" stroke-width="0.7"/>'
            )
            out.append(
                f'<path d="M {hx+dw-wl:.2f} {wy:.2f} A {wl:.2f} {wl:.2f} 0 0 0 {hx+dw:.2f} {wy-wl:.2f}" '
                f'fill="none" stroke="{BLACK}" stroke-width="0.7"/>'
            )
        else:
            out.append(_door_leaf_poly_quad(hx, wy, hx, wy - dw, th))
            out.append(
                f'<path d="M {hx+dw:.2f} {wy:.2f} A {dw:.2f} {dw:.2f} 0 0 1 {hx:.2f} {wy-dw:.2f}" '
                f'fill="none" stroke="{BLACK}" stroke-width="0.7"/>'
            )
    elif wall == "left":
        wx = rx
        hy = ry + (rh - dw) * 0.5
        hy = max(ry + edge_pad, min(hy, ry + rh - edge_pad - dw))
        out.append(R(wx - EXT_WALL, hy, gap_t, dw, fill=WHITE, stroke="none", sw=0))
        _jambs_left(wx, hy, dw)
        if _kitchen_opening_only:
            pass  # no leaf/swing for kitchen
        elif main_pair:
            wn = max(9.0, min(dw * 0.30, 20.0))
            wl = max(dw - wn - 1.0, 10.0)
            out.append(_door_leaf_poly_quad(wx, hy, wx + wn, hy, th))
            out.append(_door_leaf_poly_quad(wx, hy + dw, wx + wl, hy + dw, th))
            out.append(
                f'<path d="M {wx:.2f} {hy+wn:.2f} A {wn:.2f} {wn:.2f} 0 0 1 {wx+wn:.2f} {hy:.2f}" '
                f'fill="none" stroke="{BLACK}" stroke-width="0.7"/>'
            )
            out.append(
                f'<path d="M {wx:.2f} {hy+dw-wl:.2f} A {wl:.2f} {wl:.2f} 0 0 0 {wx+wl:.2f} {hy+dw:.2f}" '
                f'fill="none" stroke="{BLACK}" stroke-width="0.7"/>'
            )
        else:
            out.append(_door_leaf_poly_quad(wx, hy, wx + dw, hy, th))
            out.append(
                f'<path d="M {wx:.2f} {hy+dw:.2f} A {dw:.2f} {dw:.2f} 0 0 1 {wx+dw:.2f} {hy:.2f}" '
                f'fill="none" stroke="{BLACK}" stroke-width="0.7"/>'
            )
    else:  # right
        wx = rx + rw
        hy = ry + (rh - dw) * 0.5
        hy = max(ry + edge_pad, min(hy, ry + rh - edge_pad - dw))
        out.append(R(wx - EXT_WALL, hy, gap_t, dw, fill=WHITE, stroke="none", sw=0))
        _jambs_right(wx, hy, dw)
        if _kitchen_opening_only:
            pass  # no leaf/swing for kitchen
        elif main_pair:
            wn = max(9.0, min(dw * 0.30, 20.0))
            wl = max(dw - wn - 1.0, 10.0)
            out.append(_door_leaf_poly_quad(wx, hy, wx - wn, hy, th))
            out.append(_door_leaf_poly_quad(wx, hy + dw, wx - wl, hy + dw, th))
            out.append(
                f'<path d="M {wx:.2f} {hy+wn:.2f} A {wn:.2f} {wn:.2f} 0 0 0 {wx-wn:.2f} {hy:.2f}" '
                f'fill="none" stroke="{BLACK}" stroke-width="0.7"/>'
            )
            out.append(
                f'<path d="M {wx:.2f} {hy+dw-wl:.2f} A {wl:.2f} {wl:.2f} 0 0 1 {wx-wl:.2f} {hy+dw:.2f}" '
                f'fill="none" stroke="{BLACK}" stroke-width="0.7"/>'
            )
        else:
            out.append(_door_leaf_poly_quad(wx, hy, wx - dw, hy, th))
            out.append(
                f'<path d="M {wx:.2f} {hy+dw:.2f} A {dw:.2f} {dw:.2f} 0 0 0 {wx-dw:.2f} {hy:.2f}" '
                f'fill="none" stroke="{BLACK}" stroke-width="0.7"/>'
            )

    return "".join(out)


# ─── WINDOW: 3 lines in wall gap ─────────────────────────────────────────────

def win_wall(name, rx, ry, rw, rh, ext_top, ext_bot, ext_left, ext_right):
    n = name.lower(); c = cat(n)
    # sit_out / veranda: allow exterior windows (prefs below); still no windows on fully open parking / stairs.
    if c in ("car_porch", "terrace", "balcony", "corridor",
             "passage", "staircase_landing", "staircase"):
        return "none"
    if "bath" in n or "toilet" in n: return "none"
    prefs = {
        # Public zone — windows on front (top=exterior facing street) and sides
        "living_room":      ["top", "left", "right", "bot"],
        "drawing_room":     ["top", "left", "right", "bot"],
        "dining_room":      ["top", "right", "left"],
        "family_lounge":    ["top", "left", "right"],
        "foyer":            ["top", "left"],
        # Service zone — kitchen/utility on exterior side or rear
        "kitchen":          ["right", "bot", "left"],
        "wet_kitchen":      ["right", "bot"],
        "dry_kitchen":      ["right", "bot"],
        "utility_room":     ["bot", "right", "left"],
        "servant_quarters": ["bot", "left", "right"],
        "home_office":      ["left", "top", "right"],
        # Bedroom zone — exterior on bot and sides (corridor is top, no window toward corridor)
        "master_bedroom":   ["bot", "right", "left"],
        "bedroom":          ["bot", "left", "right"],
        "parents_bedroom":  ["left", "bot", "right"],
        "guest_bedroom":    ["bot", "left", "right"],
        # NE devotional space — windows facing NE (top+left for east-facing)
        "pooja_room":       ["top", "left"],
        "store_room":       ["bot", "right", "left"],
        "sit_out":          ["top", "left", "right"],
    }
    walls = {"top": ext_top, "bot": ext_bot, "left": ext_left, "right": ext_right}
    for p in prefs.get(c, ["top", "left", "right", "bot"]):
        if walls.get(p): return p
    # Fallback: any exterior wall
    for p in ["top", "bot", "left", "right"]:
        if walls[p]: return p
    # No exterior wall available: do not draw an interior "window" (non-standard).
    return "none"

def draw_window(rx, ry, rw, rh, wall, count, style: str = ""):
    """
    Reference-style window: wall cut + light frame stroke + mullions.
    - standard / casement: outer frame lines + bold centre mullion (reads as fixed / side-hung).
    - glider: overlapping pane pair (reference sliding / glider symbol) for wide service bays.
    """
    if wall == "none" or count == 0:
        return ""
    out: List[str] = []
    count = min(count, 3)
    span = (rw * 0.62) if wall in ("top", "bot") else (rh * 0.58)
    pane = max(min(span / count, 36.0), 14.0)
    WH = EXT_WALL
    edge_pad = 18.0
    st = (style or "standard").lower()
    use_glider = st == "glider" and pane >= 20.0

    for i in range(count):
        if wall in ("top", "bot"):
            a = rx + edge_pad
            b = rx + rw - edge_pad
            cx = (a + b) * 0.5 if count == 1 else (a + (b - a) * (i + 0.5) / count)
            wy = ry if wall == "top" else ry + rh
            out.append(R(cx - pane / 2, wy - WH / 2, pane, WH, fill=WHITE, stroke="none", sw=0))
            # Frame (reference: crisp opening rectangle inside wall cut)
            fx0 = cx - pane / 2 + WIN_FRAME_IN
            fy0 = wy - WH / 2 + WIN_FRAME_IN * 0.6
            fw = pane - 2 * WIN_FRAME_IN
            fh = WH - 1.4 * WIN_FRAME_IN
            out.append(R(fx0, fy0, fw, fh, fill=WHITE, stroke=BLACK, sw=0.55))
            if use_glider:
                off = 2.2
                out.append(
                    L(fx0 + off, fy0 + fh * 0.22, fx0 + fw * 0.52 + off, fy0 + fh * 0.78, DIM_C, 0.65)
                )
                out.append(
                    L(fx0 + fw * 0.48 - off, fy0 + fh * 0.22, fx0 + fw - off, fy0 + fh * 0.78, DIM_C, 0.65)
                )
                out.append(L(cx - pane * 0.18, fy0 + fh * 0.5, cx + pane * 0.18, fy0 + fh * 0.5, BLACK, 1.0))
            else:
                out.append(
                    L(fx0, fy0 + fh * 0.32, fx0 + fw, fy0 + fh * 0.32, DIM_C, 0.65)
                )
                out.append(L(cx, fy0 + 0.9, cx, fy0 + fh - 0.9, BLACK, 1.05))
                out.append(
                    L(fx0, fy0 + fh * 0.68, fx0 + fw, fy0 + fh * 0.68, DIM_C, 0.65)
                )
            # Jamb ticks at opening ends (subtle L returns)
            j = 1.8
            out.append(L(cx - pane / 2, wy, cx - pane / 2 + j, wy, BLACK, 0.45))
            out.append(L(cx - pane / 2, wy, cx - pane / 2, wy + (j if wall == "top" else -j), BLACK, 0.45))
            out.append(L(cx + pane / 2, wy, cx + pane / 2 - j, wy, BLACK, 0.45))
            out.append(L(cx + pane / 2, wy, cx + pane / 2, wy + (j if wall == "top" else -j), BLACK, 0.45))
        else:
            a = ry + edge_pad
            b = ry + rh - edge_pad
            cy = (a + b) * 0.5 if count == 1 else (a + (b - a) * (i + 0.5) / count)
            wx = rx if wall == "left" else rx + rw
            dx = 1 if wall == "left" else -1
            out.append(R(wx - WH / 2, cy - pane / 2, WH, pane, fill=WHITE, stroke="none", sw=0))
            fx0 = wx - WH / 2 + WIN_FRAME_IN * 0.6
            fy0 = cy - pane / 2 + WIN_FRAME_IN
            fw = WH - 1.4 * WIN_FRAME_IN
            fh = pane - 2 * WIN_FRAME_IN
            out.append(R(fx0, fy0, fw, fh, fill=WHITE, stroke=BLACK, sw=0.55))
            if use_glider:
                off = 2.2
                out.append(
                    L(fx0 + fw * 0.22, fy0 + off, fx0 + fw * 0.78, fy0 + fh * 0.52 + off, DIM_C, 0.65)
                )
                out.append(
                    L(fx0 + fw * 0.22, fy0 + fh - off, fx0 + fw * 0.78, fy0 + fh * 0.48 - off, DIM_C, 0.65)
                )
                out.append(L(fx0 + fw * 0.5, cy - pane * 0.18, fx0 + fw * 0.5, cy + pane * 0.18, BLACK, 1.0))
            else:
                out.append(
                    L(fx0 + fw * 0.32, fy0, fx0 + fw * 0.32, fy0 + fh, DIM_C, 0.65)
                )
                out.append(L(fx0 + 0.9, cy, fx0 + fw - 0.9, cy, BLACK, 1.05))
                out.append(
                    L(fx0 + fw * 0.68, fy0, fx0 + fw * 0.68, fy0 + fh, DIM_C, 0.65)
                )
            j = 1.8
            out.append(L(wx, cy - pane / 2, wx, cy - pane / 2 + j, BLACK, 0.45))
            out.append(L(wx, cy - pane / 2, wx + j * dx, cy - pane / 2, BLACK, 0.45))
            out.append(L(wx, cy + pane / 2, wx, cy + pane / 2 - j, BLACK, 0.45))
            out.append(L(wx, cy + pane / 2, wx + j * dx, cy + pane / 2, BLACK, 0.45))
    return "".join(out)


def _wrap_sys_opening(room_id_h: str, kind: str, slot: str, inner: str) -> str:
    inner = inner.strip()
    if not inner:
        return ""
    h = _xml_attr(room_id_h[:48])
    k = _xml_attr(kind[:12])
    s = _xml_attr(slot[:16])
    return (
        f'<g class="editable-sys-opening" data-editable="true" data-room-id="{h}" '
        f'data-sys-kind="{k}" data-sys-slot="{s}" style="cursor:move">{inner}</g>'
    )


def draw_placed_openings_on_room(
    room: Dict[str, Any],
    rx: float,
    ry: float,
    rw: float,
    rh: float,
    ext_top: bool,
    ext_bot: bool,
    ext_left: bool,
    ext_right: bool,
    room_id_hyphen: str,
) -> str:
    """
    User-authored openings on a room perimeter (Maket-style wall punches).
    Stored on room as placed_openings: [
      { "id": str, "edge": "top"|"bot"|"bottom"|"left"|"right", "u": 0..1, "kind": "door"|"window",
        "width_px"?: number }
    ]
    u = position along the wall: 0 at min corner, 1 at max (after padding).
    """
    raw = room.get("placed_openings")
    if not isinstance(raw, list) or not raw:
        return ""

    c = cat(str(room.get("name", "")).lower())

    _kitchen_opening_only = c in ("kitchen", "wet_kitchen", "dry_kitchen")
    gap_t = EXT_WALL * 2.0
    th = DOOR_LEAF_THK
    edge_pad = 16.0
    jm = JAMB_TICK * 0.85
    WH = EXT_WALL

    body_parts: List[str] = []
    for op in raw:
        if not isinstance(op, dict):
            continue
        edge = str(op.get("edge", "")).lower()
        if edge == "bottom":
            edge = "bot"
        if edge not in ("top", "bot", "left", "right"):
            continue
        kind = str(op.get("kind", "door")).lower()
        if kind not in ("door", "window"):
            kind = "door"
        u = float(op.get("u", 0.5))
        u = max(0.0, min(1.0, u))
        dw = float(op.get("width_px", 28.0 if kind == "door" else 22.0))
        dw = max(14.0, min(dw, rw * 0.42, rh * 0.42))
        oid = _xml_attr(str(op.get("id", "op"))[:48])
        sub: List[str] = []

        def _door_top(hx: float, wy: float, dw2: float) -> None:
            sub.append(R(hx, wy - EXT_WALL, dw2, gap_t, fill=WHITE, stroke="none", sw=0))
            sub.append(L(hx, wy, hx + jm, wy, BLACK, 0.55))
            sub.append(L(hx, wy, hx, wy + jm, BLACK, 0.55))
            sub.append(L(hx + dw2, wy, hx + dw2 - jm, wy, BLACK, 0.55))
            sub.append(L(hx + dw2, wy, hx + dw2, wy + jm, BLACK, 0.55))
            if not _kitchen_opening_only:
                sub.append(_door_leaf_poly_quad(hx, wy, hx, wy + dw2, th))
                sub.append(
                    f'<path d="M {hx+dw2:.2f} {wy:.2f} A {dw2:.2f} {dw2:.2f} 0 0 0 {hx:.2f} {wy+dw2:.2f}" '
                    f'fill="none" stroke="{BLACK}" stroke-width="0.7"/>'
                )

        def _door_bot(hx: float, wy: float, dw2: float) -> None:
            sub.append(R(hx, wy - EXT_WALL, dw2, gap_t, fill=WHITE, stroke="none", sw=0))
            sub.append(L(hx, wy, hx + jm, wy, BLACK, 0.55))
            sub.append(L(hx, wy, hx, wy - jm, BLACK, 0.55))
            sub.append(L(hx + dw2, wy, hx + dw2 - jm, wy, BLACK, 0.55))
            sub.append(L(hx + dw2, wy, hx + dw2, wy - jm, BLACK, 0.55))
            if not _kitchen_opening_only:
                sub.append(_door_leaf_poly_quad(hx, wy, hx, wy - dw2, th))
                sub.append(
                    f'<path d="M {hx+dw2:.2f} {wy:.2f} A {dw2:.2f} {dw2:.2f} 0 0 1 {hx:.2f} {wy-dw2:.2f}" '
                    f'fill="none" stroke="{BLACK}" stroke-width="0.7"/>'
                )

        def _door_left(wx: float, hy: float, dw2: float) -> None:
            sub.append(R(wx - EXT_WALL, hy, gap_t, dw2, fill=WHITE, stroke="none", sw=0))
            sub.append(L(wx, hy, wx, hy + jm, BLACK, 0.55))
            sub.append(L(wx, hy, wx + jm, hy, BLACK, 0.55))
            sub.append(L(wx, hy + dw2, wx, hy + dw2 - jm, BLACK, 0.55))
            sub.append(L(wx, hy + dw2, wx + jm, hy + dw2, BLACK, 0.55))
            if not _kitchen_opening_only:
                sub.append(_door_leaf_poly_quad(wx, hy, wx + dw2, hy, th))
                sub.append(
                    f'<path d="M {wx:.2f} {hy+dw2:.2f} A {dw2:.2f} {dw2:.2f} 0 0 1 {wx+dw2:.2f} {hy:.2f}" '
                    f'fill="none" stroke="{BLACK}" stroke-width="0.7"/>'
                )

        def _door_right(wx: float, hy: float, dw2: float) -> None:
            sub.append(R(wx - EXT_WALL, hy, gap_t, dw2, fill=WHITE, stroke="none", sw=0))
            sub.append(L(wx, hy, wx, hy + jm, BLACK, 0.55))
            sub.append(L(wx, hy, wx - jm, hy, BLACK, 0.55))
            sub.append(L(wx, hy + dw2, wx, hy + dw2 - jm, BLACK, 0.55))
            sub.append(L(wx, hy + dw2, wx - jm, hy + dw2, BLACK, 0.55))
            if not _kitchen_opening_only:
                sub.append(_door_leaf_poly_quad(wx, hy, wx - dw2, hy, th))
                sub.append(
                    f'<path d="M {wx:.2f} {hy+dw2:.2f} A {dw2:.2f} {dw2:.2f} 0 0 0 {wx-dw2:.2f} {hy:.2f}" '
                    f'fill="none" stroke="{BLACK}" stroke-width="0.7"/>'
                )

        def _window_top(cx: float, wy: float, pane: float) -> None:
            sub.append(R(cx - pane / 2, wy - WH / 2, pane, WH, fill=WHITE, stroke="none", sw=0))
            fx0 = cx - pane / 2 + WIN_FRAME_IN
            fy0 = wy - WH / 2 + WIN_FRAME_IN * 0.6
            fw = pane - 2 * WIN_FRAME_IN
            fh = WH - 1.4 * WIN_FRAME_IN
            sub.append(R(fx0, fy0, fw, fh, fill=WHITE, stroke=BLACK, sw=0.55))
            sub.append(L(fx0, fy0 + fh * 0.32, fx0 + fw, fy0 + fh * 0.32, DIM_C, 0.65))
            sub.append(L(cx, fy0 + 0.9, cx, fy0 + fh - 0.9, BLACK, 1.05))
            sub.append(L(fx0, fy0 + fh * 0.68, fx0 + fw, fy0 + fh * 0.68, DIM_C, 0.65))

        def _window_bot(cx: float, wy: float, pane: float) -> None:
            sub.append(R(cx - pane / 2, wy - WH / 2, pane, WH, fill=WHITE, stroke="none", sw=0))
            fx0 = cx - pane / 2 + WIN_FRAME_IN
            fy0 = wy - WH / 2 + WIN_FRAME_IN * 0.6
            fw = pane - 2 * WIN_FRAME_IN
            fh = WH - 1.4 * WIN_FRAME_IN
            sub.append(R(fx0, fy0, fw, fh, fill=WHITE, stroke=BLACK, sw=0.55))
            sub.append(L(fx0, fy0 + fh * 0.32, fx0 + fw, fy0 + fh * 0.32, DIM_C, 0.65))
            sub.append(L(cx, fy0 + 0.9, cx, fy0 + fh - 0.9, BLACK, 1.05))
            sub.append(L(fx0, fy0 + fh * 0.68, fx0 + fw, fy0 + fh * 0.68, DIM_C, 0.65))

        def _window_left(wx: float, cy: float, pane: float) -> None:
            sub.append(R(wx - WH / 2, cy - pane / 2, WH, pane, fill=WHITE, stroke="none", sw=0))
            fx0 = wx - WH / 2 + WIN_FRAME_IN * 0.6
            fy0 = cy - pane / 2 + WIN_FRAME_IN
            fw = WH - 1.4 * WIN_FRAME_IN
            fh = pane - 2 * WIN_FRAME_IN
            sub.append(R(fx0, fy0, fw, fh, fill=WHITE, stroke=BLACK, sw=0.55))
            sub.append(L(fx0 + fw * 0.32, fy0, fx0 + fw * 0.32, fy0 + fh, DIM_C, 0.65))
            sub.append(L(fx0 + 0.9, cy, fx0 + fw - 0.9, cy, BLACK, 1.05))
            sub.append(L(fx0 + fw * 0.68, fy0, fx0 + fw * 0.68, fy0 + fh, DIM_C, 0.65))

        def _window_right(wx: float, cy: float, pane: float) -> None:
            _window_left(wx, cy, pane)

        if kind == "door":
            span = max(0.1, rw - 2 * edge_pad - dw)
            if edge == "top":
                hx = rx + edge_pad + span * u
                hx = max(rx + edge_pad, min(hx, rx + rw - edge_pad - dw))
                _door_top(hx, ry, dw)
            elif edge == "bot":
                hx = rx + edge_pad + span * u
                hx = max(rx + edge_pad, min(hx, rx + rw - edge_pad - dw))
                _door_bot(hx, ry + rh, dw)
            elif edge == "left":
                span = max(0.1, rh - 2 * edge_pad - dw)
                hy = ry + edge_pad + span * u
                hy = max(ry + edge_pad, min(hy, ry + rh - edge_pad - dw))
                _door_left(rx, hy, dw)
            else:
                span = max(0.1, rh - 2 * edge_pad - dw)
                hy = ry + edge_pad + span * u
                hy = max(ry + edge_pad, min(hy, ry + rh - edge_pad - dw))
                _door_right(rx + rw, hy, dw)
        else:
            pane = dw
            span = max(0.1, rw - 2 * edge_pad - pane)
            if edge == "top":
                cx = rx + edge_pad + pane / 2 + span * u
                cx = max(rx + edge_pad + pane / 2, min(cx, rx + rw - edge_pad - pane / 2))
                _window_top(cx, ry, pane)
            elif edge == "bot":
                cx = rx + edge_pad + pane / 2 + span * u
                cx = max(rx + edge_pad + pane / 2, min(cx, rx + rw - edge_pad - pane / 2))
                _window_bot(cx, ry + rh, pane)
            elif edge == "left":
                span = max(0.1, rh - 2 * edge_pad - pane)
                cy = ry + edge_pad + pane / 2 + span * u
                cy = max(ry + edge_pad + pane / 2, min(cy, ry + rh - edge_pad - pane / 2))
                _window_left(rx, cy, pane)
            else:
                span = max(0.1, rh - 2 * edge_pad - pane)
                cy = ry + edge_pad + pane / 2 + span * u
                cy = max(ry + edge_pad + pane / 2, min(cy, ry + rh - edge_pad - pane / 2))
                _window_right(rx + rw, cy, pane)

        frag = "".join(sub)
        if frag:
            body_parts.append(
                f'<g class="editable-placed-opening" data-editable="true" data-op-id="{oid}" '
                f'data-room-id="{room_id_hyphen}" data-kind="{kind}" style="cursor:move">{frag}</g>'
            )

    inner = "".join(body_parts)
    if not inner:
        return ""
    rh_safe = _xml_attr(room_id_hyphen[:48])
    return f'<g class="placed-openings" data-room-id="{rh_safe}">{inner}</g>'


def draw_ventilator(rx, ry, rw, rh, wall) -> str:
    """
    Bathroom ventilator / high-level exhaust opening (reference: small framed opening + bars).
    """
    if wall == "none":
        return ""
    out: List[str] = []
    WH = EXT_WALL
    pane = 16.0
    edge_pad = 20.0
    j = 1.5
    if wall in ("top", "bot"):
        cx = rx + rw * 0.5
        cx = max(rx + edge_pad, min(cx, rx + rw - edge_pad))
        wy = ry if wall == "top" else ry + rh
        out.append(R(cx - pane / 2, wy - WH / 2, pane, WH, fill=WHITE, stroke="none", sw=0))
        fx0 = cx - pane / 2 + WIN_FRAME_IN * 0.5
        fy0 = wy - WH / 2 + WIN_FRAME_IN * 0.45
        fw = pane - WIN_FRAME_IN
        fh = WH - 1.2 * WIN_FRAME_IN
        out.append(R(fx0, fy0, fw, fh, fill=WHITE, stroke=BLACK, sw=0.5))
        out.append(L(cx - pane / 2, wy, cx - pane / 2 + j, wy, BLACK, 0.4))
        out.append(L(cx - pane / 2, wy, cx - pane / 2, wy + (j if wall == "top" else -j), BLACK, 0.4))
        out.append(L(cx + pane / 2, wy, cx + pane / 2 - j, wy, BLACK, 0.4))
        out.append(L(cx + pane / 2, wy, cx + pane / 2, wy + (j if wall == "top" else -j), BLACK, 0.4))
        out.append(L(cx - pane / 2, wy - WH * 0.22, cx + pane / 2, wy - WH * 0.22, BLACK, 0.75))
        out.append(L(cx - pane / 2, wy + WH * 0.22, cx + pane / 2, wy + WH * 0.22, BLACK, 0.75))
    else:
        cy = ry + rh * 0.5
        cy = max(ry + edge_pad, min(cy, ry + rh - edge_pad))
        wx = rx if wall == "left" else rx + rw
        dx = 1 if wall == "left" else -1
        out.append(R(wx - WH / 2, cy - pane / 2, WH, pane, fill=WHITE, stroke="none", sw=0))
        fx0 = wx - WH / 2 + WIN_FRAME_IN * 0.45
        fy0 = cy - pane / 2 + WIN_FRAME_IN * 0.5
        fw = WH - WIN_FRAME_IN
        fh = pane - WIN_FRAME_IN
        out.append(R(fx0, fy0, fw, fh, fill=WHITE, stroke=BLACK, sw=0.5))
        out.append(L(wx, cy - pane / 2, wx, cy - pane / 2 + j, BLACK, 0.4))
        out.append(L(wx, cy - pane / 2, wx + j * dx, cy - pane / 2, BLACK, 0.4))
        out.append(L(wx, cy + pane / 2, wx, cy + pane / 2 - j, BLACK, 0.4))
        out.append(L(wx, cy + pane / 2, wx + j * dx, cy + pane / 2, BLACK, 0.4))
        out.append(L(wx - WH * 0.22 * dx, cy - pane / 2, wx - WH * 0.22 * dx, cy + pane / 2, BLACK, 0.75))
        out.append(L(wx + WH * 0.22 * dx, cy - pane / 2, wx + WH * 0.22 * dx, cy + pane / 2, BLACK, 0.75))
    return "".join(out)


# ─── BATHROOM FIXTURES ───────────────────────────────────────────────────────

def bath_fixtures(x, y, w, h, freestanding_tub=False, double_vanity=False, rain_shower=False):
    """
    Bathroom fixtures — thin outlines only.
    Flags from room notes override pixel-size heuristics:
      freestanding_tub  → draw freestanding soaking tub (luxury 5-fixture)
      double_vanity     → draw twin basins (luxury 5-fixture)
      rain_shower       → draw rain shower head (luxury 5-fixture)
    WC + basic basin always drawn. Extra fixtures added when space or flags warrant.
    """
    out = []; p = 3.0
    # WC — left side. All dimensions guaranteed to fit within room.
    wc_w = min(w * 0.44, 22.0); wc_w = max(wc_w, 10.0)
    wc_h = min(h * 0.42, 30.0); wc_h = max(wc_h, 14.0)
    cis_h = min(wc_h * 0.28, 8.0)
    bowl_h = wc_h - cis_h
    # Cistern rectangle (fits fully within room)
    out.append(R(x+p, y+p, wc_w, cis_h, fill=WHITE, stroke=FRN, sw=FRN_W))
    # Bowl ellipse — rx and ry explicitly bounded to half of box dimensions
    bx2 = x+p; by2 = y+p+cis_h
    rx_ell = wc_w/2 - 0.5    # slightly inset so ellipse stays inside rect
    ry_ell = bowl_h/2 - 0.5  # slightly inset
    rx_ell = max(rx_ell, 2.0); ry_ell = max(ry_ell, 2.0)
    out.append(f'<ellipse cx="{bx2+wc_w/2:.1f}" cy="{by2+bowl_h/2:.1f}" '
               f'rx="{rx_ell:.1f}" ry="{ry_ell:.1f}" '
               f'fill="{WHITE}" stroke="{FRN}" stroke-width="{FRN_W}"/>')
    seat_r = min(rx_ell, ry_ell) * 0.55
    out.append(C(bx2+wc_w/2, by2+bowl_h/2, seat_r, WHITE, FRN, FRN_W*0.6))

    # Basin — right side
    bs = min(w*0.33, 16.0); bs = max(bs, 8.0)
    bsx = x+w-p-bs; bsy = y+p
    out.append(R(bsx, bsy, bs, bs, fill=WHITE, stroke=FRN, sw=FRN_W, rx=bs*0.32))
    out.append(C(bsx+bs/2, bsy+bs/2, bs*0.22, WHITE, FRN, FRN_W*0.7))

    # Luxury 5-fixture: trigger by notes flags OR large room size (>= 70sqft = 5600px²)
    _is_luxury_bath = freestanding_tub or double_vanity or rain_shower or w*h >= 5600
    if _is_luxury_bath:
        # Freestanding bathtub (center-bottom)
        bt_w = min(w*0.45, 46.0); bt_h = min(h*0.28, 30.0)
        btx = x+(w-bt_w)/2; bty = y+h-p-bt_h
        out.append(R(btx, bty, bt_w, bt_h, fill=WHITE, stroke=FRN, sw=FRN_W, rx=8))
        out.append(R(btx+4, bty+4, bt_w-8, bt_h-8, fill=WHITE, stroke=FRN, sw=FRN_W*0.5, rx=6))
        # Rain shower (top-right corner — square with cross-hatch)
        sh_s = min(w*0.28, 24.0)
        shx = x+w-p-sh_s; shy = y+p+max(wc_h,bs)+4
        out.append(R(shx, shy, sh_s, sh_s, fill=WHITE, stroke=FRN, sw=FRN_W))
        out.append(L(shx+sh_s/3, shy, shx+sh_s/3, shy+sh_s, FRN, 0.4))
        out.append(L(shx+sh_s*2/3, shy, shx+sh_s*2/3, shy+sh_s, FRN, 0.4))
        out.append(L(shx, shy+sh_s/3, shx+sh_s, shy+sh_s/3, FRN, 0.4))
        out.append(L(shx, shy+sh_s*2/3, shx+sh_s, shy+sh_s*2/3, FRN, 0.4))
        out.append(C(shx+sh_s/2, shy+sh_s/2, sh_s*0.22, WHITE, FRN, FRN_W))  # drain
        # Double vanity — two basins side by side at top
        dv_w = min(w*0.65, 60.0); dv_h = min(bs+4, 22.0)
        dvx = x+p; dvy = y+p
        out.append(R(dvx, dvy, dv_w, dv_h, fill=WHITE, stroke=FRN, sw=FRN_W))
        # Two basins in the vanity
        bsv = dv_w*0.40
        out.append(C(dvx+dv_w*0.25, dvy+dv_h/2, bsv*0.30, WHITE, FRN, FRN_W*0.7))
        out.append(C(dvx+dv_w*0.75, dvy+dv_h/2, bsv*0.30, WHITE, FRN, FRN_W*0.7))
    elif w*h > 3200:
        # Standard bath: tub only
        bt_w = min(w*0.50, 50.0); bt_h = min(h*0.32, 35.0)
        btx = x+(w-bt_w)/2; bty = y+h-p-bt_h
        out.append(R(btx, bty, bt_w, bt_h, fill=WHITE, stroke=FRN, sw=FRN_W, rx=3))
        out.append(R(btx+3, bty+3, bt_w-6, bt_h-6, fill=WHITE, stroke=FRN, sw=FRN_W*0.5, rx=2))
    return "".join(out)

def wic_fixtures(x, y, w, h):
    """Hanging rods with hanger circles — thin outlines."""
    out = []
    for rod_y in ([y+h*0.30, y+h*0.68] if h > 55 else [y+h*0.42]):
        out.append(L(x+5, rod_y, x+w-5, rod_y, FRN, 1.2))
        nh = max(2, int((w-10)/12))
        for k in range(nh):
            hx = x+5 + (w-10)*k/max(nh-1,1)
            out.append(C(hx, rod_y, 2.8, WHITE, FRN, FRN_W))
    return "".join(out)


# ─── FURNITURE (thin outlines only, no fills) ────────────────────────────────

def furniture(name, x, y, w, h, carved_zones=None, notes=""):
    """
    Notes-driven furniture renderer.
    GPT writes design intent in notes. Keywords here control exactly what gets drawn.
    Priority: notes keywords > category defaults > nothing.
    """
    n = name.lower(); c = cat(n); out = []
    p = 6.0
    nk = notes.lower()

    # ── KEYWORD DETECTION ────────────────────────────────────────────────────
    has_island        = any(k in nk for k in ["island counter", "island"])
    has_u_kitchen     = any(k in nk for k in ["u-shaped", "u shaped", "parallel counter"])
    has_freestanding  = any(k in nk for k in ["freestanding soaking tub", "freestanding", "soaking tub", "bathtub"])
    has_double_vanity = any(k in nk for k in ["double vanity", "his-and-hers", "his and hers"])
    has_rain_shower   = any(k in nk for k in ["rain shower", "rainfall", "rain-shower"])
    has_king_bed      = any(k in nk for k in ["king bed", "king size", "king-size", "king-bed"])
    has_queen_bed     = any(k in nk for k in ["queen bed", "queen size", "queen-size"])
    has_single_bed    = any(k in nk for k in ["single bed", "twin bed", "single-bed"])
    has_8seater       = any(k in nk for k in ["8-seater", "8 seater", "8 seat", "8-seat"])
    has_6seater       = any(k in nk for k in ["6-seater", "6 seater", "6 seat", "6-seat"])
    has_4seater       = any(k in nk for k in ["4-seater", "4 seater", "4 seat"])
    has_l_sofa        = any(k in nk for k in ["l-sofa", "l shaped sofa", "l-shaped sofa", "l sofa"])
    has_study_shelves = any(k in nk for k in ["built-in shelves", "built in shelves", "bookshelf", "bookshelves"])
    has_2car          = any(k in nk for k in ["2-car", "2 car", "innova", "two car", "covered parking 2"])
    has_double_height = any(k in nk for k in ["double height", "double-height", "void"])
    has_luxury        = any(k in nk for k in ["luxury", "ultra", "5-fixture", "premium"])
    has_modular       = any(k in nk for k in ["modular", "high-end", "high end"])
    has_island_seating = has_island and "seating" in nk

    def fr(fx, fy, fw, fh, rx=0):
        return R(fx, fy, fw, fh, fill=WHITE, stroke=FRN, sw=FRN_W, rx=rx)
    def fl(x1, y1, x2, y2, lw=FRN_W, dash=""):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        return f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" stroke="{FRN}" stroke-width="{lw}"{d}/>' 
    def fc(cx, cy, r):
        return C(cx, cy, r, WHITE, FRN, FRN_W)

    # ─── CAR PORCH ────────────────────────────────────────────────────────────
    if c == "car_porch":
        nc = 2 if (w > 180 or has_2car) else 1
        car_w = 18.0; car_h = 42.0
        gap = (w - nc*car_w - p*2) / max(nc+1, 1)
        car_y = y + (h - car_h) / 2
        for i in range(nc):
            cx2 = x + p + gap*(i+1) + car_w*i
            out.append(fr(cx2, car_y, car_w, car_h, rx=2))
            out.append(fl(cx2+2, car_y+car_h*0.18, cx2+car_w-2, car_y+car_h*0.18, 0.5))
            out.append(fl(cx2+2, car_y+car_h*0.82, cx2+car_w-2, car_y+car_h*0.82, 0.5))
            for wx2,wy2 in [(cx2+2,car_y+2),(cx2+car_w-2,car_y+2),(cx2+2,car_y+car_h-2),(cx2+car_w-2,car_y+car_h-2)]:
                out.append(fc(wx2, wy2, 2.0))

    # ─── FOYER ────────────────────────────────────────────────────────────────
    elif c == "foyer":
        if has_double_height:
            out.append(fl(x+p, y+p, x+w-p, y+h-p, 0.7, "10,5"))
            out.append(fl(x+w-p, y+p, x+p, y+h-p, 0.7, "10,5"))
            out.append(T(x+w/2, y+h*0.42, "DOUBLE", 7, "400", GRAY))
            out.append(T(x+w/2, y+h*0.58, "HEIGHT", 7, "400", GRAY))
        else:
            mat_w = min(w*0.50, 45.0); mat_h = min(h*0.30, 28.0)
            out.append(fr(x+(w-mat_w)/2, y+h-p-mat_h, mat_w, mat_h, rx=4))
            out.append(fl(x+(w-mat_w)/2+4, y+h-p-mat_h+4, x+(w+mat_w)/2-4, y+h-p-4, 0.3))

    # ─── SIT OUT / VERANDA ────────────────────────────────────────────────────
    elif c == "sit_out":
        # Chairs are decorative; let pointer events reach walls/openings above in z-order.
        out.append('<g style="pointer-events:none">')
        if w > 60:
            cs = min(16.0, w * 0.26)
            mid = x + w / 2
            out.append(fr(mid - cs - 4, y + p, cs, cs))
            out.append(fr(mid + 4, y + p, cs, cs))
            out.append(C(mid, y + p + cs * 0.5, 6.0, WHITE, FRN, FRN_W))
            out.append(C(mid, y + p + cs * 0.5, 4.0, WHITE, FRN, FRN_W))
        out.append("</g>")

    # ─── LIVING / FORMAL DRAWING ───────────────────────────────────────────────
    elif c in ("living_room", "drawing_room"):
        if has_l_sofa or (has_luxury and w > 140):
            sw = min(w*0.65, 220.0); sd = min(h*0.18, 88.0)
            sx = x+p; sy = y+h-p-sd
            out.append(fr(sx, sy, sw, sd))
            arm_d = min(h*0.36, 110.0); arm_w = sd
            out.append(fr(sx, sy-arm_d, arm_w, arm_d))
            out.append(fr(sx, sy-arm_d, arm_w, arm_w))
            ct_w = sw*0.32; ct_h = sd*1.2
            out.append(fr(sx+arm_w+6, sy-ct_h-3, ct_w, ct_h))
        else:
            sw = min(w*0.62, 200.0); sd = min(h*0.18, 82.0)
            sx = x+p; sy = y+h-p-sd
            out.append(fr(sx, sy, sw, sd))
            out.append(fr(sx, sy-sd*0.88, sd*0.88, sd*0.88))
            ct_w = sw*0.36; ct_h = sd*1.22
            out.append(fr(sx+(sw-ct_w)/2, sy-ct_h-4, ct_w, ct_h))
        tv_w = min(w*0.55 if has_luxury else w*0.48, 95.0 if has_luxury else 82.0)
        out.append(fr(x+(w-tv_w)/2, y+p, tv_w, 9.0))
        out.append(fl(x+(w-tv_w)/2+5, y+p+2, x+(w+tv_w)/2-5, y+p+7, 0.4))

    # ─── DINING ROOM ─────────────────────────────────────────────────────────
    elif c == "dining_room":
        area_sqft = (w/SCALE)*(h/SCALE)
        if has_8seater or area_sqft > 155:
            tw = min(w*0.52, 240.0); th = min(h*0.52, 100.0)
        elif has_6seater or area_sqft > 110:
            tw = min(w*0.50, 210.0); th = min(h*0.50, 95.0)
        elif has_4seater or area_sqft <= 90:
            tw = min(w*0.46, 160.0); th = min(h*0.46, 80.0)
        else:
            tw = min(w*0.50, 180.0); th = min(h*0.50, 90.0)
        tx = x+(w-tw)/2; ty = y+(h-th)/2
        out.append(fr(tx, ty, tw, th))
        cw2 = 11.0; cd = 7.0; gap = 1.0
        n_top = max(2, int(tw/16))
        for i in range(n_top):
            cx2 = tx + tw*(i+0.5)/n_top - cw2/2
            out.append(fr(cx2, ty-cd-gap, cw2, cd, rx=1))
            out.append(fr(cx2, ty+th+gap,  cw2, cd, rx=1))
        n_side = max(1, int(th/20))
        for j in range(n_side):
            cy2 = ty + th*(j+0.5)/n_side - cd/2
            out.append(fr(tx-cw2-gap, cy2, cw2, cd, rx=1))
            out.append(fr(tx+tw+gap,  cy2, cw2, cd, rx=1))

    # ─── KITCHEN ─────────────────────────────────────────────────────────────
    elif c in ("kitchen", "wet_kitchen", "dry_kitchen"):
        cd = min(17.0, h*0.22)
        out.append(fr(x+p, y+p, w-p*2, cd))
        sk_w = max(min(30.0, (w-p*2)*0.30), 18.0)
        sk_x = x+w-p-sk_w-3
        out.append(fr(sk_x,           y+p+2, sk_w*0.46, cd-4))
        out.append(fr(sk_x+sk_w*0.54, y+p+2, sk_w*0.46, cd-4))
        out.append(C(sk_x+sk_w*0.50, y+p+2, 2.0, WHITE, FRN, FRN_W))
        br = min(4.5, cd*0.26)
        for bxo,byo in [(0.14,0.30),(0.28,0.30),(0.14,0.70),(0.28,0.70)]:
            out.append(fc(x+p+6+(w-p*2)*bxo, y+p+cd*byo, br))
            out.append(C(x+p+6+(w-p*2)*bxo, y+p+cd*byo, br*0.40, WHITE, FRN, 0.4))
        if has_u_kitchen:
            out.append(fr(x+w-p-cd, y+p+cd, cd, h-p*2-cd))
            out.append(fr(x+p, y+h-p-cd, w-p*2, cd))
        else:
            out.append(fr(x+w-p-cd, y+p+cd, cd, h-p*2-cd))
        if has_island:
            iw = min(w*0.42, 58.0); ih = min(h*0.15, 20.0)
            ix = x + (w-iw)/2; iy = y + h*0.54
            out.append(fr(ix, iy, iw, ih))
            if has_island_seating and iw > 30:
                stool_r = 4.0; n_s = max(2, int(iw/14))
                for si in range(n_s):
                    sx2 = ix + iw*(si+0.5)/n_s
                    out.append(fc(sx2, iy+ih+stool_r+2, stool_r))

    # ─── BEDROOM ─────────────────────────────────────────────────────────────
    elif is_bedroom_cat(c):
        # Carved zone offset (bath/WIC at rear-right or rear-left)
        carved_right = 0.0; carved_left = 0.0; carved_bot = 0.0
        if carved_zones:
            for (czx, czy, czw, czh) in carved_zones:
                rel_x = czx - x
                if rel_x > w * 0.5:
                    carved_right = max(carved_right, w - rel_x)
                else:
                    carved_left = max(carved_left, rel_x + czw)
                rel_y = czy - y
                if rel_y > h * 0.5:
                    carved_bot = max(carved_bot, h - rel_y)

        safe_w = w - carved_right - carved_left - p * 2
        safe_h = h - carved_bot - p * 2
        bx_off = x + p + carved_left
        is_master = c == "master_bedroom"

        # Compact bedroom fallback: keep furniture legible and non-overlapping.
        # This preserves room connectivity/alignment while avoiding stretched icons.
        if safe_w < 34 or safe_h < 22:
            cbw = max(min(safe_w * 0.72, 42.0), 18.0)
            cbh = max(min(safe_h * 0.78, 26.0), 10.0)
            cbx = bx_off + (safe_w - cbw) / 2
            cby = y + p + max((safe_h - cbh) / 2, 1.0)
            out.append(fr(cbx, cby, cbw, cbh))
            hb_h = max(min(cbh * 0.18, 6.0), 2.0)
            out.append(fr(cbx, cby, cbw, hb_h))
            # Skip pillows/nightstands/wardrobe in very compact rooms to avoid overlap.
            return "".join(out)

        carved_compact = bool(carved_zones) and (safe_h < 40 or safe_w < 62)

        # Bed size by type
        if has_single_bed:
            bw2 = min(safe_w * 0.55, 55.0); bh2 = min(safe_h * 0.48, 65.0)
        elif has_king_bed or (is_master and has_luxury):
            bw2 = min(safe_w * 0.88, 95.0); bh2 = min(safe_h * 0.54, 88.0)
        elif has_queen_bed or is_master:
            bw2 = min(safe_w * 0.85, 85.0); bh2 = min(safe_h * 0.52, 78.0)
        else:
            bw2 = min(safe_w * 0.82, 72.0); bh2 = min(safe_h * 0.50, 68.0)
        if carved_compact:
            bw2 = min(bw2, safe_w * 0.78)
            bh2 = min(bh2, safe_h * 0.42)

        # Bed: headboard against top wall (y+p), centered horizontally
        bx2 = bx_off + (safe_w - bw2) / 2
        by2 = y + p + 4  # small gap from top wall
        out.append(fr(bx2, by2, bw2, bh2))
        # Headboard bar
        hb_h = min(bh2 * 0.14, 12.0)
        out.append(fr(bx2, by2, bw2, hb_h))
        # Pillows
        pw2 = bw2 * 0.35; ph2 = bh2 * 0.18
        if is_master:
            out.append(fr(bx2 + bw2 * 0.06, by2 + hb_h + 3, pw2 * 0.82, ph2))
            out.append(fr(bx2 + bw2 * 0.58, by2 + hb_h + 3, pw2 * 0.82, ph2))
        else:
            out.append(fr(bx2 + (bw2 - pw2) / 2, by2 + hb_h + 3, pw2, ph2))
        # Nightstand (right of bed)
        ns = 11.0
        if (not carved_compact) and bx2 + bw2 + 4 + ns < x + w - p - carved_right:
            out.append(fr(bx2 + bw2 + 4, by2 + bh2 * 0.3, ns, ns))
        # Second nightstand (left of bed for master)
        if (not carved_compact) and is_master and bx2 - 4 - ns > x + p + carved_left:
            out.append(fr(bx2 - 4 - ns, by2 + bh2 * 0.3, ns, ns))
        # Wardrobe at bottom (non-master rooms — master has WIC)
        if not is_master:
            safe_bot = h - p - carved_bot - (by2 - y + bh2) - 8
            if safe_bot > 12:
                wd_h = min(14.0, safe_bot)
                wd_w = min(safe_w, w - p * 2 - carved_right - carved_left)
                if wd_w > 20:
                    out.append(fr(bx_off, y + h - p - carved_bot - wd_h, wd_w, wd_h))
                    n_div = max(2, int(wd_w / 26))
                    for k in range(1, n_div):
                        px3 = bx_off + wd_w * k / n_div
                        out.append(fl(px3, y + h - p - carved_bot - wd_h, px3, y + h - p - carved_bot, 0.4))

    # ─── STANDALONE BATHROOM ────────────────────────────────────────────────
    elif c in ("bathroom","common_bathroom","guest_powder_room") and not is_carved(name):
        out.append(bath_fixtures(x, y, w, h,
            freestanding_tub=has_freestanding,
            double_vanity=has_double_vanity,
            rain_shower=has_rain_shower))

    # ─── HOME OFFICE ─────────────────────────────────────────────────────────
    elif c == "home_office":
        dw2 = min(w*0.68, 105.0); dd = min(h*0.22, 22.0)
        out.append(fr(x+p, y+p, dw2, dd))
        out.append(fr(x+p+dw2*0.25, y+p+3, min(dw2*0.38, 36.0), 7.0))
        out.append(fr(x+p+dw2*0.22, y+p+11, min(dw2*0.32, 28.0), 6.0))
        if has_study_shelves:
            sh_w = min(w*0.22, 22.0)
            sh_h = h - p*2 - dd - 6
            out.append(fr(x+p, y+p+dd+6, sh_w, sh_h))
            n_s = max(2, int(sh_h/12))
            for _s in range(n_s):
                out.append(fl(x+p, y+p+dd+6+_s*(sh_h/n_s), x+p+sh_w, y+p+dd+6+_s*(sh_h/n_s), 0.3))
        ch_r = min(10.0, h*0.09)
        out.append(C(x+p+dw2/3, y+p+dd+ch_r+3, ch_r, WHITE, FRN, 0.6))

    # ─── POOJA / PRAYER ROOM ─────────────────────────────────────────────────
    elif c == "pooja_room":
        aw = min(w*0.52, 28.0); ah = min(h*0.42, 24.0)
        ax = x+(w-aw)/2; ay = y+p; r_a = aw/2
        out.append(f'<path d="M {ax:.2f} {ay+ah:.2f} L {ax:.2f} {ay+r_a:.2f} '
                   f'A {r_a:.2f} {r_a:.2f} 0 0 1 {ax+aw:.2f} {ay+r_a:.2f} '
                   f'L {ax+aw:.2f} {ay+ah:.2f} Z" fill="{WHITE}" stroke="{FRN}" stroke-width="0.8"/>')
        if w > 30 and h > 38:
            out.append(f'<text x="{x+w/2:.2f}" y="{y+h*0.64:.2f}" font-size="{min(13,int(w*0.25))}" '
                       f'text-anchor="middle" fill="{FRN}" opacity="0.55" font-family="serif">ॐ</text>')

    # ─── FAMILY LOUNGE ────────────────────────────────────────────────────────
    elif c == "family_lounge":
        sw2 = min(w*0.55, 130.0); sd2 = min(h*0.22, 28.0)
        out.append(fr(x+(w-sw2)/2, y+p, sw2, sd2))
        out.append(fr(x+(w-sw2)/2, y+p, sd2*0.50, sd2))
        out.append(fr(x+(w+sw2)/2-sd2*0.50, y+p, sd2*0.50, sd2))
        ct_w = sw2*0.32; ct_h = sd2*1.1
        out.append(fr(x+(w-ct_w)/2, y+p+sd2+5, ct_w, ct_h))

    # ─── SERVANT QUARTERS ────────────────────────────────────────────────────
    elif c == "servant_quarters":
        bw3 = min(w*0.55, 52.0); bh3 = min(h*0.50, 58.0)
        out.append(fr(x+(w-bw3)/2, y+p, bw3, bh3))
        out.append(fr(x+(w-bw3)/2, y+p, bw3, min(bh3*0.15, 10.0)))
        tbl = 11.0
        if x+(w-bw3)/2+bw3+4+tbl < x+w-p:
            out.append(fr(x+(w-bw3)/2+bw3+4, y+p+bh3/2-tbl/2, tbl, tbl))

    # ─── UTILITY ROOM ────────────────────────────────────────────────────────
    elif c == "utility_room":
        if w > 50:
            mw = min(w*0.38, 34.0); mh = min(h*0.52, 38.0)
            mx = x+p; my = y+(h-mh)/2
            out.append(fr(mx, my, mw, mh, rx=3))
            out.append(C(mx+mw/2, my+mh/2, mw*0.32, WHITE, FRN, FRN_W))
            out.append(C(mx+mw/2, my+mh/2, mw*0.15, WHITE, FRN, 0.4))
            if x+p+mw+6+mw < x+w-p:
                mx2 = mx+mw+6
                out.append(fr(mx2, my, mw, mh, rx=3))
                out.append(C(mx2+mw/2, my+mh/2, mw*0.32, WHITE, FRN, FRN_W))
                out.append(C(mx2+mw/2, my+mh/2, mw*0.15, WHITE, FRN, 0.4))

    # ─── STORE ROOM ──────────────────────────────────────────────────────────
    elif c == "store_room":
        sh_w = w-p*2; n_shelves = max(2, int((h-p*2)/16))
        for _s in range(n_shelves):
            sy2 = y+p + _s*(h-p*2)/n_shelves
            out.append(fl(x+p, sy2, x+p+sh_w, sy2, 0.5))
            out.append(fr(x+p, sy2, sh_w, min(8.0,(h-p*2)/n_shelves-2)))

    return "".join(out)

# ─── STAIRCASE ───────────────────────────────────────────────────────────────

def draw_staircase(x, y, w, h, fl):
    """
    Architecturally correct staircase symbol.
    Tread spacing: 8px = 80mm at 1:100 (NBC max 190mm).
    UP arrow: arrowhead points in direction of travel (upward = negative y).
    Break line: zigzag freehand line at mid-point.
    """
    out = []
    if fl == 0:
        # Treads at 8px intervals (correct NBC scale)
        tread_sp = 8.0
        n_t = max(8, int(h / tread_sp))
        mid = y + h / 2
        # Lower flight (bottom to mid)
        n_lower = int((mid - y) / tread_sp)
        for i in range(n_lower + 1):
            ty = y + i * tread_sp
            if ty <= mid:
                out.append(L(x, ty, x+w, ty, GRAY, 0.7))
        # Break / landing line
        out.append(L(x, mid, x+w, mid, BLACK, 1.8))
        # Zigzag break symbol (3-point freehand)
        zx = x + w*0.5
        out.append(f'<polyline points="{x+2:.1f},{mid:.1f} {zx-6:.1f},{mid-5:.1f} {zx+6:.1f},{mid+5:.1f} {x+w-2:.1f},{mid:.1f}" fill="none" stroke="{GRAY}" stroke-width="1.0"/>')
        # Upper flight (mid to top)
        n_upper = int((y + h - mid) / tread_sp)
        for i in range(n_upper + 1):
            ty = mid + i * tread_sp
            if ty <= y + h:
                out.append(L(x, ty, x+w, ty, GRAY, 0.7))
        # UP arrow — starts at bottom, points UP (arrowhead at top = lower y value)
        ax = x + w*0.5
        arr_base = y + h*0.72   # arrow base (lower)
        arr_tip  = y + h*0.30   # arrow tip (upper) — lower y = visually up
        out.append(L(ax, arr_base, ax, arr_tip, BLACK, 1.2))
        # Arrowhead at TIP (upper end) — points upward
        out.append(f'<polygon points="{ax:.1f},{arr_tip:.1f} {ax-3:.1f},{arr_tip+7:.1f} {ax+3:.1f},{arr_tip+7:.1f}" fill="{BLACK}"/>')
        out.append(T(ax, arr_base + 9, "UP", 7, "700", BLACK))
    else:
        # Upper floor: cross-hatch void + DN arrow
        tread_sp = 8.0; cid = f"sv-{int(x)}-{int(y)}-{int(w)}"
        ls = [L(x+i*tread_sp, y, x+i*tread_sp, y+h, GRAY, 0.6)
              for i in range(int(w/tread_sp)+2)]
        out.append(f'<clipPath id="{cid}"><rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}"/></clipPath>')
        out.append(f'<g clip-path="url(#{cid})" opacity="0.55">{"".join(ls)}</g>')
        # DN arrow — starts at top, points DOWN
        ax = x + w*0.5
        arr_base = y + h*0.28   # arrow base (upper)
        arr_tip  = y + h*0.70   # arrow tip (lower) — higher y = visually down
        out.append(L(ax, arr_base, ax, arr_tip, BLACK, 1.2))
        out.append(f'<polygon points="{ax:.1f},{arr_tip:.1f} {ax-3:.1f},{arr_tip-7:.1f} {ax+3:.1f},{arr_tip-7:.1f}" fill="{BLACK}"/>')
        out.append(T(ax, arr_base - 8, "DN", 7, "700", BLACK))
    return "".join(out)

def draw_terrace(x, y, w, h):
    """Terrace: light diagonal hatch + parapet tick marks on all 4 sides."""
    step = 18; cid = f"tc-{int(x)}-{int(y)}-{int(w)}"
    ls = [L(x+i*step,y,x+i*step+h,y+h,GRAY,0.4)
          for i in range(int(-(w+h)/step), int((w+h)/step)+2)]
    out = [f'<clipPath id="{cid}"><rect x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="{h:.2f}"/></clipPath>',
           f'<g clip-path="url(#{cid})" opacity="0.30">{"".join(ls)}</g>']
    # Parapet tick marks (architectural convention for open terrace)
    tick = 5.0; tick_step = 14.0
    def ticks_h(x1, y1, x2, dy):
        n = max(1, int((x2-x1)/tick_step))
        return [L(x1+(x2-x1)*k/n, y1, x1+(x2-x1)*k/n, y1+dy, BLACK, 0.8)
                for k in range(n+1)]
    def ticks_v(x1, y1, y2, dx):
        n = max(1, int((y2-y1)/tick_step))
        return [L(x1, y1+(y2-y1)*k/n, x1+dx, y1+(y2-y1)*k/n, BLACK, 0.8)
                for k in range(n+1)]
    out += ticks_h(x, y,   x+w, tick)      # top edge ticks
    out += ticks_h(x, y+h, x+w, -tick)     # bottom edge ticks
    out += ticks_v(x,   y, y+h, tick)      # left edge ticks
    out += ticks_v(x+w, y, y+h, -tick)     # right edge ticks
    return "".join(out)


# ─── FONT SIZE ───────────────────────────────────────────────────────────────

def label_fs(w, h, lbl):
    lng = len(max(lbl.split(), key=len)) if lbl.split() else len(lbl)
    bw = int((w-12)/max(lng*5.0,1)*10)
    bh = int(h*0.15)
    return max(min(bw, bh, 10), 6)


# ─── DRAW ONE ROOM ───────────────────────────────────────────────────────────

def vastu_zone(cat_name, rx, ry, rw, rh, bx, by, bw, bh, facing="east"):
    """
    Return the Vastu zone name for a room based on its position in the plan.
    For east-facing: top=east, left=north, bottom=west, right=south.
    Zones: NE, N, NW, E, CENTER, W, SE, S, SW
    """
    # Normalize position within built-up (0=top/left, 1=bottom/right)
    rel_x = (rx - bx) / max(bw, 1)
    rel_y = (ry - by) / max(bh, 1)
    
    if rel_x < 0.33:   hzone = "LEFT"
    elif rel_x < 0.67: hzone = "CENTER"
    else:               hzone = "RIGHT"
    
    if rel_y < 0.33:   vzone = "TOP"
    elif rel_y < 0.67: vzone = "MID"
    else:               vzone = "BOTTOM"
    
    # Map to compass for east-facing (top=E, left=N, bottom=W, right=S)
    ZONE_MAP = {
        ("LEFT","TOP"):    "NE", ("CENTER","TOP"):    "E",  ("RIGHT","TOP"):    "SE",
        ("LEFT","MID"):    "N",  ("CENTER","MID"):    "C",  ("RIGHT","MID"):    "S",
        ("LEFT","BOTTOM"): "NW", ("CENTER","BOTTOM"): "W",  ("RIGHT","BOTTOM"): "SW",
    }
    return ZONE_MAP.get((hzone, vzone), "C")


def _furniture_transform_matrix(room: Dict[str, Any], rx: float, ry: float, rw: float, rh: float) -> str:
    """SVG transform for procedural furniture: nudge (tx,ty) + uniform scale about room centre."""
    ft = room.get("furniture_transform")
    if not isinstance(ft, dict):
        ft = {}
    try:
        tx = float(ft.get("tx") or 0)
        ty = float(ft.get("ty") or 0)
        sc = float(ft.get("s") or 1)
    except (TypeError, ValueError):
        tx, ty, sc = 0.0, 0.0, 1.0
    sc = max(0.35, min(sc, 2.5))
    rcx = rx + rw / 2.0
    rcy = ry + rh / 2.0
    return (
        f"translate({tx:.2f},{ty:.2f}) translate({rcx:.2f},{rcy:.2f}) "
        f"scale({sc:.4f}) translate({-rcx:.2f},{-rcy:.2f})"
    )


def _furniture_editor_stack(
    room: Dict[str, Any],
    room_id_hyphen: str,
    rx: float,
    ry: float,
    rw: float,
    rh: float,
    inner: str,
) -> str:
    """Wrap furniture SVG for Phase A editor: move + scale as one layer (layout: furniture_transform)."""
    inner = (inner or "").strip()
    if not inner:
        return ""
    tr = _furniture_transform_matrix(room, rx, ry, rw, rh)
    hid = _xml_attr(room_id_hyphen[:64])
    return (
        f'<g class="editable-furniture-stack" data-editable="true" data-room-id="{hid}">'
        f'<g class="editable-furniture-layer" transform="{tr}">{inner}</g>'
        f'<rect class="furniture-resize-handle" x="{rx + rw - 14:.2f}" y="{ry + rh - 14:.2f}" width="12" height="12" '
        f'fill="#5A6B4A" fill-opacity="0.35" stroke="{BLACK}" stroke-width="0.55" style="cursor:nwse-resize"/>'
        f"</g>"
    )


def _room_resize_handles(
    rx: float, ry: float, rw: float, rh: float, *, room_id_hyphen: Optional[str] = None
) -> str:
    """
    Phase A editor: corner + edge hit targets to stretch room rects (layout width/height in px).

    When ``room_id_hyphen`` is set, each handle carries ``data-room-id`` so the client can resolve
    the room after we paint this group in a global overlay (above later rooms / corridor knockouts).

    Full-length **edge bars** (inset from corners) give reliable horizontal-only / vertical-only
    drags on every room that is large enough for corners; the old mid-edge squares only appeared
    when the opposite dimension exceeded ~52px, which hid axis handles on many narrow/tall slabs.
    """
    if rw < 22.0 or rh < 22.0:
        return ""
    hsz = 10.0
    pad = 1.5
    bar_t = 12.0
    fill_c = "#8B7355"
    rid = f' data-room-id="{_xml_attr(room_id_hyphen)}"' if room_id_hyphen else ""
    out = ['<g class="room-resize-ui" style="pointer-events:all">']
    # Inset from corners so edge bars do not steal corner-handle hits (nw/ne/sw/se).
    ix = max(6.0, min(15.0, rw * 0.22, (rw - 8.0) / 2.0))
    iy = max(6.0, min(15.0, rh * 0.22, (rh - 8.0) / 2.0))
    bar_h = max(8.0, rh - 2.0 * iy)
    bar_w = max(8.0, rw - 2.0 * ix)
    edge_attrs = f'fill="{fill_c}" fill-opacity="0.22" stroke="{BLACK}" stroke-width="0.4"'
    out.append(
        f'<rect class="room-resize-handle" data-handle="w"{rid} x="{rx - 3.0:.2f}" y="{ry + iy:.2f}" '
        f'width="{bar_t:.2f}" height="{bar_h:.2f}" {edge_attrs} style="cursor:ew-resize"/>'
    )
    out.append(
        f'<rect class="room-resize-handle" data-handle="e"{rid} x="{rx + rw - bar_t + 3.0:.2f}" y="{ry + iy:.2f}" '
        f'width="{bar_t:.2f}" height="{bar_h:.2f}" {edge_attrs} style="cursor:ew-resize"/>'
    )
    out.append(
        f'<rect class="room-resize-handle" data-handle="n"{rid} x="{rx + ix:.2f}" y="{ry - 3.0:.2f}" '
        f'width="{bar_w:.2f}" height="{bar_t:.2f}" {edge_attrs} style="cursor:ns-resize"/>'
    )
    out.append(
        f'<rect class="room-resize-handle" data-handle="s"{rid} x="{rx + ix:.2f}" y="{ry + rh - bar_t + 3.0:.2f}" '
        f'width="{bar_w:.2f}" height="{bar_t:.2f}" {edge_attrs} style="cursor:ns-resize"/>'
    )
    corners = (
        (rx + pad, ry + pad, "nw", "nwse-resize"),
        (rx + rw - pad - hsz, ry + pad, "ne", "nesw-resize"),
        (rx + pad, ry + rh - pad - hsz, "sw", "nesw-resize"),
        (rx + rw - pad - hsz, ry + rh - pad - hsz, "se", "nwse-resize"),
    )
    for cx, cy, hid, cur in corners:
        out.append(
            f'<rect class="room-resize-handle" data-handle="{hid}"{rid} x="{cx:.2f}" y="{cy:.2f}" '
            f'width="{hsz:.2f}" height="{hsz:.2f}" fill="{fill_c}" fill-opacity="0.42" stroke="{BLACK}" '
            f'stroke-width="0.45" rx="1.2" style="cursor:{cur}"/>'
        )
    out.append("</g>")
    return "".join(out)


def _all_room_resize_handles_overlay(rooms: List[Dict[str, Any]], ox: float, oy: float) -> str:
    """One layer above all room bodies + spine overlays so resize targets stay clickable."""
    parts: List[str] = []
    for r in rooms:
        rn = str(r.get("name", "")).lower()
        if r.get("__is_carved", False) or is_carved(rn):
            continue
        rx = float(r["x"]) + ox
        ry = float(r["y"]) + oy
        rw = float(r["width"])
        rh = float(r["height"])
        rid_h = str(r.get("name", "")).replace("_", "-").lower()[:120]
        frag = _room_resize_handles(rx, ry, rw, rh, room_id_hyphen=rid_h)
        if frag:
            parts.append(frag)
    if not parts:
        return ""
    return '<g class="room-resize-handles-overlay">' + "".join(parts) + "</g>"


def draw_room(room, ox, oy, fl, bx, by, bw, bh, carved_children=None):
    rx = float(room["x"]) + ox;  ry = float(room["y"]) + oy
    rw = float(room["width"]);   rh = float(room["height"])
    wft = float(room.get("width_ft",  rw/SCALE))
    hft = float(room.get("depth_ft",  rh/SCALE))
    area = float(room.get("area_sqft", wft*hft))
    name = str(room.get("name", ""));  n = name.lower()
    c = cat(n)

    if room.get("__is_carved", False) or is_carved(n):
        return ""  # Rendered by parent

    # Treat staircase_landing as stair continuation (not a void marker).
    is_st = ("staircase" in n and "landing" not in n) or ("staircase_landing" in n)
    is_vd = False
    is_tr = "terrace" in n or "balcony" in n
    is_co = "corridor" in n or "passage" in n
    is_ps = n in ("service_passage", "rear_passage") or c == "passage"
    lb = room_label(name)
    rid = name.replace("_", "-")
    cid = f"f{fl}-c-{rid}-{int(rx)}"

    ext_top, ext_bot, ext_left, ext_right = ext_walls_of(rx,ry,rw,rh, bx,by,bw,bh, ox,oy)

    parts = [clip_rect(cid, rx, ry, rw, rh, 2)]

    # White room interior
    # ── Room tints — light color per room type ───────────────────────────────
    _ROOM_TINTS = {
        "master_bedroom":  "#EEF2FA", "bedroom":       "#EEF2FA",
        "parents_bedroom": "#EEF2FA", "guest_bedroom": "#EEF2FA",
        "living_room":     "#FEFDF5", "drawing_room":  "#FEFDF5",
        "dining_room":     "#FEFDF5",
        "family_lounge":   "#FEFDF5", "home_office":   "#F5F0FB",
        "kitchen":         "#F0FAF3", "wet_kitchen":   "#F0FAF3",
        "dry_kitchen":     "#F0FAF3", "bathroom":      "#EEF8FB",
        "common_bathroom": "#EEF8FB", "guest_powder_room": "#EEF8FB",
        "corridor":        "#F8F8F5", "foyer":         "#FEFAEE",
        "pooja_room":      "#FDF7EE", "car_porch":     "#F5F5EE",
        "terrace":         "#F0FAF0", "sit_out":       "#F0FAF0",
        "servant_quarters":"#F5F5F0", "utility_room":  "#F5F5F0",
        "store_room":      "#F2F2F0", "staircase":     "#F5F5F0",
        "walk_in_wardrobe":"#EEF2FA",
    }
    _room_fill = _ROOM_TINTS.get(c, WHITE)
    parts.append(R(rx, ry, rw, rh, fill=_room_fill, stroke="none", sw=0))

    # Staircase / terrace overlays
    if is_st:
        parts.append(draw_staircase(rx, ry, rw, rh, fl))
    elif is_tr:
        parts.append(draw_terrace(rx, ry, rw, rh))

    # ── SUB-ZONES (attached bath/WIC) ────────────────────────────────────────
    carved_zones = []
    if carved_children:
        for cr in carved_children:
            cx = float(cr["x"])+ox; cy = float(cr["y"])+oy
            cw2 = float(cr["width"]); ch2 = float(cr["height"])
            cn = str(cr.get("name","")).lower()
            area_cr = round(float(cr.get("area_sqft",(cw2/SCALE)*(ch2/SCALE))))
            carved_zones.append((cx, cy, cw2, ch2))

            # Sub-zone white background
            parts.append(R(cx, cy, cw2, ch2, fill=WHITE, stroke="none", sw=0))

            # Interior dividing walls (thick black lines on interior sides)
            eps = 10.0
            on_right  = abs((cx+cw2)-(rx+rw)) < eps
            on_left   = abs(cx-rx)            < eps
            on_top    = abs(cy-ry)            < eps
            on_bottom = abs((cy+ch2)-(ry+rh)) < eps

            # Draw interior walls as filled black rectangles
            if not on_left:
                parts.append(R(cx-INT_WALL/2, cy, INT_WALL, ch2, fill=BLACK, stroke="none", sw=0))
            if not on_right:
                parts.append(R(cx+cw2-INT_WALL/2, cy, INT_WALL, ch2, fill=BLACK, stroke="none", sw=0))
            if not on_top:
                parts.append(R(cx, cy-INT_WALL/2, cw2, INT_WALL, fill=BLACK, stroke="none", sw=0))
            if not on_bottom:
                parts.append(R(cx, cy+ch2-INT_WALL/2, cw2, INT_WALL, fill=BLACK, stroke="none", sw=0))

            # Fixtures
            if "wardrobe" in cn or "walk_in" in cn:
                parts.append(wic_fixtures(cx, cy, cw2, ch2))
                # WIC door: left interior wall, hinge at top, arc sweeps INTO WIC (rightward)
                # Door leaf: vertical along wall. Arc: from bottom of leaf to (cx+dw,dy0)
                dw_wic = 25.0   # 2.5ft walk-in door
                dy0 = cy + ch2 * 0.30
                parts.append(R(cx - INT_WALL, dy0, INT_WALL * 2.5, dw_wic, WHITE, "none", 0))
                parts.append(L(cx, dy0, cx, dy0 + dw_wic, BLACK, 0.8))
                parts.append(f'<path d="M {cx:.1f} {dy0+dw_wic:.1f} A {dw_wic:.1f} {dw_wic:.1f} 0 0 0 {cx+dw_wic:.1f} {dy0:.1f}" fill="none" stroke="{BLACK}" stroke-width="0.7"/>')
            else:
                # Read notes from CHILD (bathroom), not parent (bedroom)
                # Luxury fixture notes are on the bathroom room object
                # Use `or` so empty string falls through to parent notes (not just None)
                _bath_notes = str(cr.get("notes") or room.get("notes", "")).lower()
                parts.append(bath_fixtures(cx, cy, cw2, ch2,
                    freestanding_tub=any(k in _bath_notes for k in ["freestanding","soaking tub","bathtub"]),
                    double_vanity=any(k in _bath_notes for k in ["double vanity","his-and-hers"]),
                    rain_shower=any(k in _bath_notes for k in ["rain shower","rainfall"])))

                # Attached master bathroom should never appear sealed on any floor.
                # Add a proper white opening patch + leaf + swing on the bedroom seam.
                if c == "master_bedroom" and "bathroom" in cn:
                    dw = max(18.0, min(24.0, min(cw2, ch2) * 0.45))
                    jm = JAMB_TICK * 0.8
                    th = DOOR_LEAF_THK

                    if not on_left:
                        wx = cx
                        hy = cy + (ch2 - dw) * 0.5
                        parts.append(R(wx - INT_WALL, hy, INT_WALL * 2.5, dw, WHITE, "none", 0))
                        parts.append(L(wx, hy, wx + jm, hy, BLACK, 0.55))
                        parts.append(L(wx, hy, wx, hy + jm, BLACK, 0.55))
                        parts.append(L(wx, hy + dw, wx + jm, hy + dw, BLACK, 0.55))
                        parts.append(L(wx, hy + dw, wx, hy + dw - jm, BLACK, 0.55))
                        parts.append(_door_leaf_poly_quad(wx, hy, wx + dw, hy, th))
                        parts.append(
                            f'<path d="M {wx:.2f} {hy+dw:.2f} A {dw:.2f} {dw:.2f} 0 0 1 {wx+dw:.2f} {hy:.2f}" '
                            f'fill="none" stroke="{BLACK}" stroke-width="0.7"/>'
                        )
                    elif not on_right:
                        wx = cx + cw2
                        hy = cy + (ch2 - dw) * 0.5
                        parts.append(R(wx - INT_WALL * 1.5, hy, INT_WALL * 2.5, dw, WHITE, "none", 0))
                        parts.append(L(wx, hy, wx - jm, hy, BLACK, 0.55))
                        parts.append(L(wx, hy, wx, hy + jm, BLACK, 0.55))
                        parts.append(L(wx, hy + dw, wx - jm, hy + dw, BLACK, 0.55))
                        parts.append(L(wx, hy + dw, wx, hy + dw - jm, BLACK, 0.55))
                        parts.append(_door_leaf_poly_quad(wx, hy, wx - dw, hy, th))
                        parts.append(
                            f'<path d="M {wx:.2f} {hy+dw:.2f} A {dw:.2f} {dw:.2f} 0 0 0 {wx-dw:.2f} {hy:.2f}" '
                            f'fill="none" stroke="{BLACK}" stroke-width="0.7"/>'
                        )
                    elif not on_top:
                        wy = cy
                        hx = cx + (cw2 - dw) * 0.5
                        parts.append(R(hx, wy - INT_WALL, dw, INT_WALL * 2.5, WHITE, "none", 0))
                        parts.append(L(hx, wy, hx + jm, wy, BLACK, 0.55))
                        parts.append(L(hx, wy, hx, wy + jm, BLACK, 0.55))
                        parts.append(L(hx + dw, wy, hx + dw - jm, wy, BLACK, 0.55))
                        parts.append(L(hx + dw, wy, hx + dw, wy + jm, BLACK, 0.55))
                        parts.append(_door_leaf_poly_quad(hx, wy, hx, wy + dw, th))
                        parts.append(
                            f'<path d="M {hx:.2f} {wy+dw:.2f} A {dw:.2f} {dw:.2f} 0 0 1 {hx+dw:.2f} {wy:.2f}" '
                            f'fill="none" stroke="{BLACK}" stroke-width="0.7"/>'
                        )
                    elif not on_bottom:
                        wy = cy + ch2
                        hx = cx + (cw2 - dw) * 0.5
                        parts.append(R(hx, wy - INT_WALL * 1.5, dw, INT_WALL * 2.5, WHITE, "none", 0))
                        parts.append(L(hx, wy, hx + jm, wy, BLACK, 0.55))
                        parts.append(L(hx, wy, hx, wy - jm, BLACK, 0.55))
                        parts.append(L(hx + dw, wy, hx + dw - jm, wy, BLACK, 0.55))
                        parts.append(L(hx + dw, wy, hx + dw, wy - jm, BLACK, 0.55))
                        parts.append(_door_leaf_poly_quad(hx, wy, hx, wy - dw, th))
                        parts.append(
                            f'<path d="M {hx:.2f} {wy-dw:.2f} A {dw:.2f} {dw:.2f} 0 0 0 {hx+dw:.2f} {wy:.2f}" '
                            f'fill="none" stroke="{BLACK}" stroke-width="0.7"/>'
                        )

            # Sub-zone label
            lcid = f"f{fl}-cl-{rid}-{int(cx)}-{int(cy)}"
            parts.append(clip_rect(lcid, cx, cy, cw2, ch2, 2))
            lb2 = "W.I.C" if ("wardrobe" in cn or "walk_in" in cn) else "BATH"
            fsz = max(min(int(min(cw2,ch2)*0.15), 9), 6)
            lcx = cx+cw2/2; lcy = cy+ch2/2
            parts.append(f'<g clip-path="url(#{lcid})" style="pointer-events:none">')
            parts.append(T(lcx, lcy-fsz*0.6, lb2, fsz, "400", LBL_C))
            if cw2 > 35 and ch2 > 38:
                parts.append(T(lcx, lcy+fsz+1, f"{area_cr} sqft", max(fsz-1,5), "400", GRAY))
            parts.append("</g>")

    # ── FURNITURE ────────────────────────────────────────────────────────────
    if not is_st and not is_vd and not is_tr:
        fut = furniture(
            name,
            rx,
            ry,
            rw,
            rh,
            carved_zones=carved_zones or None,
            notes=str(room.get("notes", "")),
        )
        fstack = _furniture_editor_stack(room, rid, rx, ry, rw, rh, fut)
        if fstack:
            parts.append(fstack)

    # ── ROOM WALLS (on top of furniture so perimeter reads as built fabric) ─
    # Passages should read as open circulation voids (not boxed rooms).
    if c != "passage":
        # Walls are painted above furniture; without this, clicks hit wall rects instead of the furniture stack.
        parts.append(
            '<g class="room-wall-bands" style="pointer-events:none">'
            + draw_room_walls(rx, ry, rw, rh, ext_top, ext_bot, ext_left, ext_right)
            + "</g>"
        )
    elif n == "rear_passage":
        # Pack rear spine: draw closing bands on exterior sides so the passage does not
        # read as an open slot past the utility row (service passages skip full walls).
        if ext_right:
            parts.append(R(rx + rw - EXT_WALL, ry, EXT_WALL, rh, fill=BLACK, stroke="none", sw=0))
        if ext_bot:
            parts.append(R(rx, ry + rh - EXT_WALL, rw, EXT_WALL, fill=BLACK, stroke="none", sw=0))

    # ── WINDOWS + VENTS + DOORS (AFTER walls so white gaps read as real openings) ─
    if not is_st and not is_vd and not is_tr:
        wc = int(room.get("windows", 0))
        if wc > 0:
            wl = win_wall(name, rx, ry, rw, rh, ext_top, ext_bot, ext_left, ext_right)
            if wl != "none":
                win_style = (
                    "glider"
                    if c in ("kitchen", "wet_kitchen", "dry_kitchen", "utility_room")
                    else "standard"
                )
                _win_svg = draw_window(rx, ry, rw, rh, wl, wc, win_style)
                if wc == 1:
                    parts.append(_wrap_sys_opening(rid, "window", "windows", _win_svg))
                else:
                    parts.append(_win_svg)
        if c in ("bathroom", "common_bathroom", "guest_powder_room"):
            walls = {"top": ext_top, "bot": ext_bot, "left": ext_left, "right": ext_right}
            vent_wall = "none"
            for p in ["bot", "right", "left", "top"]:
                if walls.get(p):
                    vent_wall = p
                    break
            if vent_wall != "none":
                parts.append(draw_ventilator(rx, ry, rw, rh, vent_wall))

    if room.get("__main_door"):
        _md = draw_door(
            rx, ry, rw, rh, name,
            ext_top, ext_bot, ext_left, ext_right,
            int(room.get("layout_band", -1) or -1),
            str(room.get("__main_door") or ""),
            float(room.get("__main_door_px") or 0.0),
        )
        parts.append(_wrap_sys_opening(rid, "door", "main", _md))

    if not is_st and not is_vd and not is_tr:
        if not is_vd and not is_co:
            dc = int(room.get("door_count", 0))
            if dc > 0:
                _id = draw_door(
                    rx, ry, rw, rh, name,
                    ext_top, ext_bot, ext_left, ext_right,
                    int(room.get("layout_band", -1) or -1),
                    str(room.get("__door_wall", "") or ""),
                    0.0,
                )
                parts.append(_wrap_sys_opening(rid, "door", "interior", _id))
        _meal_band = 4  # layout_engine.BAND_SERVICE
        lb_dr = int(room.get("layout_band", -1) or -1)
        if c == "dining_room" and lb_dr == _meal_band and not ext_right:
            dk_h = 30.0
            dk_y = ry + rh * 0.38
            dk_x = rx + rw
            parts.append(R(dk_x - INT_WALL * 2.5, dk_y, INT_WALL * 2.5, dk_h, WHITE, "none", 0))
            jm = JAMB_TICK * 0.85
            parts.append(L(dk_x, dk_y, dk_x + jm, dk_y, BLACK, 0.5))
            parts.append(L(dk_x, dk_y, dk_x, dk_y + jm, BLACK, 0.5))
            parts.append(L(dk_x, dk_y + dk_h, dk_x + jm, dk_y + dk_h, BLACK, 0.5))
            parts.append(L(dk_x, dk_y + dk_h, dk_x, dk_y + dk_h - jm, BLACK, 0.5))
            parts.append(_door_leaf_poly_quad(dk_x, dk_y, dk_x, dk_y + dk_h, DOOR_LEAF_THK))
            parts.append(
                f'<path d="M {dk_x:.2f} {dk_y+dk_h:.2f} A {dk_h:.2f} {dk_h:.2f} 0 0 1 '
                f'{dk_x+dk_h:.2f} {dk_y:.2f}" fill="none" stroke="{BLACK}" stroke-width="0.7"/>'
            )
        elif c == "dining_room" and lb_dr == _meal_band and not ext_left:
            dk_h = 30.0
            dk_y = ry + rh * 0.38
            dk_x = rx
            parts.append(R(dk_x - INT_WALL * 0.5, dk_y, INT_WALL * 2.5, dk_h, WHITE, "none", 0))
            jm = JAMB_TICK * 0.85
            parts.append(L(dk_x, dk_y, dk_x - jm, dk_y, BLACK, 0.5))
            parts.append(L(dk_x, dk_y, dk_x, dk_y + jm, BLACK, 0.5))
            parts.append(L(dk_x, dk_y + dk_h, dk_x - jm, dk_y + dk_h, BLACK, 0.5))
            parts.append(L(dk_x, dk_y + dk_h, dk_x, dk_y + dk_h - jm, BLACK, 0.5))
            parts.append(_door_leaf_poly_quad(dk_x, dk_y, dk_x, dk_y + dk_h, DOOR_LEAF_THK))
            parts.append(
                f'<path d="M {dk_x:.2f} {dk_y+dk_h:.2f} A {dk_h:.2f} {dk_h:.2f} 0 0 0 '
                f'{dk_x-dk_h:.2f} {dk_y:.2f}" fill="none" stroke="{BLACK}" stroke-width="0.7"/>'
            )
        elif c == "dining_room" and not ext_bot:
            dk_w = 28.0
            dk_x = rx + rw * 0.55
            dk_y = ry + rh
            parts.append(R(dk_x, dk_y - INT_WALL, dk_w, INT_WALL * 2.5, WHITE, "none", 0))
            jm = JAMB_TICK * 0.85
            parts.append(L(dk_x, dk_y, dk_x, dk_y + jm, BLACK, 0.5))
            parts.append(L(dk_x, dk_y, dk_x + jm, dk_y, BLACK, 0.5))
            parts.append(L(dk_x + dk_w, dk_y, dk_x + dk_w, dk_y + jm, BLACK, 0.5))
            parts.append(L(dk_x + dk_w, dk_y, dk_x + dk_w - jm, dk_y, BLACK, 0.5))
            parts.append(_door_leaf_poly_quad(dk_x, dk_y, dk_x + dk_w, dk_y, DOOR_LEAF_THK))
            parts.append(
                f'<path d="M {dk_x+dk_w:.2f} {dk_y:.2f} A {dk_w:.2f} {dk_w:.2f} 0 0 1 '
                f'{dk_x:.2f} {dk_y+dk_w:.2f}" fill="none" stroke="{BLACK}" stroke-width="0.7"/>'
            )

    # User-placed wall openings (drag-to-wall in editor) — real punches + symbols
    if not is_st and not is_vd and not is_tr:
        parts.append(
            draw_placed_openings_on_room(
                room, rx, ry, rw, rh, ext_top, ext_bot, ext_left, ext_right, rid
            )
        )

    # ── LABEL ────────────────────────────────────────────────────────────────
    # Center label in habitable zone (left of carved zones)
    lcx2 = rx+rw/2; lcy2 = ry+rh/2
    if carved_zones and is_bedroom_cat(c):
        rzone_left = min(czx for czx,czy,czw,czh in carved_zones if czx-rx > rw*0.3) if carved_zones else rx+rw
        hab_w = rzone_left - rx
        lcx2 = rx + hab_w/2

    tp = []
    if is_co and not is_ps:
        fsz_co = max(min(8,int(rh*0.34)),6)
        tp.append(T(lcx2, lcy2-fsz_co*0.5, lb, fsz_co, "400", LBL_C))
        tp.append(T(lcx2, lcy2+fsz_co+1, f"{fmt_ft(rh)} Wide", max(fsz_co-1,5), "400", GRAY))
    elif is_tr:
        fsz = max(label_fs(rw,rh,lb), 8)
        tp.append(T(lcx2, lcy2-fsz*0.6, lb, fsz, "400", LBL_C))
        tp.append(T(lcx2, lcy2+fsz+1, f"{fmt_ft(rw)} × {fmt_ft(rh)}", max(fsz-2,6), "400", GRAY))
    elif rw < 50 or rh < 50:
        fsz = max(label_fs(rw,rh,lb), 6)
        tp.append(T(lcx2, lcy2-fsz*0.3, lb.split()[0], fsz, "400", LBL_C))
    else:
        fsz = label_fs(rw, rh, lb); words = lb.split()
        if len(words) > 2:
            mid2 = len(words)//2
            tp.append(T(lcx2, lcy2-fsz*0.9, " ".join(words[:mid2]), fsz, "400", LBL_C))
            tp.append(T(lcx2, lcy2+fsz*0.1, " ".join(words[mid2:]), fsz, "400", LBL_C))
        elif len(words)==2 and len(lb)*fsz*0.58 > rw*0.82:
            tp.append(T(lcx2, lcy2-fsz*0.7, words[0], fsz, "400", LBL_C))
            tp.append(T(lcx2, lcy2+fsz*0.3, words[1], fsz, "400", LBL_C))
        else:
            tp.append(T(lcx2, lcy2-fsz*0.7, lb, fsz, "400", LBL_C))
        dim_fs = max(fsz-1, 6)
        tp.append(T(lcx2, lcy2+fsz*0.7, f"{fmt_ft(rw)}X{fmt_ft(rh)}", dim_fs, "400", GRAY))
        if rh > 68:
            tp.append(T(lcx2, lcy2+fsz*1.7, f"{int(round(area))} sqft", max(dim_fs-1,5), "400", GRAY))

    if tp:
        # Labels sit above furniture in paint order; pointer-events none keeps Phase A furniture edit hits reachable.
        parts.append(
            f'<g clip-path="url(#{cid})" style="pointer-events:none">' + "".join(tp) + "</g>"
        )

    actual_sqft = round((rw / SCALE) * (rh / SCALE), 1)
    width_ft    = round(rw / SCALE, 2)
    depth_ft    = round(rh / SCALE, 2)
    x_ft        = round(rx / SCALE, 2)
    y_ft        = round(ry / SCALE, 2)

    # Canonical Vastu zones — single source of truth, matches architectural_rules.py
    _CANONICAL_VASTU = {
        "pooja_room":"NE","living_room":"N","drawing_room":"N","dining_room":"N","kitchen":"SE",
        "wet_kitchen":"SE","dry_kitchen":"SE","common_bathroom":"NW","guest_bedroom":"NW",
        "parents_bedroom":"NW","utility_room":"S","store_room":"S","staircase":"S",
        "home_office":"N","servant_quarters":"S","car_porch":"front","sit_out":"front",
        "foyer":"NE","corridor":"C","master_bedroom":"SW","bedroom":"NE","bedroom_2":"NE",
        "family_lounge":"C","walk_in_wardrobe":"SW","terrace":"N","balcony":"N",
        "staircase_landing":"C","guest_powder_room":"NW","bathroom":"NW",
    }
    # NBC 2016 minimum areas — used by canvas editor to show compliance badge
    _NBC_MIN_SQFT = {
        "master_bedroom":100,"bedroom":100,"parents_bedroom":100,"guest_bedroom":100,
        "living_room":120,"drawing_room":120,"dining_room":80,"kitchen":54,"bathroom":25,
        "common_bathroom":25,"utility_room":25,"store_room":16,"pooja_room":16,
        "home_office":64,"family_lounge":64,"servant_quarters":72,
        "foyer":16,"sit_out":24,"corridor":0,"staircase":0,"car_porch":0,
    }
    vzone    = _CANONICAL_VASTU.get(c, "")
    nbc_min  = _NBC_MIN_SQFT.get(c, 0)
    nbc_ok   = "true" if (nbc_min == 0 or actual_sqft >= nbc_min) else "false"
    fx_ct    = len(carved_children) if carved_children else 0
    # Full notes (untruncated) — canvas editor displays this in properties panel
    n_attr   = (str(room.get("notes",""))
                .replace('"', "&quot;")
                .replace("<", "&lt;")
                .replace(">", "&gt;"))
    # Band ID for editor reflow — prefer engine layout_band (GF sleeping vs rear_svc)
    try:
        lb_band = room.get("layout_band")
        if isinstance(lb_band, int) and lb_band >= 0:
            band_id = str(lb_band)
        else:
            from app.services.layout_engine import _get_band as _gb
            band_id = str(_gb(c, fl))
    except Exception:
        band_id = "-1"

    attrs = (
        f' class="room editable-room"'
        f' id="room-{rid}"'
        f' data-room-id="{rid}"'
        f' data-name="{name}"'
        f' data-cat="{c}"'
        f' data-floor="{fl}"'
        f' data-band="{band_id}"'
        f' data-x-ft="{x_ft}"'
        f' data-y-ft="{y_ft}"'
        f' data-width-ft="{width_ft}"'
        f' data-depth-ft="{depth_ft}"'
        f' data-sqft="{int(round(area))}"'
        f' data-actual-sqft="{actual_sqft}"'
        f' data-nbc-min-sqft="{nbc_min}"'
        f' data-nbc-compliant="{nbc_ok}"'
        f' data-vastu-zone="{vzone}"'
        f' data-fixtures="{fx_ct}"'
        f' data-editable="true"'
        f' data-notes="{n_attr}"'
        f' data-daylight-tier="{str(room.get("daylight_tier") or "")}"'
        f' data-circulation-role="{str(room.get("circulation_role") or "")}"'
        f' data-aspect-hint="{str(room.get("aspect_hint") or "")}"'
    )
    return "<g" + attrs + ">" + "".join(parts) + "</g>"


# ─── COMPASS ─────────────────────────────────────────────────────────────────

def draw_compass(cx, cy, r, facing):
    """
    Compass: arrow rotates by facing; NSEW labels placed at computed screen positions
    so they remain upright text regardless of rotation (audit S3 fix).
    east→90°: N arrow points LEFT, N label on LEFT side of circle.
    """
    import math
    rot = {"east": 90, "north": 0, "west": -90, "south": 180}.get(str(facing).lower(), 0)
    out = []
    # Arrow group (rotates)
    out.append(f'<g transform="rotate({rot} {cx:.1f} {cy:.1f})">')
    out.append(C(cx, cy, r, WHITE, BLACK, 0.7))
    out.append(C(cx, cy, r*0.15, BLACK, BLACK, 0.5))
    out.append(f'<polygon points="{cx:.1f},{cy-r*0.85:.1f} {cx-r*0.20:.1f},{cy:.1f} {cx+r*0.20:.1f},{cy:.1f}" fill="{BLACK}"/>')
    out.append(f'<polygon points="{cx:.1f},{cy+r*0.85:.1f} {cx-r*0.20:.1f},{cy:.1f} {cx+r*0.20:.1f},{cy:.1f}" fill="{WHITE}" stroke="{BLACK}" stroke-width="0.6"/>')
    out.append("</g>")
    # Labels: placed at screen positions using SVG CW rotation math.
    # Arrow-space directions: N=(0,-1), S=(0,1), E=(1,0), W=(-1,0) relative to center
    # SVG CW rotation by rot degrees: (dx,dy) → (dx*cosR + dy*sinR, -dx*sinR + dy*cosR)
    # For east (rot=90): N(0,-lr) → (-lr,0) = LEFT of center ✓
    lr = r * 1.28
    cos_r = math.cos(math.radians(rot))
    sin_r = math.sin(math.radians(rot))
    for (adx, ady), lbl in [((0,-1),"N"),((0,1),"S"),((1,0),"E"),((-1,0),"W")]:
        dx = adx * lr; dy = ady * lr
        tx = cx + dx * cos_r + dy * sin_r
        ty = cy - dx * sin_r + dy * cos_r
        out.append(T(tx, ty, lbl, 8, "700", BLACK))
    return "".join(out)


# ─── DIMENSION LINES ─────────────────────────────────────────────────────────

def draw_dims(pw, ph, bx, by, bw, bh, pw_ft, pd_ft, ox, oy):
    out = []; x1=ox+bx; y1=oy+by; x2=x1+bw; y2=y1+bh; d=20
    # Top
    out += [L(x1,y1-d-8,x1,y1-d+4,DIM_C,0.6), L(x2,y1-d-8,x2,y1-d+4,DIM_C,0.6),
            L(x1,y1-d,x2,y1-d,DIM_C,0.6),
            T((x1+x2)/2, y1-d-5, f"{int(pw_ft)}'-0\"", 8, "400", DIM_C)]
    # Left
    out += [L(x1-d-8,y1,x1-d+4,y1,DIM_C,0.6), L(x1-d-8,y2,x1-d+4,y2,DIM_C,0.6),
            L(x1-d,y1,x1-d,y2,DIM_C,0.6)]
    out.append(f'<text x="{x1-d-6:.2f}" y="{(y1+y2)/2:.2f}" font-size="8" font-weight="400" '
               f'fill="{DIM_C}" text-anchor="middle" font-family="Arial,Helvetica,sans-serif" '
               f'dominant-baseline="middle" '
               f'transform="rotate(-90,{x1-d-6:.2f},{(y1+y2)/2:.2f})">'
               f"{int(pd_ft)}'-0\"</text>")
    out.append(T((x1+x2)/2, oy+by-5, f"Built-up {int(bw/SCALE)}' × {int(bh/SCALE)}'", 6, "400", GRAY))
    return "".join(out)


def _room_envelope_px(
    rooms: List[Dict[str, Any]], ox: float, oy: float
) -> Tuple[float, float, float, float]:
    """Axis-aligned bounds of all room boxes in SVG space (includes carved cells)."""
    inf = float("inf")
    min_x = inf
    min_y = inf
    max_x = float("-inf")
    max_y = float("-inf")
    for r in rooms:
        rx = float(r["x"]) + ox
        ry = float(r["y"]) + oy
        rw = float(r["width"])
        rh = float(r["height"])
        min_x = min(min_x, rx)
        min_y = min(min_y, ry)
        max_x = max(max_x, rx + rw)
        max_y = max(max_y, ry + rh)
    if min_x == inf:
        return ox, oy, ox, oy
    return min_x, min_y, max_x, max_y


def _svg_plan_extents(
    rooms: List[Dict[str, Any]],
    ox: float,
    oy: float,
    plot_w: float,
    plot_h: float,
    bx: float,
    by_: float,
    bw: float,
    bh: float,
) -> Tuple[float, float, float, float]:
    """
    Full drawing extents: plot / built-up envelope, room hull, dimension ticks, compass.
    Returns (left, top, right, bottom) in pre-shift coordinates.
    """
    wall_pad = EXT_WALL * 0.55
    rmin_x, rmin_y, rmax_x, rmax_y = _room_envelope_px(rooms, ox, oy)
    x1 = ox + bx
    y1 = oy + by_
    x2 = x1 + bw
    y2 = y1 + bh
    d = 20.0
    dim_left = x1 - d - 10.0
    dim_top = y1 - d - 10.0
    comp_r = 24.0
    comp_right = ox + plot_w + 40.0 + comp_r * 1.28 + 10.0

    left = min(ox, dim_left, rmin_x - wall_pad, x1 - wall_pad)
    top = min(oy, dim_top, rmin_y - wall_pad)
    right = max(
        ox + plot_w,
        x2 + wall_pad,
        rmax_x + wall_pad,
        comp_right,
    )
    bottom = max(
        oy + plot_h,
        y2 + wall_pad,
        rmax_y + wall_pad,
    )
    return left, top, right, bottom


# ─── TITLE BLOCK ─────────────────────────────────────────────────────────────

def draw_title(x, y, w, h, bhk, style, floor_lbl, pw_ft, pd_ft, vastu, budget):
    out = [R(x,y,w,h,WHITE,BLACK,0.8), L(x,y,x+w,y,BLACK,1.2)]
    c1=w/3; c2=w*2/3
    out += [L(x+c1,y,x+c1,y+h,GRAY,0.5), L(x+c2,y,x+c2,y+h,GRAY,0.5)]
    out += [T(x+c1/2,y+h*0.28,"RESIDENTIAL FLOOR PLAN",9,"700",LBL_C),
            T(x+c1/2,y+h*0.58,f"{bhk} · {floor_lbl}",6,"400",GRAY),
            T(x+c1/2,y+h*0.80,(style or "")[:28],5,"400",GRAY),
            T(x+c1+c1/2,y+h*0.33,f"{int(pw_ft)}' × {int(pd_ft)}'",13,"700",LBL_C),
            T(x+c1+c1/2,y+h*0.68,"SCALE 1:100",7,"400",GRAY)]
    cx3 = x+c2+c1/2
    if vastu:
        out += [C(cx3-18,y+h*0.38,7,WHITE,"#2A7A2A",1.0),
                T(cx3-18,y+h*0.38,"✓",7,"700","#2A7A2A"),
                T(cx3+5,y+h*0.28,"VASTU",7,"700","#2A7A2A"),
                T(cx3+5,y+h*0.50,"COMPLIANT",6,"400","#2A7A2A")]
    # Budget omitted from title block — Guide Ch.12 Fix 4
    # Graphic scale bar — CORRECT 1:100 scale (Guide Ch.7)
    # 1 metre = 3.281ft × 10px/ft = 32.81px
    seg = 32.81  # px per metre
    n_seg = 5
    sb_x = x + c1; sb_y = y + h - 8; bar_h = 4
    out.append(R(sb_x, sb_y, seg*n_seg, bar_h, WHITE, BLACK, 0.5))
    for i in range(n_seg):
        if i % 2 == 0:
            out.append(R(sb_x + i*seg, sb_y, seg, bar_h, BLACK, "none", 0))
        out.append(T(sb_x + i*seg, sb_y + bar_h + 5, f"{i}m", 5, "400", GRAY, "start"))
    out.append(T(sb_x + n_seg*seg, sb_y + bar_h + 5, f"{n_seg}m", 5, "400", GRAY, "start"))
    return f'<g class="title-block" style="pointer-events:none">{"".join(out)}</g>'


# ─── EXTERNAL WALL PERIMETER ─────────────────────────────────────────────────

def draw_ext_boundary(bx, by, bw, bh, ox, oy):
    """
    External wall as two filled black rect outlines — NO stroke bleed.
    Outer rect: at exact building boundary.
    Inner rect: inset by EXT_WALL, creating a filled wall band.
    """
    x1=ox+bx; y1=oy+by
    out = []
    # Outer boundary line (1px stroke, no bleed)
    out.append(R(x1, y1, bw, bh, fill="none", stroke=BLACK, sw=1.0))
    # Inner boundary line (creates visual wall thickness without bleed)
    inner = EXT_WALL * 0.7
    out.append(R(x1+inner, y1+inner, bw-inner*2, bh-inner*2,
                 fill="none", stroke=BLACK, sw=0.8))
    return "".join(out)


def _door_opening_width_px(rw: float, rh: float) -> float:
    """Match draw_door default width (no main-entry override)."""
    if rw < 60 or rh < 60:
        dw = max(min(rw * 0.38, 22.0), 14.0)
    else:
        dw = max(min(rw * 0.28, 32.0), 20.0)
    return min(dw, rw * 0.42, rh * 0.42)


def corridor_service_seam_door_overlays(rooms: List[Dict[str, Any]], ox: float, oy: float) -> str:
    """
    Corridor / service_passage ↔ **dining only** (per plan spec: single door opening here).

    1) White knockouts re-punch wall bands drawn after the dining room.
    2) Door swing graphics (jambs + leaf + arc) on top of the white patch.

    Spines: `corridor`, `service_passage` only. Kitchen / dry kitchen are unchanged here.
    """
    byname = {str(r.get("name", "")).lower(): r for r in rooms}
    spines: List[Tuple[float, float, float, float]] = []
    for key in ("corridor", "service_passage"):
        sp = byname.get(key)
        if not sp or sp.get("__is_carved", False):
            continue
        px1 = ox + float(sp["x"])
        py1 = oy + float(sp["y"])
        px2 = px1 + float(sp["width"])
        py2 = py1 + float(sp["height"])
        spines.append((px1, py1, px2, py2))
    if not spines:
        return ""

    service_cats = frozenset({"dining_room"})
    knock: List[str] = []
    sym: List[str] = []
    gap_t = EXT_WALL * 2.0
    tol = 2.0
    edge_pad = 16.0
    th = DOOR_LEAF_THK
    jm = JAMB_TICK

    def ov1(a1: float, a2: float, b1: float, b2: float) -> float:
        return min(a2, b2) - max(a1, b1)

    for r in rooms:
        n = str(r.get("name", "")).lower()
        if r.get("__is_carved", False) or is_carved(n):
            continue
        if cat(n) not in service_cats:
            continue
        rx = ox + float(r["x"])
        ry = oy + float(r["y"])
        rw = float(r["width"])
        rh = float(r["height"])
        sx1, sy1, sx2, sy2 = rx, ry, rx + rw, ry + rh
        dw = _door_opening_width_px(rw, rh)

        best = ""
        best_score = -1.0
        for cx1, cy1, cx2, cy2 in spines:
            if abs(sy2 - cy1) < tol:
                sc = ov1(sx1, sx2, cx1, cx2)
                if sc > best_score:
                    best_score, best = sc, "bot"
            if abs(sy1 - cy2) < tol:
                sc = ov1(sx1, sx2, cx1, cx2)
                if sc > best_score:
                    best_score, best = sc, "top"
            if abs(sx2 - cx1) < tol:
                sc = ov1(sy1, sy2, cy1, cy2)
                if sc > best_score:
                    best_score, best = sc, "right"
            if abs(sx1 - cx2) < tol:
                sc = ov1(sy1, sy2, cy1, cy2)
                if sc > best_score:
                    best_score, best = sc, "left"

        if best_score < 14.0 or not best:
            continue

        if best == "bot":
            hx = rx + (rw - dw) * 0.5
            hx = max(rx + edge_pad, min(hx, rx + rw - edge_pad - dw))
            wy = sy2
            knock.append(R(hx, wy - EXT_WALL, dw, gap_t, WHITE, "none", 0))
            sym.append(L(hx, wy, hx + jm, wy, BLACK, 0.55))
            sym.append(L(hx, wy, hx, wy - jm, BLACK, 0.55))
            sym.append(L(hx + dw, wy, hx + dw - jm, wy, BLACK, 0.55))
            sym.append(L(hx + dw, wy, hx + dw, wy - jm, BLACK, 0.55))
            sym.append(_door_leaf_poly_quad(hx, wy, hx, wy - dw, th))
            sym.append(
                f'<path d="M {hx+dw:.2f} {wy:.2f} A {dw:.2f} {dw:.2f} 0 0 1 {hx:.2f} {wy-dw:.2f}" '
                f'fill="none" stroke="{BLACK}" stroke-width="0.7"/>'
            )
        elif best == "top":
            hx = rx + (rw - dw) * 0.5
            hx = max(rx + edge_pad, min(hx, rx + rw - edge_pad - dw))
            wy = sy1
            knock.append(R(hx, wy - EXT_WALL, dw, gap_t, WHITE, "none", 0))
            sym.append(L(hx, wy, hx + jm, wy, BLACK, 0.55))
            sym.append(L(hx, wy, hx, wy + jm, BLACK, 0.55))
            sym.append(L(hx + dw, wy, hx + dw - jm, wy, BLACK, 0.55))
            sym.append(L(hx + dw, wy, hx + dw, wy + jm, BLACK, 0.55))
            sym.append(_door_leaf_poly_quad(hx, wy, hx, wy + dw, th))
            sym.append(
                f'<path d="M {hx+dw:.2f} {wy:.2f} A {dw:.2f} {dw:.2f} 0 0 0 {hx:.2f} {wy+dw:.2f}" '
                f'fill="none" stroke="{BLACK}" stroke-width="0.7"/>'
            )
        elif best == "right":
            wx = sx2
            hy = ry + (rh - dw) * 0.5
            hy = max(ry + edge_pad, min(hy, ry + rh - edge_pad - dw))
            knock.append(R(wx - EXT_WALL, hy, gap_t, dw, WHITE, "none", 0))
            sym.append(L(wx, hy, wx, hy + jm, BLACK, 0.55))
            sym.append(L(wx, hy, wx - jm, hy, BLACK, 0.55))
            sym.append(L(wx, hy + dw, wx, hy + dw - jm, BLACK, 0.55))
            sym.append(L(wx, hy + dw, wx - jm, hy + dw, BLACK, 0.55))
            sym.append(_door_leaf_poly_quad(wx, hy, wx - dw, hy, th))
            sym.append(
                f'<path d="M {wx:.2f} {hy+dw:.2f} A {dw:.2f} {dw:.2f} 0 0 0 {wx-dw:.2f} {hy:.2f}" '
                f'fill="none" stroke="{BLACK}" stroke-width="0.7"/>'
            )
        else:  # left
            wx = sx1
            hy = ry + (rh - dw) * 0.5
            hy = max(ry + edge_pad, min(hy, ry + rh - edge_pad - dw))
            knock.append(R(wx - EXT_WALL, hy, gap_t, dw, WHITE, "none", 0))
            sym.append(L(wx, hy, wx, hy + jm, BLACK, 0.55))
            sym.append(L(wx, hy, wx + jm, hy, BLACK, 0.55))
            sym.append(L(wx, hy + dw, wx, hy + dw - jm, BLACK, 0.55))
            sym.append(L(wx, hy + dw, wx + jm, hy + dw, BLACK, 0.55))
            sym.append(_door_leaf_poly_quad(wx, hy, wx + dw, hy, th))
            sym.append(
                f'<path d="M {wx:.2f} {hy+dw:.2f} A {dw:.2f} {dw:.2f} 0 0 1 {wx+dw:.2f} {hy:.2f}" '
                f'fill="none" stroke="{BLACK}" stroke-width="0.7"/>'
            )

    if not knock:
        return ""
    parts = [f'<g class="corridor-service-door-knockouts">{"".join(knock)}</g>']
    if sym:
        parts.append(f'<g class="corridor-service-door-symbols">{"".join(sym)}</g>')
    return "".join(parts)


def _arch_q_horizontal(hx: float, wy: float, dw: float, bulge: float) -> str:
    """Shallow arch above a horizontal door opening (bulge in -Y)."""
    mid = hx + dw * 0.5
    return (
        f'<path d="M {hx:.2f},{wy:.2f} Q {mid:.2f},{wy-bulge:.2f} {hx+dw:.2f},{wy:.2f}" '
        f'fill="none" stroke="{BLACK}" stroke-width="0.65"/>'
    )


def _arch_q_vertical_into_left(wx: float, hy: float, dw: float, bulge: float) -> str:
    """Shallow arch on a vertical seam, bulging into the room on the left (-X from seam)."""
    mid = hy + dw * 0.5
    return (
        f'<path d="M {wx:.2f},{hy:.2f} Q {wx-bulge:.2f},{mid:.2f} {wx:.2f},{hy+dw:.2f}" '
        f'fill="none" stroke="{BLACK}" stroke-width="0.65"/>'
    )


def _append_opening_top(
    knock: List[str], sym: List[str], arch: List[str],
    hx: float, wy: float, dw: float, gap_t: float, th: float, jm: float, bulge: float,
) -> None:
    knock.append(R(hx, wy - EXT_WALL, dw, gap_t, WHITE, "none", 0))
    sym.append(L(hx, wy, hx + jm, wy, BLACK, 0.55))
    sym.append(L(hx, wy, hx, wy + jm, BLACK, 0.55))
    sym.append(L(hx + dw, wy, hx + dw - jm, wy, BLACK, 0.55))
    sym.append(L(hx + dw, wy, hx + dw, wy + jm, BLACK, 0.55))
    sym.append(_door_leaf_poly_quad(hx, wy, hx, wy + dw, th))
    sym.append(
        f'<path d="M {hx+dw:.2f} {wy:.2f} A {dw:.2f} {dw:.2f} 0 0 0 {hx:.2f} {wy+dw:.2f}" '
        f'fill="none" stroke="{BLACK}" stroke-width="0.7"/>'
    )
    arch.append(_arch_q_horizontal(hx, wy, dw, bulge))


def _append_opening_right(
    knock: List[str], sym: List[str], arch: List[str],
    wx: float, hy: float, dw: float, gap_t: float, th: float, jm: float, bulge: float,
) -> None:
    knock.append(R(wx - EXT_WALL, hy, gap_t, dw, WHITE, "none", 0))
    sym.append(L(wx, hy, wx, hy + jm, BLACK, 0.55))
    sym.append(L(wx, hy, wx - jm, hy, BLACK, 0.55))
    sym.append(L(wx, hy + dw, wx, hy + dw - jm, BLACK, 0.55))
    sym.append(L(wx, hy + dw, wx - jm, hy + dw, BLACK, 0.55))
    sym.append(_door_leaf_poly_quad(wx, hy, wx - dw, hy, th))
    sym.append(
        f'<path d="M {wx:.2f} {hy+dw:.2f} A {dw:.2f} {dw:.2f} 0 0 0 {wx-dw:.2f} {hy:.2f}" '
        f'fill="none" stroke="{BLACK}" stroke-width="0.7"/>'
    )
    arch.append(_arch_q_vertical_into_left(wx, hy, dw, bulge))


def dining_cluster_arch_openings(rooms: List[Dict[str, Any]], ox: float, oy: float) -> str:
    """
    Meal-strip cased openings (drawing-only): dining↔living/drawing, dining↔kitchen,
    kitchen↔dry kitchen. White knock + door swing + shallow arch; layout unchanged.
    """
    byname = {str(r.get("name", "")).lower(): r for r in rooms}
    din = byname.get("dining_room")
    kit = byname.get("kitchen")
    dry = byname.get("dry_kitchen")
    if not din or not kit:
        return ""

    tol = 2.5
    gap_t = EXT_WALL * 2.0
    edge_pad = 16.0
    th = DOOR_LEAF_THK
    jm = JAMB_TICK
    bulge = 5.5
    knock: List[str] = []
    sym: List[str] = []
    arch: List[str] = []

    def ov1(a1: float, a2: float, b1: float, b2: float) -> float:
        return min(a2, b2) - max(a1, b1)

    def rbox(r: Dict[str, Any]) -> Tuple[float, float, float, float]:
        x1 = ox + float(r["x"])
        y1 = oy + float(r["y"])
        return x1, y1, x1 + float(r["width"]), y1 + float(r["height"])

    # ── Dining top ↔ living or drawing bottom (whichever is actually shared) ─
    dx1, dy1, dx2, dy2 = rbox(din)
    d_rw = float(din["width"])
    d_rh = float(din["height"])
    for pub_key in ("drawing_room", "living_room"):
        liv = byname.get(pub_key)
        if not liv or liv.get("__is_carved", False):
            continue
        lx1, ly1, lx2, ly2 = rbox(liv)
        if abs(dy1 - ly2) < tol and ov1(dx1, dx2, lx1, lx2) > 18.0:
            dw = _door_opening_width_px(d_rw, d_rh)
            ov_l = max(dx1, lx1)
            ov_r = min(dx2, lx2)
            hx = (ov_l + ov_r - dw) * 0.5
            hx = max(dx1 + edge_pad, min(hx, dx2 - edge_pad - dw))
            wy = dy1
            _append_opening_top(knock, sym, arch, hx, wy, dw, gap_t, th, jm, bulge)
            break

    # ── Dining right ↔ kitchen left ────────────────────────────────────────
    dx1, dy1, dx2, dy2 = rbox(din)
    kx1, ky1, kx2, ky2 = rbox(kit)
    if abs(dx2 - kx1) < tol and ov1(dy1, dy2, ky1, ky2) > 18.0:
        d_rw = float(din["width"])
        d_rh = float(din["height"])
        dw = _door_opening_width_px(d_rw, d_rh)
        ov_b = max(dy1, ky1)
        ov_t = min(dy2, ky2)
        hy = (ov_b + ov_t - dw) * 0.5
        hy = max(dy1 + edge_pad, min(hy, dy2 - edge_pad - dw))
        wx = dx2
        _append_opening_right(knock, sym, arch, wx, hy, dw, gap_t, th, jm, bulge)

    # ── Kitchen right ↔ dry kitchen left ───────────────────────────────────
    if dry and not dry.get("__is_carved", False):
        kx1, ky1, kx2, ky2 = rbox(kit)
        zx1, zy1, zx2, zy2 = rbox(dry)
        if abs(kx2 - zx1) < tol and ov1(ky1, ky2, zy1, zy2) > 18.0:
            k_rw = float(kit["width"])
            k_rh = float(kit["height"])
            dw = _door_opening_width_px(k_rw, k_rh)
            ov_b = max(ky1, zy1)
            ov_t = min(ky2, zy2)
            hy = (ov_b + ov_t - dw) * 0.5
            hy = max(ky1 + edge_pad, min(hy, ky2 - edge_pad - dw))
            wx = kx2
            _append_opening_right(knock, sym, arch, wx, hy, dw, gap_t, th, jm, bulge)

    if not knock:
        return ""
    out = [f'<g class="dining-cluster-opening-knockouts">{"".join(knock)}</g>']
    if sym:
        out.append(f'<g class="dining-cluster-opening-symbols">{"".join(sym)}</g>')
    if arch:
        out.append(f'<g class="dining-cluster-opening-arches">{"".join(arch)}</g>')
    return "".join(out)


def master_store_access_door_overlay(
    rooms: List[Dict[str, Any]],
    ox: float,
    oy: float,
    parent_to_carved: Dict[str, List[Dict[str, Any]]],
    _bx: float,
    _by: float,
    _bw: float,
    _bh: float,
) -> str:
    """
    If store_room shares a slab seam with master_bedroom, draw a real door opening
    biased toward the sleeping zone (not centred only under the ensuite carve-out)
    so storage reads as suite-linked, not implied access only through the WC.
    """
    byname = {str(r.get("name", "")).lower(): r for r in rooms}
    master = byname.get("master_bedroom")
    store = byname.get("store_room")
    if not master or not store or master.get("__is_carved", False) or store.get("__is_carved", False):
        return ""

    mx1 = ox + float(master["x"])
    my1 = oy + float(master["y"])
    mx2 = mx1 + float(master["width"])
    my2 = my1 + float(master["height"])

    sx1 = ox + float(store["x"])
    sy1 = oy + float(store["y"])
    sx2 = sx1 + float(store["width"])
    sy2 = sy1 + float(store["height"])

    tol = 2.5
    edge_pad = 14.0
    gap_t = EXT_WALL * 2.0
    th = DOOR_LEAF_THK
    jm = JAMB_TICK

    def ov1(a1: float, a2: float, b1: float, b2: float) -> float:
        return min(a2, b2) - max(a1, b1)

    mrw = float(master["width"])
    mrh = float(master["height"])
    dw = max(18.0, min(_door_opening_width_px(mrw, mrh), 30.0))

    # Left / lower limit of ensuite strip on plan (sleeping zone is to the left).
    sleep_right = mx2
    for ch in parent_to_carved.get("master_bedroom", []) or []:
        cn = str(ch.get("name", "")).lower()
        if "bath" in cn or "toilet" in cn:
            cx1 = ox + float(ch["x"])
            sleep_right = min(sleep_right, cx1 - INT_WALL * 0.5)

    knock: List[str] = []
    sym: List[str] = []

    # Master bottom ↔ store top (typical stacked rear service)
    if abs(my2 - sy1) < tol:
        ovw = ov1(mx1, mx2, sx1, sx2)
        if ovw < 18.0:
            return ""
        seg_l = max(mx1, sx1)
        seg_r = min(mx2, sx2)
        prefer_r = min(seg_r, sleep_right)
        if prefer_r - seg_l < 16.0:
            hx = seg_l + (seg_r - seg_l - dw) * 0.25
        else:
            hx = (seg_l + prefer_r - dw) * 0.5
        hx = max(seg_l + edge_pad, min(hx, seg_r - edge_pad - dw))
        wy = my2
        knock.append(R(hx, wy - EXT_WALL, dw, gap_t, WHITE, "none", 0))
        sym.append(L(hx, wy, hx + jm, wy, BLACK, 0.55))
        sym.append(L(hx, wy, hx, wy - jm, BLACK, 0.55))
        sym.append(L(hx + dw, wy, hx + dw - jm, wy, BLACK, 0.55))
        sym.append(L(hx + dw, wy, hx + dw, wy - jm, BLACK, 0.55))
        sym.append(_door_leaf_poly_quad(hx, wy, hx, wy - dw, th))
        sym.append(
            f'<path d="M {hx+dw:.2f} {wy:.2f} A {dw:.2f} {dw:.2f} 0 0 1 {hx:.2f} {wy-dw:.2f}" '
            f'fill="none" stroke="{BLACK}" stroke-width="0.7"/>'
        )
    # Master right ↔ store left
    elif abs(mx2 - sx1) < tol:
        ovh = ov1(my1, my2, sy1, sy2)
        if ovh < 18.0:
            return ""
        seg_b = max(my1, sy1)
        seg_t = min(my2, sy2)
        hy = (seg_b + seg_t - dw) * 0.5
        # Bias upward away from bottom ensuite if carved bath sits on bottom-right
        sleep_bot = my2
        for ch in parent_to_carved.get("master_bedroom", []) or []:
            cn = str(ch.get("name", "")).lower()
            if "bath" in cn or "toilet" in cn:
                cy1 = oy + float(ch["y"])
                sleep_bot = min(sleep_bot, cy1 - INT_WALL * 0.5)
        if sleep_bot - seg_b < dw + 20.0:
            hy = seg_b + edge_pad
        else:
            hy = min(hy, sleep_bot - edge_pad - dw)
        hy = max(seg_b + edge_pad, min(hy, seg_t - edge_pad - dw))
        wx = mx2
        knock.append(R(wx - EXT_WALL, hy, gap_t, dw, WHITE, "none", 0))
        sym.append(L(wx, hy, wx, hy + jm, BLACK, 0.55))
        sym.append(L(wx, hy, wx - jm, hy, BLACK, 0.55))
        sym.append(L(wx, hy + dw, wx, hy + dw - jm, BLACK, 0.55))
        sym.append(L(wx, hy + dw, wx - jm, hy + dw, BLACK, 0.55))
        sym.append(_door_leaf_poly_quad(wx, hy, wx - dw, hy, th))
        sym.append(
            f'<path d="M {wx:.2f} {hy+dw:.2f} A {dw:.2f} {dw:.2f} 0 0 0 {wx-dw:.2f} {hy:.2f}" '
            f'fill="none" stroke="{BLACK}" stroke-width="0.7"/>'
        )
    else:
        return ""

    if not knock:
        return ""
    parts = [f'<g class="master-store-door-knockouts">{"".join(knock)}</g>']
    if sym:
        parts.append(f'<g class="master-store-door-symbols">{"".join(sym)}</g>')
    return "".join(parts)


def rear_common_bathroom_door_overlay(
    rooms: List[Dict[str, Any]],
    ox: float,
    oy: float,
    bx: float,
    by: float,
    bw: float,
    bh: float,
) -> str:
    """
    Re-punch + redraw door swing for `common_bathroom` on its best interior seam
    toward circulation or service (passage, utility, store) — never through a
    bedroom wall (avoids orphan white gaps on sleeping-room façades).
    Drawing-only; jambs only (full swing is from service_passage_bath_door_overlay).
    """
    byname = {str(r.get("name", "")).lower(): r for r in rooms}
    bath = byname.get("common_bathroom")
    if not bath or bath.get("__is_carved", False):
        return ""

    rx = ox + float(bath["x"])
    ry = oy + float(bath["y"])
    rw = float(bath["width"])
    rh = float(bath["height"])
    ext_top, ext_bot, ext_left, ext_right = ext_walls_of(rx, ry, rw, rh, bx, by, bw, bh, ox, oy)

    bx1, by1, bx2, by2 = rx, ry, rx + rw, ry + rh
    dw = _door_opening_width_px(rw, rh)
    gap_t = EXT_WALL * 2.0
    edge_pad = 16.0
    jm = JAMB_TICK
    tol = 2.5

    def ov1(a1: float, a2: float, b1: float, b2: float) -> float:
        return min(a2, b2) - max(a1, b1)

    # Higher = better category for common-WC knockouts (never bedrooms).
    _PREFERRED_COMMON_BATH_NEIGHBOR = (
        "rear_passage",
        "service_passage",
        "corridor",
        "utility_room",
        "store_room",
        "kitchen",
        "staircase",
        "dining_room",
        "living_room",
        "foyer",
    )

    def _neighbor_tier(name: str) -> int:
        nl = name.lower()
        if is_bedroom_cat(cat(nl)):
            return -999
        if nl in _PREFERRED_COMMON_BATH_NEIGHBOR:
            return 2
        return 1

    candidates: List[Tuple[int, float, str, str, Tuple[float, float, float, float, float]]] = []

    for r in rooms:
        n = str(r.get("name", "")).lower()
        if r.get("__is_carved", False) or is_carved(n):
            continue
        if n == "common_bathroom":
            continue
        tier = _neighbor_tier(n)
        if tier < 0:
            continue
        ox1 = ox + float(r["x"])
        oy1 = oy + float(r["y"])
        ox2 = ox1 + float(r["width"])
        oy2 = oy1 + float(r["height"])

        # bathroom TOP ↔ neighbor BOTTOM
        if not ext_top and abs(by1 - oy2) < tol:
            sc = ov1(bx1, bx2, ox1, ox2)
            if sc >= 14.0:
                ov_l = max(bx1, ox1)
                ov_r = min(bx2, ox2)
                hx = (ov_l + ov_r - dw) * 0.5
                hx = max(bx1 + edge_pad, min(hx, bx2 - edge_pad - dw))
                candidates.append((tier, sc, "top", n, (hx, by1, dw, 0.0, 0.0)))

        # bathroom RIGHT ↔ neighbor LEFT
        if not ext_right and abs(bx2 - ox1) < tol:
            sc = ov1(by1, by2, oy1, oy2)
            if sc >= 14.0:
                ov_b = max(by1, oy1)
                ov_t = min(by2, oy2)
                hy = (ov_b + ov_t - dw) * 0.5
                hy = max(by1 + edge_pad, min(hy, by2 - edge_pad - dw))
                candidates.append((tier, sc, "right", n, (bx2, hy, dw, 0.0, 0.0)))

        # bathroom LEFT ↔ neighbor RIGHT
        if not ext_left and abs(bx1 - ox2) < tol:
            sc = ov1(by1, by2, oy1, oy2)
            if sc >= 14.0:
                ov_b = max(by1, oy1)
                ov_t = min(by2, oy2)
                hy = (ov_b + ov_t - dw) * 0.5
                hy = max(by1 + edge_pad, min(hy, by2 - edge_pad - dw))
                candidates.append((tier, sc, "left", n, (bx1, hy, dw, 0.0, 0.0)))

        # bathroom BOTTOM ↔ neighbor TOP
        if not ext_bot and abs(by2 - oy1) < tol:
            sc = ov1(bx1, bx2, ox1, ox2)
            if sc >= 14.0:
                ov_l = max(bx1, ox1)
                ov_r = min(bx2, ox2)
                hx = (ov_l + ov_r - dw) * 0.5
                hx = max(bx1 + edge_pad, min(hx, bx2 - edge_pad - dw))
                candidates.append((tier, sc, "bot", n, (hx, by2, dw, 0.0, 0.0)))

    if not candidates:
        return ""

    tier_m = max(c[0] for c in candidates)
    tier_pool = [c for c in candidates if c[0] == tier_m]
    _, best_sc, best_w, _neighbor_dbg, best_geom = max(
        tier_pool, key=lambda c: (c[1], c[4][0], c[4][1])
    )

    if best_sc < 14.0 or not best_w:
        return ""

    knock: List[str] = []
    sym: List[str] = []

    # rear_common_bathroom_door_overlay: punch opening + jambs only — no leaf/swing.
    # The toilet swing toward utility is always suppressed here; the proper bath
    # door (with swing) is drawn by service_passage_bath_door_overlay instead.
    if best_w == "top":
        hx, wy, d, _, _ = best_geom
        knock.append(R(hx, wy - EXT_WALL, d, gap_t, WHITE, "none", 0))
        sym.append(L(hx, wy, hx + jm, wy, BLACK, 0.55))
        sym.append(L(hx, wy, hx, wy + jm, BLACK, 0.55))
        sym.append(L(hx + d, wy, hx + d - jm, wy, BLACK, 0.55))
        sym.append(L(hx + d, wy, hx + d, wy + jm, BLACK, 0.55))
    elif best_w == "right":
        wx, hy, d, _, _ = best_geom
        knock.append(R(wx - EXT_WALL, hy, gap_t, d, WHITE, "none", 0))
        sym.append(L(wx, hy, wx, hy + jm, BLACK, 0.55))
        sym.append(L(wx, hy, wx - jm, hy, BLACK, 0.55))
        sym.append(L(wx, hy + d, wx, hy + d - jm, BLACK, 0.55))
        sym.append(L(wx, hy + d, wx - jm, hy + d, BLACK, 0.55))
    elif best_w == "left":
        wx, hy, d, _, _ = best_geom
        knock.append(R(wx - EXT_WALL, hy, gap_t, d, WHITE, "none", 0))
        sym.append(L(wx, hy, wx, hy + jm, BLACK, 0.55))
        sym.append(L(wx, hy, wx + jm, hy, BLACK, 0.55))
        sym.append(L(wx, hy + d, wx, hy + d - jm, BLACK, 0.55))
        sym.append(L(wx, hy + d, wx + jm, hy + d, BLACK, 0.55))
    else:  # bot
        hx, wy, d, _, _ = best_geom
        knock.append(R(hx, wy - EXT_WALL, d, gap_t, WHITE, "none", 0))
        sym.append(L(hx, wy, hx + jm, wy, BLACK, 0.55))
        sym.append(L(hx, wy, hx, wy - jm, BLACK, 0.55))
        sym.append(L(hx + d, wy, hx + d - jm, wy, BLACK, 0.55))
        sym.append(L(hx + d, wy, hx + d, wy - jm, BLACK, 0.55))

    parts = [f'<g class="rear-common-bath-door-knockouts">{"".join(knock)}</g>']
    if sym:
        parts.append(f'<g class="rear-common-bath-door-symbols">{"".join(sym)}</g>')
    return "".join(parts)


def service_passage_bath_door_overlay(
    rooms: List[Dict[str, Any]],
    ox: float,
    oy: float,
    bx: float,
    by: float,
    bw: float,
    bh: float,
) -> str:
    """
    Draw a door from service_passage (or rear_passage) into common_bathroom.
    This ensures the bath door appears on the passage side wall.
    """
    byname = {str(r.get("name", "")).lower(): r for r in rooms}
    bath = byname.get("common_bathroom")
    if not bath or bath.get("__is_carved", False):
        return ""

    # Find passage rooms
    passage_rooms = []
    for key in ("service_passage", "rear_passage", "corridor"):
        p = byname.get(key)
        if p and not p.get("__is_carved", False):
            passage_rooms.append(p)
    if not passage_rooms:
        return ""

    bx1 = ox + float(bath["x"])
    by1 = oy + float(bath["y"])
    bx2 = bx1 + float(bath["width"])
    by2 = by1 + float(bath["height"])
    rw = float(bath["width"])
    rh = float(bath["height"])
    dw = _door_opening_width_px(rw, rh)
    gap_t = EXT_WALL * 2.0
    edge_pad = 14.0
    th = DOOR_LEAF_THK
    jm = JAMB_TICK
    tol = 2.5

    knock: List[str] = []
    sym: List[str] = []

    for pr in passage_rooms:
        px1 = ox + float(pr["x"])
        py1 = oy + float(pr["y"])
        px2 = px1 + float(pr["width"])
        py2 = py1 + float(pr["height"])

        # bath TOP ↔ passage BOTTOM
        if abs(by1 - py2) < tol:
            ov = min(bx2, px2) - max(bx1, px1)
            if ov > 14.0:
                ov_l = max(bx1, px1); ov_r = min(bx2, px2)
                hx = (ov_l + ov_r - dw) * 0.5
                hx = max(bx1 + edge_pad, min(hx, bx2 - edge_pad - dw))
                knock.append(R(hx, by1 - EXT_WALL, dw, gap_t, WHITE, "none", 0))
                sym.append(L(hx, by1, hx + jm, by1, BLACK, 0.55))
                sym.append(L(hx, by1, hx, by1 + jm, BLACK, 0.55))
                sym.append(L(hx + dw, by1, hx + dw - jm, by1, BLACK, 0.55))
                sym.append(L(hx + dw, by1, hx + dw, by1 + jm, BLACK, 0.55))
                sym.append(_door_leaf_poly_quad(hx, by1, hx, by1 + dw, th))
                sym.append(
                    f'<path d="M {hx+dw:.2f} {by1:.2f} A {dw:.2f} {dw:.2f} 0 0 0 {hx:.2f} {by1+dw:.2f}" '
                    f'fill="none" stroke="{BLACK}" stroke-width="0.7"/>'
                )
                break

        # bath BOTTOM ↔ passage TOP
        if abs(by2 - py1) < tol:
            ov = min(bx2, px2) - max(bx1, px1)
            if ov > 14.0:
                ov_l = max(bx1, px1); ov_r = min(bx2, px2)
                hx = (ov_l + ov_r - dw) * 0.5
                hx = max(bx1 + edge_pad, min(hx, bx2 - edge_pad - dw))
                knock.append(R(hx, by2 - EXT_WALL, dw, gap_t, WHITE, "none", 0))
                sym.append(L(hx, by2, hx + jm, by2, BLACK, 0.55))
                sym.append(L(hx, by2, hx, by2 - jm, BLACK, 0.55))
                sym.append(L(hx + dw, by2, hx + dw - jm, by2, BLACK, 0.55))
                sym.append(L(hx + dw, by2, hx + dw, by2 - jm, BLACK, 0.55))
                sym.append(_door_leaf_poly_quad(hx, by2, hx, by2 - dw, th))
                sym.append(
                    f'<path d="M {hx+dw:.2f} {by2:.2f} A {dw:.2f} {dw:.2f} 0 0 1 {hx:.2f} {by2-dw:.2f}" '
                    f'fill="none" stroke="{BLACK}" stroke-width="0.7"/>'
                )
                break

        # bath LEFT ↔ passage RIGHT
        if abs(bx1 - px2) < tol:
            ov = min(by2, py2) - max(by1, py1)
            if ov > 14.0:
                ov_b = max(by1, py1); ov_t = min(by2, py2)
                hy = (ov_b + ov_t - dw) * 0.5
                hy = max(by1 + edge_pad, min(hy, by2 - edge_pad - dw))
                knock.append(R(bx1 - EXT_WALL, hy, gap_t, dw, WHITE, "none", 0))
                sym.append(L(bx1, hy, bx1, hy + jm, BLACK, 0.55))
                sym.append(L(bx1, hy, bx1 + jm, hy, BLACK, 0.55))
                sym.append(L(bx1, hy + dw, bx1, hy + dw - jm, BLACK, 0.55))
                sym.append(L(bx1, hy + dw, bx1 + jm, hy + dw, BLACK, 0.55))
                sym.append(_door_leaf_poly_quad(bx1, hy, bx1 + dw, hy, th))
                sym.append(
                    f'<path d="M {bx1:.2f} {hy+dw:.2f} A {dw:.2f} {dw:.2f} 0 0 1 {bx1+dw:.2f} {hy:.2f}" '
                    f'fill="none" stroke="{BLACK}" stroke-width="0.7"/>'
                )
                break

        # bath RIGHT ↔ passage LEFT
        if abs(bx2 - px1) < tol:
            ov = min(by2, py2) - max(by1, py1)
            if ov > 14.0:
                ov_b = max(by1, py1); ov_t = min(by2, py2)
                hy = (ov_b + ov_t - dw) * 0.5
                hy = max(by1 + edge_pad, min(hy, by2 - edge_pad - dw))
                knock.append(R(bx2 - EXT_WALL, hy, gap_t, dw, WHITE, "none", 0))
                sym.append(L(bx2, hy, bx2, hy + jm, BLACK, 0.55))
                sym.append(L(bx2, hy, bx2 - jm, hy, BLACK, 0.55))
                sym.append(L(bx2, hy + dw, bx2, hy + dw - jm, BLACK, 0.55))
                sym.append(L(bx2, hy + dw, bx2 - jm, hy + dw, BLACK, 0.55))
                sym.append(_door_leaf_poly_quad(bx2, hy, bx2 - dw, hy, th))
                sym.append(
                    f'<path d="M {bx2:.2f} {hy+dw:.2f} A {dw:.2f} {dw:.2f} 0 0 0 {bx2-dw:.2f} {hy:.2f}" '
                    f'fill="none" stroke="{BLACK}" stroke-width="0.7"/>'
                )
                break

    if not knock:
        return ""
    parts = [f'<g class="service-passage-bath-door-knockouts">{"".join(knock)}</g>']
    if sym:
        parts.append(f'<g class="service-passage-bath-door-symbols">{"".join(sym)}</g>')
    return "".join(parts)


def upper_floor_terrace_access_overlay(
    rooms: List[Dict[str, Any]],
    ox: float,
    oy: float,
    floor_index: int,
) -> str:
    """Add explicit terrace-access openings (white patch + swing) on upper floors."""
    if floor_index < 1:
        return ""

    tol = 2.5
    min_overlap = 16.0
    gap_t = EXT_WALL * 2.0
    edge_pad = 16.0
    th = DOOR_LEAF_THK
    jm = JAMB_TICK

    knock: List[str] = []
    sym: List[str] = []

    def _is_terrace_room(r: Dict[str, Any]) -> bool:
        n = str(r.get("name", "")).lower()
        return ("terrace" in n) or ("balcony" in n)

    def _eligible_interior_room(r: Dict[str, Any]) -> bool:
        n = str(r.get("name", "")).lower()
        if r.get("__is_carved", False) or is_carved(n):
            return False
        if _is_terrace_room(r):
            return False
        c = cat(n)
        return c not in ("void", "staircase", "staircase_landing", "corridor", "passage", "car_porch")

    def rbox(r: Dict[str, Any]) -> Tuple[float, float, float, float]:
        x1 = ox + float(r["x"])
        y1 = oy + float(r["y"])
        return x1, y1, x1 + float(r["width"]), y1 + float(r["height"])

    def ov1(a1: float, a2: float, b1: float, b2: float) -> float:
        return min(a2, b2) - max(a1, b1)

    terraces = [r for r in rooms if _is_terrace_room(r) and not r.get("__is_carved", False)]
    interiors = [r for r in rooms if _eligible_interior_room(r)]
    if not terraces or not interiors:
        return ""

    for ir in interiors:
        ix1, iy1, ix2, iy2 = rbox(ir)
        dw = _door_opening_width_px(float(ir["width"]), float(ir["height"]))

        best_side = ""
        best_score = -1.0
        for tr in terraces:
            tx1, ty1, tx2, ty2 = rbox(tr)
            if abs(iy2 - ty1) < tol:
                sc = ov1(ix1, ix2, tx1, tx2)
                if sc > best_score:
                    best_side, best_score = "bot", sc
            if abs(iy1 - ty2) < tol:
                sc = ov1(ix1, ix2, tx1, tx2)
                if sc > best_score:
                    best_side, best_score = "top", sc
            if abs(ix2 - tx1) < tol:
                sc = ov1(iy1, iy2, ty1, ty2)
                if sc > best_score:
                    best_side, best_score = "right", sc
            if abs(ix1 - tx2) < tol:
                sc = ov1(iy1, iy2, ty1, ty2)
                if sc > best_score:
                    best_side, best_score = "left", sc

        if best_score < min_overlap or not best_side:
            continue

        if best_side == "bot":
            hx = ix1 + (ix2 - ix1 - dw) * 0.5
            hx = max(ix1 + edge_pad, min(hx, ix2 - edge_pad - dw))
            wy = iy2
            knock.append(R(hx, wy - EXT_WALL, dw, gap_t, WHITE, "none", 0))
            sym.append(L(hx, wy, hx + jm, wy, BLACK, 0.55))
            sym.append(L(hx, wy, hx, wy - jm, BLACK, 0.55))
            sym.append(L(hx + dw, wy, hx + dw - jm, wy, BLACK, 0.55))
            sym.append(L(hx + dw, wy, hx + dw, wy - jm, BLACK, 0.55))
            sym.append(_door_leaf_poly_quad(hx, wy, hx, wy - dw, th))
            sym.append(
                f'<path d="M {hx+dw:.2f} {wy:.2f} A {dw:.2f} {dw:.2f} 0 0 1 {hx:.2f} {wy-dw:.2f}" '
                f'fill="none" stroke="{BLACK}" stroke-width="0.7"/>'
            )
        elif best_side == "top":
            hx = ix1 + (ix2 - ix1 - dw) * 0.5
            hx = max(ix1 + edge_pad, min(hx, ix2 - edge_pad - dw))
            wy = iy1
            knock.append(R(hx, wy - EXT_WALL, dw, gap_t, WHITE, "none", 0))
            sym.append(L(hx, wy, hx + jm, wy, BLACK, 0.55))
            sym.append(L(hx, wy, hx, wy + jm, BLACK, 0.55))
            sym.append(L(hx + dw, wy, hx + dw - jm, wy, BLACK, 0.55))
            sym.append(L(hx + dw, wy, hx + dw, wy + jm, BLACK, 0.55))
            sym.append(_door_leaf_poly_quad(hx, wy, hx, wy + dw, th))
            sym.append(
                f'<path d="M {hx+dw:.2f} {wy:.2f} A {dw:.2f} {dw:.2f} 0 0 0 {hx:.2f} {wy+dw:.2f}" '
                f'fill="none" stroke="{BLACK}" stroke-width="0.7"/>'
            )
        elif best_side == "right":
            wx = ix2
            hy = iy1 + (iy2 - iy1 - dw) * 0.5
            hy = max(iy1 + edge_pad, min(hy, iy2 - edge_pad - dw))
            knock.append(R(wx - EXT_WALL, hy, gap_t, dw, WHITE, "none", 0))
            sym.append(L(wx, hy, wx, hy + jm, BLACK, 0.55))
            sym.append(L(wx, hy, wx - jm, hy, BLACK, 0.55))
            sym.append(L(wx, hy + dw, wx, hy + dw - jm, BLACK, 0.55))
            sym.append(L(wx, hy + dw, wx - jm, hy + dw, BLACK, 0.55))
            sym.append(_door_leaf_poly_quad(wx, hy, wx - dw, hy, th))
            sym.append(
                f'<path d="M {wx:.2f} {hy+dw:.2f} A {dw:.2f} {dw:.2f} 0 0 0 {wx-dw:.2f} {hy:.2f}" '
                f'fill="none" stroke="{BLACK}" stroke-width="0.7"/>'
            )
        else:  # left
            wx = ix1
            hy = iy1 + (iy2 - iy1 - dw) * 0.5
            hy = max(iy1 + edge_pad, min(hy, iy2 - edge_pad - dw))
            knock.append(R(wx - EXT_WALL, hy, gap_t, dw, WHITE, "none", 0))
            sym.append(L(wx, hy, wx, hy + jm, BLACK, 0.55))
            sym.append(L(wx, hy, wx + jm, hy, BLACK, 0.55))
            sym.append(L(wx, hy + dw, wx, hy + dw - jm, BLACK, 0.55))
            sym.append(L(wx, hy + dw, wx + jm, hy + dw, BLACK, 0.55))
            sym.append(_door_leaf_poly_quad(wx, hy, wx + dw, hy, th))
            sym.append(
                f'<path d="M {wx:.2f} {hy+dw:.2f} A {dw:.2f} {dw:.2f} 0 0 1 {wx+dw:.2f} {hy:.2f}" '
                f'fill="none" stroke="{BLACK}" stroke-width="0.7"/>'
            )

    if not knock:
        return ""
    out = [f'<g class="terrace-access-opening-knockouts">{"".join(knock)}</g>']
    if sym:
        out.append(f'<g class="terrace-access-opening-symbols">{"".join(sym)}</g>')
    return "".join(out)


def _xml_attr(s: str) -> str:
    return (
        str(s)
        .replace("&", "&amp;")
        .replace('"', "&quot;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


# ─── MAIN RENDER ─────────────────────────────────────────────────────────────

def render_floor_plan_svg(layout_data, parsed, floor_index=0, floor_label="GROUND FLOOR"):
    rooms  = layout_data.get("rooms", [])
    plot_w = float(layout_data.get("plot_w_px") or layout_data.get("plot",{}).get("width_px",400))
    plot_h = float(layout_data.get("plot_h_px") or layout_data.get("plot",{}).get("height_px",600))
    bx     = float(layout_data.get("built_up_x") or layout_data.get("built_up",{}).get("x",20))
    by_    = float(layout_data.get("built_up_y") or layout_data.get("built_up",{}).get("y",50))
    bw     = float(layout_data.get("built_up_w") or layout_data.get("built_up",{}).get("width",360))
    bh     = float(layout_data.get("built_up_h") or layout_data.get("built_up",{}).get("height",520))
    pw_ft  = float(parsed.get("plot_width_ft", 40) or 40)
    pd_ft  = float(parsed.get("plot_depth_ft", 60) or 60)
    bhk    = str(parsed.get("bhk_type","") or "")
    style  = str(parsed.get("style","") or "")
    vastu  = bool(parsed.get("vastu_compliant", False))
    budget = int(parsed.get("budget", 0) or 0)
    facing = str(parsed.get("plot_facing","unknown") or "unknown").lower()

    ox = MARGIN + DIM_SPC
    oy = MARGIN + DIM_SPC

    # Build parent → carved_children map
    parent_to_carved: dict = {}
    for r in rooms:
        rn = str(r.get("name","")).lower()
        if not (r.get("__is_carved", False) or is_carved(rn)): continue
        pname = None
        if rn.endswith("_bathroom"):
            cand = rn[:-len("_bathroom")]
            if any(str(p.get("name","")).lower()==cand for p in rooms): pname=cand
        if pname is None and ("walk_in_wardrobe" in rn or "wardrobe" in rn):
            for p2 in rooms:
                p2n=str(p2.get("name","")).lower()
                if "master_bedroom" in p2n and "_bathroom" not in p2n and not is_carved(p2n):
                    pname=p2n; break
        if pname is None:
            notes=(r.get("notes") or "").lower()
            if "attached to " in notes:
                cand2=notes.split("attached to ")[1].split()[0].rstrip(",;.")
                if any(str(p.get("name","")).lower()==cand2 for p in rooms): pname=cand2
        if pname:
            parent_to_carved.setdefault(pname,[]).append(r)

    geom_left, _geom_top, geom_right, geom_bottom = _svg_plan_extents(
        rooms, ox, oy, plot_w, plot_h, bx, by_, bw, bh
    )
    title_y = geom_bottom + TITLE_GAP_BELOW_PLOT
    ch = title_y + TITLE_H + SCALE_BAR_TEXT_DROP + TITLE_BOTTOM_PAD + MARGIN
    sym_w = (geom_right - geom_left) + 2.0 * SIDE_PAD
    legacy_min = plot_w + ox + MARGIN + 80.0
    cw = max(sym_w, legacy_min)
    extra_w = cw - sym_w
    x_shift = SIDE_PAD - geom_left + extra_w * 0.5

    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {cw:.0f} {ch:.0f}" '
        f'width="{cw:.0f}" height="{ch:.0f}" data-floor="{floor_index}" '
        f'data-editor-ox="{ox:.4f}" data-editor-oy="{oy:.4f}" data-editor-x-shift="{x_shift:.4f}" '
        f'preserveAspectRatio="xMidYMid meet">',
        '<defs><style>.room{cursor:pointer;}.room:hover rect:first-of-type{opacity:0.92;}</style></defs>',
        f'<rect width="{cw:.0f}" height="{ch:.0f}" fill="{PAPER}"/>',
        f'<g transform="translate({x_shift:.2f},0)">',
        # Plot outline (light dashed)
        R(ox, oy, plot_w, plot_h, fill=WHITE, stroke="#CCCCCC", sw=0.5),
        # Building interior white background
        R(ox+bx, oy+by_, bw, bh, fill=WHITE, stroke="none", sw=0),
        '<g class="rooms">',
    ]

    # ── Adjacency-derived door wall selection ────────────────────────────────
    # Pick the wall that actually touches corridor/passage (more realistic than band heuristics).
    def _rect(r):
        return (
            float(r["x"]) + ox,
            float(r["y"]) + oy,
            float(r["x"]) + ox + float(r["width"]),
            float(r["y"]) + oy + float(r["height"]),
        )
    def _overlap(a1, a2, b1, b2):
        return min(a2, b2) - max(a1, b1)

    tol = 2.0
    circulation = []
    for r in rooms:
        n = str(r.get("name","")).lower()
        if r.get("__is_carved", False) or is_carved(n):
            continue
        if ("corridor" in n) or ("passage" in n):
            circulation.append(r)

    for r in rooms:
        n = str(r.get("name","")).lower()
        if r.get("__is_carved", False) or is_carved(n):
            continue
        if ("corridor" in n) or ("passage" in n):
            continue
        x1,y1,x2,y2 = _rect(r)
        best = ""
        best_score = -1.0
        for croom in circulation:
            cx1,cy1,cx2,cy2 = _rect(croom)
            # share vertical wall?
            if abs(x2 - cx1) < tol and _overlap(y1,y2,cy1,cy2) > 14:
                score = _overlap(y1,y2,cy1,cy2)
                if score > best_score:
                    best_score = score; best = "right"
            if abs(x1 - cx2) < tol and _overlap(y1,y2,cy1,cy2) > 14:
                score = _overlap(y1,y2,cy1,cy2)
                if score > best_score:
                    best_score = score; best = "left"
            # share horizontal wall?
            if abs(y2 - cy1) < tol and _overlap(x1,x2,cx1,cx2) > 14:
                score = _overlap(x1,x2,cx1,cx2)
                if score > best_score:
                    best_score = score; best = "bot"
            if abs(y1 - cy2) < tol and _overlap(x1,x2,cx1,cx2) > 14:
                score = _overlap(x1,x2,cx1,cx2)
                if score > best_score:
                    best_score = score; best = "top"
        if best:
            r["__door_wall"] = best

    # ── Targeted door-wall overrides for common G+1 issues ───────────────────
    # Keep these drawing-only overrides close to render-time so layout geometry
    # stays unchanged while door graphics/openings become buildable.
    byname = {str(r.get("name", "")).lower(): r for r in rooms}
    pooja = byname.get("pooja_room")
    if pooja and not pooja.get("__is_carved", False):
        # Prayer room should open to the habitable side (typically dining/corridor),
        # not to facade/top by default.
        pooja["__door_wall"] = "left"

    kitchen = byname.get("kitchen")
    stair = byname.get("staircase")
    if kitchen and stair and not kitchen.get("__is_carved", False):
        kx1, ky1, kx2, ky2 = _rect(kitchen)
        sx1, sy1, sx2, sy2 = _rect(stair)
        # If stair touches kitchen at the seam, avoid a kitchen opening on that seam.
        if abs(ky1 - sy2) < tol and _overlap(kx1, kx2, sx1, sx2) > 14.0:
            kitchen["__door_wall"] = "right"

    for svc_name in ("common_bathroom", "utility_room"):
        svc = byname.get(svc_name)
        if svc and not svc.get("__is_carved", False):
            # Rear service rooms should open from the circulation/service strip.
            svc["__door_wall"] = "top"

    # Main entrance: add a wider door on foyer exterior (if present).
    # This is a drawing-only enhancement; it doesn't change layout connectivity.
    main_door_ft = float(parsed.get("main_door_width_ft", 4.0) or 4.0)
    main_door_px = max(32.0, min(main_door_ft * SCALE, 60.0))
    for r in rooms:
        n = str(r.get("name","")).lower()
        if r.get("__is_carved", False) or is_carved(n):
            continue
        if cat(n) != "foyer":
            continue
        # Editor may remove __main_door when the entrance is moved into placed_openings;
        # do not re-inject the default foyer main door on every preview in that case.
        if r.get("__suppress_foyer_main_door"):
            continue
        x1,y1,x2,y2 = _rect(r)
        ext_top, ext_bot, ext_left, ext_right = ext_walls_of(
            x1, y1, float(r["width"]), float(r["height"]), bx, by_, bw, bh, 0.0, 0.0
        )
        # Prefer top exterior, else any exterior wall.
        wall = "top" if ext_top else ("left" if ext_left else ("right" if ext_right else ("bot" if ext_bot else "")))
        if not wall:
            continue
        r["__main_door"] = wall
        r["__main_door_px"] = main_door_px

    for r in rooms:
        rn = str(r.get("name","")).lower()
        if r.get("__is_carved",False) or is_carved(rn): continue
        children = parent_to_carved.get(rn, [])
        svg.append(draw_room(r, ox, oy, floor_index, bx, by_, bw, bh,
                             carved_children=children if children else None))

    # ── Connectivity openings for passage spine ───────────────────────────────
    # Cut small wall gaps to make the rear passage spine feel open and connected.
    byname = {str(r.get("name","")).lower(): r for r in rooms}
    def _gap_h(xc: float, y: float, w: float = 28.0):
        """Punch a horizontal opening centered at (xc, y)."""
        svg.append(R(xc - w/2, y - INT_WALL * 1.2, w, INT_WALL * 2.4, WHITE, "none", 0))

    def _gap_v(x: float, yc: float, h: float = 28.0):
        """Punch a vertical opening centered at (x, yc)."""
        svg.append(R(x - INT_WALL * 1.2, yc - h/2, INT_WALL * 2.4, h, WHITE, "none", 0))

    def _rect0(r: Dict[str, Any]) -> Tuple[float, float, float, float]:
        """Room rect in SVG coordinates (x1,y1,x2,y2)."""
        x1 = ox + float(r["x"])
        y1 = oy + float(r["y"])
        x2 = x1 + float(r["width"])
        y2 = y1 + float(r["height"])
        return x1, y1, x2, y2

    def _ov(a1: float, a2: float, b1: float, b2: float) -> float:
        return min(a2, b2) - max(a1, b1)

    def _gap_if_touching_h(upper: Dict[str, Any], lower: Dict[str, Any], w: float = 30.0):
        """
        If upper.bottom touches lower.top with enough overlap, punch a gap at overlap center.
        Prevents accidental external wall holes when rooms aren't truly adjacent.
        """
        tol2 = 2.5
        ux1, uy1, ux2, uy2 = _rect0(upper)
        lx1, ly1, lx2, ly2 = _rect0(lower)
        if abs(uy2 - ly1) > tol2:
            return
        ov = _ov(ux1, ux2, lx1, lx2)
        if ov < 18.0:
            return
        xc = max(ux1, lx1) + ov * 0.5
        _gap_h(xc, ly1, w)

    def _gap_if_touching_v(left: Dict[str, Any], right: Dict[str, Any], h: float = 28.0):
        """
        If left.right touches right.left with enough overlap, punch a gap at overlap center.
        """
        tol2 = 2.5
        lx1, ly1, lx2, ly2 = _rect0(left)
        rx1, ry1, rx2, ry2 = _rect0(right)
        if abs(lx2 - rx1) > tol2:
            return
        ov = _ov(ly1, ly2, ry1, ry2)
        if ov < 18.0:
            return
        yc = max(ly1, ry1) + ov * 0.5
        _gap_v(rx1, yc, h)

    cor = byname.get("corridor")
    sp  = byname.get("service_passage")
    rp  = byname.get("rear_passage")
    cb  = byname.get("common_bathroom")
    ut  = byname.get("utility_room")
    if cor and sp:
        # corridor bottom → service_passage top (ONLY if they actually touch)
        _gap_if_touching_h(cor, sp, 30.0)
    if sp and rp:
        # service_passage bottom → rear_passage top (ONLY if they actually touch)
        _gap_if_touching_h(sp, rp, 30.0)
    if rp and cb:
        # rear_passage ↔ common_bathroom (ONLY if they actually touch)
        # Note: ordering (left/right) depends on layout; try both safely.
        _gap_if_touching_v(cb, rp, 28.0)
        _gap_if_touching_v(rp, cb, 28.0)
    # Open the passage → utility_room wall (was a solid black band)
    if sp and ut:
        _gap_if_touching_h(sp, ut, 28.0)
        _gap_if_touching_h(ut, sp, 28.0)
        _gap_if_touching_v(sp, ut, 28.0)
        _gap_if_touching_v(ut, sp, 28.0)
    if rp and ut:
        _gap_if_touching_h(rp, ut, 28.0)
        _gap_if_touching_h(ut, rp, 28.0)
        _gap_if_touching_v(rp, ut, 28.0)
        _gap_if_touching_v(ut, rp, 28.0)
    st = byname.get("staircase")
    if cor and st:
        # Ensure staircase entry is visibly from corridor (not read from kitchen seam).
        _gap_if_touching_v(st, cor, 30.0)
        _gap_if_touching_v(cor, st, 30.0)

    svg.append(corridor_service_seam_door_overlays(rooms, ox, oy))
    svg.append(dining_cluster_arch_openings(rooms, ox, oy))
    svg.append(
        master_store_access_door_overlay(
            rooms, ox, oy, parent_to_carved, bx, by_, bw, bh
        )
    )
    svg.append(rear_common_bathroom_door_overlay(rooms, ox, oy, bx, by_, bw, bh))
    svg.append(service_passage_bath_door_overlay(rooms, ox, oy, bx, by_, bw, bh))
    svg.append(upper_floor_terrace_access_overlay(rooms, ox, oy, floor_index))

    svg += [
        '</g>',
        # External boundary drawn OVER everything for clean edges
        draw_ext_boundary(bx, by_, bw, bh, ox, oy),
        draw_dims(plot_w, plot_h, bx, by_, bw, bh, pw_ft, pd_ft, ox, oy),
        draw_compass(ox+plot_w+40, oy+40, 24, facing),
        # Floor label
        R(ox+bx, oy+by_-22, 140, 19, fill=BLACK, stroke="none", sw=0),
        T(ox+bx+70, oy+by_-13, floor_label, 8, "700", WHITE),
    ]
    if floor_index == 0:
        # Entrance arrow: sits above the building, points DOWN toward it
        ex = ox+bx+bw/2; ey = oy+by_-18
        svg += [
            L(ex, ey, ex, ey+12, BLACK, 1.2),
            # Arrowhead points DOWN (toward building)
            f'<polygon points="{ex:.1f},{ey+12:.1f} {ex-4:.1f},{ey+5:.1f} {ex+4:.1f},{ey+5:.1f}" fill="{BLACK}"/>',
            T(ex, ey-5, "MAIN ENTRANCE", 6, "400", GRAY)
        ]
    svg.append(draw_title(ox+bx, title_y, bw, TITLE_H,
                          bhk, style, floor_label, pw_ft, pd_ft, vastu, budget))
    # After boundary / dims / labels / title so those layers never steal `.room-resize-handle` hits.
    svg.append(_all_room_resize_handles_overlay(rooms, ox, oy))
    svg.append("</g>")
    svg.append("</svg>")
    return "\n".join(svg)


def render_all_floors(per_floor_layouts, parsed):
    L={0:"GROUND FLOOR",1:"FIRST FLOOR",2:"SECOND FLOOR",3:"THIRD FLOOR"}
    return {k: render_floor_plan_svg(v, parsed, int(k), L.get(int(k),f"FLOOR {k}"))
            for k, v in per_floor_layouts.items()}


def render_floor_svg(
    *,
    parsed: Dict[str, Any],
    layout: Dict[str, Any],
    floor_index: int = 0,
    floor_label: str = "GROUND FLOOR",
) -> str:
    """Keyword API for floor_plan_generator — wraps render_floor_plan_svg."""
    return render_floor_plan_svg(layout, parsed, floor_index, floor_label)


def _strip_svg_inner(s: str) -> Tuple[str, float, float]:
    """Extract inner markup and size from a complete SVG document."""
    m = re.search(
        r'<svg[^>]*\bviewBox="0\s+0\s+([\d.]+)\s+([\d.]+)"',
        s,
        re.I,
    )
    if not m:
        return s, 800.0, 1000.0
    cw, ch = float(m.group(1)), float(m.group(2))
    lo = s.lower().find("<svg")
    if lo < 0:
        return s, cw, ch
    i = s.find(">", lo) + 1
    j = s.rfind("</svg>")
    if i <= 0 or j < i:
        return s, cw, ch
    return s[i:j].strip(), cw, ch


def render_combined_svg(
    *,
    parsed: Dict[str, Any],
    layouts: List[Tuple[str, Dict[str, Any]]],
) -> str:
    """Horizontal multi-floor sheet; used for combined SVG/PNG downloads."""
    if not layouts:
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 200" '
            f'width="400" height="200"><rect width="100%" height="100%" fill="{PAPER}"/>'
            f'<text x="200" y="100" text-anchor="middle" font-size="12" fill="{GRAY}">'
            f"No floors</text></svg>"
        )
    gap = 56.0
    pad = 48.0
    x_acc = pad
    blocks: List[str] = []
    max_h = 0.0
    for idx, (label, layout) in enumerate(layouts):
        doc = render_floor_plan_svg(layout, parsed, idx, label)
        frag, cw, ch = _strip_svg_inner(doc)
        blocks.append(f'<g transform="translate({x_acc:.2f},{pad:.2f})">{frag}</g>')
        x_acc += cw + gap
        max_h = max(max_h, ch)
    total_w = x_acc - gap + pad
    total_h = max_h + 2.0 * pad
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {total_w:.0f} {total_h:.0f}" '
        f'width="{total_w:.0f}" height="{total_h:.0f}" '
        f'preserveAspectRatio="xMidYMid meet">\n'
        f'<rect x="0" y="0" width="{total_w:.0f}" height="{total_h:.0f}" fill="{PAPER}"/>\n'
        + "\n".join(blocks)
        + "\n</svg>"
    )