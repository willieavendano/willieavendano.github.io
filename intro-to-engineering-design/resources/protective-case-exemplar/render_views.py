"""Render the exemplar's CAD views with Blender (Workbench engine, transparent background).

Run:  blender -b -P render_views.py
Reads the STLs written by build_case.py, writes PNGs to ./img/.
"""
import math
from pathlib import Path

import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
IMG = HERE / "img"
IMG.mkdir(exist_ok=True)

COLORS = {
    "case_shell": (0.00, 0.44, 0.81, 1),        # partner A: blue
    "case_cap": (0.95, 0.55, 0.16, 1),          # partner B: orange
    "demo_phone_dummy": (0.17, 0.18, 0.20, 1),  # graphite
}


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_WORKBENCH"
    sc.render.film_transparent = True
    sh = sc.display.shading
    sh.light = "STUDIO"
    sh.color_type = "OBJECT"
    sh.show_cavity = True
    sh.cavity_type = "BOTH"
    sh.show_object_outline = True
    sh.object_outline_color = (0.08, 0.08, 0.08)
    sh.show_specular_highlight = True
    sc.display.render_aa = "16"
    return sc


def load(name, offset=(0, 0, 0)):
    bpy.ops.wm.stl_import(filepath=str(HERE / f"{name}.stl"))
    ob = bpy.context.selected_objects[0]
    ob.name = name
    ob.location = Vector(offset)
    ob.color = COLORS[name]
    return ob


def camera(sc, direction, up, res, margin=1.08):
    """Orthographic look-at camera along -direction, auto-framed to every mesh in the scene."""
    from mathutils import Matrix
    sc.render.resolution_x, sc.render.resolution_y = res
    d = Vector(direction).normalized()
    f = -d
    r = f.cross(Vector(up)).normalized()
    u = r.cross(f).normalized()
    rot = Matrix((r, u, d)).transposed()          # columns: camera x, y, z(back)
    pts = [ob.matrix_world @ v.co for ob in sc.objects if ob.type == "MESH" for v in ob.data.vertices]
    xs = [p.dot(r) for p in pts]; ys = [p.dot(u) for p in pts]; zs = [p.dot(d) for p in pts]
    cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    w, h = max(xs) - min(xs), max(ys) - min(ys)
    aspect = res[0] / res[1]
    cam_data = bpy.data.cameras.new("cam")
    cam_data.type = "ORTHO"
    cam_data.ortho_scale = max(w, h * aspect) * margin if aspect >= 1 else max(w / aspect, h) * margin * aspect
    cam_data.sensor_fit = "AUTO"
    cam_data.clip_end = 5000
    cam = bpy.data.objects.new("cam", cam_data)
    sc.collection.objects.link(cam)
    cam.matrix_world = Matrix.Translation(r * cx + u * cy + d * (max(zs) + 500)) @ rot.to_4x4()
    sc.camera = cam


def shot(fname, parts, direction, up=(0, 1, 0), res=(1600, 1000)):
    sc = reset()
    for name, off in parts:
        load(name, off)
    bpy.context.view_layer.update()
    camera(sc, direction, up, res)
    sc.render.filepath = str(IMG / fname)
    bpy.ops.render.render(write_still=True)


ALL = [("case_shell", (0, 0, 0)), ("case_cap", (0, 0, 0)), ("demo_phone_dummy", (0, 0, 0))]
CASE = [("case_shell", (0, 0, 0)), ("case_cap", (0, 0, 0))]
FRONT = (0.45, -0.35, 1.0)    # screen side, slight three-quarter
BACK = (-0.45, -0.35, -1.0)   # back side
LAND = (1, 0, 0)              # "up" in the image = phone's +x  -> phone lies landscape

shot("assembly_front.png", ALL, FRONT, LAND)
shot("assembly_back.png", ALL, BACK, (-1, 0, 0))
shot("case_only_front.png", CASE, FRONT, LAND)
shot("exploded.png", [("case_shell", (0, 0, 0)), ("case_cap", (0, 60, 0)),
                      ("demo_phone_dummy", (0, 0, 28))], (0.5, -0.45, 0.9), LAND)
shot("shell.png", [("case_shell", (0, 0, 0))], (0.55, -0.6, 1.0), LAND, res=(1400, 1000))
shot("cap.png", [("case_cap", (0, 0, 0))], (0.6, -0.8, 1.0), (0, 1, 0), res=(1200, 1000))
shot("cap_back.png", [("case_cap", (0, 0, 0))], (-0.5, -0.8, -1.0), (0, 1, 0), res=(1200, 1000))
shot("phone.png", [("demo_phone_dummy", (0, 0, 0))], BACK, (-1, 0, 0))
