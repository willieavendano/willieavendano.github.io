"""Fusion API script: rebuild the IED midterm exemplar case natively in Fusion.

Same design as build_case.py (the build123d version), but built the way a
student builds it in Fusion: user parameters (phone size, clearance, wall),
sketches, extrudes, a split body, then two components. Run it from
Utilities > Scripts and Add-Ins in a new, empty design. It also saves the
viewport images used in the exemplar deck and an .f3d archive.

Fusion's internal length unit is cm; every number below is written in mm
and converted with cm().
"""
import math
import os
import adsk.core
import adsk.fusion

OUT = os.environ.get("EXEMPLAR_OUT", os.path.join(os.path.expanduser("~"), "Desktop", "protective-case-exemplar"))
P3 = adsk.core.Point3D.create
VI = adsk.core.ValueInput
FO = adsk.fusion.FeatureOperations


def cm(v):
    return v / 10.0


# ---------------- numbers (mm), identical to build_case.py ----------------
PH_L, PH_W, PH_T, PH_R = 150.0, 72.0, 8.0, 10.0
CAM_W, CAM_R, CAM_H, CAM_X0, CAM_Y0 = 30.0, 6.0, 1.5, 8.0, 8.0
PWR_Y, PWR_LEN, VOL_Y, VOL_LEN = 52.0, 16.0, 50.0, 28.0
BTN_PROUD, BTN_H = 0.5, 3.0
USB_W, USB_H = 9.0, 3.2
CLR, WALL, FLOOR, LIP_T, LIP_IN, FIL = 0.4, 2.0, 2.0, 1.2, 2.0, 1.0
SPLIT, JOINT, TONGUE_INSET, JCLR = 104.0, 6.0, 1.0, 0.2
DETENT_R, DETENT_PROUD, DETENT_HOLE_D = 1.0, 0.4, 2.2
SLOT_H, SLOT_EXTRA, RELIEF, RELIEF_H = 5.0, 2.0, 0.3, 4.0
USB_SLOT, SPK_SLOT, SPK_X = (14.0, 7.0), (12.0, 3.5), 20.0

W_I, L_I, R_I = PH_W + 2 * CLR, PH_L + 2 * CLR, PH_R + CLR
W_O, L_O, R_O = W_I + 2 * WALL, L_I + 2 * WALL, R_I + WALL
H_I = PH_T + CLR
YC = PH_L / 2
CAM_CX, CAM_CY = PH_W / 2 - CAM_X0 - CAM_W / 2, PH_L - CAM_Y0 - CAM_W / 2
CAM_WIN = CAM_W + 1.0
PWR_CY, VOL_CY = PH_L - PWR_Y - PWR_LEN / 2, PH_L - VOL_Y - VOL_LEN / 2
FACE = W_O / 2 - TONGUE_INSET            # outside face of the tongue
Y_TONGUE_END, Y_DETENT = SPLIT + JOINT, SPLIT + JOINT / 2

PARAMS = [
    ("phone_L", PH_L, "Demo Phone length, measured (average of 3)"),
    ("phone_W", PH_W, "Demo Phone width, measured"),
    ("phone_T", PH_T, "Demo Phone thickness, measured"),
    ("phone_R", PH_R, "Demo Phone corner radius"),
    ("clearance", CLR, "gap per side, phone to case"),
    ("wall", WALL, "side and end wall"),
    ("floor_t", FLOOR, "back floor (camera bump is 1.5)"),
    ("lip_t", LIP_T, "lip thickness over the screen"),
    ("lip_in", LIP_IN, "lip overhang onto the screen"),
    ("split_y", SPLIT, "shell / cap split, from the phone's bottom end"),
    ("joint_L", JOINT, "tongue / socket length"),
    ("joint_clr", JCLR, "gap per side, tongue to socket"),
    ("detent_proud", DETENT_PROUD, "snap bump height"),
]


class Builder:
    def __init__(self, app):
        self.app = app
        self.doc = app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
        self.des = adsk.fusion.Design.cast(app.activeProduct)
        self.des.designType = adsk.fusion.DesignTypes.ParametricDesignType
        self.root = self.des.rootComponent
        for name, val, note in PARAMS:
            self.des.userParameters.add(name, VI.createByString(f"{val} mm"), "mm", note)

    # ---- sketch helpers: every point is given in model mm, then mapped into the sketch ----
    @staticmethod
    def sp(sk, x, y, z):
        return sk.modelToSketchSpace(P3(cm(x), cm(y), cm(z)))

    def loop(self, sk, M, segs):
        """Closed loop. M(u, v) -> model (x, y, z). segs: ('L', end) or ('A', mid, end) in (u, v);
        the first entry is ('S', start)."""
        L, A = sk.sketchCurves.sketchLines, sk.sketchCurves.sketchArcs
        P = lambda uv: self.sp(sk, *M(*uv))
        start = P(segs[0][1])
        first = cur = None
        cur_pt = start
        n = len(segs) - 1
        for i, s in enumerate(segs[1:]):
            last = i == n - 1
            a = cur if cur is not None else cur_pt
            if s[0] == "L":
                end = first if last else P(s[1])
                c = L.addByTwoPoints(a, end)
                want = P(s[1])
            else:
                end = first if last else P(s[2])
                c = A.addByThreePoints(a, P(s[1]), end)
                want = P(s[2])
            ends = [c.startSketchPoint, c.endSketchPoint]
            if first is None:
                first = min(ends, key=lambda p: p.geometry.distanceTo(start))
            cur = min(ends, key=lambda p: p.geometry.distanceTo(want))
        return sk

    def rrect(self, sk, M, cu, cv, w, l, r):
        hw, hl, k = w / 2, l / 2, r * (1 - 1 / math.sqrt(2))
        o = lambda u, v: (cu + u, cv + v)
        segs = [("S", o(-hw + r, -hl)), ("L", o(hw - r, -hl)),
                ("A", o(hw - k, -hl + k), o(hw, -hl + r)), ("L", o(hw, hl - r)),
                ("A", o(hw - k, hl - k), o(hw - r, hl)), ("L", o(-hw + r, hl)),
                ("A", o(-hw + k, hl - k), o(-hw, hl - r)), ("L", o(-hw, -hl + r)),
                ("A", o(-hw + k, -hl + k), o(-hw + r, -hl))]
        return self.loop(sk, M, segs)

    def slot(self, sk, M, cu, cv, w, h):
        r, hw = h / 2, w / 2
        o = lambda u, v: (cu + u, cv + v)
        segs = [("S", o(-hw + r, -r)), ("L", o(hw - r, -r)), ("A", o(hw, 0), o(hw - r, r)),
                ("L", o(-hw + r, r)), ("A", o(-hw, 0), o(-hw + r, -r))]
        return self.loop(sk, M, segs)

    def poly(self, sk, M, pts):
        return self.loop(sk, M, [("S", pts[0])] + [("L", p) for p in pts[1:]] + [("L", pts[0])])

    # ---- feature helpers ----
    @staticmethod
    def val(v):
        return VI.createByString(v) if isinstance(v, str) else VI.createByReal(cm(v))

    def extrude(self, comp, sk, dist, op, start=0.0, bodies=None, name=None, both=None):
        profs = adsk.core.ObjectCollection.create()
        for p in sk.profiles:
            profs.add(p)
        ext = comp.features.extrudeFeatures
        inp = ext.createInput(profs, op)
        if start:
            inp.startExtent = adsk.fusion.OffsetStartDefinition.create(self.val(start))
        if both:
            inp.setTwoSidesExtent(adsk.fusion.DistanceExtentDefinition.create(self.val(both)),
                                  adsk.fusion.DistanceExtentDefinition.create(self.val(both)))
        else:
            neg = (not isinstance(dist, str)) and dist < 0
            d = abs(dist) if not isinstance(dist, str) else dist
            inp.setOneSideExtent(adsk.fusion.DistanceExtentDefinition.create(self.val(d)),
                                 adsk.fusion.ExtentDirections.NegativeExtentDirection if neg
                                 else adsk.fusion.ExtentDirections.PositiveExtentDirection)
        if bodies:
            inp.participantBodies = bodies
        f = ext.add(inp)
        if name:
            f.name = name
        return f

    def sketch(self, comp, plane, name):
        sk = comp.sketches.add(plane)
        sk.name = name
        sk.isComputeDeferred = True
        return sk

    def done(self, sk):
        sk.isComputeDeferred = False
        return sk

    def offset_plane(self, comp, base, mm_or_expr, name):
        inp = comp.constructionPlanes.createInput()
        inp.setByOffset(base, self.val(mm_or_expr))
        pl = comp.constructionPlanes.add(inp)
        pl.name = name
        return pl

    def fillet_flat_edges(self, comp, body, r, name):
        edges = adsk.core.ObjectCollection.create()
        zs = [f.pointOnFace.z for f in body.faces]
        zmin, zmax = min(zs), max(zs)
        for f in body.faces:
            g = f.geometry
            if isinstance(g, adsk.core.Plane) and abs(abs(g.normal.z) - 1) < 1e-6 and \
                    (abs(f.pointOnFace.z - zmin) < 1e-6 or abs(f.pointOnFace.z - zmax) < 1e-6):
                for e in f.edges:
                    edges.add(e)
        fi = comp.features.filletFeatures.createInput()
        fi.addConstantRadiusEdgeSet(edges, self.val(r), True)
        f = comp.features.filletFeatures.add(fi)
        f.name = name

    def new_comp(self, name):
        occ = self.root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
        occ.component.name = name
        return occ

    # ---- the model ----
    def build(self):
        XY = lambda u, v: (u, v, 0.0)
        XZ = lambda u, v: (u, 0.0, v)          # u = x, v = z  (plane normal +Y)
        YZ = lambda u, v: (0.0, u, v)          # u = y, v = z  (plane normal +X)
        nb = FO.NewBodyFeatureOperation
        join, cut = FO.JoinFeatureOperation, FO.CutFeatureOperation

        # ---------- Demo Phone ----------
        ph_occ = self.new_comp("Demo Phone")
        ph = ph_occ.component
        sk = self.sketch(ph, ph.xYConstructionPlane, "Phone outline")
        self.done(self.rrect(sk, XY, 0, YC, PH_W, PH_L, PH_R))
        f = self.extrude(ph, sk, "phone_T", nb, name="Phone body")
        phone = f.bodies.item(0)
        phone.name = "Demo Phone"
        self.fillet_flat_edges(ph, phone, 1.0, "Phone edge round")
        sk = self.sketch(ph, ph.xYConstructionPlane, "Camera bump")
        self.done(self.rrect(sk, XY, CAM_CX, CAM_CY, CAM_W, CAM_W, CAM_R))
        self.extrude(ph, sk, -CAM_H, join, bodies=[phone], name="Camera bump")
        sk = self.sketch(ph, ph.xYConstructionPlane, "Buttons")
        x_in = PH_W / 2 + BTN_PROUD / 2 - 0.5 - (BTN_PROUD + 1) / 2
        x_out = x_in + BTN_PROUD + 1
        self.poly(sk, XY, [(x_in, PWR_CY - 8), (x_out, PWR_CY - 8), (x_out, PWR_CY + 8), (x_in, PWR_CY + 8)])
        self.poly(sk, XY, [(-x_out, VOL_CY - 14), (-x_in, VOL_CY - 14), (-x_in, VOL_CY + 14), (-x_out, VOL_CY + 14)])
        self.done(sk)
        self.extrude(ph, sk, BTN_H, join, start=PH_T / 2 - BTN_H / 2, bodies=[phone], name="Buttons")
        sk = self.sketch(ph, ph.xZConstructionPlane, "USB-C port")
        self.done(self.slot(sk, XZ, 0, PH_T / 2, USB_W, USB_H))
        self.extrude(ph, sk, 7.0, cut, start=-1.0, bodies=[phone], name="USB-C port")

        # ---------- Case (one body, then split) ----------
        cs_occ = self.new_comp("Case")
        cs = cs_occ.component
        sk = self.sketch(cs, cs.xYConstructionPlane, "Outer profile")
        self.done(self.rrect(sk, XY, 0, YC, W_O, L_O, R_O))
        f = self.extrude(cs, sk, "floor_t + phone_T + clearance + lip_t", nb, start="-floor_t", name="Case blank")
        case = f.bodies.item(0)
        case.name = "Case"
        self.fillet_flat_edges(cs, case, FIL, "Outer edge round")

        sk = self.sketch(cs, cs.xYConstructionPlane, "Phone pocket = phone + clearance")
        self.done(self.rrect(sk, XY, 0, YC, W_I, L_I, R_I))
        self.dimension_pocket(sk)
        self.extrude(cs, sk, "phone_T + clearance", cut, bodies=[case], name="Phone pocket")

        sk = self.sketch(cs, cs.xYConstructionPlane, "Screen window")
        self.done(self.rrect(sk, XY, 0, YC, W_I - 2 * LIP_IN, L_I - 2 * LIP_IN, R_I - LIP_IN))
        self.extrude(cs, sk, 3.0, cut, start="phone_T + clearance", bodies=[case], name="Screen window (lip)")

        for side, cy, ln, nm in ((+1, PWR_CY, PWR_LEN, "Power"), (-1, VOL_CY, VOL_LEN, "Volume")):
            sk = self.sketch(cs, cs.yZConstructionPlane, f"{nm} button slot")
            self.done(self.slot(sk, YZ, cy, PH_T / 2, ln + SLOT_EXTRA, SLOT_H))
            self.extrude(cs, sk, side * 3.0, cut, start=side * (W_I / 2 - 0.5), bodies=[case],
                         name=f"{nm} button slot")

        sk = self.sketch(cs, cs.xZConstructionPlane, "USB-C and speaker openings")
        for x, (w, h) in ((0.0, USB_SLOT), (-SPK_X, SPK_SLOT), (SPK_X, SPK_SLOT)):
            self.slot(sk, XZ, x, PH_T / 2, w, h)
        self.done(sk)
        self.extrude(cs, sk, 3.4, cut, start=-(CLR + WALL + 1.0), bodies=[case], name="USB-C and speaker openings")

        split_pl = self.offset_plane(cs, cs.xZConstructionPlane, "split_y", "Split plane")
        si = cs.features.splitBodyFeatures.createInput(case, split_pl, True)
        sf = cs.features.splitBodyFeatures.add(si)
        sf.name = "Split into shell + cap"
        bodies = sorted([b for b in cs.bRepBodies], key=lambda b: b.boundingBox.minPoint.y)
        shell, cap = bodies[0], bodies[1]
        shell.name, cap.name = "Shell", "Snap cap"

        sk = self.sketch(cs, split_pl, "Tongue")
        t_out, t_in, zb = FACE, W_I / 2, -FLOOR + TONGUE_INSET
        XZs = lambda u, v: (u, SPLIT, v)
        self.done(self.poly(sk, XZs, [(-t_out, zb), (t_out, zb), (t_out, H_I), (t_in, H_I), (t_in, 0),
                                      (-t_in, 0), (-t_in, H_I), (-t_out, H_I)]))
        # the split plane's normal is +Y in model space, but check: sketch on an offset plane keeps it
        self.extrude(cs, sk, "joint_L", join, bodies=[shell], name="Tongue")

        for side, cy, nm in ((+1, PWR_CY, "Power"), (-1, VOL_CY, "Volume")):
            sk = self.sketch(cs, cs.yZConstructionPlane, f"{nm} button relief (v2)")
            self.done(self.poly(sk, YZ, [(cy, PH_T / 2 - RELIEF_H / 2), (Y_TONGUE_END + 1, PH_T / 2 - RELIEF_H / 2),
                                         (Y_TONGUE_END + 1, PH_T / 2 + RELIEF_H / 2), (cy, PH_T / 2 + RELIEF_H / 2)]))
            self.extrude(cs, sk, side * (RELIEF + 0.5), cut, start=side * (W_I / 2 - 0.5), bodies=[shell],
                         name=f"{nm} button relief (v2)")

        sk = self.sketch(cs, split_pl, "Socket = tongue + joint clearance")
        so, zb2 = FACE + JCLR, -FLOOR + TONGUE_INSET - JCLR
        self.done(self.poly(sk, XZs, [(-so, zb2), (so, zb2), (so, H_I + JCLR), (-so, H_I + JCLR)]))
        self.extrude(cs, sk, "joint_L + joint_clr", cut, bodies=[cap], name="Socket")

        det_pl = self.offset_plane(cs, cs.xYConstructionPlane, PH_T / 2, "Detent plane")
        XYd = lambda u, v: (u, v, PH_T / 2)
        chord = FACE - 0.05
        ctr = FACE + DETENT_PROUD - DETENT_R
        dx = chord - ctr
        hc = math.sqrt(DETENT_R ** 2 - dx ** 2)
        a_end = math.atan2(hc, dx)
        for side in (+1, -1):
            sk = self.sketch(cs, det_pl, "Snap detent " + ("right" if side > 0 else "left"))
            mid = (side * (ctr + DETENT_R * math.cos(a_end / 2)), Y_DETENT + DETENT_R * math.sin(a_end / 2))
            pts = [(side * chord, Y_DETENT), (side * (ctr + DETENT_R), Y_DETENT)]
            segs = [("S", pts[0]), ("L", pts[1]), ("A", mid, (side * chord, Y_DETENT + hc)), ("L", pts[0])]
            self.done(self.loop(sk, XYd, segs))
            axis = sk.sketchCurves.sketchLines.item(0)
            rv = cs.features.revolveFeatures
            ri = rv.createInput(sk.profiles.item(0), axis, join)
            ri.setAngleExtent(False, VI.createByString("360 deg"))
            ri.participantBodies = [shell]
            rv.add(ri).name = "Snap detent " + ("right" if side > 0 else "left")

        sk = self.sketch(cs, cs.yZConstructionPlane, "Detent holes")
        c = sk.sketchCurves.sketchCircles.addByCenterRadius(self.sp(sk, *YZ(Y_DETENT, PH_T / 2)), cm(DETENT_HOLE_D / 2))
        self.done(sk)
        self.extrude(cs, sk, None, cut, both=W_O, bodies=[cap], name="Detent holes")

        sk = self.sketch(cs, cs.xYConstructionPlane, "Camera notch (v2)")
        h, r = CAM_WIN / 2, CAM_R + 0.5
        k = r * (1 - 1 / math.sqrt(2))
        top = CAM_CY + h
        o = lambda u, v: (CAM_CX + u, v)
        self.done(self.loop(sk, XY, [("S", o(-h, SPLIT - 1)), ("L", o(h, SPLIT - 1)), ("L", o(h, top - r)),
                                     ("A", o(h - k, top - k), o(h - r, top)), ("L", o(-h + r, top)),
                                     ("A", o(-h + k, top - k), o(-h, top - r)), ("L", o(-h, SPLIT - 1))]))
        self.extrude(cs, sk, -(FLOOR + 1), cut, bodies=[cap], name="Camera notch (v2)")

        # one component per part, like a student's assembly
        try:
            for body, comp_name, body_name in ((shell, "Case Shell", "Shell"), (cap, "Snap Cap", "Snap cap")):
                moved = body.createComponent()
                moved.parentComponent.name = comp_name
                moved.name = body_name
        except Exception:
            pass
        self.phone_occ = ph_occ
        return phone

    def dimension_pocket(self, sk):
        """Tie the pocket sketch to the parameters: width and length = phone + 2 x clearance."""
        try:
            lines = sk.sketchCurves.sketchLines
            vert = [l for l in lines if abs(l.geometry.startPoint.x - l.geometry.endPoint.x) < 1e-9]
            horiz = [l for l in lines if abs(l.geometry.startPoint.y - l.geometry.endPoint.y) < 1e-9]
            dims = sk.sketchDimensions
            d1 = dims.addOffsetDimension(vert[0], vert[1], self.sp(sk, 0, YC + 20, 0))
            d1.parameter.expression = "phone_W + 2 * clearance"
            d2 = dims.addOffsetDimension(horiz[0], horiz[1], self.sp(sk, 20, YC, 0))
            d2.parameter.expression = "phone_L + 2 * clearance"
        except Exception:
            pass


def all_bodies(root):
    out = {}
    for occ in root.allOccurrences:
        for b in occ.bRepBodies:
            out[b.name] = b
    return out


def appearance(des, app, base, name, rgb):
    lib = app.materialLibraries.itemByName("Fusion Appearance Library")
    a = des.appearances.itemByName(name)
    if a is None:
        a = des.appearances.addByCopy(lib.appearances.itemByName(base), name)
        for p in a.appearanceProperties:
            if isinstance(p, adsk.core.ColorProperty) and p.value is not None:
                try:
                    p.value = adsk.core.Color.create(*rgb, 255)
                except Exception:
                    pass
    return a


def shoot(app, vp, path, eye, target, up, w=1600, h=1000):
    cam = vp.camera
    cam.isSmoothTransition = False
    cam.cameraType = adsk.core.CameraTypes.OrthographicCameraType
    cam.eye, cam.target, cam.upVector = P3(*eye), P3(*target), adsk.core.Vector3D.create(*up)
    vp.camera = cam
    vp.fit()
    vp.refresh()
    return vp.saveAsImageFile(path, w, h)


def run_all(app, log=print):
    os.makedirs(OUT, exist_ok=True)
    b = Builder(app)
    b.build()
    des, root = b.des, b.root
    bodies = all_bodies(root)
    log("bodies", {k: round(v.physicalProperties.volume, 3) for k, v in bodies.items()})
    log("timeline", des.timeline.count, "features")
    for nm, base, rgb in (("Shell", "Plastic - Matte (Blue)", (0, 113, 206)),
                          ("Snap cap", "Plastic - Matte (Yellow)", (224, 123, 0)),
                          ("Demo Phone", "Plastic - Glossy (Black)", (40, 40, 44))):
        if nm in bodies:
            try:
                bodies[nm].appearance = appearance(des, app, base, "IED " + nm, rgb)
            except Exception as e:
                log("appearance", nm, e)

    vp = app.activeViewport
    try:
        vp.visualStyle = adsk.core.VisualStyles.ShadedWithVisibleEdgesOnlyVisualStyle
    except Exception:
        pass
    occs = {o.component.name: o for o in root.allOccurrences}
    c = (0, cm(YC), 0)
    iso = (cm(260), cm(-120), cm(260))
    shots = []

    def vis(**kw):
        for n, o in occs.items():
            o.isLightBulbOn = kw.get(n, True)

    vis()
    shots.append(("fusion_assembly.png", shoot(app, vp, os.path.join(OUT, "img", "fusion_assembly.png"), iso, c, (0, 0, 1))))
    shots.append(("fusion_back.png", shoot(app, vp, os.path.join(OUT, "img", "fusion_back.png"),
                                           (cm(200), cm(-80), cm(-260)), c, (0, 0, 1))))
    vis(**{"Demo Phone": False})
    shots.append(("fusion_case_only.png", shoot(app, vp, os.path.join(OUT, "img", "fusion_case_only.png"), iso, c, (0, 0, 1))))
    vis(**{"Demo Phone": False, "Snap Cap": False})
    shots.append(("fusion_shell.png", shoot(app, vp, os.path.join(OUT, "img", "fusion_shell.png"),
                                            (cm(220), cm(330), cm(200)), (0, cm(90), 0), (0, 0, 1))))
    vis(**{"Demo Phone": False, "Case Shell": False})
    shots.append(("fusion_cap.png", shoot(app, vp, os.path.join(OUT, "img", "fusion_cap.png"),
                                          (cm(200), cm(-160), cm(-200)), (0, cm(127), 0), (0, 0, 1))))
    vis()
    vp.camera.viewOrientation = adsk.core.ViewOrientations.IsoTopRightViewOrientation
    log("shots", shots)

    em = des.exportManager
    f3d = os.path.join(OUT, "protective_case_exemplar.f3d")
    em.execute(em.createFusionArchiveExportOptions(f3d, root))
    log("f3d", os.path.exists(f3d), os.path.getsize(f3d) if os.path.exists(f3d) else 0)
    return b


def run(context):
    app = adsk.core.Application.get()
    try:
        run_all(app)
    except Exception:
        import traceback
        app.userInterface.messageBox(traceback.format_exc())
