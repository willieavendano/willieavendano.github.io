"""Parametric prototype. Requires cadquery and trimesh. Units: mm.
Run from any directory: python build_model.py
Hardware envelopes are layout references, not manufacturer CAD.
"""
from pathlib import Path
import math, json
import cadquery as cq
import trimesh
ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'stl'
OUT.mkdir(exist_ok=True)
AXLE_X = 50.8
AXLE_Z = 54
CRANK_RADIUS = 12
SHAFT_SQUARE = 3.40
PIVOT_D = 3.4
BRAIN = (139.7, 101.6, 33.02)

def box(x,y,z,at):
    return cq.Workplane('XY').box(x,y,z).translate(at)
def cyl_y(r,length,at):
    return cq.Workplane('XZ').circle(r).extrude(length/2,both=True).translate(at)
def hole_z(d,h,at):
    return cq.Workplane('XY').circle(d/2).extrude(h/2,both=True).translate(at)

parts={}
# Deck, open corner cage, straps beside screen; 2 mm foam clearance.
deck=box(180,160,6,(0,0,93))
for sx in [-1,1]:
    for sy in [-1,1]:
        deck=deck.union(box(3,15,12,(sx*73.5,sy*47,102)))
        deck=deck.union(box(15,3,12,(sx*67.5,sy*55.5,102)))
        deck=deck.cut(hole_z(3.4,12,(sx*70,sy*67,93)))
        deck=deck.cut(box(18,4,12,(sx*60,sy*62,93)))
# Battery strap slots; battery held below deck on right half.
for y in [-55,55]:
    for x in [13,70]:
        deck=deck.cut(box(4,18,12,(x,y,93)))
# Cooling grid under Brain; avoid the perimeter and fasteners.
for x in [-40,-20,0,20,40]:
    deck=deck.cut(box(8,64,12,(x,0,93)))
parts['brain_deck']=deck

# Side walls, both identical (mirror for assembly), integral bolt flanges.
side=box(180,6,66,(0,-79,57))
side=side.union(box(180,18,6,(0,-70,87)))
side=side.union(box(180,18,6,(0,-70,27)))
for x in [-AXLE_X,AXLE_X]:
    side=side.union(cyl_y(9,10,(x,-77,AXLE_Z)))
    side=side.cut(cyl_y(2.5,20,(x,-77,AXLE_Z)))
for x in [-70,70]:
    side=side.cut(hole_z(3.4,15,(x,-67,87)))
for x in [-70,-25]:
    side=side.cut(hole_z(3.4,15,(x,-67,27)))
for x in [-27,27]:
    side=side.cut(box(19,20,30,(x,-79,60)))
# Slot for a separately supplied chain tensioner.
side=side.cut(box(3.4,20,22,(0,-79,65)))
parts['side_wall_left']=side
parts['side_wall_right']=side.mirror('XZ')

# Motor sled: straps clamp housing; shims set shaft axis at 54 mm.
sled=box(86,140,4,(-47,0,32))
for x in [-70,-25]:
    for y in [-67,67]:
        sled=sled.cut(hole_z(3.4,10,(x,y,32)))
for x in [-77,-17]:
    for y in [-30,30]:
        sled=sled.cut(box(4,30,10,(x,y,32)))
# Flexible positioning of screw/strap adapters.
for x in [-60,-40]:
    sled=sled.cut(box(4,75,10,(x,0,32)))
parts['motor_sled']=sled

# Flat crank arm, assembled along Y. Four copies, opposed left/right.
crank=cyl_y(9,8,(0,0,0)).union(cyl_y(6,8,(12,0,0)))
crank=crank.union(box(12,8,12,(6,0,0)))
crank=crank.cut(box(SHAFT_SQUARE,14,SHAFT_SQUARE,(0,0,0)))
crank=crank.cut(cyl_y(PIVOT_D/2,14,(12,0,0)))
# M3 grub-screw pilot, tap gently after printing; retains crank axially.
crank=crank.cut(hole_z(2.6,12,(0,0,7)))
parts['crank_x4']=crank

# Interleaved foot combs. Only these bars touch the ground.
def foot(sign, xs):
    f=box(180,8,62,(0,sign*97,37))
    for x in xs:
        f=f.union(box(8,180,6,(x,sign*7,3)))
        # Reinforced root overlapping rail and the bar.
        f=f.union(box(14,18,8,(x,sign*92,7)))
    for x in [-AXLE_X,AXLE_X]:
        f=f.cut(cyl_y(PIVOT_D/2,20,(x,sign*97,AXLE_Z)))
    return f
parts['foot_left']=foot(-1,[-72,0,72])
parts['foot_right']=foot(1,[-36,36])
# Captive spacing washers between arms and feet (M3 hardware).
parts['pivot_spacer_x4']=cq.Workplane('XY').circle(3.5).circle(1.7).extrude(2)
for h in [1,2,4]:
    shim=box(70,50,h,(0,0,h/2))
    for x in [-20,20]: shim=shim.cut(box(4,36,h+2,(x,0,h/2)))
    parts[f'motor_shim_{h}mm']=shim
coupon=box(72,24,5,(0,0,2.5))
for x,s in [(-24,3.3),(-8,3.4),(8,3.5)]:
    coupon=coupon.cut(box(s,s,10,(x,0,2.5)))
coupon=coupon.cut(hole_z(5,10,(24,0,2.5)))
parts['fit_coupon']=coupon

# Assembly retains actual part placement; STL exports are oriented on bed.
assembly=cq.Assembly(name='Silly_Walks_prototype')
assembly.add(deck,name='brain_deck',color=cq.Color(0.13,0.24,0.34))
assembly.add(side,name='left_wall',color=cq.Color(0.16,0.34,0.44))
assembly.add(side.mirror('XZ'),name='right_wall',color=cq.Color(0.16,0.34,0.44))
assembly.add(sled,name='motor_sled',color=cq.Color(0.4,0.45,0.5))
assembly.add(parts['foot_left'].translate((12,0,0)),name='left_foot',color=cq.Color(1,0.49,0.12))
assembly.add(parts['foot_right'].translate((-12,0,0)),name='right_foot',color=cq.Color(0.2,0.75,0.62))
for sign in [-1,1]:
    for x in [-AXLE_X,AXLE_X]:
        arm=crank if sign==-1 else crank.rotate((0,0,0),(0,1,0),180)
        assembly.add(arm.translate((x,sign*87,AXLE_Z)),name=f'crank_{sign}_{x}',color=cq.Color(0.9,0.7,0.2))

for x in [-AXLE_X,AXLE_X]:
    assembly.add(box(3.175,180,3.175,(x,0,AXLE_Z)),name=f'steel_shaft_{x}',color=cq.Color(0.65,0.68,0.7))
for x in [-AXLE_X,AXLE_X]:
    assembly.add(cyl_y(14,6,(x,-60,AXLE_Z)),name=f'REF_sprocket_{x}',color=cq.Color(0.55,0.55,0.58))
for dz in [-14,14]:
    assembly.add(box(101.6,5,2,(0,-60,AXLE_Z+dz)),name=f'REF_chain_span_{dz}',color=cq.Color(0.3,0.3,0.32))
# Separate simplified envelopes: omit them from printable STLs.
assembly.add(box(*BRAIN,(0,0,98+BRAIN[2]/2)),name='REF_brain_envelope',color=cq.Color(0.65,0.66,0.68,0.5))
assembly.add(box(105,72,0.8,(0,0,131.42)),name='REF_screen',color=cq.Color(0.06,0.12,0.16))
assembly.add(box(76,65,48,(-48,0,58)),name='REF_motor_MEASURE',color=cq.Color(0.75,0.25,0.2,0.4))
assembly.add(box(45,145,30,(43,0,74)),name='REF_battery_MEASURE',color=cq.Color(0.3,0.3,0.32,0.4))
assembly.save(str(ROOT/'walker_assembly.step'))
report=[]
mesh_data=[]
for name,part in parts.items():
    # Face-down side parts and arms. Feet print bars down; upright rails need support at bores only.
    p=part
    if name in ['side_wall_left','crank_x4']:
        p=p.rotate((0,0,0),(1,0,0),90)
    if name=='side_wall_right':
        p=p.rotate((0,0,0),(1,0,0),-90)
    bb=p.val().BoundingBox()
    p=p.translate((-bb.xmin,-bb.ymin,-bb.zmin))
    path=OUT/(name+'.stl')
    cq.exporters.export(p,str(path),tolerance=0.08,angularTolerance=0.12)
    mesh=trimesh.load_mesh(path)
    assert mesh.is_watertight, name
    assert part.val().isValid(), name
    assert len(part.solids().vals()) == 1, name
    assert all(v<250 for v in mesh.extents), name
    report.append(dict(part=name,mm=[round(float(v),2) for v in mesh.extents],watertight=bool(mesh.is_watertight),solids=1))
# Export tessellated assembly meshes for the self-contained viewer.
for name,obj in assembly.objects.items():
    if obj.obj is None: continue
    shape=obj.obj.val() if hasattr(obj.obj,'val') else obj.obj
    verts,tris=shape.tessellate(0.7)
    col=obj.color.toTuple()[:3] if obj.color else (0.5,0.5,0.5)
    mesh_data.append(dict(name=name,color=[round(c*255) for c in col],v=[[round(v.x,2),round(v.y,2),round(v.z,2)] for v in verts],f=[list(t) for t in tris]))
(ROOT/'mesh_data.json').write_text(json.dumps(mesh_data,separators=(',',':')))
(ROOT/'validation.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))

# Sample nominal moving-part clearances over a full revolution.
fixed=deck.union(side).union(side.mirror('XZ')).union(sled)
collisions=[]
for deg in range(0,360,15):
    a=math.radians(deg)
    dx,dz=CRANK_RADIUS*math.cos(a),CRANK_RADIUS*math.sin(a)
    lf=parts['foot_left'].translate((dx,0,dz))
    rf=parts['foot_right'].translate((-dx,0,-dz))
    for label,a,b in [('feet',lf,rf),('left_vs_frame',lf,fixed),('right_vs_frame',rf,fixed)]:
        vol=a.intersect(b).val().Volume()
        if vol>0.001: collisions.append([deg,label,vol])
(ROOT/'motion_check.json').write_text(json.dumps(dict(sample_interval_degrees=15,collisions=collisions,scope='Printed feet against each other and printed frame only. Excludes hardware, load, friction and tolerances.'),indent=2))
assert not collisions, collisions
print('Nominal foot/frame motion check passed at 24 angles.')
