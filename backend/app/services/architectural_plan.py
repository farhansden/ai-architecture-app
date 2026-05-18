from __future__ import annotations

from typing import Any, Dict, List

import svgwrite


class IndianResidentialPlan:
    """
    Template-based floor plan for Indian residential houses.
    Templates are defined per BHK type and plot proportion.
    """

    SCALE = 10  # px per foot

    def __init__(self, parsed: dict):
        self.parsed = parsed or {}
        self.pw = float(self.parsed.get("plot_width_ft") or 30)
        self.pd = float(self.parsed.get("plot_depth_ft") or 50)
        self.bhk = self._detect_bhk()
        self.cars = int(self.parsed.get("car_spaces", 1) or 1)
        self.vastu = bool(self.parsed.get("vastu_compliant", False))
        self.budget = float(self.parsed.get("budget", 0) or 0)

        sb = self.parsed.get("setbacks") or {}
        self.sb_l = float(sb.get("left", 2) or 2)
        self.sb_r = float(sb.get("right", 2) or 2)
        self.sb_f = float(sb.get("front", 5) or 5)
        self.sb_re = float(sb.get("rear", 3) or 3)

        # Built-up dimensions
        self.bw = self.pw - self.sb_l - self.sb_r
        self.bh = self.pd - self.sb_f - self.sb_re

        self.rooms: List[Dict[str, Any]] = []

    def _detect_bhk(self) -> int:
        bhk = str(self.parsed.get("bhk_type", "3BHK") or "3BHK")
        for n in ["4", "3", "2", "1"]:
            if n in bhk:
                return int(n)
        return 3

    def build(self) -> List[Dict[str, Any]]:
        """Build room list using architectural template."""
        self.rooms = []
        if self.bhk >= 3:
            self._template_3bhk()
        elif self.bhk == 2:
            self._template_2bhk()
        else:
            self._template_1bhk()
        return self.rooms

    def _template_3bhk(self):
        bw = self.bw
        bh = self.bh

        row_A = min(max(self.sb_f * 1.8, 11.0), 13.0)
        row_C = float(self.parsed.get("corridor_width_ft") or 4.0)
        remaining = bh - row_A - row_C
        row_B = max(remaining * 0.48, 12.0)
        row_DE = remaining - row_B
        row_D = max(row_DE * 0.62, 11.0)
        row_E = row_DE - row_D

        big_kitchen = "big" in str(self.parsed.get("special_requirements", "")).lower()
        kit_min_w = 11.0 if big_kitchen else 9.0
        col_right = max(bw * 0.38, kit_min_w)
        col_left = bw - col_right

        pooja_w = min(5.0, col_left * 0.30)
        util_w = min(5.0, col_left * 0.28)
        liv_din_w = col_left - pooja_w - util_w

        yA = 0.0
        yB = row_A
        yC = yB + row_B
        yD = yC + row_C
        yE = yD + row_D

        mbr_w = max(bw * 0.35, 11.0)
        pbr_w = max(bw * 0.35, 11.0)
        gbr_w = bw - mbr_w - pbr_w
        if gbr_w < 8.0:
            deficit = 8.0 - gbr_w
            mbr_w -= deficit / 2
            pbr_w -= deficit / 2
            gbr_w = 8.0

        bath_w = min(5.0, mbr_w * 0.42)
        bath_h = min(8.0, row_D * 0.58)

        # Row A
        car_w = min(self.cars * 10.0 + 2.0, bw * 0.62)
        sit_w = bw - car_w

        self._room(
            "car_porch",
            "CAR PORCH",
            x=0,
            y=yA,
            w=car_w,
            h=row_A,
            color="#EEEBD8",
            windows=0,
            doors=0,
            note=f"Fits {self.cars} car(s)",
        )
        self._room(
            "sit_out",
            "SIT OUT",
            x=car_w,
            y=yA,
            w=sit_w,
            h=row_A,
            color="#E8F2E8",
            windows=0,
            doors=1,
        )

        # Row B
        self._room(
            "pooja_room",
            "POOJA ROOM",
            x=0,
            y=yB,
            w=pooja_w,
            h=row_B * 0.45,
            color="#FDF0DC",
            windows=1,
            doors=1,
        )

        self._room(
            "utility_room",
            "UTILITY",
            x=pooja_w,
            y=yB,
            w=util_w,
            h=row_B * 0.40,
            color="#F0F0EC",
            windows=1,
            doors=1,
        )

        liv_h = row_B - row_B * 0.45
        self._room(
            "living_room",
            "LIVING ROOM",
            x=0,
            y=yB + row_B * 0.45,
            w=pooja_w + util_w,
            h=liv_h,
            color="#FDF6E3",
            windows=3,
            doors=2,
        )

        self._room(
            "dining_room",
            "DINING ROOM",
            x=pooja_w + util_w,
            y=yB,
            w=liv_din_w,
            h=row_B,
            color="#FDF6E3",
            windows=1,
            doors=1,
        )

        self._room(
            "kitchen",
            "KITCHEN",
            x=col_left,
            y=yB,
            w=col_right,
            h=row_B,
            color="#E8F5EC",
            windows=2,
            doors=1,
            note="Big kitchen" if big_kitchen else "",
        )

        # Row C
        self._room(
            "corridor",
            "CORRIDOR",
            x=0,
            y=yC,
            w=bw,
            h=row_C,
            color="#F5F5EE",
            windows=0,
            doors=0,
        )

        # Row D
        self._room(
            "parents_bedroom",
            "PARENTS BEDROOM",
            x=0,
            y=yD,
            w=pbr_w,
            h=row_D,
            color="#E8EEF8",
            windows=2,
            doors=1,
            attached_bath=True,
        )

        self._room(
            "parents_bathroom",
            "BATH",
            x=pbr_w - bath_w,
            y=yD,
            w=bath_w,
            h=bath_h,
            color="#E0F2F8",
            windows=1,
            doors=1,
        )

        self._room(
            "guest_room",
            "GUEST ROOM",
            x=pbr_w,
            y=yD,
            w=gbr_w,
            h=row_D,
            color="#EEF2FF",
            windows=2,
            doors=1,
        )

        mbr_x = pbr_w + gbr_w
        self._room(
            "master_bedroom",
            "MASTER BEDROOM",
            x=mbr_x,
            y=yD,
            w=mbr_w,
            h=row_D,
            color="#E8EEF8",
            windows=2,
            doors=1,
            attached_bath=True,
        )

        self._room(
            "master_bathroom",
            "BATH",
            x=mbr_x,
            y=yD,
            w=bath_w,
            h=bath_h,
            color="#E0F2F8",
            windows=1,
            doors=1,
        )

        # Row E
        if row_E >= 5.0:
            store_w = pbr_w * 0.50
            cbath_w = pbr_w - store_w
            self._room(
                "store_room",
                "STORE",
                x=0,
                y=yE,
                w=store_w,
                h=row_E,
                color="#EDEDED",
                windows=0,
                doors=1,
            )
            self._room(
                "common_bathroom",
                "COMMON BATH",
                x=store_w,
                y=yE,
                w=cbath_w,
                h=row_E,
                color="#E0F2F8",
                windows=1,
                doors=1,
            )

    def _template_2bhk(self):
        bw = self.bw
        bh = self.bh

        row_A = min(max(self.sb_f * 1.8, 10.0), 12.0)
        row_C = float(self.parsed.get("corridor_width_ft") or 3.5)
        remaining = bh - row_A - row_C
        row_B = max(remaining * 0.45, 11.0)
        row_DE = remaining - row_B

        col_right = max(bw * 0.38, 9.0)
        col_left = bw - col_right
        pooja_w = min(5.0, col_left * 0.32)

        yA = 0.0
        yB = row_A
        yC = yB + row_B
        yD = yC + row_C

        car_w = min(self.cars * 10.0 + 2.0, bw * 0.65)
        sit_w = bw - car_w

        self._room("car_porch", "CAR PORCH", 0, yA, car_w, row_A, "#EEEBD8", 0, 0)
        self._room("sit_out", "SIT OUT", car_w, yA, sit_w, row_A, "#E8F2E8", 0, 1)
        self._room("pooja_room", "POOJA ROOM", 0, yB, pooja_w, row_B * 0.40, "#FDF0DC", 1, 1)
        self._room(
            "living_room",
            "LIVING ROOM",
            0,
            yB + row_B * 0.40,
            pooja_w,
            row_B * 0.60,
            "#FDF6E3",
            3,
            2,
        )
        self._room("dining_room", "DINING ROOM", pooja_w, yB, col_left - pooja_w, row_B, "#FDF6E3", 1, 1)
        self._room("kitchen", "KITCHEN", col_left, yB, col_right, row_B, "#E8F5EC", 2, 1)
        self._room("corridor", "CORRIDOR", 0, yC, bw, row_C, "#F5F5EE", 0, 0)

        mbr_w = bw * 0.50
        mbr_h = row_DE
        bath_w = min(5.0, mbr_w * 0.40)
        bath_h = min(8.0, mbr_h * 0.55)

        self._room(
            "master_bedroom",
            "MASTER BEDROOM",
            bw - mbr_w,
            yD,
            mbr_w,
            mbr_h,
            "#E8EEF8",
            2,
            1,
            attached_bath=True,
        )
        self._room("master_bathroom", "BATH", bw - bath_w, yD, bath_w, bath_h, "#E0F2F8", 1, 1)
        self._room("bedroom", "BEDROOM", 0, yD, bw - mbr_w, mbr_h, "#EEF2FF", 2, 1)

        cbath_w = (bw - mbr_w) * 0.45
        self._room("common_bathroom", "COMMON BATH", 0, yD + mbr_h * 0.65, cbath_w, mbr_h * 0.35, "#E0F2F8", 1, 1)
        self._room("store_room", "STORE", cbath_w, yD + mbr_h * 0.65, bw - mbr_w - cbath_w, mbr_h * 0.35, "#EDEDED", 0, 1)

    def _template_1bhk(self):
        bw = self.bw
        bh = self.bh

        row_A = min(max(self.sb_f * 1.8, 9.5), 11.5)
        row_C = float(self.parsed.get("corridor_width_ft") or 3.5)
        remaining = bh - row_A - row_C
        row_B = max(remaining * 0.52, 11.0)
        row_D = remaining - row_B

        col_right = max(bw * 0.38, 9.0)
        col_left = bw - col_right
        pooja_w = min(5.0, col_left * 0.30)
        util_w = min(4.5, col_left * 0.25)

        yA = 0.0
        yB = row_A
        yC = yB + row_B
        yD = yC + row_C

        car_w = min(self.cars * 10.0 + 2.0, bw * 0.65)
        sit_w = bw - car_w

        self._room("car_porch", "CAR PORCH", 0, yA, car_w, row_A, "#EEEBD8", 0, 0)
        self._room("sit_out", "SIT OUT", car_w, yA, sit_w, row_A, "#E8F2E8", 0, 1)

        self._room("pooja_room", "POOJA ROOM", 0, yB, pooja_w, row_B * 0.40, "#FDF0DC", 1, 1)
        self._room("utility_room", "UTILITY", pooja_w, yB, util_w, row_B * 0.40, "#F0F0EC", 1, 1)
        self._room("living_room", "LIVING ROOM", 0, yB + row_B * 0.40, pooja_w + util_w, row_B * 0.60, "#FDF6E3", 3, 2)
        self._room("dining_room", "DINING ROOM", pooja_w + util_w, yB, col_left - (pooja_w + util_w), row_B, "#FDF6E3", 1, 1)
        self._room("kitchen", "KITCHEN", col_left, yB, col_right, row_B, "#E8F5EC", 2, 1)
        self._room("corridor", "CORRIDOR", 0, yC, bw, row_C, "#F5F5EE", 0, 0)

        mbr_w = bw * 0.60
        bath_w = min(5.0, mbr_w * 0.40)
        bath_h = min(8.0, row_D * 0.58)

        self._room("master_bedroom", "MASTER BEDROOM", bw - mbr_w, yD, mbr_w, row_D, "#E8EEF8", 2, 1, attached_bath=True)
        self._room("master_bathroom", "BATH", bw - bath_w, yD, bath_w, bath_h, "#E0F2F8", 1, 1)
        self._room("common_bathroom", "COMMON BATH", 0, yD + row_D * 0.60, bw - mbr_w, row_D * 0.40, "#E0F2F8", 1, 1)

    def _room(
        self,
        name,
        label,
        x,
        y,
        w,
        h,
        color,
        windows=1,
        doors=1,
        attached_bath=False,
        note="",
    ):
        """All coordinates in FEET relative to built-up top-left."""
        w = max(float(w), 3.0)
        h = max(float(h), 3.0)
        self.rooms.append(
            {
                "name": name,
                "label": label,
                "x": round(float(x), 2),
                "y": round(float(y), 2),
                "w": round(float(w), 2),
                "h": round(float(h), 2),
                "area_sqft": round(float(w) * float(h), 1),
                "width_ft": round(float(w), 2),
                "depth_ft": round(float(h), 2),
                "color": color,
                "category": self._category(name),
                "windows": int(windows),
                "door_count": int(doors),
                "attached_bath": bool(attached_bath),
                "note": note,
            }
        )

    def _category(self, name: str) -> str:
        n = name.lower()
        if "car_porch" in n:
            return "car_porch"
        if "sit_out" in n or "verandah" in n or "veranda" in n:
            return "sit_out"
        if "living" in n:
            return "living_room"
        if "dining" in n:
            return "dining_room"
        if "kitchen" in n:
            return "kitchen"
        if "pooja" in n:
            return "pooja_room"
        if "utility" in n:
            return "utility_room"
        if "store" in n:
            return "store_room"
        if "corridor" in n:
            return "corridor"
        if "bath" in n:
            return "bathroom"
        if "master_bed" in n:
            return "master_bedroom"
        if "parents_bed" in n:
            return "parents_bedroom"
        if "bedroom" in n or "guest" in n:
            return "bedroom"
        if "stair" in n:
            return "staircase"
        return "default"


class PlanRenderer:
    """Renders IndianResidentialPlan rooms to SVG."""

    SCALE = 10  # px per foot
    MARGIN = 90  # canvas margin px
    TITLE_H = 65  # title block height px
    EXT_W = 8.0  # external wall thickness px
    INT_W = 4.0  # internal wall thickness px

    FONTS = "Arial, Helvetica, sans-serif"

    def __init__(self, plan: IndianResidentialPlan):
        self.plan = plan
        self.parsed = plan.parsed
        self.rooms = plan.build()
        self.S = self.SCALE
        self.M = self.MARGIN

        self.pw_px = plan.pw * self.S
        self.ph_px = plan.pd * self.S
        self.cw = self.pw_px + self.M * 2
        self.ch = self.ph_px + self.M * 2 + self.TITLE_H

        self.ox = self.M + plan.sb_l * self.S
        self.oy = self.M + plan.sb_f * self.S
        self.bw_px = plan.bw * self.S
        self.bh_px = plan.bh * self.S

    def render(self) -> str:
        dwg = svgwrite.Drawing(size=(self.cw, self.ch), viewBox=f"0 0 {self.cw} {self.ch}")
        dwg.attribs["shape-rendering"] = "geometricPrecision"
        dwg.attribs["font-family"] = self.FONTS

        self._add_defs(dwg)
        self._draw_background(dwg)
        self._draw_plot_boundary(dwg)
        self._draw_setbacks(dwg)
        self._draw_room_fills(dwg)
        self._draw_furniture(dwg)
        self._draw_internal_walls(dwg)
        self._draw_external_walls(dwg)
        self._draw_windows(dwg)
        self._draw_doors(dwg)
        self._draw_labels(dwg)
        self._draw_dimensions(dwg)
        self._draw_compass(dwg)
        self._draw_title_block(dwg)
        return dwg.tostring()

    def _add_defs(self, dwg):
        # Drop shadow filter (compatible across svgwrite versions).
        f = dwg.defs.add(dwg.filter(id="wallshadow", x="-5%", y="-5%", width="115%", height="115%"))
        try:
            fe = f.feDropShadow(dx="2", dy="3", stdDeviation="3")
            fe["flood-color"] = "#000000"
            fe["flood-opacity"] = "0.22"
        except Exception:
            # Classic filter pipeline: blur + offset + merge.
            f.feGaussianBlur(in_="SourceAlpha", stdDeviation=3, result="blur")
            f.feOffset(in_="blur", dx=2, dy=3, result="shadow")
            # svgwrite versions differ here; prefer keyword form.
            try:
                f.feMerge(layernames=["shadow", "SourceGraphic"])
            except TypeError:
                f.feMerge(["shadow", "SourceGraphic"])

        patterns = {
            "bedroom": ("#E8EEF8", "#C8D4EC"),
            "living": ("#FDF6E3", "#EDE0C8"),
            "kitchen": ("#E8F5EC", "#C8E0D0"),
            "bath": ("#E0F2F8", "#B8D8E8"),
            "service": ("#F0F0EC", "#D8D8D0"),
        }
        for pid, (base, line) in patterns.items():
            pat = dwg.defs.add(dwg.pattern(id=f"p_{pid}", patternUnits="userSpaceOnUse", width="10", height="10"))
            pat.add(dwg.rect(insert=(0, 0), size=(10, 10), fill=base))
            pat.add(dwg.line(start=(0, 10), end=(10, 0), stroke=line, stroke_width=0.5, opacity=0.4))

    def _draw_background(self, dwg):
        dwg.add(dwg.rect(insert=(0, 0), size=(self.cw, self.ch), fill="#F5F0E8"))

    def _draw_plot_boundary(self, dwg):
        dwg.add(dwg.rect(insert=(self.M, self.M), size=(self.pw_px, self.ph_px), fill="none", stroke="#BBBBBB", stroke_width=0.75))

    def _draw_setbacks(self, dwg):
        p = self.plan
        M = self.M
        S = self.S
        ox, oy = self.ox, self.oy
        bw, bh = self.bw_px, self.bh_px
        pw, ph = self.pw_px, self.ph_px

        def strip(x, y, w, h):
            if w > 1 and h > 1:
                dwg.add(dwg.rect(insert=(x, y), size=(w, h), fill="#EBE6D8", stroke="none"))

        strip(M, M, pw, p.sb_f * S)
        strip(M, oy + bh, pw, p.sb_re * S)
        strip(M, oy, p.sb_l * S, bh)
        strip(ox + bw, oy, p.sb_r * S, bh)

        dwg.add(
            dwg.rect(
                insert=(ox, oy),
                size=(bw, bh),
                fill="none",
                stroke="#999999",
                stroke_width=0.75,
                stroke_dasharray="5,3",
            )
        )

    def _draw_room_fills(self, dwg):
        for r in self.rooms:
            rx, ry = self.ox + r["x"] * self.S, self.oy + r["y"] * self.S
            rw, rh = r["w"] * self.S, r["h"] * self.S
            dwg.add(dwg.rect(insert=(rx, ry), size=(rw, rh), fill=r["color"], stroke="#2A2A2A", stroke_width=1.2))

    def _draw_external_walls(self, dwg):
        T = self.EXT_W
        ox, oy = self.ox, self.oy
        bw, bh = self.bw_px, self.bh_px
        wc = "#1A1A1A"
        g = dwg.g(filter="url(#wallshadow)")

        walls = [
            (ox - T, oy - T, bw + 2 * T, T),
            (ox - T, oy + bh, bw + 2 * T, T),
            (ox - T, oy, T, bh),
            (ox + bw, oy, T, bh),
        ]
        for (x, y, w, h) in walls:
            g.add(dwg.rect(insert=(x, y), size=(w, h), fill=wc))
        dwg.add(g)

    def _draw_internal_walls(self, dwg):
        from shapely.geometry import box as sbox

        T = self.INT_W
        ox, oy = self.ox, self.oy
        S = self.S

        polys = []
        for r in self.rooms:
            rx = ox + r["x"] * S
            ry = oy + r["y"] * S
            polys.append((r, sbox(rx, ry, rx + r["w"] * S, ry + r["h"] * S)))

        drawn = set()
        for i in range(len(polys)):
            for j in range(i + 1, len(polys)):
                inter = polys[i][1].boundary.intersection(polys[j][1].boundary)
                if inter.is_empty or inter.length < 4:
                    continue
                b = inter.bounds
                key = (round(b[0]), round(b[1]), round(b[2]), round(b[3]))
                if key in drawn:
                    continue
                drawn.add(key)

                is_vert = (b[2] - b[0]) < (b[3] - b[1])
                if is_vert:
                    dwg.add(dwg.rect(insert=(b[0] - T / 2, b[1]), size=(T, b[3] - b[1]), fill="#383838"))
                else:
                    dwg.add(dwg.rect(insert=(b[0], b[1] - T / 2), size=(b[2] - b[0], T), fill="#383838"))

    def _draw_furniture(self, dwg):
        for r in self.rooms:
            rx = self.ox + r["x"] * self.S
            ry = self.oy + r["y"] * self.S
            rw = r["w"] * self.S
            rh = r["h"] * self.S
            self._furniture_for(dwg, r, rx, ry, rw, rh)

    def _furniture_for(self, dwg, r, rx, ry, rw, rh):
        cat = r["category"]
        cx = rx + rw / 2
        cy = ry + rh / 2
        PAD = 10
        iw = rw - PAD * 2
        ih = rh - PAD * 2

        if iw < 20 or ih < 20:
            return

        def rect(x, y, w, h, fill, stroke="#999999", sw=0.75, rx=0, ry2=0):
            dwg.add(dwg.rect(insert=(x, y), size=(w, h), fill=fill, stroke=stroke, stroke_width=sw, rx=rx, ry=ry2))

        def circ(cx2, cy2, r2, fill, stroke="#999999", sw=0.75):
            dwg.add(dwg.circle(center=(cx2, cy2), r=r2, fill=fill, stroke=stroke, stroke_width=sw))

        def line(x1, y1, x2, y2, stroke="#AAAAAA", sw=0.6):
            dwg.add(dwg.line(start=(x1, y1), end=(x2, y2), stroke=stroke, stroke_width=sw))

        if cat in ("master_bedroom", "parents_bedroom"):
            bw = min(iw * 0.68, 55)
            bh = min(ih * 0.72, 72)
            bx = cx - bw / 2
            by = ry + PAD + 4
            rect(bx, by, bw, 7, "#8AAAC8", "#6A8AAA", 1.0, 3, 3)
            rect(bx, by + 7, bw, bh - 7, "#C5D5E8", "#8AAAC8", 0.75, 2, 2)
            for px in [cx - bw * 0.20, cx + bw * 0.05]:
                dwg.add(dwg.ellipse(center=(px, by + 13), r=(bw * 0.15, 5), fill="#FFFFFF", stroke="#AABBD0", stroke_width=0.5))
            ww = min(iw * 0.82, 62)
            wh = 14
            rect(cx - ww / 2, ry + rh - PAD - wh, ww, wh, "#C8B89A", "#A89878", 0.75)
            for k in range(1, 3):
                line(cx - ww / 2 + ww * k / 3, ry + rh - PAD - wh, cx - ww / 2 + ww * k / 3, ry + rh - PAD)

        elif cat == "bedroom":
            bw = min(iw * 0.60, 42)
            bh = min(ih * 0.68, 65)
            bx = cx - bw / 2
            by = ry + PAD + 4
            rect(bx, by, bw, 7, "#8AAAC8", "#6A8AAA", 1.0, 3, 3)
            rect(bx, by + 7, bw, bh - 7, "#C5D5E8", "#8AAAC8", 0.75, 2, 2)
            rect(cx - min(iw * 0.78, 52) / 2, ry + rh - PAD - 13, min(iw * 0.78, 52), 12, "#C8B89A", "#A89878", 0.75)

        elif cat == "living_room":
            if iw < 55 or ih < 45:
                return
            sw = min(iw * 0.82, 85)
            sh = 28
            sy = cy - 8
            rect(cx - sw / 2, sy, sw, sh, "#C8BAB0", "#A89890", 0.75, 4, 4)
            for k in range(1, 3):
                line(cx - sw / 2 + sw * k / 3, sy, cx - sw / 2 + sw * k / 3, sy + sh)
            rect(cx - 22, sy + sh + 5, 44, 24, "#B8A888", "#988870", 0.6, 4, 4)
            rect(cx - 36, ry + rh - PAD - 13, 72, 12, "#A8988A", "#888070", 0.6)

        elif cat == "dining_room":
            if iw < 40 or ih < 38:
                return
            tw = min(iw * 0.65, 50)
            th = min(ih * 0.60, 34)
            rect(cx - tw / 2, cy - th / 2, tw, th, "#C4B08A", "#A49070", 0.75, 5, 5)
            csize = 10
            for (chx, chy) in [
                (cx - tw / 2 - csize - 2, cy - csize / 2),
                (cx + tw / 2 + 2, cy - csize / 2),
                (cx - csize * 1.1, cy - th / 2 - csize - 2),
                (cx + csize * 0.1, cy - th / 2 - csize - 2),
                (cx - csize * 1.1, cy + th / 2 + 2),
                (cx + csize * 0.1, cy + th / 2 + 2),
            ]:
                rect(chx, chy, csize, csize, "#B09870", "#907850", 0.5, 2, 2)

        elif cat == "kitchen":
            if iw < 28:
                return
            rect(rx + PAD, ry + PAD, iw, 16, "#D8D0C4", "#B0A898", 0.75)
            rect(rx + PAD + 4, ry + PAD + 3, 18, 10, "#B8D8E0", "#88A8B0", 0.6)
            for (bx2, by2) in [(rx + PAD + iw - 22, ry + PAD + 4), (rx + PAD + iw - 12, ry + PAD + 4), (rx + PAD + iw - 22, ry + PAD + 11), (rx + PAD + iw - 12, ry + PAD + 11)]:
                circ(bx2, by2, 3.5, "#888888", "#555555", 0.5)
            rect(rx + rw - PAD - 16, ry + PAD + 16, 16, ih - 16, "#D8D0C4", "#B0A898", 0.75)

        elif cat == "bathroom":
            if iw < 18 or ih < 24:
                return
            rect(rx + PAD, ry + PAD, iw, min(ih * 0.48, 26), "#C8E0E8", "#88AABB", 0.6, 2, 2)
            rect(rx + PAD, ry + rh - PAD - 22, min(iw * 0.55, 20), 20, "#D8EAEF", "#88AABB", 0.6, 4, 4)
            rect(rx + PAD, ry + PAD + min(ih * 0.48, 26) + 3, iw, 13, "#D8D0C8", "#B0A898", 0.6)

        elif cat == "pooja_room":
            aw = min(iw * 0.75, 38)
            ah = 14
            rect(cx - aw / 2, ry + PAD + 4, aw, ah, "#ECD090", "#C8A840", 1.0)
            circ(cx, ry + PAD + 4 + ah + 8, 5, "#F5C030", "#D09010", 0.75)

        elif cat == "car_porch":
            caw = min(iw * 0.50, 55)
            cah = min(ih * 0.72, 98)
            cax = cx - caw / 2
            cay = cy - cah / 2
            rect(cax, cay, caw, cah, "#CCCCBB", "#888880", 0.75, 8, 8)
            rect(cax + 4, cay + 6, caw - 8, 12, "#AACCDD", "none", 0, 2, 2)
            rect(cax + 4, cay + cah - 18, caw - 8, 12, "#AACCDD", "none", 0, 2, 2)
            for (wx, wy) in [(cax - 1, cay + 8), (cax + caw - 7, cay + 8), (cax - 1, cay + cah - 22), (cax + caw - 7, cay + cah - 22)]:
                rect(wx, wy, 8, 14, "#444444", "none", 0, 2, 2)

        elif cat == "sit_out":
            circ(cx - 14, cy, 11, "#C8B898", "#A09878", 0.75)
            circ(cx + 14, cy, 11, "#C8B898", "#A09878", 0.75)
            circ(cx, cy, 7, "#B8A880", "#908860", 0.75)

    def _draw_doors(self, dwg):
        ox, oy = self.ox, self.oy
        S = self.S

        def arc(hx, hy, dw, direction):
            r = dw
            stroke_kw = dict(stroke="#555555", stroke_width=1.2, fill="none", stroke_dasharray="3,2")
            leaf_kw = dict(stroke="#555555", stroke_width=1.8)

            if direction == "right":
                dwg.add(dwg.line(start=(hx, hy), end=(hx + r, hy), **leaf_kw))
                dwg.add(dwg.path(d=f"M{hx + r:.1f},{hy:.1f} " f"A{r:.1f},{r:.1f} 0 0 0 {hx:.1f},{hy + r:.1f}", **stroke_kw))
            elif direction == "left":
                dwg.add(dwg.line(start=(hx, hy), end=(hx - r, hy), **leaf_kw))
                dwg.add(dwg.path(d=f"M{hx - r:.1f},{hy:.1f} " f"A{r:.1f},{r:.1f} 0 0 1 {hx:.1f},{hy + r:.1f}", **stroke_kw))
            elif direction == "down":
                dwg.add(dwg.line(start=(hx, hy), end=(hx, hy + r), **leaf_kw))
                dwg.add(dwg.path(d=f"M{hx:.1f},{hy + r:.1f} " f"A{r:.1f},{r:.1f} 0 0 1 {hx + r:.1f},{hy:.1f}", **stroke_kw))
            elif direction == "up":
                dwg.add(dwg.line(start=(hx, hy), end=(hx, hy - r), **leaf_kw))
                dwg.add(dwg.path(d=f"M{hx:.1f},{hy - r:.1f} " f"A{r:.1f},{r:.1f} 0 0 0 {hx + r:.1f},{hy:.1f}", **stroke_kw))

        for r in self.rooms:
            rx = ox + r["x"] * S
            ry = oy + r["y"] * S
            rw = r["w"] * S
            rh = r["h"] * S
            cat = r["category"]

            dw = 30

            if cat == "car_porch":
                continue
            elif cat == "sit_out":
                arc(rx + rw - dw * 0.3, ry + rh * 0.45, dw, "up")
            elif cat in ("master_bedroom", "parents_bedroom", "bedroom"):
                arc(rx + rw * 0.30, ry, dw, "down")
            elif cat == "living_room":
                arc(rx + rw * 0.65, ry + rh, dw, "up")
            elif cat == "kitchen":
                arc(rx, ry + rh * 0.35, dw, "right")
            elif cat in ("bathroom", "common_bathroom"):
                arc(rx, ry + rh * 0.50, min(dw, 24), "right")
            elif cat in ("pooja_room", "utility_room", "store_room"):
                arc(rx + rw * 0.30, ry + rh, min(dw, 24), "up")

            if cat == "sit_out":
                main_dw = float(self.parsed.get("main_door_width_ft", 4) or 4) * S
                arc(ox + self.plan.bw * 0.65 * S, oy, main_dw, "down")

    def _draw_windows(self, dwg):
        ox, oy = self.ox, self.oy
        S = self.S

        WIN = 36
        T = self.EXT_W

        def win_h(wx, wy):
            dwg.add(dwg.rect(insert=(wx - WIN / 2, wy - T), size=(WIN, T * 2 + 1), fill="#F5F0E8", stroke="none"))
            for off, sw, dash in [(-2, 1.5, None), (0, 0.75, "4,3"), (2, 1.5, None)]:
                line_args = dict(
                    start=(wx - WIN / 2, wy + off),
                    end=(wx + WIN / 2, wy + off),
                    stroke="#4A88AA" if off == 0 else "#335577",
                    stroke_width=sw,
                )

                if dash:
                    line_args["stroke_dasharray"] = dash

                dwg.add(dwg.line(**line_args))

        def win_v(wx, wy):
            dwg.add(dwg.rect(insert=(wx - T, wy - WIN / 2), size=(T * 2 + 1, WIN), fill="#F5F0E8", stroke="none"))
            for off, sw in [(-2, 1.5), (0, 0.75), (2, 1.5)]:
                dwg.add(
                    dwg.line(
                        start=(wx + off, wy - WIN / 2),
                        end=(wx + off, wy + WIN / 2),
                        stroke="#4A88AA" if off == 0 else "#335577",
                        stroke_width=sw,
                    )
                )

        for r in self.rooms:
            wc = r.get("windows", 0)
            if wc <= 0:
                continue
            rx = ox + r["x"] * S
            ry = oy + r["y"] * S
            rw = r["w"] * S
            rh = r["h"] * S

            if r["y"] < 0.3:
                for k in range(wc):
                    t = (k + 1) / (wc + 1)
                    win_h(rx + rw * t, ry)
            if r["y"] + r["h"] > self.plan.bh - 0.3:
                for k in range(wc):
                    t = (k + 1) / (wc + 1)
                    win_h(rx + rw * t, ry + rh)
            if r["x"] < 0.3:
                win_v(rx, ry + rh * 0.45)
            if r["x"] + r["w"] > self.plan.bw - 0.3:
                win_v(rx + rw, ry + rh * 0.45)

    def _draw_labels(self, dwg):
        for r in self.rooms:
            rx = self.ox + r["x"] * self.S
            ry = self.oy + r["y"] * self.S
            rw = r["w"] * self.S
            rh = r["h"] * self.S
            cx = rx + rw / 2
            cy = ry + rh / 2

            label = r["label"]
            dims = f"{r['width_ft']:.0f}' × {r['depth_ft']:.0f}'  •  {r['area_sqft']:.0f} sqft"

            fs = max(6.5, min(10, rw / 9))
            fd = max(5.5, min(7.5, rw / 12))

            if rw >= 52 and rh >= 34:
                dwg.add(
                    dwg.text(
                        label,
                        insert=(cx, cy - 5),
                        text_anchor="middle",
                        dominant_baseline="middle",
                        font_size=fs,
                        font_weight="700",
                        fill="#1A1A1A",
                        letter_spacing="0.2",
                    )
                )
                dwg.add(
                    dwg.text(
                        dims,
                        insert=(cx, cy + 8),
                        text_anchor="middle",
                        dominant_baseline="middle",
                        font_size=fd,
                        fill="#666666",
                        font_style="italic",
                    )
                )
            elif rw >= 28:
                dwg.add(
                    dwg.text(
                        label,
                        insert=(cx, cy),
                        text_anchor="middle",
                        dominant_baseline="middle",
                        font_size=max(6, fs - 1),
                        font_weight="700",
                        fill="#1A1A1A",
                    )
                )

    def _draw_dimensions(self, dwg):
        ox, oy = self.ox, self.oy
        bw, bh = self.bw_px, self.bh_px
        M = self.M
        S = self.S
        p = self.plan

        def ft_str(ft):
            f = int(ft)
            i = round((ft - f) * 12)
            if i == 12:
                f += 1
                i = 0
            return f"{f}'-{i}\""

        def tick_h(x1, x2, y, lbl, bold=False):
            dwg.add(dwg.line(start=(x1, y), end=(x2, y), stroke="#666666", stroke_width=0.75))
            for x in [x1, x2]:
                dwg.add(dwg.line(start=(x, y - 5), end=(x, y + 5), stroke="#666666", stroke_width=1.0))
            dwg.add(
                dwg.text(
                    lbl,
                    insert=((x1 + x2) / 2, y - 5),
                    text_anchor="middle",
                    font_size=8 if bold else 7,
                    font_weight="600" if bold else "400",
                    fill="#444444",
                )
            )

        def tick_v(y1, y2, x, lbl, bold=False):
            dwg.add(dwg.line(start=(x, y1), end=(x, y2), stroke="#666666", stroke_width=0.75))
            for y in [y1, y2]:
                dwg.add(dwg.line(start=(x - 5, y), end=(x + 5, y), stroke="#666666", stroke_width=1.0))
            my = (y1 + y2) / 2
            dwg.add(
                dwg.text(
                    lbl,
                    insert=(x - 8, my),
                    text_anchor="middle",
                    dominant_baseline="middle",
                    font_size=8 if bold else 7,
                    font_weight="600" if bold else "400",
                    fill="#444444",
                    transform=f"rotate(-90,{x-8},{my})",
                )
            )

        tick_h(M, M + p.pw * S, M - 30, ft_str(p.pw), bold=True)
        tick_v(M, M + p.pd * S, M - 30, ft_str(p.pd), bold=True)

        tick_h(ox, ox + bw, oy - 14, ft_str(p.bw))
        tick_v(oy, oy + bh, ox - 14, ft_str(p.bh))

    def _draw_compass(self, dwg):
        SIZE = 56
        M = self.M
        cx = self.cw - M / 2 - SIZE / 2 - 4
        cy = M / 2 + SIZE / 2 + 4

        dwg.add(dwg.circle(center=(cx, cy), r=SIZE / 2, fill="white", stroke="#888888", stroke_width=1))
        dwg.add(dwg.polygon(points=[(cx, cy - 24), (cx - 6, cy - 6), (cx + 6, cy - 6)], fill="#1A1A1A"))
        dwg.add(dwg.polygon(points=[(cx, cy + 24), (cx - 6, cy + 6), (cx + 6, cy + 6)], fill="white", stroke="#1A1A1A", stroke_width=1))
        dwg.add(dwg.circle(center=(cx, cy), r=4, fill="#333333"))
        for lbl, dx, dy in [("N", 0, -29), ("S", 0, 32), ("E", 31, 3), ("W", -31, 3)]:
            dwg.add(
                dwg.text(
                    lbl,
                    insert=(cx + dx, cy + dy),
                    text_anchor="middle",
                    dominant_baseline="middle",
                    font_size=10,
                    font_weight="bold",
                    fill="#1A1A1A",
                )
            )

    def _draw_title_block(self, dwg):
        cw = self.cw
        ch = self.ch
        TH = self.TITLE_H
        y0 = ch - TH
        p = self.plan

        dwg.add(dwg.rect(insert=(0, y0), size=(cw, TH), fill="#FFFFFF", stroke="#333333", stroke_width=1.5))

        c1 = cw * 0.36
        c2 = cw * 0.70
        for x in [c1, c2]:
            dwg.add(dwg.line(start=(x, y0), end=(x, ch), stroke="#CCCCCC", stroke_width=0.75))

        mid = y0 + TH / 2

        bhk = str(p.parsed.get("bhk_type", "3BHK") or "3BHK").upper()
        style = str(p.parsed.get("style", "Modern") or "Modern").title()
        fl = int(p.parsed.get("floors", 1) or 1)
        dwg.add(dwg.text("RESIDENTIAL FLOOR PLAN", insert=(14, mid - 10), font_size=11, font_weight="700", fill="#111111", dominant_baseline="middle"))
        dwg.add(dwg.text(f"{bhk}  ·  {fl} STOREY  ·  {style.upper()}", insert=(14, mid + 10), font_size=7.5, fill="#555555", dominant_baseline="middle"))

        mc = (c1 + c2) / 2
        dwg.add(dwg.text(f"Plot {int(p.pw)}'-0\" × {int(p.pd)}'-0\"", insert=(mc, mid - 9), text_anchor="middle", font_size=9, font_weight="600", fill="#222222", dominant_baseline="middle"))
        dwg.add(dwg.text(f"Built-up: {int(p.bw * p.bh)} sq ft  |  Scale 1:100", insert=(mc, mid + 9), text_anchor="middle", font_size=7.5, fill="#555555", dominant_baseline="middle"))

        mr = (c2 + cw) / 2
        rcw = cw - c2
        vastu = p.vastu
        budget = p.budget

        if vastu:
            bw2 = min(rcw - 12, 118)
            bh2 = 20
            dwg.add(dwg.rect(insert=(mr - bw2 / 2, mid - 22), size=(bw2, bh2), fill="#E8F5E9", stroke="#4CAF50", stroke_width=1, rx=4))
            vfs = max(6.5, min(8, (bw2 - 10) / 13))
            dwg.add(dwg.text("✓ VASTU COMPLIANT", insert=(mr, mid - 12), text_anchor="middle", dominant_baseline="middle", font_size=vfs, font_weight="600", fill="#2E7D32"))

        if budget > 0:
            if budget >= 100_000:
                bs = f"₹{budget / 100_000:.0f} Lakhs"
            else:
                bs = f"₹{int(budget):,}"
            dwg.add(dwg.text(f"Budget: {bs}", insert=(mr, mid + 10), text_anchor="middle", dominant_baseline="middle", font_size=8, fill="#444444"))


def render_architectural_plan(parsed: dict) -> str:
    """
    Main entry point. Returns SVG string.
    Usage:
        svg = render_architectural_plan(parsed_json)
    """

    plan = IndianResidentialPlan(parsed)
    renderer = PlanRenderer(plan)
    return renderer.render()

