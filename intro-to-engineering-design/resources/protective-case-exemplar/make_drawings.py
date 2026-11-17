"""Dimensioned multiview drawings (third-angle, ANSI A landscape) for the exemplar case.

Run after build_case.py:  python make_drawings.py
Writes img/drawing_shell.svg and img/drawing_cap.svg. Views come from build123d's
hidden-line projection of the real parts; dimensions are drawn from the same parameters
build_case.py uses, so the drawing and the model can't disagree.
"""
import math
from pathlib import Path

import build_case as M

HERE = Path(__file__).resolve().parent
IMG = HERE / "img"
IMG.mkdir(exist_ok=True)

SHEET_W, SHEET_H = 279.4, 215.9
INK, DIM, HID = "#141412", "#0E406A", "#6E6E68"
FONT = "Helvetica, Arial, sans-serif"


# ---------- projection ----------
# view name -> (viewport direction from look_at, up). 2D output convention verified in testing:
#   front (from +z): X = y, Y = -x     top (from -x): X = y, Y = -z
#   right (from +y): X = -z, Y = -x    end (from -y, up +z): X = x, Y = z
VIEWS = {
    "front": ((0, 0, 1), (-1, 0, 0)),
    "top": ((-1, 0, 0), (0, 0, -1)),
    "right": ((0, 1, 0), (-1, 0, 0)),
    "end": ((0, -1, 0), (0, 0, 1)),
    "iso": ((1, -1, 1), (0, 0, 1)),
}


def project(part, view, center):
    d, up = VIEWS[view]
    org = tuple(c + 500 * k for c, k in zip(center, d))
    vis, hid = part.project_to_viewport(org, up, look_at=center)
    return vis, hid


def polyline(edge, n=24):
    if edge.geom_type.name == "LINE":
        pts = [edge.position_at(0), edge.position_at(1)]
    else:
        pts = [edge.position_at(i / n) for i in range(n + 1)]
    return [(p.X, p.Y) for p in pts]


class Sheet:
    def __init__(self):
        self.out = []

    def add(self, s):
        self.out.append(s)

    def edges(self, edges, ox, oy, s, hidden=False):
        style = (f'stroke="{HID}" stroke-width="0.25" stroke-dasharray="1.6 0.9"' if hidden
                 else f'stroke="{INK}" stroke-width="0.45"')
        for e in edges:
            pts = polyline(e)
            d = " ".join(f"{ox + s * x:.2f},{oy - s * y:.2f}" for x, y in pts)
            self.add(f'<polyline points="{d}" fill="none" {style} stroke-linecap="round" stroke-linejoin="round"/>')

    def text(self, x, y, t, size=3.0, anchor="middle", weight="normal", color=DIM, rotate=0):
        rot = f' transform="rotate({rotate} {x:.2f} {y:.2f})"' if rotate else ""
        self.add(f'<text x="{x:.2f}" y="{y:.2f}" font-family="{FONT}" font-size="{size}" '
                 f'font-weight="{weight}" fill="{color}" text-anchor="{anchor}"{rot}>{t}</text>')

    def line(self, x1, y1, x2, y2, w=0.18, color=DIM, dash=None):
        da = f' stroke-dasharray="{dash}"' if dash else ""
        self.add(f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" stroke="{color}" stroke-width="{w}"{da}/>')

    def arrow(self, x, y, ang):
        a = math.radians(ang)
        L, W = 2.4, 0.75
        bx, by = x - L * math.cos(a), y - L * math.sin(a)
        px, py = -math.sin(a) * W, math.cos(a) * W
        self.add(f'<polygon points="{x:.2f},{y:.2f} {bx + px:.2f},{by + py:.2f} {bx - px:.2f},{by - py:.2f}" fill="{DIM}"/>')

    def dim_h(self, x1, x2, y_feat1, y_feat2, y, label):
        """Horizontal dimension between sheet x1 and x2, dimension line at sheet y."""
        g = 1.0 if y > max(y_feat1, y_feat2) else -1.0
        self.line(x1, y_feat1 + g * 1.0, x1, y + g * 1.5)
        self.line(x2, y_feat2 + g * 1.0, x2, y + g * 1.5)
        inside = abs(x2 - x1) > 14
        if inside:
            self.line(x1, y, x2, y)
            self.arrow(x1, y, 180 if x2 > x1 else 0)
            self.arrow(x2, y, 0 if x2 > x1 else 180)
            self.text((x1 + x2) / 2, y - 1.0, label)
        else:
            lo, hi = min(x1, x2), max(x1, x2)
            self.line(lo - 6, y, hi + 6, y)
            self.arrow(lo, y, 0)
            self.arrow(hi, y, 180)
            self.text(hi + 7, y + 1.1, label, anchor="start")

    def dim_v(self, y1, y2, x_feat1, x_feat2, x, label):
        """Vertical dimension between sheet y1 and y2, dimension line at sheet x."""
        g = 1.0 if x > max(x_feat1, x_feat2) else -1.0
        self.line(x_feat1 + g * 1.0, y1, x + g * 1.5, y1)
        self.line(x_feat2 + g * 1.0, y2, x + g * 1.5, y2)
        inside = abs(y2 - y1) > 14
        if inside:
            self.line(x, y1, x, y2)
            self.arrow(x, y1, -90 if y2 > y1 else 90)
            self.arrow(x, y2, 90 if y2 > y1 else -90)
            self.text(x - 1.0, (y1 + y2) / 2, label, rotate=-90)
        else:
            lo, hi = min(y1, y2), max(y1, y2)
            self.line(x, lo - 5, x, hi + 5)
            self.arrow(x, lo, 90)
            self.arrow(x, hi, -90)
            self.text(x + (2 if g > 0 else -2), hi + 8, label, anchor="start" if g > 0 else "end")

    def leader(self, x, y, tx, ty, label, anchor="start"):
        self.line(x, y, tx, ty)
        self.arrow(x, y, math.degrees(math.atan2(y - ty, x - tx)))
        self.line(tx, ty, tx + (6 if anchor == "start" else -6), ty)
        self.text(tx + (7 if anchor == "start" else -7), ty + 1.1, label, anchor=anchor)

    def label(self, x, y, t):
        self.text(x, y, t, size=2.8, color=INK, weight="bold")

    def frame(self, title, part_no, scale, sheet, notes):
        self.add(f'<rect x="8" y="8" width="{SHEET_W - 16}" height="{SHEET_H - 16}" fill="none" stroke="{INK}" stroke-width="0.6"/>')
        x0, y0, w, h = SHEET_W - 8 - 118, SHEET_H - 8 - 30, 118, 30
        self.add(f'<rect x="{x0}" y="{y0}" width="{w}" height="{h}" fill="#fff" stroke="{INK}" stroke-width="0.5"/>')
        for yy in (y0 + 12, y0 + 21):
            self.line(x0, yy, x0 + w, yy, w=0.3, color=INK)
        for xx in (x0 + 40, x0 + 79):
            self.line(xx, y0 + 12, xx, y0 + h, w=0.3, color=INK)
        self.text(x0 + 3, y0 + 5, "TITLE", size=2.0, anchor="start", color=HID)
        self.text(x0 + 3, y0 + 10, title, size=3.6, anchor="start", weight="bold", color=INK)
        cells = [("PART", part_no), ("MATERIAL", "PLA, 0.4 NOZZLE"), ("SCALE", scale),
                 ("DRAWN", "EXEMPLAR TEAM"), ("DATE", "12/04/2026"), ("SHEET", sheet)]
        for i, (k, v) in enumerate(cells):
            cx, cy = x0 + (i % 3) * 39.5 + 2, y0 + 12 + (i // 3) * 9
            self.text(cx + 1, cy + 3, k, size=1.9, anchor="start", color=HID)
            self.text(cx + 1, cy + 7.3, v, size=2.7, anchor="start", color=INK, weight="bold")
        nx, ny = 13, SHEET_H - 8 - 3 - 3.8 * (len(notes) - 1)
        self.text(nx, ny - 4.2, "NOTES", size=2.8, anchor="start", color=INK, weight="bold")
        for i, n in enumerate(notes):
            self.text(nx, ny + i * 3.8, f"{i + 1}. {n}", size=2.35, anchor="start", color=INK)
        self.add(f'<g font-family="{FONT}"><text x="{SHEET_W - 10}" y="13" font-size="2.4" fill="{HID}" '
                 f'text-anchor="end">THIRD-ANGLE PROJECTION &#183; ALL DIMENSIONS IN mm</text></g>')

    def svg(self):
        body = "\n".join(self.out)
        return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {SHEET_W} {SHEET_H}" '
                f'width="{SHEET_W}mm" height="{SHEET_H}mm">\n<rect width="100%" height="100%" fill="#fff"/>\n{body}\n</svg>\n')


def place(sheet, part, view, center, ox, oy, s, hidden=True):
    vis, hid = project(part, view, center)
    if hidden:
        sheet.edges(hid, ox, oy, s, hidden=True)
    sheet.edges(vis, ox, oy, s)


def shell_sheet(shell):
    S = Sheet()
    s = 1.5
    y_lo, y_hi = -M.CLR - M.WALL, M.Y_TONGUE_END                 # -2.4 .. 110
    cx, cy, cz = 0.0, (y_lo + y_hi) / 2, (M.Z_BOT + M.Z_TOP) / 2
    FX, FY = 112, 100      # front view center on sheet
    TX, TY = FX, 25        # top view (third-angle: above front)
    RX, RY = 222, FY       # right view (third-angle: right of front)
    place(S, shell, "front", (cx, cy, cz), FX, FY, s)
    place(S, shell, "top", (cx, cy, cz), TX, TY, s)
    place(S, shell, "right", (cx, cy, cz), RX, RY, s)
    place(S, shell, "iso", (cx, cy, cz), 240, 31, 0.30, hidden=False)
    fx = lambda y: FX + s * (y - cy)
    fy = lambda x: FY + s * x
    ty = lambda z: TY + s * (z - cz)
    rx = lambda z: RX - s * (z - cz)
    half = M.W_O / 2
    # front view
    S.dim_h(fx(M.SPLIT), fx(y_hi), fy(half), fy(half), fy(half) + 6, f"{M.JOINT:.1f} TONGUE")
    S.dim_h(fx(y_lo), fx(y_hi), fy(half), fy(half), fy(half) + 12, f"{y_hi - y_lo:.1f}")
    S.dim_v(fy(-half), fy(half), fx(y_lo), fx(y_lo), fx(y_lo) - 10, f"{M.W_O:.1f}")
    win = M.W_I / 2 - M.LIP_IN
    xin = fx(55)
    S.dim_v(fy(-win), fy(win), xin, xin, xin, f"{2 * win:.1f} SCREEN OPENING")
    S.leader(fx(y_lo) + 3.2, fy(half) - 3.2, fx(y_lo) + 22, fy(half) - 14, f"R{M.R_O:.1f} OUTSIDE")
    # top view (seen from -x, the volume side)
    v0 = M.VOL_CY - (M.VOL_LEN + M.BTN_SLOT_EXTRA) / 2
    v1 = M.VOL_CY + (M.VOL_LEN + M.BTN_SLOT_EXTRA) / 2
    zs = M.PH_T / 2
    S.dim_h(fx(v0), fx(v1), ty(zs - 2.5), ty(zs - 2.5), ty(M.Z_BOT) - 4.5,
            f"{v1 - v0:.0f} &#215; {M.BTN_SLOT_H:.0f} VOLUME SLOT")
    S.dim_h(fx(y_lo), fx(v0), ty(M.Z_TOP), ty(zs + 2.5), ty(M.Z_TOP) + 5.5, f"{v0 - y_lo:.1f}")
    S.dim_v(ty(M.Z_TOP), ty(M.Z_BOT), fx(y_hi), fx(y_hi), fx(y_hi) + 7, f"{M.Z_TOP - M.Z_BOT:.1f}")
    # right view (from +y, looking into the open tongue end)
    S.dim_h(rx(M.Z_TOP), rx(M.Z_BOT), fy(half), fy(half), fy(half) + 12, f"{M.Z_TOP - M.Z_BOT:.1f}")
    S.leader(rx(M.Z_TOP - M.LIP_T / 2), fy(-(M.W_I / 2 - 1)), RX - 10, 37, f"LIP {M.LIP_T} &#215; {M.LIP_IN}", anchor="end")
    S.leader(rx(M.Z_BOT + M.FLOOR / 2), fy(-6), RX + 13, fy(-8), f"FLOOR {M.FLOOR:.1f}")
    S.leader(rx(M.PH_T / 2) + 1, fy(half - 0.5), RX + 13, fy(18), f"WALL {M.WALL:.1f}")
    S.leader(rx(M.PH_T / 2) + 1, fy(-half + 1.5), RX + 13, fy(-31), f"TONGUE {M.WALL - M.TONGUE_INSET:.1f}")
    # labels
    S.label(FX, fy(half) + 19, "FRONT (SCREEN SIDE)")
    S.text(fx(y_lo), 12.5, "TOP (VOLUME SIDE)", size=2.8, color=INK, weight="bold", anchor="start")
    S.label(RX, fy(half) + 19, "RIGHT (TONGUE END)")
    S.label(253, 47, "ISOMETRIC")
    S.frame("CASE SHELL &#8212; PART A", "1.3.7-A", "3:2", "1 OF 2", [
        f"INTERIOR = DEMO PHONE + {M.CLR} PER SIDE: {M.W_I:.1f} &#215; {M.L_I:.1f} &#215; {M.H_I:.1f}, R{M.R_I:.1f} CORNERS.",
        f"POWER SLOT {M.PWR_LEN + M.BTN_SLOT_EXTRA:.0f} &#215; {M.BTN_SLOT_H:.0f}, OPPOSITE SIDE, {M.PWR_CY - (M.PWR_LEN + M.BTN_SLOT_EXTRA) / 2 - y_lo:.1f} FROM BOTTOM END.",
        f"BOTTOM END: USB-C SLOT {M.USB_SLOT[0]:.0f} &#215; {M.USB_SLOT[1]:.0f} CENTERED; SPEAKER SLOTS {M.SPK_SLOT[0]:.0f} &#215; {M.SPK_SLOT[1]} AT &#177;{M.SPK_X:.0f}.",
        f"BUTTON RELIEF CHANNELS {M.BTN_RELIEF} DEEP &#215; {M.BTN_RELIEF_H:.0f} TALL INSIDE BOTH WALLS, SLOT TO TONGUE END.",
        f"DETENT BUMPS R{M.DETENT_R:.0f}, {M.DETENT_PROUD} PROUD, BOTH TONGUE WALLS, {M.JOINT / 2:.0f} FROM TONGUE END.",
        "PRINT BACK-DOWN, NO SUPPORTS. UNTOLERANCED DIMENSIONS &#177;0.2.",
    ])
    return S.svg()


def cap_sheet(cap):
    S = Sheet()
    s = 1.5
    y_lo, y_hi = M.SPLIT, M.L_I - M.CLR + M.WALL  # 104 .. 152.4
    cx, cy, cz = 0.0, (y_lo + y_hi) / 2, (M.Z_BOT + M.Z_TOP) / 2
    FX, FY = 80, 100
    TX, TY = FX, 25
    RX, RY = 160, FY
    place(S, cap, "front", (cx, cy, cz), FX, FY, s)
    place(S, cap, "top", (cx, cy, cz), TX, TY, s)
    place(S, cap, "right", (cx, cy, cz), RX, RY, s)
    place(S, cap, "iso", (cx, cy, cz), 228, 72, 0.5, hidden=False)
    fx = lambda y: FX + s * (y - cy)
    fy = lambda x: FY + s * x
    ty = lambda z: TY + s * (z - cz)
    rx = lambda z: RX - s * (z - cz)
    half = M.W_O / 2
    S.dim_h(fx(y_lo), fx(M.Y_TONGUE_END), fy(half), fy(half), fy(half) + 6, f"{M.JOINT:.1f} SOCKET")
    S.dim_h(fx(y_lo), fx(y_hi), fy(half), fy(half), fy(half) + 12, f"{y_hi - y_lo:.1f}")
    S.dim_v(fy(-half), fy(half), fx(y_lo), fx(y_lo), fx(y_lo) - 10, f"{M.W_O:.1f}")
    n0, n1 = M.CAM_CX - M.CAM_WIN / 2, M.CAM_CX + M.CAM_WIN / 2
    nt = M.CAM_CY + M.CAM_WIN / 2
    S.dim_v(fy(n0), fy(n1), fx(nt), fx(nt), fx(y_hi) + 7, f"{M.CAM_WIN:.1f} NOTCH")
    S.dim_v(fy(n1), fy(half), fx(y_hi), fx(y_hi), fx(y_hi) + 7, f"{half - n1:.1f}")
    S.dim_h(fx(y_lo), fx(nt), fy(n0), fy(n0), fy(-half) - 5, f"{nt - y_lo:.1f} TO END OF NOTCH")
    S.leader(fx(nt - 1.9), fy(n1 - 1.9), fx(nt) - 14, fy(n1) - 14, f"R{M.CAM_R + 0.5:.1f}", anchor="end")
    S.dim_h(fx(y_lo), fx(M.Y_DETENT), ty(M.Z_BOT), ty(M.PH_T / 2), ty(M.Z_BOT) - 4.5,
            f"{M.Y_DETENT - y_lo:.1f} TO &#216;{M.DETENT_HOLE_D} DETENT HOLE (BOTH SIDES)")
    S.dim_v(ty(M.Z_TOP), ty(M.Z_BOT), fx(y_hi), fx(y_hi), fx(y_hi) + 7, f"{M.Z_TOP - M.Z_BOT:.1f}")
    S.dim_h(rx(M.Z_TOP), rx(M.Z_BOT), fy(half), fy(half), fy(half) + 6, f"{M.Z_TOP - M.Z_BOT:.1f}")
    S.leader(rx(M.Z_BOT + 1), fy(-half + 6), RX + 13, fy(-30), f"FLOOR {M.FLOOR:.1f}")
    S.leader(rx(M.PH_T / 2) + 1, fy(half - 0.5), RX + 13, fy(20), f"WALL {M.WALL:.1f}")
    S.label(FX, fy(half) + 19, "FRONT (SCREEN SIDE)")
    S.text(fx(y_lo) - 4, TY + 1, "TOP (VOLUME SIDE)", size=2.8, color=INK, weight="bold", anchor="end")
    S.label(RX, fy(half) + 19, "RIGHT (TOP END)")
    S.label(228, 102, "ISOMETRIC")
    S.frame("SNAP CAP &#8212; PART B", "1.3.7-B", "3:2", "2 OF 2", [
        f"CAP SHARES THE SHELL PROFILE: {M.W_O:.1f} &#215; {M.Z_TOP - M.Z_BOT:.1f}, R{M.R_O:.1f} CORNERS, LIP {M.LIP_T} &#215; {M.LIP_IN}.",
        f"SOCKET = TONGUE + {M.JCLR} PER SIDE, {M.JOINT:.0f} DEEP. PART A DETENT BUMPS SNAP INTO &#216;{M.DETENT_HOLE_D} HOLES.",
        f"CAMERA NOTCH IS OPEN TO THE LOWER EDGE SO THE CAP NEVER RIDES OVER THE {M.CAM_H} mm CAMERA BUMP.",
        f"BACK STANDS {M.FLOOR - M.CAM_H:.1f} PROUD OF THE CAMERA BUMP; LIP STANDS {M.Z_TOP - M.PH_T:.1f} ABOVE THE SCREEN.",
        "PRINT BACK-DOWN, NO SUPPORTS. UNTOLERANCED DIMENSIONS &#177;0.2.",
    ])
    return S.svg()


def main():
    shell, cap = M.build_case()
    (IMG / "drawing_shell.svg").write_text(shell_sheet(shell))
    (IMG / "drawing_cap.svg").write_text(cap_sheet(cap))
    print("wrote drawing_shell.svg, drawing_cap.svg")


if __name__ == "__main__":
    main()
