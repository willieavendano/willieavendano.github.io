#!/usr/bin/env python3
"""Builds the site favicon: a right triangle with its right-angle tick,
white on a Cushman-blue rounded tile.

Drawn at 8x and downsampled rather than rasterised at final size, so the
hypotenuse stays clean at 32px. The 16px version drops the right-angle tick
and thickens the figure — at that size the tick is sub-pixel and only muddies
the silhouette.

    python3 tools/make-favicon.py

Writes favicon.svg, favicon.ico, favicon-16/32/48.png, apple-touch-icon.png.
Requires Pillow.
"""

from __future__ import annotations

import os

from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMG = os.path.join(ROOT, "assets", "img")

BLUE = (14, 64, 106, 255)      # --blue  #0E406A
WHITE = (255, 255, 255, 255)
SS = 8                          # supersample factor


def draw_icon(size: int, tick: bool = True) -> Image.Image:
    """Render one icon at `size` px. Geometry is expressed on a 32-unit grid."""
    S = size * SS
    u = S / 32.0                                    # one grid unit, in pixels
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)

    # Rounded tile. Corner radius scales down at small sizes so the square
    # does not read as a circle.
    radius = (4.0 if size <= 16 else 7.0) * u
    d.rounded_rectangle([0, 0, S - 1, S - 1], radius=radius, fill=BLUE)

    if size <= 16:
        # Chunkier triangle, no tick — mass beats detail at this size.
        pts = [(7.0 * u, 25.0 * u), (25.0 * u, 25.0 * u), (7.0 * u, 7.0 * u)]
        d.polygon(pts, fill=WHITE)
    else:
        pts = [(8.5 * u, 23.5 * u), (24.0 * u, 23.5 * u), (8.5 * u, 8.0 * u)]
        d.polygon(pts, fill=WHITE)
        if tick:
            # Right-angle tick: a small blue square notched into the corner,
            # held off the edges so the corner itself stays white.
            d.rectangle([10.6 * u, 19.6 * u, 13.6 * u, 22.6 * u], fill=BLUE)

    return im.resize((size, size), Image.LANCZOS)


SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" role="img" aria-label="Willie Avendano — courses">
  <rect width="32" height="32" rx="7" fill="#0E406A"/>
  <path d="M8.5 23.5 H24 L8.5 8 Z" fill="#ffffff"/>
  <rect x="10.6" y="19.6" width="3" height="3" fill="#0E406A"/>
</svg>
"""


def main():
    os.makedirs(IMG, exist_ok=True)

    sizes = [16, 32, 48, 180]
    images = {s: draw_icon(s, tick=(s > 16)) for s in sizes}

    for s in (16, 32, 48):
        p = os.path.join(IMG, f"favicon-{s}.png")
        images[s].save(p)
        print(f"wrote {os.path.relpath(p, ROOT)}")

    # apple-touch-icon wants an opaque square with no transparency
    at = Image.new("RGB", (180, 180), BLUE[:3])
    at.paste(images[180], (0, 0), images[180])
    p = os.path.join(ROOT, "apple-touch-icon.png")
    at.save(p)
    print(f"wrote {os.path.relpath(p, ROOT)}")

    # Multi-resolution .ico at the repo root — this is the path browsers
    # probe by default, and the one that was 404ing site-wide.
    p = os.path.join(ROOT, "favicon.ico")
    images[48].save(p, format="ICO", sizes=[(16, 16), (32, 32), (48, 48)])
    print(f"wrote {os.path.relpath(p, ROOT)}")

    p = os.path.join(IMG, "favicon.svg")
    with open(p, "w") as f:
        f.write(SVG)
    print(f"wrote {os.path.relpath(p, ROOT)}")


if __name__ == "__main__":
    main()
