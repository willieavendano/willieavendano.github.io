# Kinematics Video Architecture (Unit 1)

Design spec for the Unit 1 concept videos. Same pipeline and palette as
`phy_u0_vectors.py` (paper `#F7F7F4` / ink `#141412` / Cushman blue `#0E406A`,
site fonts, no LaTeX yet). Render `-qh` for final; naming `PHY-U1-<slug>`.

Principle: **animate the one idea a static slide can't show.** A deck can list
the kinematic equations; only motion can show a slope *becoming* the next graph.
Reserve Manim for those; everything else is a deck or a tablet walkthrough.

## Slate

| Code | Type | Status | Serves |
|---|---|---|---|
| `PHY-U0-vectors-components` | Manim | **built — render now** | Workshop III + projectiles |
| `PHY-U1-motion-graphs` | Manim | spec below → build | Week 4 (position/velocity/acceleration) |
| `PHY-U1-projectile-decomposition` | Manim | spec below → build | Week 7 (projectile motion) |
| Kinematic-equations derivation | tablet walkthrough | recording-kit, not Manim | Week 5 (uniform acceleration) |

The derivation is deliberately NOT Manim: it's line-by-line algebra (KDEA), which
is exactly what a screencast does cheaply and Manim does expensively. Keep it in
the walkthrough lane.

## Scene 1 — `PHY-U1-motion-graphs` (the hero, ~75s)

**One idea:** the slope of the position graph *is* the velocity graph; the slope
of the velocity graph *is* the acceleration graph. Three stacked axes update in
lockstep with a moving cart.

Beats:
1. A cart on a track at the top; three empty stacked axes below (x–t, v–t, a–t),
   shared time axis, Fragment-Mono labels.
2. **Constant velocity:** cart glides steadily → x–t traces a straight ramp,
   v–t a flat positive line, a–t sits at zero. Caption: "steady speed = straight
   position line, flat velocity, zero acceleration."
3. **Speeding up:** cart accelerates → x–t curves upward (concave), v–t ramps
   linearly, a–t a flat positive line. Highlight the tangent slope on x–t and
   drop it onto v–t as the SAME value — the "slope becomes the next graph" reveal.
4. **Repeat once for slowing down** (negative a) so the sign logic lands.
5. Title card: "Each graph is the slope of the one above it."

Build notes: use `Axes`, a `Dot`/`Rectangle` cart on a `NumberLine`, `ValueTracker`
for time, `always_redraw` for the tracing dots and the tangent line. Deterministic
(no random). Keep three panels inside frame — scale down if tight (the
`keep_in_frame` habit from the vectors scene).

## Scene 2 — `PHY-U1-projectile-decomposition` (~70s)

**One idea:** horizontal and vertical motions are independent; that independence
is the entire trick of projectile motion. Directly reuses the Workshop III
components language.

Beats:
1. Launch a projectile on a parabolic path (a monkey/ball; Miami flavor welcome —
   a coconut off a seawall).
2. At several instants, freeze and show the velocity vector decomposing into a
   **constant** horizontal component (same arrow length every time) and a
   **changing** vertical component (shrinks to zero at apex, grows downward after).
3. Split-screen the two 1-D motions: horizontal = constant velocity (even spacing),
   vertical = free fall (accelerating spacing). Then recombine into the parabola.
4. Payoff card: "Horizontal: constant. Vertical: gravity. They never talk to each
   other — solve them separately, KDEA each."

Build notes: parametric parabola via `ParametricFunction` or manual kinematics with
a `ValueTracker`; component arrows via `Arrow` keyed to the parametric velocity.
Ends by explicitly invoking KDEA (the house protocol) so it threads Unit 0 → Unit 1.

## Render + publish

Per `videos/manim/README.md`: `manim -qh <file>.py <Scene>` for the 1080p60 final,
then upload per `docs/recording-kit.md` naming/description conventions and paste the
YouTube id into the course README Materials placeholder for that week.
