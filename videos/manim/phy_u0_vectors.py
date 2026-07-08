"""
phy_u0_vectors.py — Manim CE scene: VectorComponents
=====================================================

Video code: PHY-U0-vectors-components  (see videos/manim/README.md for the
full render + upload workflow, and docs/recording-kit.md for naming/upload
conventions used across the whole course library.)

This is the TEMPLATE scene for the Cushman Physics video pipeline — the
comments below are intentionally verbose so future scenes can be copy/pasted
from this one without re-deriving the same decisions.

What it shows (~70-80s at normal render speed):
    A delivery drone launches from a fixed point and flies a straight-line
    displacement of 5 km, 37 degrees north of east. The vector is decomposed
    into its x (east) and y (north) components using dashed projection
    lines, the right triangle it forms is traced solid, and SOH-CAH-TOA is
    revealed as GEOMETRY — the words "opposite", "adjacent", and
    "hypotenuse" are labeled directly on the triangle's own sides, not on a
    separate formula card — before the actual numbers are computed on
    screen (cos 37 deg x 5 km = 4.0 km, sin 37 deg x 5 km = 3.0 km). Because
    37 degrees is used, this lands on the classic 3-4-5 right triangle,
    which the scene calls out explicitly at the end. It closes on a title
    card using the site's paper/ink/blue palette.

Render commands (see README for details):
    manim -pqh phy_u0_vectors.py VectorComponents      # 1080p60 final export
    manim -pql phy_u0_vectors.py VectorComponents      # fast draft preview

Design notes for anyone copying this file for the next scene:
  - NO LaTeX DEPENDENCY. Every label uses manim's `Text` (Pango), never
    `MathTex`/`Tex`. That keeps the whole pipeline to "just manim + ffmpeg"
    with no MacTeX/BasicTeX install. Math is written out as plain unicode
    strings ("cos 37 deg = adjacent / hypotenuse") instead of typeset
    equations. If a future scene truly needs typeset math (stacked
    fractions, integrals, summations), that's the moment to install a LaTeX
    distribution and switch to MathTex — treat it as a deliberate
    trade-off, not a default.
  - PALETTE. Colors below mirror the site's CSS custom properties in
    assets/css/site.css (--paper, --ink, --blue, etc.) — reuse these
    constants, don't hardcode hex again, so every course video shares one
    look. The background is set once at module level via
    `config.background_color`; don't rely on Manim's default dark theme.
  - FONTS. FONT_DISPLAY / FONT_MONO reference the site's Familjen Grotesk
    (display) and Fragment Mono (mono) families. Pango (the text engine
    Manim's `Text` uses) silently falls back to a system default if a font
    isn't installed locally, so the scene still renders correctly without
    them — install the fonts locally for a pixel-perfect match to the site.
  - GEOMETRY IS COMPUTED, NOT EYEBALLED. All triangle points are derived
    from KM_* constants and SCALE below, so changing the story (a different
    angle, a different distance) is a one-line edit, not a re-draw.
"""

import math

from manim import *

# ---------------------------------------------------------------------------
# Site palette (mirrors assets/css/site.css custom properties). Reuse these
# constants in any future course scene instead of re-hardcoding hex values.
# ---------------------------------------------------------------------------
PAPER = "#F7F7F4"       # --paper       : scene background
PAPER_DEEP = "#EFEFEA"  # --paper-deep  : subtle panels / construction lines
INK = "#141412"         # --ink         : primary text + triangle strokes
INK_SOFT = "#6E6E68"    # --ink-soft    : secondary/caption text, reference axes
BLUE = "#0E406A"        # --blue        : accent — the displacement vector,
                        #                 the title-card band, emphasis text

FONT_DISPLAY = "Familjen Grotesk"  # site display face (title card headline)
FONT_MONO = "Fragment Mono"        # site mono face (labels, video code)

# Render on the site's light paper background everywhere, not Manim's
# default dark theme. Setting this once at import time (rather than per
# Scene) means it applies no matter which scene in this file gets rendered.
config.background_color = PAPER

# ---------------------------------------------------------------------------
# The story's numbers. A drone launches from a fixed pad and flies a
# straight-line displacement of 5 km at 37 degrees north of east. Because
# cos(37 deg) ~ 0.7986 and sin(37 deg) ~ 0.6018, 5 km at 37 degrees resolves
# to (almost exactly) a 3-4-5 right triangle — deliberately chosen so the
# on-screen arithmetic lands on clean, memorable numbers.
# ---------------------------------------------------------------------------
ANGLE_DEG = 37
HYP_KM = 5.0
ADJ_KM = round(HYP_KM * math.cos(math.radians(ANGLE_DEG)), 1)  # -> 4.0 km east
OPP_KM = round(HYP_KM * math.sin(math.radians(ANGLE_DEG)), 1)  # -> 3.0 km north

# Manim units per kilometer. Purely a "how big on screen" scale factor —
# has no bearing on the physics, only the layout.
SCALE = 1.15


def keep_in_frame(mobject, margin=0.4):
    """Nudge a mobject horizontally so it stays fully inside the visible
    frame. Handy for computed f-string labels (e.g. "opposite = 5 km ×
    sin 37° = 3.0 km north") whose final rendered width isn't known until
    the numbers are filled in — this guarantees the label never runs off
    either edge, regardless of how long the string turns out to be.
    Reuse this in future scenes for any text built from an f-string."""
    right_limit = config.frame_x_radius - margin
    left_limit = -config.frame_x_radius + margin
    if mobject.get_right()[0] > right_limit:
        mobject.shift(LEFT * (mobject.get_right()[0] - right_limit))
    if mobject.get_left()[0] < left_limit:
        mobject.shift(RIGHT * (left_limit - mobject.get_left()[0]))
    return mobject


class VectorComponents(Scene):
    """A displacement vector decomposed into components, with SOH-CAH-TOA
    shown as geometry on the resulting right triangle."""

    def construct(self):
        # The three corners of our right triangle, computed once and reused
        # by every helper method below. Shifted left/down so there's open
        # canvas to the right and above for equations and callouts.
        self.origin = LEFT * 4.3 + DOWN * 2.0                       # O: launch pad
        self.foot = self.origin + RIGHT * ADJ_KM * SCALE            # Q: foot of the
                                                                     #    perpendicular
                                                                     #    (east component)
        self.tip = self.foot + UP * OPP_KM * SCALE                  # P: vector tip
                                                                     #    (north component)

        self.draw_reference_axes()
        self.draw_displacement_vector()
        self.decompose_into_components()
        self.reveal_soh_cah_toa()
        self.compute_components_numerically()
        self.call_out_three_four_five()
        self.closing_title_card()

    # -- 1. Ground reference -------------------------------------------------
    def draw_reference_axes(self):
        """Faint compass axes (east/north) so the vector's angle has a frame
        of reference. These are reference lines only — the actual triangle
        sides get drawn solid on top of them in draw_displacement_vector()
        and decompose_into_components()."""
        east_axis = Arrow(
            self.origin, self.origin + RIGHT * 6.4,
            buff=0, color=INK_SOFT, stroke_width=2, tip_length=0.18,
        )
        north_axis = Arrow(
            self.origin, self.origin + UP * 4.4,
            buff=0, color=INK_SOFT, stroke_width=2, tip_length=0.18,
        )
        east_label = Text("EAST", font=FONT_MONO, font_size=20, color=INK_SOFT)
        east_label.next_to(east_axis.get_end(), RIGHT, buff=0.15)
        north_label = Text("NORTH", font=FONT_MONO, font_size=20, color=INK_SOFT)
        north_label.next_to(north_axis.get_end(), UP, buff=0.15)

        pad_dot = Dot(self.origin, color=INK, radius=0.07)
        pad_label = Text("launch pad", font=FONT_MONO, font_size=18, color=INK_SOFT)
        pad_label.next_to(pad_dot, DOWN, buff=0.2)

        caption = Text(
            "A delivery drone launches from South Beach:\n"
            "displacement 5 km, 37° north of east.",
            font_size=28, color=INK, line_spacing=1.2,
        ).to_edge(UP, buff=0.6)
        self.intro_caption = caption  # stashed so later methods can fade it

        self.play(Create(east_axis), Create(north_axis), run_time=1.2)
        self.play(
            FadeIn(east_label), FadeIn(north_label),
            FadeIn(pad_dot), FadeIn(pad_label),
            run_time=0.6,
        )
        self.play(Write(caption), run_time=1.6)
        self.wait(2.4)

        # Kept for the angle-arc construction in the next method.
        self.east_axis = east_axis

    # -- 2. The displacement vector (hypotenuse) ------------------------------
    def draw_displacement_vector(self):
        """Draw the resultant displacement as a single blue arrow, label its
        magnitude, and mark the 37-degree angle it makes with east."""
        vector = Arrow(
            self.origin, self.tip, buff=0, color=BLUE, stroke_width=7,
            tip_length=0.28, max_tip_length_to_length_ratio=0.15,
        )
        self.vector_label = Text("5 km", font=FONT_MONO, font_size=30, color=BLUE)
        self.vector_label.next_to(vector.get_center(), UP * 0.6 + RIGHT * 0.3, buff=0.15)

        # Angle mobject needs two Line objects that share a vertex (here,
        # self.origin) — it draws the arc between them automatically.
        vector_line = Line(self.origin, self.tip)
        angle_arc = Angle(self.east_axis, vector_line, radius=0.9, color=INK)
        angle_label = Text(f"{ANGLE_DEG}°", font=FONT_MONO, font_size=26, color=INK)
        angle_label.move_to(
            self.origin + RIGHT * 1.25 + UP * 0.45
        )

        self.play(Create(vector), run_time=1.8)
        self.play(Write(self.vector_label), run_time=0.8)
        self.play(Create(angle_arc), Write(angle_label), run_time=1.2)
        self.wait(2.8)
        self.play(FadeOut(self.intro_caption), run_time=0.6)

        self.vector = vector
        self.angle_arc = angle_arc
        self.angle_label = angle_label

    # -- 3. Decompose into x/y components --------------------------------------
    def decompose_into_components(self):
        """Drop a dashed projection line from the vector's tip to the east
        axis, then solidify it into the two component vectors that make up
        the right triangle: O->Q (east/adjacent) and Q->P (north/opposite)."""
        projection = DashedLine(
            self.tip, self.foot, color=INK_SOFT, stroke_width=3, dash_length=0.12,
        )
        self.play(Create(projection), run_time=1.3)
        self.wait(0.8)

        x_component = Arrow(
            self.origin, self.foot, buff=0, color=INK, stroke_width=6, tip_length=0.22,
        )
        self.x_label = Text("x", font=FONT_MONO, font_size=28, color=INK)
        self.x_label.next_to(x_component, DOWN, buff=0.2)

        y_component = Arrow(
            self.foot, self.tip, buff=0, color=INK, stroke_width=6, tip_length=0.22,
        )
        self.y_label = Text("y", font=FONT_MONO, font_size=28, color=INK)
        self.y_label.next_to(y_component, RIGHT, buff=0.2)

        self.play(Create(x_component), Write(self.x_label), run_time=1.3)
        self.play(Create(y_component), Write(self.y_label), run_time=1.3)
        self.play(FadeOut(projection), run_time=0.5)

        right_angle = RightAngle(
            Line(self.origin, self.foot), Line(self.foot, self.tip),
            length=0.3, color=INK,
        )
        self.play(Create(right_angle), run_time=0.8)

        emerge_caption = Text(
            "The vector, its components, and the ground\nform a right triangle.",
            font_size=26, color=INK_SOFT, line_spacing=1.2,
        ).to_edge(UP, buff=0.6)
        self.play(Write(emerge_caption), run_time=1.3)
        self.wait(2.8)
        self.play(FadeOut(emerge_caption), run_time=0.6)

        self.x_component = x_component
        self.y_component = y_component

    # -- 4. SOH-CAH-TOA as geometry --------------------------------------------
    def reveal_soh_cah_toa(self):
        """Show the SOH-CAH-TOA mnemonic, then relabel the triangle's own
        sides as opposite/adjacent/hypotenuse — the whole point being that
        the mnemonic is a description of THIS triangle, not an abstract rule."""
        mnemonic = Text(
            "SOH   CAH   TOA",
            font=FONT_MONO, font_size=34, color=INK, weight=BOLD,
            t2c={"SOH": BLUE, "CAH": BLUE},
        ).to_edge(UP, buff=0.5)
        self.play(Write(mnemonic), run_time=1.6)
        self.wait(2.8)
        self.mnemonic = mnemonic

        # Relabel the sides directly on the triangle: x -> adjacent,
        # y -> opposite, 5 km -> hypotenuse. Transform (not FadeOut+Write)
        # so the connection between the old and new label is visually clear.
        adjacent_label = Text("adjacent", font=FONT_MONO, font_size=24, color=INK)
        adjacent_label.next_to(self.x_component, DOWN, buff=0.2)
        opposite_label = Text("opposite", font=FONT_MONO, font_size=24, color=INK)
        opposite_label.next_to(self.y_component, RIGHT, buff=0.2)
        hyp_label = Text("hypotenuse", font=FONT_MONO, font_size=24, color=BLUE)
        hyp_label.next_to(self.vector_label, UP, buff=0.1)

        self.play(
            Transform(self.x_label, adjacent_label),
            Transform(self.y_label, opposite_label),
            run_time=1.3,
        )
        self.play(Write(hyp_label), run_time=1.0)
        self.wait(2.2)
        self.hyp_label = hyp_label

    # -- 5. Compute the components numerically ---------------------------------
    def compute_components_numerically(self):
        """cos(37 deg) x 5 km -> 4.0 km (adjacent/east), and
        sin(37 deg) x 5 km -> 3.0 km (opposite/north) — worked out as text
        next to the triangle side each one belongs to."""
        cah_setup = Text(
            "CAH:  cos 37° = adjacent / hypotenuse",
            font=FONT_MONO, font_size=24, color=INK,
        ).next_to(self.x_component, DOWN, buff=0.9).align_to(self.x_component, LEFT)
        self.play(Write(cah_setup), run_time=1.6)
        self.wait(1.8)

        cah_result = keep_in_frame(Text(
            f"adjacent = 5 km × cos 37° ≈ {ADJ_KM:.1f} km east",
            font=FONT_MONO, font_size=24, color=BLUE,
        ).move_to(cah_setup, aligned_edge=LEFT))
        self.play(Transform(cah_setup, cah_result), run_time=1.6)
        self.wait(2.8)

        soh_setup = Text(
            "SOH:  sin 37° = opposite / hypotenuse",
            font=FONT_MONO, font_size=24, color=INK,
        ).next_to(self.y_component, RIGHT, buff=0.6).shift(UP * 0.3)
        self.play(Write(soh_setup), run_time=1.6)
        self.wait(1.8)

        soh_result = keep_in_frame(Text(
            f"opposite = 5 km × sin 37° ≈ {OPP_KM:.1f} km north",
            font=FONT_MONO, font_size=24, color=BLUE,
        ).move_to(soh_setup, aligned_edge=LEFT))
        self.play(Transform(soh_setup, soh_result), run_time=1.6)
        self.wait(2.8)

        self.cah_setup = cah_setup
        self.soh_setup = soh_setup

    # -- 6. The punchline: it's a 3-4-5 triangle --------------------------------
    def call_out_three_four_five(self):
        callout = Text(
            "4.0, 3.0, 5.0 — almost exactly the classic 3-4-5 triangle (why physics loves 37°)",
            font=FONT_MONO, font_size=28, color=BLUE, weight=BOLD,
        ).to_edge(DOWN, buff=0.7)
        self.play(Write(callout), run_time=1.6)
        self.play(
            Indicate(self.x_component, color=BLUE, scale_factor=1.05),
            Indicate(self.y_component, color=BLUE, scale_factor=1.05),
            Indicate(self.vector, color=BLUE, scale_factor=1.05),
            run_time=1.4,
        )
        self.wait(3.2)

        # Sweep everything off screen before the title card. Plain `Group`
        # (not `VGroup`) as a safe template habit: everything here is a VMobject,
        # shapes and other Mobject types — VGroup only accepts VMobjects.
        self.play(FadeOut(Group(*self.mobjects)), run_time=1.2)

    # -- 7. Closing title card --------------------------------------------------
    def closing_title_card(self):
        """Site-palette title card: paper background (already set globally),
        ink headline, a Cushman-blue accent band, and the video code in mono
        — the same closer every future scene should reuse."""
        headline = Text(
            "Vectors & Components", font=FONT_DISPLAY, font_size=52,
            color=INK, weight=BOLD,
        )
        subtitle = Text(
            "AP Physics · Unit 0 · Triangles & Vectors",
            font=FONT_MONO, font_size=26, color=INK_SOFT,
        )
        subtitle.next_to(headline, DOWN, buff=0.35)

        accent_band = Rectangle(
            width=headline.width + 0.6, height=0.12,
            color=BLUE, fill_color=BLUE, fill_opacity=1, stroke_width=0,
        )
        accent_band.next_to(subtitle, DOWN, buff=0.45)

        video_code = Text(
            "PHY-U0-vectors-components", font=FONT_MONO, font_size=20, color=INK_SOFT,
        )
        video_code.next_to(accent_band, DOWN, buff=0.6)

        title_card = VGroup(headline, subtitle, accent_band, video_code).move_to(ORIGIN)

        self.play(FadeIn(title_card, shift=UP * 0.2), run_time=1.6)
        self.wait(5.0)
