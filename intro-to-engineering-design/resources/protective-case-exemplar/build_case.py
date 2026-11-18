"""IED Midterm exemplar: Project 1.3.7 Design a Protective Case (Phone Edition).

Parametric model of the exemplar student's chosen concept, "Slide-In Shell +
Snap Cap", designed for a generic DEMO PHONE with round-number dimensions.
Coordinates: phone back at z = 0, screen at z = PH_T, bottom end (USB-C) at
y = 0, top end (camera) at y = PH_L, centered on x = 0. All units mm.

How it goes together: the phone slides DOWN into the shell from its open top
end (the bottom wall and side lips hold it), then the cap slides down over the
shell's tongue and snaps on with two detent bumps. The camera window is a
notch open to the cap's lower edge so the cap never rides over the camera bump.

Outputs (written next to this file):
  case_shell.stl, case_cap.stl, demo_phone_dummy.stl
  protective_case_exemplar.step   (shell + cap + phone; opens in Fusion)
  model.json                      (every dimension, volumes, fit checks)

Run:  python build_case.py      (needs build123d)
"""
import json
from pathlib import Path

from build123d import (
    Box, Cylinder, Sphere, RectangleRounded, SlotOverall, Plane, Pos, Rot, Axis,
    extrude, fillet, export_stl, export_step, Compound, Align,
)

OUT = Path(__file__).resolve().parent

# ---------------- Demo phone (the "device") ----------------
PH_L, PH_W, PH_T, PH_R = 150.0, 72.0, 8.0, 10.0      # body
CAM_W, CAM_R, CAM_H = 30.0, 6.0, 1.5                 # square camera bump on the back
CAM_X0, CAM_Y0 = 8.0, 8.0                            # bump inset from side / top edge
PWR_Y, PWR_LEN = 52.0, 16.0                          # power: starts 52 from top, right side (+x)
VOL_Y, VOL_LEN = 50.0, 28.0                          # volume rocker: starts 50 from top, left side (-x)
BTN_PROUD, BTN_H = 0.5, 3.0
USB_W, USB_H = 9.0, 3.2                              # USB-C port, bottom end, centered

# ---------------- Case design decisions ----------------
CLR = 0.4          # clearance per side, phone to case (length & width)
CLR_T = 0.4        # clearance above the screen (thickness)
WALL = 2.0         # side / end wall
FLOOR = 2.0        # back floor (camera bump 1.5 -> case stands 0.5 proud of lens)
LIP_T = 1.2        # lip thickness over the screen
LIP_IN = 2.0       # lip overhang onto the screen edge
EDGE_FILLET = 1.0  # outer edge rounding
SPLIT = 104.0      # shell / cap split, measured from the phone's bottom end
JOINT = 6.0        # telescoping joint length (tongue on shell, socket in cap)
TONGUE_INSET = 1.0 # tongue skin removed from outside of shell
JCLR = 0.2         # joint clearance per side
DETENT_R, DETENT_PROUD = 1.0, 0.4
DETENT_HOLE_D = 2.2
BTN_SLOT_H, BTN_SLOT_EXTRA = 5.0, 2.0                # slot height, extra length (1 mm each end)
BTN_RELIEF = 0.3   # v2: inside channel so the 0.5-proud buttons clear the 0.4 clearance while sliding in
BTN_RELIEF_H = 4.0
USB_SLOT = (14.0, 7.0)
SPK_SLOT, SPK_X = (12.0, 3.5), 20.0

# derived
W_I, L_I, R_I = PH_W + 2 * CLR, PH_L + 2 * CLR, PH_R + CLR
W_O, L_O, R_O = W_I + 2 * WALL, L_I + 2 * WALL, R_I + WALL
H_I = PH_T + CLR_T
Z_BOT, Z_TOP = -FLOOR, H_I + LIP_T
YC = PH_L / 2
EPS = 0.01
CAM_CX = PH_W / 2 - CAM_X0 - CAM_W / 2
CAM_CY = PH_L - CAM_Y0 - CAM_W / 2
CAM_WIN = CAM_W + 1.0
PWR_CY = PH_L - PWR_Y - PWR_LEN / 2
VOL_CY = PH_L - VOL_Y - VOL_LEN / 2
Y_TONGUE_END = SPLIT + JOINT
Y_DETENT = SPLIT + JOINT / 2


def prism(w, l, r, z0, z1, x=0.0, y=YC):
    """Rounded-rectangle prism from z0 to z1, centered at (x, y)."""
    return Pos(x, y, z0) * extrude(RectangleRounded(w, l, r), z1 - z0)


def build_case():
    body = prism(W_O, L_O, R_O, Z_BOT, Z_TOP)
    body = fillet(body.edges().group_by(Axis.Z)[0] + body.edges().group_by(Axis.Z)[-1], EDGE_FILLET)
    cavity = prism(W_I, L_I, R_I, 0, H_I)
    window = prism(W_I - 2 * LIP_IN, L_I - 2 * LIP_IN, R_I - LIP_IN, H_I - EPS, Z_TOP + 1)
    case = body - cavity - window

    # button slots (side walls) + v2 relief channels from each slot up past the tongue
    for side, cy, ln in ((+1, PWR_CY, PWR_LEN), (-1, VOL_CY, VOL_LEN)):
        slot = extrude(Plane.YZ * SlotOverall(ln + BTN_SLOT_EXTRA, BTN_SLOT_H), WALL + 2, both=True)
        case -= Pos(side * (W_I / 2 + WALL / 2), cy, PH_T / 2) * slot
        y0, y1 = cy, Y_TONGUE_END + 1
        chan = Box(BTN_RELIEF + 0.5, y1 - y0, BTN_RELIEF_H, align=(Align.CENTER, Align.MIN, Align.CENTER))
        case -= Pos(side * (W_I / 2 + (BTN_RELIEF - 0.5) / 2), y0, PH_T / 2) * chan

    # bottom end: USB-C + two speaker slots
    for x, (w, h) in ((0.0, USB_SLOT), (-SPK_X, SPK_SLOT), (SPK_X, SPK_SLOT)):
        slot = extrude(Plane.XZ * SlotOverall(w, h), WALL + 2, both=True)
        case -= Pos(x, -CLR - WALL / 2, PH_T / 2) * slot

    big = 400
    below = Pos(0, SPLIT - big / 2, 0) * Box(big, big, big)
    above = Pos(0, SPLIT + big / 2, 0) * Box(big, big, big)

    # SHELL: everything below the split + a tongue (walls + floor, skinned, no lip) JOINT mm past it.
    # One intersection with (below + tongue region) keeps the shell a single solid.
    tongue_keep = Box(W_O - 2 * TONGUE_INSET, JOINT + EPS, H_I - (Z_BOT + TONGUE_INSET),
                      align=(Align.CENTER, Align.MAX, Align.MIN))
    tongue_keep = Pos(0, Y_TONGUE_END, Z_BOT + TONGUE_INSET) * tongue_keep
    shell = case & (below + tongue_keep)
    # detent domes on both tongue walls: sphere clipped to the outside of the wall so nothing
    # pokes into the phone cavity; rotated so OCCT's sphere seam stays off the boolean
    face = W_O / 2 - TONGUE_INSET
    for side in (+1, -1):
        sph = Pos(side * (face + DETENT_PROUD - DETENT_R), Y_DETENT, PH_T / 2) * Rot(0, 0, 90) * Sphere(DETENT_R)
        clip = Pos(side * (face + 0.4), Y_DETENT, PH_T / 2) * Box(1.0, 4, 4)
        shell += sph & clip

    # CAP: everything above the split, minus the socket for the tongue, minus the camera notch
    socket = Box(W_O - 2 * TONGUE_INSET + 2 * JCLR, JOINT + 1, H_I + JCLR - (Z_BOT + TONGUE_INSET - JCLR),
                 align=(Align.CENTER, Align.MAX, Align.MIN))
    socket = Pos(0, Y_TONGUE_END + JCLR, Z_BOT + TONGUE_INSET - JCLR) * socket
    cap = (case & above) - socket
    notch = prism(CAM_WIN, CAM_WIN, CAM_R + 0.5, Z_BOT - 1, EPS, x=CAM_CX, y=CAM_CY)
    notch_tail = Box(CAM_WIN, CAM_CY - (SPLIT - 1), FLOOR + 1 + EPS, align=(Align.CENTER, Align.MIN, Align.MIN))
    notch += Pos(CAM_CX, SPLIT - 1, Z_BOT - 1) * notch_tail
    cap -= notch
    for side in (+1, -1):
        cap -= Pos(side * (W_O / 2), Y_DETENT, PH_T / 2) * (Plane.YZ * Cylinder(DETENT_HOLE_D / 2, WALL * 2))
    return shell, cap


def build_phone():
    ph = prism(PH_W, PH_L, PH_R, 0, PH_T)
    ph = fillet(ph.edges().group_by(Axis.Z)[0] + ph.edges().group_by(Axis.Z)[-1], 1.0)
    ph += prism(CAM_W, CAM_W, CAM_R, -CAM_H, EPS, x=CAM_CX, y=CAM_CY)
    for side, cy, ln in ((+1, PWR_CY, PWR_LEN), (-1, VOL_CY, VOL_LEN)):
        ph += Pos(side * (PH_W / 2 + BTN_PROUD / 2 - 0.5), cy, PH_T / 2) * Box(BTN_PROUD + 1, ln, BTN_H)
    port = extrude(Plane.XZ * SlotOverall(USB_W, USB_H), 7, both=True)
    ph -= Pos(0, 0, PH_T / 2) * port
    return ph


def fit_checks(shell, cap, phone):
    """Interference volumes (mm^3). Zero = no collision."""
    c = {
        "phone_vs_shell": (phone & shell).volume,
        "phone_vs_cap": (phone & cap).volume,
        "shell_vs_cap_assembled": (shell & cap).volume,
    }
    # step 1: phone slides down into the shell from above (cap off)
    c["phone_slide_in_max"] = max((Pos(0, dy, 0) * phone & shell).volume for dy in range(5, 156, 5))
    # step 2: cap slides down onto the shell + phone. Only the detent bumps may touch (that's the snap).
    c["cap_slide_vs_phone_max"] = max((Pos(0, dy, 0) * cap & phone).volume for dy in range(2, 51, 2))
    snap = [(Pos(0, dy, 0) * cap & shell).volume for dy in (1, 2, 3, 4, 5)]
    c["cap_slide_snap_interference_max"] = max(snap)
    return {k: round(v, 4) for k, v in c.items()}


def main():
    shell, cap = build_case()
    phone = build_phone()
    for name, part in (("case_shell", shell), ("case_cap", cap), ("demo_phone_dummy", phone)):
        assert part.is_valid and len(part.solids()) == 1, name
        export_stl(part, OUT / f"{name}.stl", tolerance=0.02, angular_tolerance=0.15)
    shell.label, cap.label, phone.label = "Case shell", "Snap cap", "Demo phone"
    export_step(Compound(children=[shell, cap, phone], label="Protective case exemplar"),
                OUT / "protective_case_exemplar.step")

    def bb(p):
        b = p.bounding_box()
        return [round(b.size.X, 2), round(b.size.Y, 2), round(b.size.Z, 2)]

    PLA = 1.24  # g/cm^3
    data = {
        "phone": dict(L=PH_L, W=PH_W, T=PH_T, corner_R=PH_R, camera=[CAM_W, CAM_W, CAM_H],
                      camera_from_top=CAM_Y0, camera_from_side=CAM_X0,
                      power_from_top=PWR_Y, power_len=PWR_LEN, volume_from_top=VOL_Y, volume_len=VOL_LEN,
                      button_proud=BTN_PROUD, usb=[USB_W, USB_H]),
        "case": dict(clearance=CLR, clearance_screen=CLR_T, wall=WALL, floor=FLOOR, lip_t=LIP_T,
                     lip_in=LIP_IN, interior=[W_I, L_I, H_I], interior_R=R_I, outer=[W_O, L_O, Z_TOP - Z_BOT],
                     outer_R=R_O, split_from_phone_bottom=SPLIT, joint=JOINT, tongue_wall=WALL - TONGUE_INSET,
                     joint_clearance=JCLR, socket_wall=round(WALL - TONGUE_INSET - JCLR, 2),
                     detent_proud=DETENT_PROUD, detent_hole_d=DETENT_HOLE_D,
                     lip_above_screen=round(Z_TOP - PH_T, 2), back_proud_of_camera=round(FLOOR - CAM_H, 2),
                     camera_window=CAM_WIN, power_slot=PWR_LEN + BTN_SLOT_EXTRA,
                     volume_slot=VOL_LEN + BTN_SLOT_EXTRA, button_slot_h=BTN_SLOT_H,
                     button_relief=BTN_RELIEF, button_relief_h=BTN_RELIEF_H,
                     usb_slot=list(USB_SLOT), speaker_slot=list(SPK_SLOT), speaker_x=SPK_X),
        "parts": {},
    }
    for name, part in (("shell", shell), ("cap", cap), ("phone", phone)):
        v = part.volume / 1000
        data["parts"][name] = dict(bbox_mm=bb(part), volume_cm3=round(v, 2), solid_pla_g=round(v * PLA, 1))
    data["fit_checks_mm3"] = fc = fit_checks(shell, cap, phone)
    must_be_zero = [k for k in fc if k != "cap_slide_snap_interference_max"]
    assert all(fc[k] == 0 for k in must_be_zero), fc
    assert 0 < fc["cap_slide_snap_interference_max"] < 5, fc   # the detents, and nothing else
    (OUT / "model.json").write_text(json.dumps(data, indent=2))
    print(json.dumps({"parts": data["parts"], "fit_checks_mm3": fc}, indent=2))


if __name__ == "__main__":
    main()
