"use client";

import React, { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";

function cloneLayout<T>(v: T): T {
  return JSON.parse(JSON.stringify(v)) as T;
}

/** Editor SVG lives inside `dangerouslySetInnerHTML`; ref sync can lag one frame — always resolve from the wrapper. */
function resolvePlanSvg(wrap: HTMLDivElement | null, hint: SVGSVGElement | null): SVGSVGElement | null {
  if (hint && wrap?.contains(hint)) return hint;
  const q = wrap?.querySelector("svg");
  return q instanceof SVGSVGElement ? q : null;
}

function roomIdFromDataAttr(rid: string | null): string {
  if (!rid) return "";
  return rid.replace(/-/g, "_");
}

/** Read root viewBox (or width/height) for mapping client pixels → SVG user units. */
function readSvgViewBoxRect(svg: SVGSVGElement): { x: number; y: number; width: number; height: number } {
  const vb = svg.viewBox?.baseVal;
  if (vb && vb.width > 0 && vb.height > 0) {
    return { x: vb.x, y: vb.y, width: vb.width, height: vb.height };
  }
  const w = Number.parseFloat(String(svg.getAttribute("width") ?? "").replace(/[^\d.+-]/g, "")) || 800;
  const h = Number.parseFloat(String(svg.getAttribute("height") ?? "").replace(/[^\d.+-]/g, "")) || 600;
  return { x: 0, y: 0, width: w, height: h };
}

/**
 * Map viewport (client) coordinates → root SVG user space.
 * Uses viewBox + getBoundingClientRect so pan/zoom CSS transforms on ancestors stay correct;
 * getScreenCTM().inverse() is unreliable when a parent has translate/scale (common in editors).
 */
function toSvgPoint(svg: SVGSVGElement, clientX: number, clientY: number): DOMPoint {
  const rect = svg.getBoundingClientRect();
  const vb = readSvgViewBoxRect(svg);
  if (rect.width <= 0 || rect.height <= 0 || vb.width <= 0 || vb.height <= 0) {
    const p = svg.createSVGPoint();
    p.x = clientX;
    p.y = clientY;
    const ctm = svg.getScreenCTM();
    if (!ctm) return new DOMPoint(clientX, clientY);
    return p.matrixTransform(ctm.inverse());
  }

  const par = (svg.getAttribute("preserveAspectRatio") || "xMidYMid meet").trim().split(/\s+/);
  const align = (par[0] || "xMidYMid").toLowerCase();
  const meetOrSlice = (par[1] || "meet").toLowerCase();
  const scale =
    meetOrSlice === "slice"
      ? Math.max(rect.width / vb.width, rect.height / vb.height)
      : Math.min(rect.width / vb.width, rect.height / vb.height);

  const innerW = vb.width * scale;
  const innerH = vb.height * scale;

  let offX = rect.left;
  let offY = rect.top;
  if (align.includes("mid")) {
    offX += (rect.width - innerW) / 2;
    offY += (rect.height - innerH) / 2;
  } else if (align.includes("max")) {
    offX += rect.width - innerW;
    offY += rect.height - innerH;
  }

  const x = vb.x + (clientX - offX) / scale;
  const y = vb.y + (clientY - offY) / scale;
  return new DOMPoint(x, y);
}

const SVG_NS = "http://www.w3.org/2000/svg";

function readEditorOffsets(svg: SVGSVGElement): { ox: number; oy: number; xShift: number } {
  return {
    ox: Number(svg.getAttribute("data-editor-ox") ?? 0),
    oy: Number(svg.getAttribute("data-editor-oy") ?? 0),
    xShift: Number(svg.getAttribute("data-editor-x-shift") ?? 0),
  };
}

/** Root SVG user units → layout JSON coordinates (matches room `x` / `y`). */
function rootSvgPointToLayout(svg: SVGSVGElement, pt: DOMPoint): { x: number; y: number } {
  const { ox, oy, xShift } = readEditorOffsets(svg);
  return { x: pt.x - xShift - ox, y: pt.y - oy };
}

function paintVoidSelectionOverlay(svg: SVGSVGElement, a: DOMPoint, b: DOMPoint) {
  const x = Math.min(a.x, b.x);
  const y = Math.min(a.y, b.y);
  const w = Math.max(Math.abs(b.x - a.x), 2);
  const h = Math.max(Math.abs(b.y - a.y), 2);
  let g = svg.querySelector("#void-region-draft");
  if (!g) {
    g = document.createElementNS(SVG_NS, "g");
    g.setAttribute("id", "void-region-draft");
    g.setAttribute("pointer-events", "none");
    svg.appendChild(g);
  }
  while (g.firstChild) g.removeChild(g.firstChild);
  const r = document.createElementNS(SVG_NS, "rect");
  r.setAttribute("x", String(x));
  r.setAttribute("y", String(y));
  r.setAttribute("width", String(w));
  r.setAttribute("height", String(h));
  r.setAttribute("fill", "rgba(90, 107, 74, 0.14)");
  r.setAttribute("stroke", "#5A6B4A");
  r.setAttribute("stroke-width", "1.5");
  r.setAttribute("stroke-dasharray", "5 4");
  g.appendChild(r);
}

function clearVoidSelectionOverlay(svg: SVGSVGElement | null) {
  svg?.querySelector("#void-region-draft")?.remove();
}

function clampRoomRect(
  x: number,
  y: number,
  w: number,
  h: number,
  bx: number,
  by: number,
  bw: number,
  bh: number,
  minW: number,
  minH: number,
): { x: number; y: number; width: number; height: number } {
  let nx = x;
  let ny = y;
  let nw = Math.max(minW, w);
  let nh = Math.max(minH, h);
  if (nx < bx) {
    nw -= bx - nx;
    nx = bx;
  }
  if (ny < by) {
    nh -= by - ny;
    ny = by;
  }
  nw = Math.max(minW, nw);
  nh = Math.max(minH, nh);
  if (nx + nw > bx + bw) nw = bx + bw - nx;
  if (ny + nh > by + bh) nh = by + bh - ny;
  nw = Math.max(minW, nw);
  nh = Math.max(minH, nh);
  if (nx + nw > bx + bw) nx = bx + bw - nw;
  if (ny + nh > by + bh) ny = by + bh - nh;
  nx = Math.max(bx, nx);
  ny = Math.max(by, ny);
  return { x: nx, y: ny, width: nw, height: nh };
}

function computeResizeRect(
  handle: string,
  x0: number,
  y0: number,
  w0: number,
  h0: number,
  lx: number,
  ly: number,
  bx: number,
  by: number,
  bw: number,
  bh: number,
  minW: number,
  minH: number,
): { x: number; y: number; width: number; height: number } {
  let x = x0;
  let y = y0;
  let w = w0;
  let h = h0;
  switch (handle) {
    case "se":
      w = lx - x0;
      h = ly - y0;
      break;
    case "e":
      w = lx - x0;
      h = h0;
      break;
    case "s":
      w = w0;
      h = ly - y0;
      break;
    case "w":
      x = lx;
      w = x0 + w0 - lx;
      h = h0;
      break;
    case "n":
      y = ly;
      w = w0;
      h = y0 + h0 - ly;
      break;
    case "nw":
      x = lx;
      y = ly;
      w = x0 + w0 - lx;
      h = y0 + h0 - ly;
      break;
    case "ne":
      y = ly;
      w = lx - x0;
      h = y0 + h0 - ly;
      break;
    case "sw":
      x = lx;
      w = x0 + w0 - lx;
      h = ly - y0;
      break;
    default:
      return clampRoomRect(x0, y0, w0, h0, bx, by, bw, bh, minW, minH);
  }
  return clampRoomRect(x, y, w, h, bx, by, bw, bh, minW, minH);
}

/**
 * Root SVG Δx/Δy along a drag equals layout Δx/Δy (only a constant x_shift is applied inside the plan `<g>`).
 * Map those deltas to the synthetic (lx, ly) that computeResizeRect expects, so stretch does not rely on
 * absolute svgRootToLayoutXY (which can disagree slightly with viewBox-based toSvgPoint under CSS pan/zoom).
 */
function layoutResizePointerFromDelta(
  handle: string,
  x0: number,
  y0: number,
  w0: number,
  h0: number,
  drx: number,
  dry: number,
): { lx: number; ly: number } {
  const h = handle.toLowerCase();
  switch (h) {
    case "e":
      return { lx: x0 + w0 + drx, ly: y0 };
    case "w":
      return { lx: x0 + drx, ly: y0 };
    case "s":
      return { lx: x0, ly: y0 + h0 + dry };
    case "n":
      return { lx: x0, ly: y0 + dry };
    case "se":
      return { lx: x0 + w0 + drx, ly: y0 + h0 + dry };
    case "nw":
      return { lx: x0 + drx, ly: y0 + dry };
    case "ne":
      return { lx: x0 + w0 + drx, ly: y0 + dry };
    case "sw":
      return { lx: x0 + drx, ly: y0 + h0 + dry };
    default:
      return { lx: x0 + w0 + drx, ly: y0 + h0 + dry };
  }
}

function applyRoomSizeDerivedFields(room: RoomRec, scalePxPerFt: number) {
  const rw = Number(room.width ?? 0);
  const rh = Number(room.height ?? 0);
  const sc = scalePxPerFt > 0 ? scalePxPerFt : 10;
  room.width_ft = Math.round((rw / sc) * 100) / 100;
  room.depth_ft = Math.round((rh / sc) * 100) / 100;
  room.area_sqft = Math.round((rw / sc) * (rh / sc) * 10) / 10;
}

/** Scale carved sub-zones that lay inside the pre-resize parent footprint (attached bath / WIC). */
function scaleCarvedInsideParentBounds(
  rooms: unknown[],
  px0: number,
  py0: number,
  pw0: number,
  ph0: number,
  nx: number,
  ny: number,
  nw: number,
  nh: number,
  scalePxPerFt: number,
) {
  const pw = Math.max(pw0, 1e-6);
  const ph = Math.max(ph0, 1e-6);
  const rx = nw / pw;
  const ry = nh / ph;
  for (const r of rooms) {
    if (!r || typeof r !== "object") continue;
    const rec = r as RoomRec;
    if (rec.__is_carved !== true) continue;
    const cx = Number(rec.x ?? 0);
    const cy = Number(rec.y ?? 0);
    const cw = Number(rec.width ?? 0);
    const ch = Number(rec.height ?? 0);
    if (cx + cw > px0 + pw + 0.5 || cy + ch > py0 + ph + 0.5 || cx < px0 - 0.5 || cy < py0 - 0.5) continue;
    const relx = cx - px0;
    const rely = cy - py0;
    rec.x = nx + relx * rx;
    rec.y = ny + rely * ry;
    rec.width = cw * rx;
    rec.height = ch * ry;
    applyRoomSizeDerivedFields(rec, scalePxPerFt);
  }
}

function ensureResizePreviewRect(roomG: SVGGElement): SVGRectElement {
  let el = roomG.querySelector("rect.room-resize-live-outline") as SVGRectElement | null;
  if (!el) {
    el = document.createElementNS(SVG_NS, "rect");
    el.setAttribute("class", "room-resize-live-outline");
    el.setAttribute("fill", "none");
    el.setAttribute("stroke", "#5A6B4A");
    el.setAttribute("stroke-width", "2");
    el.setAttribute("stroke-dasharray", "6 4");
    el.setAttribute("pointer-events", "none");
    roomG.appendChild(el);
  }
  return el;
}

function removeResizePreviewRect(roomG: SVGGElement) {
  roomG.querySelector("rect.room-resize-live-outline")?.remove();
}

function layoutScale(L: Record<string, unknown>): number {
  const s = Number(L.scale ?? 10);
  return s > 0 ? s : 10;
}

function newOpeningId(): string {
  return `op_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 7)}`;
}

/** Strip deprecated editor_furniture; keep layout aligned with server SVG. */
function normalizeLayout(lf: Record<string, unknown>): Record<string, unknown> {
  const c = cloneLayout(lf);
  delete c.editor_furniture;
  return c;
}

type RoomRec = Record<string, unknown>;
type PlacedOpening = { id: string; edge: string; u: number; kind: "door" | "window"; width_px?: number };

function distToSegment(px: number, py: number, x1: number, y1: number, x2: number, y2: number): number {
  const dx = x2 - x1;
  const dy = y2 - y1;
  const len2 = dx * dx + dy * dy;
  if (len2 < 1e-9) return Math.hypot(px - x1, py - y1);
  let t = ((px - x1) * dx + (py - y1) * dy) / len2;
  t = Math.max(0, Math.min(1, t));
  const qx = x1 + t * dx;
  const qy = y1 + t * dy;
  return Math.hypot(px - qx, py - qy);
}

/** Client (viewport) → room group's local SVG coordinates; works with CSS pan/zoom on ancestors. */
function clientPointToRoomLocal(roomG: SVGGElement, clientX: number, clientY: number): DOMPoint | null {
  try {
    const m = (roomG as unknown as SVGGraphicsElement).getScreenCTM?.();
    if (!m) return null;
    return new DOMPoint(clientX, clientY).matrixTransform(m.inverse());
  } catch {
    return null;
  }
}

/** Match `draw_door` default leaf width (no width_override). */
function defaultDoorWidthPx(rw: number, rh: number): number {
  let dw: number;
  if (rw < 60 || rh < 60) {
    dw = Math.max(Math.min(rw * 0.38, 22), 14);
  } else {
    dw = Math.max(Math.min(rw * 0.28, 32), 20);
  }
  return Math.min(dw, rw * 0.42, rh * 0.42);
}

/** Match `draw_window` single-pane width for the given wall orientation (count=1). */
function defaultWindowPanePx(rw: number, rh: number, edge: string): number {
  const e = edge.toLowerCase();
  const span = e === "top" || e === "bot" || e === "bottom" ? rw * 0.62 : rh * 0.58;
  return Math.max(Math.min(span, 36), 14);
}

function findMainRoomRect(g: SVGGElement): { x: number; y: number; width: number; height: number } | null {
  let best: { x: number; y: number; width: number; height: number } | null = null;
  let bestArea = 0;
  for (const ch of Array.from(g.children)) {
    if (ch instanceof SVGRectElement) {
      const w = ch.width.baseVal.value;
      const h = ch.height.baseVal.value;
      const a = w * h;
      // Skip editor / UI chrome rects so we keep the true room slab (kitchen, pooja, etc.).
      const cls = (ch.getAttribute("class") || "").toLowerCase();
      if (cls.includes("furniture-resize")) continue;
      if (cls.includes("room-resize")) continue;
      if (a > bestArea && w > 12 && h > 12) {
        bestArea = a;
        best = { x: ch.x.baseVal.value, y: ch.y.baseVal.value, width: w, height: h };
      }
    }
  }
  return best;
}

/**
 * Largest floor slab rect in the room group (walks nested `<g>`), excluding furniture/cars
 * so parking symbols on car porch do not steal the footprint from wall snapping.
 */
function findMainRoomRectDeep(g: SVGGElement): { x: number; y: number; width: number; height: number } | null {
  let best: { x: number; y: number; width: number; height: number } | null = null;
  let bestArea = 0;
  const walk = (node: Element) => {
    if (node instanceof SVGRectElement) {
      const cls = (node.getAttribute("class") || "").toLowerCase();
      if (cls.includes("furniture-resize")) return;
      if (cls.includes("room-resize")) return;
      if (node.closest(".editable-furniture-stack")) return;
      const w = node.width.baseVal.value;
      const h = node.height.baseVal.value;
      const a = w * h;
      if (a > bestArea && w > 12 && h > 12) {
        bestArea = a;
        best = { x: node.x.baseVal.value, y: node.y.baseVal.value, width: w, height: h };
      }
    }
    for (const ch of Array.from(node.children)) walk(ch);
  };
  walk(g);
  return best;
}

/** Nearest wall on one room group (client coords → room local via getScreenCTM). */
function snapWallForRoom(
  roomG: SVGGElement,
  clientX: number,
  clientY: number,
  tol = 48,
): { edge: string; u: number; dist: number } | null {
  const p = clientPointToRoomLocal(roomG, clientX, clientY);
  if (!p) return null;
  // Prefer painted DOM footprint (matches pointer CTM).
  const geom = findMainRoomRectDeep(roomG) ?? findMainRoomRect(roomG) ?? null;
  if (!geom) return null;
  const { x: rx, y: ry, width: rw, height: rh } = geom;
  const x2 = rx + rw;
  const y2 = ry + rh;
  const pad = 18;
  let best = { d: tol + 1, edge: "top", u: 0.5 };
  const tests: Array<{ edge: string; u: number; d: number }> = [
    {
      edge: "top",
      u: rw > 2 * pad ? Math.max(0, Math.min(1, (p.x - rx - pad) / Math.max(0.01, rw - 2 * pad))) : 0.5,
      d: distToSegment(p.x, p.y, rx, ry, x2, ry),
    },
    {
      edge: "bot",
      u: rw > 2 * pad ? Math.max(0, Math.min(1, (p.x - rx - pad) / Math.max(0.01, rw - 2 * pad))) : 0.5,
      d: distToSegment(p.x, p.y, rx, y2, x2, y2),
    },
    {
      edge: "left",
      u: rh > 2 * pad ? Math.max(0, Math.min(1, (p.y - ry - pad) / Math.max(0.01, rh - 2 * pad))) : 0.5,
      d: distToSegment(p.x, p.y, rx, ry, rx, y2),
    },
    {
      edge: "right",
      u: rh > 2 * pad ? Math.max(0, Math.min(1, (p.y - ry - pad) / Math.max(0.01, rh - 2 * pad))) : 0.5,
      d: distToSegment(p.x, p.y, x2, ry, x2, y2),
    },
  ];
  for (const t of tests) {
    if (t.d < best.d) best = { d: t.d, edge: t.edge, u: t.u };
  }
  if (best.d <= tol) {
    return { edge: best.edge, u: best.u, dist: best.d };
  }
  // Any click inside the slab: snap to nearest wall (place-door / move-opening must work
  // from the room interior, not only on the thin wall strip).
  if (p.x >= rx && p.x <= x2 && p.y >= ry && p.y <= y2) {
    return { edge: best.edge, u: best.u, dist: best.d };
  }
  // Fat-finger band just outside the perimeter (still this room only).
  const frame = Math.max(40, Math.min(90, tol * 1.2));
  if (
    p.x >= rx - frame &&
    p.x <= x2 + frame &&
    p.y >= ry - frame &&
    p.y <= y2 + frame &&
    best.d <= tol + frame
  ) {
    return { edge: best.edge, u: best.u, dist: best.d };
  }
  return null;
}

/** Snap pointer to nearest room wall; returns edge in server convention (top/bot/left/right) and u along wall. */
function snapWallFromPoint(
  svg: SVGSVGElement,
  clientX: number,
  clientY: number,
  tol = 48,
): { roomName: string; edge: string; u: number } | null {
  const primary = findEditableRoomFromPointForWallTools(svg, clientX, clientY);
  const primaryName = primary
    ? roomIdFromDataAttr(primary.getAttribute("data-room-id")).toLowerCase()
    : "";

  type Cand = { roomName: string; edge: string; u: number; dist: number };
  const cand: Cand[] = [];
  for (const g of Array.from(svg.querySelectorAll(".editable-room"))) {
    if (!(g instanceof SVGGElement)) continue;
    if (g.getAttribute("data-editable") === "false") continue;
    const rid = g.getAttribute("data-room-id");
    if (!rid) continue;
    const rname = roomIdFromDataAttr(rid);
    const hit = snapWallForRoom(g, clientX, clientY, tol);
    if (!hit) continue;
    cand.push({ roomName: rname, edge: hit.edge, u: hit.u, dist: hit.dist });
  }
  if (cand.length === 0) return null;
  const dMin = Math.min(...cand.map((c) => c.dist));
  const eps = 3;
  const tight = cand.filter((c) => c.dist <= dMin + eps);
  if (primaryName) {
    const pref = tight.find((c) => c.roomName.toLowerCase() === primaryName);
    if (pref) return { roomName: pref.roomName, edge: pref.edge, u: pref.u };
  }
  tight.sort((a, b) => a.dist - b.dist || a.roomName.localeCompare(b.roomName));
  const best = tight[0];
  return { roomName: best.roomName, edge: best.edge, u: best.u };
}

function roomHyphenIdFromUnderscore(roomNameUnderscore: string): string {
  return roomNameUnderscore.replace(/_/g, "-").toLowerCase();
}

/** Find `.editable-room` group whose `data-room-id` matches layout `name` (underscores vs hyphens). */
function findEditableRoomGroup(svg: SVGSVGElement, roomNameUnderscore: string): SVGGElement | null {
  const want = roomHyphenIdFromUnderscore(roomNameUnderscore);
  for (const g of Array.from(svg.querySelectorAll(".editable-room"))) {
    if (!(g instanceof SVGGElement)) continue;
    const rid = (g.getAttribute("data-room-id") || "").toLowerCase();
    if (rid === want) return g;
  }
  return null;
}

/**
 * Wall snap for place-door / place-window: prefer the room chosen in the dropdown, else the room
 * under the pointer, else nearest wall globally (avoids attaching to a neighbour like pooja).
 */
function snapWallPlacement(
  svg: SVGSVGElement,
  clientX: number,
  clientY: number,
  selectedRoomUnderscore: string,
  eventTarget: Element | null,
): { roomName: string; edge: string; u: number } | null {
  const wallSnapTols = [52, 88, 120, 160, 220, 280] as const;

  const tryRoom = (g: SVGGElement): { roomName: string; edge: string; u: number } | null => {
    if (g.getAttribute("data-editable") === "false") return null;
    const rid = g.getAttribute("data-room-id");
    if (!rid) return null;
    const rname = roomIdFromDataAttr(rid);
    // Rely on painted DOM (findMainRoomRectDeep) so CTM + footprint match the click; layout
    // JSON can drift from SVG and broke wall tools on many rooms.
    for (const tol of wallSnapTols) {
      const hit = snapWallForRoom(g, clientX, clientY, tol);
      if (hit) return { roomName: rname, edge: hit.edge, u: hit.u };
    }
    return null;
  };

  const sel = selectedRoomUnderscore.trim();
  if (sel) {
    const g = findEditableRoomGroup(svg, sel);
    if (g) {
      const r = tryRoom(g);
      if (r) return r;
      // Do not bail out: user may have clicked the floor slab while a room is selected —
      // fall through to under-pointer / global snap with the same tolerances.
    }
  }

  const under =
    resolveRoomGroupFromEventTarget(svg, eventTarget) ??
    findEditableRoomFromPointForWallTools(svg, clientX, clientY);
  if (under) {
    const r = tryRoom(under);
    if (r) return r;
  }

  for (const tol of [48, 80, 120, 160, 220] as const) {
    const w = snapWallFromPoint(svg, clientX, clientY, tol);
    if (w) return w;
  }
  return null;
}

/** Resolve `.editable-room` from hit stack (SVG root may not be `event.target` when nested). */
function findEditableRoomFromPoint(svg: SVGSVGElement, clientX: number, clientY: number): SVGGElement | null {
  if (typeof document === "undefined" || typeof document.elementsFromPoint !== "function") return null;
  for (const node of document.elementsFromPoint(clientX, clientY)) {
    if (!(node instanceof Element)) continue;
    if (!svg.contains(node)) continue;
    const rg = node.closest(".editable-room");
    if (rg instanceof SVGGElement && rg.getAttribute("data-editable") !== "false") return rg;
  }
  return null;
}

/**
 * Like `findEditableRoomFromPoint`, but for wall tools: resize handles sit in a global overlay on
 * top of walls/seams (not under `.editable-room`) yet carry `data-room-id` — use that so place-door
 * / place-window still snap when the user clicks the wall band.
 */
function findEditableRoomFromPointForWallTools(
  svg: SVGSVGElement,
  clientX: number,
  clientY: number,
): SVGGElement | null {
  if (typeof document === "undefined" || typeof document.elementsFromPoint !== "function") return null;
  for (const node of document.elementsFromPoint(clientX, clientY)) {
    if (!(node instanceof Element)) continue;
    if (!svg.contains(node)) continue;
    const hr = node.closest(".room-resize-handle");
    if (hr) {
      const hid = hr.getAttribute("data-room-id");
      if (hid) {
        const g = findEditableRoomGroup(svg, roomIdFromDataAttr(hid));
        if (g) return g;
      }
      continue;
    }
    if (node.closest(".room-resize-live-outline")) continue;
    const rg = node.closest(".editable-room");
    if (rg instanceof SVGGElement && rg.getAttribute("data-editable") !== "false") return rg;
  }
  return null;
}

function resolveRoomGroupFromEventTarget(svg: SVGSVGElement, eventTarget: Element | null): SVGGElement | null {
  const g0 = eventTarget?.closest?.(".editable-room");
  if (g0 instanceof SVGGElement && g0.getAttribute("data-editable") !== "false") return g0;
  const hr = eventTarget?.closest?.(".room-resize-handle");
  if (hr) {
    const hid = hr.getAttribute("data-room-id");
    if (hid) {
      const g = findEditableRoomGroup(svg, roomIdFromDataAttr(hid));
      if (g) return g;
    }
  }
  return null;
}

/** Snap point on room perimeter in SVG user space (same coords as `findMainRoomRectDeep`). */
function wallAnchorSvgPoint(
  geom: { x: number; y: number; width: number; height: number },
  edge: string,
  u: number,
): { ax: number; ay: number } {
  const { x: rx, y: ry, width: rw, height: rh } = geom;
  const x2 = rx + rw;
  const y2 = ry + rh;
  const pad = 18;
  const e = edge.toLowerCase();
  const spanH = Math.max(0.01, rw - 2 * pad);
  const spanV = Math.max(0.01, rh - 2 * pad);
  if (e === "top") return { ax: rx + pad + spanH * u, ay: ry };
  if (e === "bot" || e === "bottom") return { ax: rx + pad + spanH * u, ay: y2 };
  if (e === "left") return { ax: rx, ay: ry + pad + spanV * u };
  return { ax: x2, ay: ry + pad + spanV * u };
}

/** Position for a hover marker inside `wrap` (absolute px). */
function placePreviewDotInWrap(
  svg: SVGSVGElement,
  wrap: HTMLDivElement,
  snap: { roomName: string; edge: string; u: number },
): { left: number; top: number } | null {
  const g = findEditableRoomGroup(svg, snap.roomName);
  if (!g) return null;
  const geom = findMainRoomRectDeep(g) ?? findMainRoomRect(g);
  if (!geom) return null;
  const { ax, ay } = wallAnchorSvgPoint(geom, snap.edge, snap.u);
  const pt = svg.createSVGPoint();
  pt.x = ax;
  pt.y = ay;
  const ctm = svg.getScreenCTM();
  if (!ctm) return null;
  const scr = pt.matrixTransform(ctm);
  const wb = wrap.getBoundingClientRect();
  return {
    left: scr.x - wb.left + wrap.scrollLeft,
    top: scr.y - wb.top + wrap.scrollTop,
  };
}

/** Topmost `.room-resize-handle` under the pointer (handles may be in a global overlay). */
function findResizeHandleFromPoint(svg: SVGSVGElement, clientX: number, clientY: number): SVGGraphicsElement | null {
  if (typeof document === "undefined" || typeof document.elementsFromPoint !== "function") return null;
  for (const node of document.elementsFromPoint(clientX, clientY)) {
    if (!(node instanceof Element)) continue;
    const h = node.closest(".room-resize-handle");
    if (!(h instanceof SVGGraphicsElement)) continue;
    // Prefer ownerSVGElement — svg.contains can be flaky for detached / shadow edge cases.
    if (h.ownerSVGElement !== svg && !svg.contains(h)) continue;
    return h;
  }
  return null;
}

/** Hit-test openings even when a room floor rect is painted above them in the stack. */
function findOpeningGroupFromPoint(svg: SVGSVGElement, clientX: number, clientY: number): SVGGElement | null {
  if (typeof document === "undefined" || typeof document.elementsFromPoint !== "function") return null;
  for (const node of document.elementsFromPoint(clientX, clientY)) {
    if (!(node instanceof Element)) continue;
    if (!svg.contains(node)) continue;
    const og = node.closest(".editable-placed-opening, .editable-sys-opening");
    if (og instanceof SVGGElement && svg.contains(og)) return og;
  }
  return null;
}

function furnitureTransformMatrix(tx: number, ty: number, s: number, rcx: number, rcy: number): string {
  const sc = Math.max(0.35, Math.min(2.5, s));
  return `translate(${tx},${ty}) translate(${rcx},${rcy}) scale(${sc}) translate(${-rcx},${-rcy})`;
}

function readFurnitureTransform(room: RoomRec): { tx: number; ty: number; s: number } {
  const ft = room.furniture_transform;
  if (!ft || typeof ft !== "object") return { tx: 0, ty: 0, s: 1 };
  const o = ft as Record<string, unknown>;
  const tx = Number(o.tx ?? 0);
  const ty = Number(o.ty ?? 0);
  const s = Number(o.s ?? 1);
  return {
    tx: Number.isFinite(tx) ? tx : 0,
    ty: Number.isFinite(ty) ? ty : 0,
    s: Number.isFinite(s) && s > 0 ? Math.max(0.35, Math.min(2.5, s)) : 1,
  };
}

export interface LayoutEditorPhaseAProps {
  floorKey: string;
  floorIndex: number;
  layoutFloor: Record<string, unknown>;
  initialSvg: string;
  parsed: Record<string, unknown>;
  apiBase: string;
  onThreeDHtml?: (floorKey: string, html: string) => void;
}

const C = {
  paper:    "#FAF7F2",
  border:   "#DDD6CA",
  ink:      "#2C2820",
  inkMid:   "#6B6258",
  inkLight: "#9A9080",
  accent:   "#5A6B4A",
  headerBg: "#F2EDE4",
};

export function LayoutEditorPhaseA({
  floorKey,
  floorIndex,
  layoutFloor,
  initialSvg,
  parsed,
  apiBase,
  onThreeDHtml,
}: LayoutEditorPhaseAProps) {
  const [layout, setLayout] = useState<Record<string, unknown>>(() => normalizeLayout(layoutFloor));
  const [svgPreview, setSvgPreview] = useState(initialSvg);
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [panMode, setPanMode] = useState(false);
  const [previewing, setPreviewing] = useState(false);
  const [err, setErr] = useState("");
  const [status, setStatus] = useState("");
  const [placeKind, setPlaceKind] = useState<null | "door" | "window">(null);
  const [placeHover, setPlaceHover] = useState<null | { left: number; top: number }>(null);
  const [furnitureEdit, setFurnitureEdit] = useState(false);
  const [selectedRoom, setSelectedRoom] = useState("");
  const [voidSelectMode, setVoidSelectMode] = useState(false);
  const [voidModal, setVoidModal] = useState<null | { x: number; y: number; width: number; height: number }>(null);
  const [voidPrompt, setVoidPrompt] = useState("");
  const [voidSubmitting, setVoidSubmitting] = useState(false);
  const [editorCanvasFullscreen, setEditorCanvasFullscreen] = useState(false);

  const wrapRef = useRef<HTMLDivElement>(null);
  const svgRef = useRef<SVGSVGElement | null>(null);
  const layoutRef = useRef(layout);
  layoutRef.current = layout;

  useEffect(() => {
    if (!editorCanvasFullscreen) return;
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = prev;
    };
  }, [editorCanvasFullscreen]);

  useEffect(() => {
    if (!editorCanvasFullscreen) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== "Escape") return;
      if (voidModal) return;
      setEditorCanvasFullscreen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [editorCanvasFullscreen, voidModal]);

  const dragRaf = useRef<number | null>(null);
  const dragRef = useRef<
    | {
        kind: "room";
        pointerId: number;
        roomName: string;
        el: SVGGElement;
        last: DOMPoint;
        accX: number;
        accY: number;
      }
    | {
        kind: "opening";
        pointerId: number;
        roomName: string;
        roomEl: SVGGElement;
        el: SVGGElement;
        last: DOMPoint;
        accX: number;
        accY: number;
        openingKind: "placed" | "sys";
        placedId: string;
        sysSlot: string;
        sysKind: "door" | "window";
      }
    | {
        kind: "pan";
        pointerId: number;
        lastClientX: number;
        lastClientY: number;
      }
    | {
        kind: "furniture_move";
        pointerId: number;
        roomName: string;
        layerEl: SVGGElement;
        last: DOMPoint;
        accX: number;
        accY: number;
        baseTx: number;
        baseTy: number;
        s: number;
        rcx: number;
        rcy: number;
      }
    | {
        kind: "furniture_res";
        pointerId: number;
        roomName: string;
        layerEl: SVGGElement;
        startClientY: number;
        moveClientY: number;
        baseS: number;
        baseTx: number;
        baseTy: number;
        rcx: number;
        rcy: number;
      }
    | {
        kind: "room_resize";
        pointerId: number;
        roomName: string;
        roomEl: SVGGElement;
        handle: string;
        ox: number;
        oy: number;
        x0: number;
        y0: number;
        w0: number;
        h0: number;
        bx: number;
        by: number;
        bw: number;
        bh: number;
        minW: number;
        minH: number;
        lastGeom: { x: number; y: number; width: number; height: number };
        rootStartX: number;
        rootStartY: number;
      }
    | {
        kind: "void_region";
        pointerId: number;
        svg: SVGSVGElement;
        start: DOMPoint;
        last: DOMPoint;
      }
    | null
  >(null);

  const base = apiBase.trim().replace(/\/+$/, "");

  useEffect(() => {
    setLayout(normalizeLayout(layoutFloor));
    setSvgPreview(initialSvg);
    setPan({ x: 0, y: 0 });
    setZoom(1);
    setErr("");
    setStatus("");
    setPlaceKind(null);
    setPlaceHover(null);
    setSelectedRoom("");
    setFurnitureEdit(false);
    setVoidSelectMode(false);
    setVoidModal(null);
    setVoidPrompt("");
    setVoidSubmitting(false);
  }, [layoutFloor, initialSvg]);

  useEffect(() => {
    if (!placeKind) setPlaceHover(null);
  }, [placeKind]);

  useLayoutEffect(() => {
    const w = wrapRef.current;
    if (!w) return;
    const svg = w.querySelector("svg");
    svgRef.current = svg instanceof SVGSVGElement ? svg : null;
  }, [svgPreview]);

  useEffect(() => {
    const w = wrapRef.current;
    const svg = resolvePlanSvg(w, svgRef.current);
    clearVoidSelectionOverlay(svg);
  }, [svgPreview]);

  const scheduleDragPaint = useCallback(() => {
    if (dragRaf.current != null) return;
    dragRaf.current = requestAnimationFrame(() => {
      dragRaf.current = null;
      const d = dragRef.current;
      if (!d) return;
      if (d.kind === "furniture_move") {
        d.layerEl.setAttribute(
          "transform",
          furnitureTransformMatrix(d.baseTx + d.accX, d.baseTy + d.accY, d.s, d.rcx, d.rcy),
        );
        return;
      }
      if (d.kind === "furniture_res") {
        const dy = d.startClientY - d.moveClientY;
        const nextS = Math.max(0.35, Math.min(2.5, d.baseS * (1 + dy * 0.002)));
        d.layerEl.setAttribute(
          "transform",
          furnitureTransformMatrix(d.baseTx, d.baseTy, nextS, d.rcx, d.rcy),
        );
        return;
      }
      if (d.kind === "room_resize") {
        const g = d.lastGeom;
        const pre = ensureResizePreviewRect(d.roomEl);
        pre.setAttribute("x", String(g.x + d.ox));
        pre.setAttribute("y", String(g.y + d.oy));
        pre.setAttribute("width", String(g.width));
        pre.setAttribute("height", String(g.height));
        return;
      }
      if (d.kind !== "room" && d.kind !== "opening") return;
      d.el.setAttribute("transform", `translate(${d.accX},${d.accY})`);
    });
  }, []);

  const clampRoom = useCallback((room: RoomRec, L: Record<string, unknown>) => {
    const bx = Number(L.built_up_x ?? 0);
    const by = Number(L.built_up_y ?? 0);
    const bw = Number(L.built_up_w ?? 1);
    const bh = Number(L.built_up_h ?? 1);
    const rw = Number(room.width ?? 0);
    const rh = Number(room.height ?? 0);
    let x = Number(room.x ?? 0);
    let y = Number(room.y ?? 0);
    x = Math.max(bx, Math.min(x, bx + bw - rw));
    y = Math.max(by, Math.min(y, by + bh - rh));
    room.x = x;
    room.y = y;
  }, []);

  const postPreview = useCallback(
    async (include3d: boolean, layoutPayload?: Record<string, unknown>) => {
      const L = layoutPayload ?? layoutRef.current;
      setPreviewing(true);
      setErr("");
      try {
        const res = await fetch(`${base}/api/layout/render-preview`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            parsed,
            floor_index: floorIndex,
            layout: L,
            include_3d: include3d,
          }),
        });
        const data = (await res.json()) as Record<string, unknown>;
        if (!res.ok) {
          const d = data?.detail;
          throw new Error(typeof d === "string" ? d : JSON.stringify(d ?? res.status));
        }
        const svg = String(data.svg ?? "");
        if (!svg.includes("<svg")) throw new Error("Server did not return SVG");
        setSvgPreview(svg);
        setStatus(include3d ? "SVG + 3D updated." : "Plan updated.");
        if (include3d && data.html_3d && typeof data.html_3d === "string" && data.html_3d.length > 50) {
          onThreeDHtml?.(floorKey, data.html_3d);
        } else if (include3d && data.html_3d_error) {
          setErr(String(data.html_3d_error));
        }
      } catch (e) {
        setErr(e instanceof Error ? e.message : String(e));
      } finally {
        setPreviewing(false);
      }
    },
    [base, parsed, floorIndex, floorKey, onThreeDHtml],
  );

  const submitVoidRoomProposal = useCallback(async () => {
    if (!voidModal || !voidPrompt.trim()) {
      setErr("Describe the room you want (for example: small guest bedroom with north light).");
      return;
    }
    setVoidSubmitting(true);
    setErr("");
    try {
      const res = await fetch(`${base}/api/layout/propose-room-in-region`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          parsed,
          floor_index: floorIndex,
          layout: layoutRef.current,
          region: voidModal,
          user_prompt: voidPrompt.trim(),
        }),
      });
      const data = (await res.json()) as Record<string, unknown>;
      if (!res.ok) {
        const d = data?.detail;
        throw new Error(typeof d === "string" ? d : JSON.stringify(d ?? res.status));
      }
      const next = data.layout as Record<string, unknown>;
      if (!next || !Array.isArray(next.rooms)) throw new Error("Invalid response layout.");
      const rn = String((data.room as Record<string, unknown> | undefined)?.name ?? "room");
      const reasoning = String(data.reasoning ?? "");
      const used = data.used_llm === true ? "LLM" : "keyword map";
      setLayout(next);
      setVoidModal(null);
      setVoidPrompt("");
      setVoidSelectMode(false);
      setStatus(
        `Added "${rn.replace(/_/g, " ")}" (${used}). ${reasoning.slice(0, 340)}${reasoning.length > 340 ? "…" : ""}`,
      );
      await postPreview(false, next);
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setVoidSubmitting(false);
    }
  }, [base, parsed, floorIndex, voidModal, voidPrompt, postPreview]);

  const findRoomByName = useCallback(
    (name: string): RoomRec | null => {
      const rooms = layout.rooms;
      if (!Array.isArray(rooms)) return null;
      const target = name.toLowerCase();
      for (const r of rooms) {
        if (r && typeof r === "object") {
          const rn = String((r as RoomRec).name ?? "").toLowerCase();
          if (rn === target) return r as RoomRec;
        }
      }
      return null;
    },
    [layout],
  );

  const clearPlacedForSelectedRoom = useCallback(() => {
    if (!selectedRoom) {
      setErr("Pick a room in the list first.");
      return;
    }
    const next = cloneLayout(layoutRef.current);
    const rooms = next.rooms;
    if (!Array.isArray(rooms)) return;
    const t = selectedRoom.toLowerCase();
    for (const r of rooms) {
      const rec = r as RoomRec;
      if (String(rec.name ?? "").toLowerCase() !== t) continue;
      rec.placed_openings = [];
      delete rec.__suppress_foyer_main_door;
      break;
    }
    setLayout(next);
    void postPreview(false, next);
    setErr("");
    setStatus(`Cleared placed openings for ${selectedRoom}.`);
  }, [selectedRoom, postPreview]);

  const onPointerDown = (e: React.PointerEvent<HTMLDivElement>) => {
    if (previewing) return;
    const wrap = wrapRef.current;
    const svg = resolvePlanSvg(wrap, svgRef.current);
    if (svg) svgRef.current = svg;

    if (placeKind) {
      if (e.button !== 0) {
        e.preventDefault();
        return;
      }
      if (!svg) {
        setErr("Floor plan SVG is not ready yet. Click Re-render SVG or wait a moment, then try again.");
        e.preventDefault();
        return;
      }
      const pk = placeKind;
      const snap = snapWallPlacement(
        svg,
        e.clientX,
        e.clientY,
        selectedRoom,
        (e.target as Element | null) ?? null,
      );
      if (snap) {
        const next = cloneLayout(layoutRef.current);
        const rooms = next.rooms;
        let matched = false;
        if (Array.isArray(rooms)) {
          const target = snap.roomName.toLowerCase();
          for (const r of rooms) {
            const rec = r as RoomRec;
            if (String(rec.name ?? "").toLowerCase() !== target) continue;
            matched = true;
            const rw = Number(rec.width ?? 0);
            const rh = Number(rec.height ?? 0);
            const list = (Array.isArray(rec.placed_openings)
              ? [...(rec.placed_openings as PlacedOpening[])]
              : []) as PlacedOpening[];
            list.push({
              id: newOpeningId(),
              edge: snap.edge,
              u: snap.u,
              kind: pk,
              width_px: pk === "door" ? defaultDoorWidthPx(rw, rh) : defaultWindowPanePx(rw, rh, snap.edge),
            });
            rec.placed_openings = list as unknown[];
            break;
          }
        }
        if (!matched) {
          setErr(
            `Snapped to SVG room "${snap.roomName}" but that name is missing from the layout JSON. Re-render SVG or reset layout.`,
          );
          e.preventDefault();
          return;
        }
        setLayout(next);
        setPlaceKind(null);
        setPlaceHover(null);
        void postPreview(false, next);
        setStatus(`Placed ${pk} on ${snap.roomName} (${snap.edge}).`);
      } else {
        setErr(
          selectedRoom.trim()
            ? `Could not place on a wall of the selected room (${selectedRoom.replace(/_/g, " ")}). Click inside that room's floor area.`
            : "Could not detect a room under the click. Click inside a room's floor, or pick a target room in the list first.",
        );
      }
      e.preventDefault();
      return;
    }

    if (!svg) return;

    const el = e.target as Element | null;

    if (furnitureEdit && !placeKind) {
      // Walls, labels, and openings are painted above furniture; `e.target` is often not inside
      // the furniture stack. Walk the hit stack so we still pick up the layer/handle underneath.
      const els =
        typeof document !== "undefined" && typeof document.elementsFromPoint === "function"
          ? document.elementsFromPoint(e.clientX, e.clientY)
          : el
            ? [el]
            : [];
      let stack: SVGGElement | null = null;
      let hitNode: Element | null = null;
      for (const node of els) {
        if (!(node instanceof Element)) continue;
        if (!svg.contains(node)) continue;
        if (node.closest(".editable-placed-opening, .editable-sys-opening")) {
          stack = null;
          hitNode = null;
          break;
        }
        const st = node.closest(".editable-furniture-stack");
        if (st instanceof SVGGElement) {
          const roomWrap = st.closest(".editable-room");
          if (roomWrap instanceof SVGGElement && roomWrap.getAttribute("data-editable") !== "false") {
            stack = st;
            hitNode = node;
            break;
          }
        }
      }
      if (stack && hitNode) {
        const roomWrap = stack.closest(".editable-room") as SVGGElement;
        const layer = stack.querySelector(".editable-furniture-layer") as SVGGElement | null;
        if (layer && roomWrap.getAttribute("data-editable") !== "false") {
          const rid = roomWrap.getAttribute("data-room-id");
          if (rid) {
            const roomName = roomIdFromDataAttr(rid);
            const roomRec = findRoomByName(roomName);
            if (roomRec && roomRec.__is_carved !== true) {
              const g = findMainRoomRect(roomWrap);
              if (g) {
                const rcx = g.x + g.width / 2;
                const rcy = g.y + g.height / 2;
                const { tx, ty, s } = readFurnitureTransform(roomRec);
                setSelectedRoom(roomName);
                const isHandle = !!hitNode.closest(".furniture-resize-handle");
                if (isHandle) {
                  dragRef.current = {
                    kind: "furniture_res",
                    pointerId: e.pointerId,
                    roomName,
                    layerEl: layer,
                    startClientY: e.clientY,
                    moveClientY: e.clientY,
                    baseS: s,
                    baseTx: tx,
                    baseTy: ty,
                    rcx,
                    rcy,
                  };
                  e.currentTarget.setPointerCapture(e.pointerId);
                  e.preventDefault();
                  return;
                }
                if (hitNode.closest(".editable-furniture-layer")) {
                  const last = toSvgPoint(svg, e.clientX, e.clientY);
                  dragRef.current = {
                    kind: "furniture_move",
                    pointerId: e.pointerId,
                    roomName,
                    layerEl: layer,
                    last,
                    accX: 0,
                    accY: 0,
                    baseTx: tx,
                    baseTy: ty,
                    s,
                    rcx,
                    rcy,
                  };
                  e.currentTarget.setPointerCapture(e.pointerId);
                  e.preventDefault();
                  return;
                }
              }
            }
          }
        }
      }
    }

    const resizeHit =
      (svg && !placeKind ? findResizeHandleFromPoint(svg, e.clientX, e.clientY) : null) ??
      (el?.closest?.(".room-resize-handle") as SVGGraphicsElement | null);
    if (resizeHit && svg && !placeKind) {
      if (!svg.hasAttribute("data-editor-ox")) {
        setErr('Click "Re-render SVG" once so the plan includes editor alignment data for stretch handles.');
        e.preventDefault();
        return;
      }
      const ridAttr = resizeHit.getAttribute("data-room-id");
      const roomG =
        (ridAttr ? findEditableRoomGroup(svg, roomIdFromDataAttr(ridAttr)) : null) ??
        (resizeHit.closest(".editable-room") as SVGGElement | null);
      if (roomG && roomG.getAttribute("data-editable") !== "false") {
        const rid = roomG.getAttribute("data-room-id");
        if (rid) {
          const roomName = roomIdFromDataAttr(rid);
          const roomsArr = layoutRef.current.rooms;
          let roomRec: RoomRec | null = null;
          if (Array.isArray(roomsArr)) {
            const t = roomName.toLowerCase();
            for (const r of roomsArr) {
              if (r && typeof r === "object" && String((r as RoomRec).name ?? "").toLowerCase() === t) {
                roomRec = r as RoomRec;
                break;
              }
            }
          }
          if (roomRec && roomRec.__is_carved !== true) {
            const L = layoutRef.current;
            const bx = Number(L.built_up_x ?? 0);
            const by = Number(L.built_up_y ?? 0);
            const bw = Number(L.built_up_w ?? 1);
            const bh = Number(L.built_up_h ?? 1);
            const x0 = Number(roomRec.x ?? 0);
            const y0 = Number(roomRec.y ?? 0);
            const w0 = Number(roomRec.width ?? 0);
            const h0 = Number(roomRec.height ?? 0);
            const sc = layoutScale(L);
            const minW = Math.max(16, sc * 2.2);
            const minH = Math.max(16, sc * 2.2);
            const ox = Number(svg.getAttribute("data-editor-ox") ?? 0);
            const oy = Number(svg.getAttribute("data-editor-oy") ?? 0);
            const handle = resizeHit.getAttribute("data-handle") || "se";
            const p = toSvgPoint(svg, e.clientX, e.clientY);
            const { lx, ly } = layoutResizePointerFromDelta(handle, x0, y0, w0, h0, 0, 0);
            const lastGeom = computeResizeRect(handle, x0, y0, w0, h0, lx, ly, bx, by, bw, bh, minW, minH);
            setSelectedRoom(roomName);
            dragRef.current = {
              kind: "room_resize",
              pointerId: e.pointerId,
              roomName,
              roomEl: roomG,
              handle,
              ox,
              oy,
              x0,
              y0,
              w0,
              h0,
              bx,
              by,
              bw,
              bh,
              minW,
              minH,
              lastGeom,
              rootStartX: p.x,
              rootStartY: p.y,
            };
            scheduleDragPaint();
            e.currentTarget.setPointerCapture(e.pointerId);
            e.preventDefault();
            return;
          }
        }
      }
    }

    const openingG =
      (svg && !placeKind ? findOpeningGroupFromPoint(svg, e.clientX, e.clientY) : null) ??
      (el?.closest?.(".editable-placed-opening, .editable-sys-opening") as SVGGElement | null);
    if (openingG && svg && !placeKind) {
      const roomWrap = openingG.closest(".editable-room") as SVGGElement | null;
      if (roomWrap && roomWrap.getAttribute("data-editable") !== "false") {
        const rid = roomWrap.getAttribute("data-room-id");
        if (rid) {
          const roomName = roomIdFromDataAttr(rid);
          setSelectedRoom(roomName);
          const last =
            clientPointToRoomLocal(roomWrap, e.clientX, e.clientY) ?? toSvgPoint(svg, e.clientX, e.clientY);
          const isSys = openingG.classList.contains("editable-sys-opening");
          const sk = (openingG.getAttribute("data-sys-kind") as "door" | "window" | null) ?? "door";
          dragRef.current = {
            kind: "opening",
            pointerId: e.pointerId,
            roomName,
            roomEl: roomWrap,
            el: openingG,
            last,
            accX: 0,
            accY: 0,
            openingKind: isSys ? "sys" : "placed",
            placedId: openingG.getAttribute("data-op-id") ?? "",
            sysSlot: openingG.getAttribute("data-sys-slot") ?? "",
            sysKind: sk === "window" ? "window" : "door",
          };
          e.currentTarget.setPointerCapture(e.pointerId);
          e.preventDefault();
          return;
        }
      }
    }

    if (
      voidSelectMode &&
      !placeKind &&
      !furnitureEdit &&
      !panMode &&
      (e.button === 0 || e.button === 2)
    ) {
      if (!svg) {
        setErr("Floor plan SVG is not ready yet.");
        e.preventDefault();
        return;
      }
      if (!svg.hasAttribute("data-editor-ox")) {
        setErr('Click "Re-render SVG" once so void picks map to layout coordinates.');
        e.preventDefault();
        return;
      }
      const onRoom = findEditableRoomFromPoint(svg, e.clientX, e.clientY);
      if (!onRoom) {
        const p = toSvgPoint(svg, e.clientX, e.clientY);
        dragRef.current = {
          kind: "void_region",
          pointerId: e.pointerId,
          svg,
          start: new DOMPoint(p.x, p.y),
          last: new DOMPoint(p.x, p.y),
        };
        paintVoidSelectionOverlay(svg, dragRef.current.start, dragRef.current.last);
        e.currentTarget.setPointerCapture(e.pointerId);
        e.preventDefault();
        return;
      }
    }

    const roomG = el?.closest?.(".editable-room") as SVGGElement | null;
    if (roomG && roomG.getAttribute("data-editable") !== "false" && !(furnitureEdit && !placeKind)) {
      const rid = roomG.getAttribute("data-room-id");
      const roomName = roomIdFromDataAttr(rid);
      const room = findRoomByName(roomName);
      if (!room || room.__is_carved === true) return;
      setSelectedRoom(roomName);
      const last = toSvgPoint(svg, e.clientX, e.clientY);
      dragRef.current = {
        kind: "room",
        pointerId: e.pointerId,
        roomName,
        el: roomG,
        last,
        accX: 0,
        accY: 0,
      };
      e.currentTarget.setPointerCapture(e.pointerId);
      e.preventDefault();
      return;
    }

    if (panMode || e.button === 1) {
      dragRef.current = {
        kind: "pan",
        pointerId: e.pointerId,
        lastClientX: e.clientX,
        lastClientY: e.clientY,
      };
      e.currentTarget.setPointerCapture(e.pointerId);
      e.preventDefault();
    }
  };

  const onPointerMove = (e: React.PointerEvent<HTMLDivElement>) => {
    const svg = resolvePlanSvg(wrapRef.current, svgRef.current);
    if (svg) svgRef.current = svg;

    if (placeKind && !dragRef.current && !previewing) {
      const wrap = wrapRef.current;
      if (!svg || !wrap) {
        setPlaceHover(null);
      } else {
        const snap = snapWallPlacement(
          svg,
          e.clientX,
          e.clientY,
          selectedRoom,
          (e.target as Element | null) ?? null,
        );
        if (!snap) setPlaceHover(null);
        else {
          const dot = placePreviewDotInWrap(svg, wrap, snap);
          setPlaceHover(dot);
        }
      }
      return;
    }

    const vd = dragRef.current;
    if (vd?.kind === "void_region" && svg && e.pointerId === vd.pointerId) {
      vd.last = toSvgPoint(svg, e.clientX, e.clientY);
      paintVoidSelectionOverlay(vd.svg, vd.start, vd.last);
      return;
    }

    const d = dragRef.current;
    if (!d || !svg) return;
    if (e.pointerId !== d.pointerId) return;

    if (d.kind === "pan") {
      const dx = e.clientX - d.lastClientX;
      const dy = e.clientY - d.lastClientY;
      d.lastClientX = e.clientX;
      d.lastClientY = e.clientY;
      setPan((p) => ({ x: p.x + dx, y: p.y + dy }));
      return;
    }

    if (d.kind === "furniture_res") {
      d.moveClientY = e.clientY;
      scheduleDragPaint();
      return;
    }
    if (d.kind === "room_resize") {
      const p = toSvgPoint(svg, e.clientX, e.clientY);
      const drx = p.x - d.rootStartX;
      const dry = p.y - d.rootStartY;
      const { lx, ly } = layoutResizePointerFromDelta(d.handle, d.x0, d.y0, d.w0, d.h0, drx, dry);
      d.lastGeom = computeResizeRect(
        d.handle,
        d.x0,
        d.y0,
        d.w0,
        d.h0,
        lx,
        ly,
        d.bx,
        d.by,
        d.bw,
        d.bh,
        d.minW,
        d.minH,
      );
      scheduleDragPaint();
      return;
    }
    if (d.kind === "furniture_move") {
      const now = toSvgPoint(svg, e.clientX, e.clientY);
      const dx = now.x - d.last.x;
      const dy = now.y - d.last.y;
      d.last = now;
      d.accX += dx;
      d.accY += dy;
      scheduleDragPaint();
      return;
    }

    if (d.kind === "opening") {
      const now = clientPointToRoomLocal(d.roomEl, e.clientX, e.clientY);
      if (!now) return;
      const dx = now.x - d.last.x;
      const dy = now.y - d.last.y;
      d.last = now;
      d.accX += dx;
      d.accY += dy;
      scheduleDragPaint();
      return;
    }
    if (d.kind !== "room") return;
    const now = toSvgPoint(svg, e.clientX, e.clientY);
    const dx = now.x - d.last.x;
    const dy = now.y - d.last.y;
    d.last = now;
    d.accX += dx;
    d.accY += dy;
    scheduleDragPaint();
  };

  const endDrag = (e: React.PointerEvent<HTMLDivElement>) => {
    const d = dragRef.current;
    if (dragRaf.current != null) {
      cancelAnimationFrame(dragRaf.current);
      dragRaf.current = null;
    }
    if (!d || e.pointerId !== d.pointerId) return;
    dragRef.current = null;
    try {
      e.currentTarget.releasePointerCapture(e.pointerId);
    } catch {
      /* ignore */
    }

    if (d.kind === "void_region") {
      clearVoidSelectionOverlay(d.svg);
      const la = rootSvgPointToLayout(d.svg, d.start);
      const lb = rootSvgPointToLayout(d.svg, d.last);
      const x = Math.min(la.x, lb.x);
      const y = Math.min(la.y, lb.y);
      const width = Math.abs(lb.x - la.x);
      const height = Math.abs(lb.y - la.y);
      if (width < 6 || height < 6) {
        setErr("");
        return;
      }
      setVoidModal({ x, y, width, height });
      setVoidPrompt("");
      setErr("");
      return;
    }

    if (d.kind === "room_resize") {
      removeResizePreviewRect(d.roomEl);
      const g = d.lastGeom;
      const unchanged =
        Math.abs(g.x - d.x0) < 0.5 &&
        Math.abs(g.y - d.y0) < 0.5 &&
        Math.abs(g.width - d.w0) < 0.5 &&
        Math.abs(g.height - d.h0) < 0.5;
      if (unchanged) {
        setErr("");
        return;
      }
      const next = cloneLayout(layoutRef.current);
      const sc = layoutScale(next);
      const rooms = next.rooms;
      if (!Array.isArray(rooms)) return;
      const target = d.roomName.toLowerCase();
      for (const r of rooms) {
        const rec = r as RoomRec;
        if (String(rec.name ?? "").toLowerCase() !== target) continue;
        scaleCarvedInsideParentBounds(rooms, d.x0, d.y0, d.w0, d.h0, g.x, g.y, g.width, g.height, sc);
        rec.x = g.x;
        rec.y = g.y;
        rec.width = g.width;
        rec.height = g.height;
        applyRoomSizeDerivedFields(rec, sc);
        break;
      }
      setLayout(next);
      void postPreview(false, next);
      setErr("");
      setStatus("Room size updated.");
      return;
    }

    if (d.kind === "furniture_move") {
      if (d.accX === 0 && d.accY === 0) return;
      const tx = d.baseTx + d.accX;
      const ty = d.baseTy + d.accY;
      const s = d.s;
      const next = cloneLayout(layoutRef.current);
      const rooms = next.rooms;
      if (!Array.isArray(rooms)) return;
      const target = d.roomName.toLowerCase();
      for (const r of rooms) {
        const rec = r as RoomRec;
        if (String(rec.name ?? "").toLowerCase() !== target) continue;
        const rw = Number(rec.width ?? 0);
        const rh = Number(rec.height ?? 0);
        const lim = Math.max(rw, rh) * 0.5;
        rec.furniture_transform = {
          tx: Math.max(-lim, Math.min(lim, tx)),
          ty: Math.max(-lim, Math.min(lim, ty)),
          s,
        } as unknown as Record<string, unknown>;
        break;
      }
      setLayout(next);
      void postPreview(false, next);
      setErr("");
      setStatus("Furniture position updated.");
      return;
    }

    if (d.kind === "furniture_res") {
      const dy = d.startClientY - e.clientY;
      let s = Math.max(0.35, Math.min(2.5, d.baseS * (1 + dy * 0.002)));
      if (Math.abs(s - d.baseS) < 1e-5) {
        d.layerEl.setAttribute(
          "transform",
          furnitureTransformMatrix(d.baseTx, d.baseTy, d.baseS, d.rcx, d.rcy),
        );
        return;
      }
      const tx = d.baseTx;
      const ty = d.baseTy;
      const next = cloneLayout(layoutRef.current);
      const rooms = next.rooms;
      if (!Array.isArray(rooms)) return;
      const target = d.roomName.toLowerCase();
      for (const r of rooms) {
        const rec = r as RoomRec;
        if (String(rec.name ?? "").toLowerCase() !== target) continue;
        const rw = Number(rec.width ?? 0);
        const rh = Number(rec.height ?? 0);
        const lim = Math.max(rw, rh) * 0.5;
        rec.furniture_transform = {
          tx: Math.max(-lim, Math.min(lim, tx)),
          ty: Math.max(-lim, Math.min(lim, ty)),
          s,
        } as unknown as Record<string, unknown>;
        break;
      }
      setLayout(next);
      void postPreview(false, next);
      setErr("");
      setStatus("Furniture scale updated.");
      return;
    }

    if (d.kind === "opening") {
      d.el.setAttribute("transform", `translate(${d.accX},${d.accY})`);
      d.el.removeAttribute("transform");
      if (d.accX === 0 && d.accY === 0) return;
      const roomG = d.el.closest(".editable-room") as SVGGElement | null;
      if (!roomG) return;
      let snap: { edge: string; u: number; dist: number } | null = null;
      for (const tol of [52, 88, 120, 160, 220, 280] as const) {
        snap = snapWallForRoom(roomG, e.clientX, e.clientY, tol);
        if (snap) break;
      }
      if (!snap) {
        setErr("Release inside that room's floor — the opening snaps to the nearest wall.");
        return;
      }
      const next = cloneLayout(layoutRef.current);
      const rooms = next.rooms;
      if (!Array.isArray(rooms)) return;
      const target = d.roomName.toLowerCase();
      let roomRec: RoomRec | null = null;
      for (const r of rooms) {
        const rec = r as RoomRec;
        if (String(rec.name ?? "").toLowerCase() === target) {
          roomRec = rec;
          break;
        }
      }
      if (!roomRec) return;

      if (d.openingKind === "placed" && d.placedId) {
        const list = (Array.isArray(roomRec.placed_openings)
          ? [...(roomRec.placed_openings as PlacedOpening[])]
          : []) as PlacedOpening[];
        const ix = list.findIndex((o) => o.id === d.placedId);
        if (ix < 0) {
          setErr("Could not update that opening (id mismatch). Try Re-render SVG or Reset layout.");
          return;
        }
        list[ix] = { ...list[ix], edge: snap.edge, u: snap.u };
        roomRec.placed_openings = list as unknown[];
      } else if (d.openingKind === "sys") {
        const rw = Number(roomRec.width ?? 0);
        const rh = Number(roomRec.height ?? 0);
        const width_px =
          d.sysKind === "window" ? defaultWindowPanePx(rw, rh, snap.edge) : defaultDoorWidthPx(rw, rh);
        const newOp: PlacedOpening = {
          id: newOpeningId(),
          edge: snap.edge,
          u: snap.u,
          kind: d.sysKind,
          width_px,
        };
        const list = (Array.isArray(roomRec.placed_openings)
          ? [...(roomRec.placed_openings as PlacedOpening[])]
          : []) as PlacedOpening[];
        list.push(newOp);
        roomRec.placed_openings = list as unknown[];

        const slot = d.sysSlot;
        if (slot === "main") {
          delete roomRec.__main_door;
          delete roomRec.__main_door_px;
          roomRec.__suppress_foyer_main_door = true;
        } else if (slot === "interior") {
          const dc = Math.max(0, Number(roomRec.door_count ?? 0) - 1);
          roomRec.door_count = dc;
          if (dc === 0) delete roomRec.__door_wall;
        } else if (slot === "windows") {
          roomRec.windows = 0;
        }
      }

      setLayout(next);
      void postPreview(false, next);
      setErr("");
      setStatus("Opening repositioned on wall.");
      return;
    }

    if (d.kind !== "room") return;

    d.el.setAttribute("transform", `translate(${d.accX},${d.accY})`);
    d.el.removeAttribute("transform");
    const { accX, accY, roomName } = d;
    if (accX === 0 && accY === 0) return;

    const next = cloneLayout(layoutRef.current);
    const rooms = next.rooms;
    if (Array.isArray(rooms)) {
      const target = roomName.toLowerCase();
      for (let i = 0; i < rooms.length; i++) {
        const r = rooms[i] as RoomRec;
        if (String(r.name ?? "").toLowerCase() === target) {
          r.x = Number(r.x ?? 0) + accX;
          r.y = Number(r.y ?? 0) + accY;
          clampRoom(r, next);
          break;
        }
      }
    }
    setLayout(next);
    void postPreview(false, next);
  };

  const onWheel = (e: React.WheelEvent<HTMLDivElement>) => {
    if (!e.ctrlKey && !e.metaKey) return;
    e.preventDefault();
    const factor = e.deltaY > 0 ? 0.92 : 1.08;
    setZoom((z) => Math.min(3, Math.max(0.35, z * factor)));
  };

  const scaledSvg = (() => {
    const trimmed = svgPreview.trimStart();
    if (!/^<svg\s/i.test(trimmed)) return svgPreview;
    let s = trimmed.replace(
      /^<svg\s+/i,
      '<svg style="max-width:none;height:auto;display:block;-webkit-user-select:none;user-select:none;-moz-user-select:none" ',
    );
    // Labels are real SVG <text>; without this, drag-to-stretch selects blue text instead of resizing.
    s = s.replace(
      /(<defs>\s*<style>)/i,
      "$1text,tspan{-webkit-user-select:none;user-select:none;-moz-user-select:none;cursor:default}",
    );
    return s;
  })();

  const roomNames: string[] = [];
  const rooms = layout.rooms;
  if (Array.isArray(rooms)) {
    for (const r of rooms) {
      if (!r || typeof r !== "object") continue;
      const rec = r as RoomRec;
      if (rec.__is_carved === true) continue;
      const n = String(rec.name ?? "");
      if (n) roomNames.push(n);
    }
  }

  const scale = layoutScale(layout);

  const editorCanvasInner = (
    <>
      {previewing ? (
        <div
          style={{
            position: "absolute",
            inset: 0,
            zIndex: 2,
            pointerEvents: "none",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            background: "rgba(250,247,242,0.35)",
            fontSize: 12,
            color: C.inkMid,
          }}
        >
          Updating plan…
        </div>
      ) : null}
      {placeKind && placeHover ? (
        <div
          aria-hidden
          style={{
            position: "absolute",
            left: placeHover.left,
            top: placeHover.top,
            width: 14,
            height: 14,
            marginLeft: -7,
            marginTop: -7,
            borderRadius: 999,
            border: `2.5px solid ${placeKind === "door" ? C.accent : "#3d6ea5"}`,
            background: "rgba(255,255,255,0.88)",
            boxShadow: "0 1px 3px rgba(0,0,0,0.2)",
            pointerEvents: "none",
            zIndex: 3,
          }}
        />
      ) : null}
      <div
        style={{
          transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
          transformOrigin: "0 0",
          width: "max-content",
          height: "max-content",
          willChange: "transform",
          WebkitUserSelect: "none",
          userSelect: "none",
          MozUserSelect: "none",
        }}
      >
        <div dangerouslySetInnerHTML={{ __html: scaledSvg }} />
      </div>
    </>
  );

  const editorWrapSurfaceStyle = (fullscreen: boolean): React.CSSProperties => ({
    position: "relative",
    ...(fullscreen ? { flex: 1, minHeight: 0 } : { height: 520 }),
    overflow: "hidden",
    background: "#ebe6de",
    border: `1px solid ${C.border}`,
    borderRadius: fullscreen ? 0 : 8,
    cursor: placeKind ? "crosshair" : voidSelectMode ? "crosshair" : panMode ? "grab" : "default",
    touchAction: "none",
    WebkitUserSelect: "none",
    userSelect: "none",
    MozUserSelect: "none",
  });

  return (
    <div
      style={{
        marginTop: 12,
        borderTop: `1px solid ${C.border}`,
        paddingTop: 12,
        paddingLeft: 16,
        paddingRight: 16,
        paddingBottom: 16,
        background: C.paper,
      }}
    >
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", flexWrap: "wrap", gap: 10, marginBottom: 10 }}>
        <div>
          <span style={{ fontSize: 11, fontWeight: 600, letterSpacing: "0.1em", color: C.inkMid, textTransform: "uppercase" }}>
            Wall-accurate editor
          </span>
          <p style={{ margin: "4px 0 0", fontSize: 11, color: C.inkLight, lineHeight: 1.55, maxWidth: 900 }}>
            <strong>Drag rooms</strong> to move them (release to commit).{" "}
            <strong>Drag corner or edge handles</strong> on a room (brown squares / bands) to stretch it within the built-up area; attached bath / wardrobe zones inside that footprint scale with the room.{" "}
            <strong>Furniture edit</strong>: drag the furniture layer inside a room to move it; drag the green corner handle to scale (uniform, about room center).{" "}
            <strong>Drag doors and windows</strong> along a wall to reposition (AI openings become custom wall punches when moved).{" "}
            <strong>Place door / place window</strong>: choose a room in the list (optional), then click anywhere in that room — the opening snaps to the nearest wall.{" "}
            <strong>Empty floor → new room</strong>: arm <strong>Add room in void</strong> (below), keep <strong>Pan off</strong>, then <strong>click-drag on white space</strong> (not on a room slab) and describe the room (OpenAI when <code style={{ fontSize: 10 }}>OPENAI_API_KEY</code> is set on the server; otherwise keywords).{" "}
            <strong>For rooms that touch (e.g. veranda and pooja)</strong>, pick the target room in the list below first so the opening is not snapped to the neighbour.{" "}
            The server draws a real wall punch, frame, and swing like the generated plan (not a white patch overlay).{" "}
            If an AI door overlaps your placement, reduce <code style={{ fontSize: 10 }}>door_count</code> on that room in a future regenerate, or clear custom openings below.
          </p>
        </div>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 6, alignItems: "center" }}>
          <button
            type="button"
            disabled={previewing}
            onClick={() => {
              setLayout(normalizeLayout(layoutFloor));
              setSvgPreview(initialSvg);
              setErr("");
              setStatus("Restored original layout.");
              setVoidSelectMode(false);
              setVoidModal(null);
              setVoidPrompt("");
            }}
            style={btnStyle(false)}
          >
            Reset layout
          </button>
          <button type="button" disabled={previewing} onClick={() => void postPreview(false)} style={btnStyle(false)}>
            Re-render SVG
          </button>
          {onThreeDHtml && (
            <button type="button" disabled={previewing} onClick={() => void postPreview(true)} style={btnStyle(true)}>
              Refresh 3D (this floor)
            </button>
          )}
          <button type="button" onClick={() => setPanMode((m) => !m)} style={btnStyle(panMode)}>
            {panMode ? "Pan on" : "Pan off"}
          </button>
          <button type="button" onClick={() => setZoom((z) => Math.min(3, z * 1.15))} style={btnStyle(false)}>+</button>
          <button type="button" onClick={() => setZoom((z) => Math.max(0.35, z / 1.15))} style={btnStyle(false)}>−</button>
          <button type="button" onClick={() => { setZoom(1); setPan({ x: 0, y: 0 }); }} style={btnStyle(false)}>Fit zoom</button>
          <button
            type="button"
            onClick={() => setEditorCanvasFullscreen(true)}
            style={{
              ...btnStyle(false),
              fontWeight: 600,
              background: "#1a1714",
              color: "#c8a96e",
              border: "1px solid #1a1714",
            }}
          >
            Full screen
          </button>
        </div>
      </div>

      {err ? <p style={{ fontSize: 12, color: "#a33", marginBottom: 8 }}>{err}</p> : null}
      {status && !err ? <p style={{ fontSize: 11, color: C.accent, marginBottom: 8 }}>{status}</p> : null}

      <div style={{ display: "flex", flexWrap: "wrap", gap: 10, marginBottom: 10, alignItems: "center" }}>
        <span style={{ fontSize: 10, color: C.inkMid, fontWeight: 600 }}>WALL TOOLS</span>
        <button
          type="button"
          style={btnStyle(placeKind === "door")}
          onClick={() => {
            setVoidSelectMode(false);
            setPlaceKind((k) => (k === "door" ? null : "door"));
          }}
        >
          {placeKind === "door" ? "Click a wall… (door)" : "Place door"}
        </button>
        <button
          type="button"
          style={btnStyle(placeKind === "window")}
          onClick={() => {
            setVoidSelectMode(false);
            setPlaceKind((k) => (k === "window" ? null : "window"));
          }}
        >
          {placeKind === "window" ? "Click a wall… (window)" : "Place window"}
        </button>
        <button type="button" style={btnStyle(false)} onClick={() => { setPlaceKind(null); setVoidSelectMode(false); }}>Cancel tool</button>
        <button
          type="button"
          style={btnStyle(furnitureEdit)}
          onClick={() => {
            setVoidSelectMode(false);
            setFurnitureEdit((v) => !v);
            setPlaceKind(null);
          }}
        >
          {furnitureEdit ? "Furniture edit on" : "Furniture edit off"}
        </button>
        <label style={{ fontSize: 10, color: C.inkLight, marginLeft: 8 }}>
          Target room (place / clear):
          <select
            value={selectedRoom}
            onChange={(ev) => setSelectedRoom(ev.target.value)}
            style={{ ...sel, marginLeft: 6 }}
          >
            <option value="">—</option>
            {roomNames.map((n) => (
              <option key={n} value={n}>{n.replace(/_/g, " ")}</option>
            ))}
          </select>
        </label>
        <button type="button" disabled={previewing} style={btnStyle(false)} onClick={clearPlacedForSelectedRoom}>
          Clear placed openings
        </button>
      </div>

      <div style={{ display: "flex", flexWrap: "wrap", gap: 10, marginBottom: 10, alignItems: "center" }}>
        <span style={{ fontSize: 10, color: C.inkMid, fontWeight: 600 }}>VOID FILL</span>
        <button
          type="button"
          disabled={previewing}
          style={btnStyle(voidSelectMode)}
          onClick={() => {
            setVoidSelectMode((v) => !v);
            setPlaceKind(null);
            setFurnitureEdit(false);
          }}
        >
          {voidSelectMode ? "Drag on empty floor…" : "Add room in void"}
        </button>
        <span style={{ fontSize: 10, color: C.inkLight, maxWidth: 720, lineHeight: 1.45 }}>
          Pan off. With this tool on, <strong>left-drag</strong> (or right-drag) a rectangle on unused white floor — not on an existing room. If nothing happens, click <strong>Re-render SVG</strong> first. Overlap with rooms must stay low or the server rejects the pick.
        </span>
      </div>

      {editorCanvasFullscreen ? (
        <div
          style={{
            position: "fixed",
            inset: 0,
            zIndex: 9990,
            display: "flex",
            flexDirection: "column",
            background: "#faf7f2",
            paddingTop: "env(safe-area-inset-top, 0px)",
            paddingBottom: "env(safe-area-inset-bottom, 0px)",
            paddingLeft: "env(safe-area-inset-left, 0px)",
            paddingRight: "env(safe-area-inset-right, 0px)",
          }}
        >
          <div
            style={{
              flexShrink: 0,
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              flexWrap: "wrap",
              gap: 10,
              padding: "10px 14px",
              background: C.headerBg,
              borderBottom: `1px solid ${C.border}`,
            }}
          >
            <span style={{ fontSize: 12, fontWeight: 600, color: C.ink, letterSpacing: "0.02em" }}>
              Plan canvas — full screen
            </span>
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
              <button type="button" onClick={() => { setZoom(1); setPan({ x: 0, y: 0 }); }} style={btnStyle(false)}>
                Fit zoom
              </button>
              <button
                type="button"
                onClick={() => setEditorCanvasFullscreen(false)}
                style={{
                  ...btnStyle(false),
                  fontWeight: 600,
                  background: "#1a1714",
                  color: "#c8a96e",
                  border: "1px solid #1a1714",
                }}
              >
                Exit full screen
              </button>
            </div>
          </div>
          <div
            ref={wrapRef}
            onPointerDownCapture={onPointerDown}
            onPointerMove={onPointerMove}
            onPointerLeave={() => {
              if (placeKind) setPlaceHover(null);
            }}
            onPointerUp={endDrag}
            onPointerCancel={endDrag}
            onSelectStart={(e) => {
              e.preventDefault();
            }}
            onWheel={onWheel}
            style={editorWrapSurfaceStyle(true)}
          >
            {editorCanvasInner}
          </div>
        </div>
      ) : (
        <div
          ref={wrapRef}
          onPointerDownCapture={onPointerDown}
          onPointerMove={onPointerMove}
          onPointerLeave={() => {
            if (placeKind) setPlaceHover(null);
          }}
          onPointerUp={endDrag}
          onPointerCancel={endDrag}
          onSelectStart={(e) => {
            e.preventDefault();
          }}
          onWheel={onWheel}
          style={editorWrapSurfaceStyle(false)}
        >
          {editorCanvasInner}
        </div>
      )}

      {voidModal ? (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="void-room-dialog-title"
          style={{
            position: "fixed",
            inset: 0,
            zIndex: 10050,
            background: "rgba(44, 40, 32, 0.42)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: 16,
          }}
          onMouseDown={(ev) => {
            if (ev.target === ev.currentTarget) {
              setVoidModal(null);
              setVoidPrompt("");
            }
          }}
        >
          <div
            style={{
              width: "100%",
              maxWidth: 460,
              background: C.paper,
              borderRadius: 10,
              border: `1px solid ${C.border}`,
              boxShadow: "0 8px 32px rgba(0,0,0,0.12)",
              padding: "16px 18px 14px",
            }}
            onMouseDown={(ev) => ev.stopPropagation()}
          >
            <h3 id="void-room-dialog-title" style={{ margin: "0 0 6px", fontSize: 14, fontWeight: 600, color: C.ink }}>
              Describe the new room
            </h3>
            <p style={{ margin: "0 0 10px", fontSize: 11, color: C.inkLight, lineHeight: 1.5 }}>
              Selected void ≈{" "}
              <strong>
                {Math.round((voidModal.width / scale) * 10) / 10}′ × {Math.round((voidModal.height / scale) * 10) / 10}′
              </strong>{" "}
              (~{Math.round((voidModal.width / scale) * (voidModal.height / scale))} sqft). Type what you want here;
              the server picks a programme name and draws it like the other rooms.
            </p>
            <textarea
              value={voidPrompt}
              onChange={(ev) => setVoidPrompt(ev.target.value)}
              rows={4}
              placeholder='Example: "Small guest bedroom, north light" or "Study with built-in desk"'
              style={{
                width: "100%",
                boxSizing: "border-box",
                fontSize: 12,
                fontFamily: "inherit",
                padding: "8px 10px",
                borderRadius: 6,
                border: `1px solid ${C.border}`,
                resize: "vertical",
                minHeight: 88,
              }}
            />
            <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginTop: 12, justifyContent: "flex-end" }}>
              <button
                type="button"
                disabled={voidSubmitting}
                onClick={() => {
                  setVoidModal(null);
                  setVoidPrompt("");
                }}
                style={btnStyle(false)}
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={voidSubmitting || previewing}
                onClick={() => void submitVoidRoomProposal()}
                style={btnStyle(true)}
              >
                {voidSubmitting ? "Placing…" : "Place room"}
              </button>
            </div>
          </div>
        </div>
      ) : null}

      <p style={{ fontSize: 10, color: C.inkLight, marginTop: 10, lineHeight: 1.5 }}>
        Scale for manual size edits (ft ↔ px): <strong>{scale}</strong> px/ft — use JSON panel if you need to tweak <code>door_count</code> / <code>windows</code> on the base AI run.
      </p>
    </div>
  );
}

const sel: React.CSSProperties = {
  fontSize: 11,
  padding: "4px 8px",
  borderRadius: 5,
  border: `1px solid ${C.border}`,
  fontFamily: "inherit",
};

function btnStyle(active: boolean): React.CSSProperties {
  return {
    fontSize: 11,
    fontWeight: 500,
    padding: "5px 10px",
    borderRadius: 5,
    border: `1px solid ${active ? C.accent : C.border}`,
    background: active ? `${C.accent}22` : C.headerBg,
    color: C.ink,
    cursor: "pointer",
    fontFamily: "inherit",
  };
}
