"""Concept-sketch stand-ins and the tolerance section detail for the exemplar deck.

Real student decks use PHOTOS of notebook sketches. These hand-drawn-style figures
(matplotlib xkcd mode on graph paper) only stand in for those photos in the exemplar.
Also draws img/section_detail.svg, a 5:1 section through one side of the case + phone,
straight from build_case.py's parameters.

Run:  python make_sketches.py
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Rectangle, Arc

import build_case as M

HERE = Path(__file__).resolve().parent
IMG = HERE / "img"
FONT = "/System/Library/Fonts/Supplemental/Bradley Hand Bold.ttf"
font_manager.fontManager.addfont(FONT)
HAND = font_manager.FontProperties(fname=FONT).get_name()
PENCIL = "#2b2b33"
BLUE = "#1f5fa8"


def paper(ax, w, h):
    ax.set_xlim(0, w)
    ax.set_ylim(0, h)
    ax.set_aspect("equal")
    ax.axis("off")
    for x in range(0, w + 1, 5):
        ax.axvline(x, color="#b9d3ea", lw=0.5 if x % 25 else 0.9, zorder=0)
    for y in range(0, h + 1, 5):
        ax.axhline(y, color="#b9d3ea", lw=0.5 if y % 25 else 0.9, zorder=0)


def rrect(ax, x, y, w, h, r, **kw):
    ax.add_patch(FancyBboxPatch((x + r, y + r), w - 2 * r, h - 2 * r, boxstyle=f"round,pad={r}",
                                fill=False, ec=kw.pop("ec", PENCIL), lw=kw.pop("lw", 2.0), **kw))


def arrow(ax, a, b, color=BLUE, rad=0.0, lw=1.8):
    ax.add_patch(FancyArrowPatch(a, b, arrowstyle="-|>", mutation_scale=16, color=color, lw=lw,
                                 connectionstyle=f"arc3,rad={rad}"))


def dim(ax, a, b, label, off=(0, 0), rot=0):
    ax.annotate("", xy=a, xytext=b, arrowprops=dict(arrowstyle="<->", color=BLUE, lw=1.3))
    mx, my = (a[0] + b[0]) / 2 + off[0], (a[1] + b[1]) / 2 + off[1]
    ax.text(mx, my, label, color=BLUE, fontsize=15, ha="center", va="center", rotation=rot, fontfamily=HAND)


def note(ax, x, y, t, size=16, color=PENCIL, **kw):
    ax.text(x, y, t, fontsize=size, color=color, fontfamily=HAND, **kw)


def sketch(fname, draw):
    with plt.xkcd(scale=0.8, length=120, randomness=3):
        fig, ax = plt.subplots(figsize=(8, 6), dpi=150)
        fig.patch.set_facecolor("#fbfaf4")
        paper(ax, 200, 150)
        draw(ax)
        fig.savefig(IMG / fname, bbox_inches="tight", pad_inches=0.05, facecolor=fig.get_facecolor())
        plt.close(fig)


def concept_a(ax):
    note(ax, 6, 138, "Concept A: Slide-in shell + snap cap", size=21)
    rrect(ax, 20, 18, 77, 84, 9)                              # shell
    ax.plot([24, 93], [102, 102], color="#fbfaf4", lw=3)      # open top end of the shell
    rrect(ax, 20, 108, 77, 22, 8, ec=BLUE)                    # cap, exploded above
    arrow(ax, (106, 128), (106, 112))
    note(ax, 110, 116, "cap slides on,\nsnaps (detents)", size=14, color=BLUE)
    arrow(ax, (58, 100), (58, 78))
    note(ax, 26, 64, "phone slides in\nfrom the top", size=14, color=BLUE)
    note(ax, 26, 32, "lip 2 mm all\naround the screen", size=13)
    note(ax, 112, 66, "+ only 2 parts\n+ no hinge to print\n- joint must stay tight", size=13)
    dim(ax, (20, 10), (97, 10), "76.8 wide", off=(0, -5))
    dim(ax, (12, 18), (12, 130), "~155 long", off=(-6, 0), rot=90)


def concept_b(ax):
    note(ax, 6, 138, "Concept B: Hinged flip folio", size=21)
    rrect(ax, 18, 14, 70, 92, 9)                               # back tray
    rrect(ax, 104, 14, 70, 92, 9, ec=BLUE)                     # cover, opened flat
    for y in (24, 42, 60, 78, 96):                             # knuckles
        ax.add_patch(Rectangle((88, y - 4), 16, 8, fill=False, ec=PENCIL, lw=1.6))
    ax.plot([96, 96], [17, 103], color=PENCIL, lw=1.2, ls="--")
    arrow(ax, (150, 112), (55, 112), rad=-0.25)
    note(ax, 152, 114, "cover\nfolds over", size=14, color=BLUE)
    dim(ax, (18, 6), (88, 6), "~77", off=(0, -5))
    note(ax, 108, 52, "pin hinge,\n0.5 clearance?", size=13, color=BLUE)
    note(ax, 22, 48, "+ covers the screen\n- hinge prints badly\n- 7 s? flap in the way\n- 2x the plastic", size=13)


def concept_c(ax):
    note(ax, 6, 138, "Concept C: Bumper frame + back plate", size=21)
    rrect(ax, 20, 66, 80, 52, 10)                              # frame (perimeter)
    rrect(ax, 28, 74, 64, 36, 6, lw=1.4)
    rrect(ax, 20, 14, 80, 40, 10, ec=BLUE)                     # back plate (exploded below)
    arrow(ax, (60, 56), (60, 68))
    note(ax, 64, 58, "press-fit", size=14, color=BLUE)
    for x in (30, 50, 70, 90):                                 # snap tabs
        ax.plot([x, x], [54, 58], color=BLUE, lw=2)
    note(ax, 108, 100, "frame = ring around\nthe phone's sides", size=13)
    note(ax, 108, 50, "+ easy phone insertion\n- 8 snap tabs to tune\n- thin ring walls crack\n- most complex", size=13)
    dim(ax, (20, 124), (100, 124), "~77", off=(0, 5))


def section_detail():
    """5:1 section through the -x side of shell + phone at mid-length."""
    k = 5.0
    W, H = 178.0, 105.0
    ox, oy = 18.0, 82.0         # sheet coords of case outer bottom-left corner region
    X = lambda x: ox + k * (x - (-M.W_O / 2))   # x measured from case outer wall
    Y = lambda z: oy - k * (z - M.Z_BOT)
    xo, xi = -M.W_O / 2, -M.W_I / 2
    xlip = xi + M.LIP_IN
    xr = xo + 24.0              # crop line
    case = [(xo, M.Z_BOT), (xr, M.Z_BOT), (xr, 0), (xi, 0), (xi, M.H_I), (xlip, M.H_I),
            (xlip, M.Z_TOP), (xo, M.Z_TOP)]
    ph_x0 = -M.PH_W / 2
    phone = [(ph_x0, 0), (xr, 0), (xr, M.PH_T), (ph_x0, M.PH_T)]
    poly = lambda pts: " ".join(f"{X(x):.2f},{Y(z):.2f}" for x, z in pts)
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" font-family="Helvetica, Arial, sans-serif">',
           '<defs><pattern id="hatch" width="2" height="2" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
           '<line x1="0" y1="0" x2="0" y2="2" stroke="#0071CE" stroke-width="0.5"/></pattern></defs>',
           f'<polygon points="{poly(case)}" fill="url(#hatch)" stroke="#0E406A" stroke-width="0.5"/>',
           f'<polygon points="{poly(phone)}" fill="#2b2d33" stroke="#141412" stroke-width="0.4"/>',
           f'<line x1="{X(xr):.2f}" y1="{Y(M.Z_BOT) + 4:.2f}" x2="{X(xr):.2f}" y2="{Y(M.Z_TOP) - 4:.2f}" stroke="#6E6E68" stroke-width="0.3" stroke-dasharray="1.5 1"/>',
           f'<text x="{X(ph_x0) + 30:.2f}" y="{Y(M.PH_T / 2) + 1.5:.2f}" fill="#fff" font-size="4">DEMO PHONE</text>']

    def d(x1, y1, x2, y2, label, tx, ty, anchor="middle"):
        out.append(f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" stroke="#0E406A" stroke-width="0.25" '
                   'marker-start="url(#a)" marker-end="url(#a)"/>')
        out.append(f'<text x="{tx:.2f}" y="{ty:.2f}" fill="#0E406A" font-size="3.6" text-anchor="{anchor}">{label}</text>')

    out.insert(2, '<defs><marker id="a" viewBox="0 0 6 6" refX="3" refY="3" markerWidth="4" markerHeight="4" orient="auto-start-reverse">'
                  '<path d="M0,0 L6,3 L0,6 z" fill="#0E406A"/></marker></defs>')
    # side clearance 0.4
    d(X(xi), Y(M.PH_T / 2), X(ph_x0), Y(M.PH_T / 2), "", 0, 0)
    gap = lambda x0, z0, x1, z1: out.append(f'<rect x="{X(x0):.2f}" y="{Y(z1):.2f}" width="{X(x1) - X(x0):.2f}" height="{Y(z0) - Y(z1):.2f}" fill="#E5484D"/>')
    gap(xi, 0, ph_x0, M.H_I)                 # side clearance
    gap(xi, M.PH_T, xr, M.H_I)               # clearance above the screen
    out.append(f'<text x="{X(ph_x0) + 3:.2f}" y="{Y(M.PH_T / 2) + 6:.2f}" fill="#FF8A8F" font-size="3.6" font-weight="bold">&#8592; {M.CLR} SIDE CLEARANCE</text>')
    # top clearance 0.4
    out.append(f'<text x="{X(xlip) + 3:.2f}" y="{Y(M.PH_T) + 5:.2f}" fill="#FF8A8F" font-size="3.6" font-weight="bold">&#8593; {M.CLR_T} ABOVE THE SCREEN</text>')
    # wall, floor, lip, overall
    d(X(xo), Y(M.Z_BOT) + 6, X(xi), Y(M.Z_BOT) + 6, "", 0, 0)
    out.append(f'<text x="{X(xo) + 5:.2f}" y="{Y(M.Z_BOT) + 11:.2f}" fill="#0E406A" font-size="3.6" text-anchor="middle">WALL {M.WALL}</text>')
    d(X(xr) + 6, Y(M.Z_BOT), X(xr) + 6, Y(0), "", 0, 0)
    out.append(f'<text x="{X(xr) + 8:.2f}" y="{Y(-M.FLOOR / 2) + 1.3:.2f}" fill="#0E406A" font-size="3.6">FLOOR {M.FLOOR}</text>')
    d(X(xo) - 5, Y(M.Z_BOT), X(xo) - 5, Y(M.Z_TOP), "", 0, 0)
    out.append(f'<text x="{X(xo) - 7:.2f}" y="{Y((M.Z_TOP + M.Z_BOT) / 2):.2f}" fill="#0E406A" font-size="3.6" text-anchor="middle" '
               f'transform="rotate(-90 {X(xo) - 7:.2f} {Y((M.Z_TOP + M.Z_BOT) / 2):.2f})">{M.Z_TOP - M.Z_BOT:.1f}</text>')
    d(X(xi), Y(M.Z_TOP) - 8, X(xlip), Y(M.Z_TOP) - 8, "", 0, 0)
    out.append(f'<text x="{X(xlip) + 2:.2f}" y="{Y(M.Z_TOP) - 7:.2f}" fill="#0E406A" font-size="3.6">LIP OVERHANG {M.LIP_IN}</text>')
    out.append(f'<line x1="{X(xlip):.2f}" y1="{Y(M.Z_TOP):.2f}" x2="{X(xlip) + 34:.2f}" y2="{Y(M.Z_TOP):.2f}" stroke="#0E406A" stroke-width="0.2"/>')
    d(X(xlip) + 30, Y(M.Z_TOP), X(xlip) + 30, Y(M.PH_T), "", 0, 0)
    out.append(f'<text x="{X(xlip) + 33:.2f}" y="{Y(M.PH_T) - 2:.2f}" fill="#0E406A" font-size="3.6">LIP STANDS {M.Z_TOP - M.PH_T:.1f} ABOVE SCREEN</text>')
    out.append(f'<text x="2" y="{H - 3}" fill="#6E6E68" font-size="3.2">SECTION A&#8211;A (5:1) &#183; HATCH = CASE (PLA) &#183; mm</text>')
    out.append("</svg>")
    (IMG / "section_detail.svg").write_text("\n".join(out))


if __name__ == "__main__":
    sketch("sketch_concept_a.png", concept_a)
    sketch("sketch_concept_b.png", concept_b)
    sketch("sketch_concept_c.png", concept_c)
    section_detail()
    print("sketches + section detail written")
