#!/usr/bin/env python3
"""Parametric concept CAD for the Axiom modular 2WD rover (all units mm)."""
from __future__ import annotations
import argparse, json, hashlib
from pathlib import Path
from itertools import combinations
import cadquery as cq
from cadquery import exporters

P={"base_w":200.,"base_l":260.,"base_t":4.,"ground_z":-15.,"axle_y":-50.,"axle_z":17.5,"wheel_x":110.,"wheel_d":65.,"caster_nominal_h":15.,"pcb_w":120.,"pcb_l":80.,"pcb_z":18.,"pcb_t":1.6,"pcb_component_h":18.,"idc_bend_h":22.,"tray_w":200.,"tray_l":160.,"tray_z":80.,"pi_x":-50.,"pi_z":89.,"pi_standoff_h":6.,"mount_x":85.,"mount_y":65.}

def rounded_plate(w,l,t,r=10):
    s=cq.Workplane("XY").box(w-2*r,l,t,centered=(True,True,False)).union(cq.Workplane("XY").box(w,l-2*r,t,centered=(True,True,False)))
    for x in (-w/2+r,w/2-r):
        for y in (-l/2+r,l/2-r): s=s.union(cq.Workplane("XY").center(x,y).circle(r).extrude(t))
    return s

def slot_xy(x,y,length,width,angle=90,z=20): return cq.Workplane("XY").center(x,y).slot2D(length,width,angle).extrude(z)
def drill(s,holes,d,z=30):
    for x,y in holes: s=s.cut(cq.Workplane("XY").center(x,y).circle(d/2).extrude(z))
    return s

def base():
    s=rounded_plate(P["base_w"],P["base_l"],P["base_t"],12)
    # PCB carrier bosses: holes are drilled through the final fused base below.
    for x in (-55,55):
        for y in (-35,35):
            s=s.union(cq.Workplane("XY").center(x,y).circle(4.5).extrude(P["pcb_z"]))
    s=drill(s,[(x,y) for x in (-85,85) for y in (-65,65)],3.4)
    # M3 interfaces for the unmeasured TT strap brackets, caster fixture, sensor and shell lugs.
    for side in (-1,1):
        for y in (-48,-22): s=s.cut(slot_xy(side*94,y,18,4,90))
    for x in (-20,20): s=s.cut(slot_xy(x,20,18,4,90))
    s=drill(s,[(x,y) for x in (-28,28) for y in (55,75)],3.4) # Shrike/L298 plate
    s=drill(s,[(-28,116),(28,116)]+[(x,y) for x in (-80,80) for y in (-110,110)],3.4)
    for x in (-48,48):
        for y in (-112,-88): s=s.cut(slot_xy(x,y,14,4,0)) # 90x50 motor pack strap slots
        for y in (88,102): s=s.cut(slot_xy(x,y,14,4,0)) # 90x25 base-5V pack strap slots
    for x in (-78,78): s=s.union(cq.Workplane("XY").center(x,0).box(4,190,7,centered=(True,True,False)).translate((0,0,-3)))
    # M3 clearance through carrier bosses and deck: M3x25 + washer/nut from underside.
    s=drill(s,[(x,y) for x in (-55,55) for y in (-35,35)],3.4,30)
    return s.combine()

def motor_bracket(side=1):
    """TT envelope bracket: adjustable slots, intentionally no claimed motor-hole fit."""
    x=side*94; wall_x=side*98
    s=cq.Workplane("XY").center(x,-35).box(12,40,4,centered=(True,True,False)).translate((0,0,4)).union(cq.Workplane("XY").center(wall_x,P["axle_y"]).box(4,48,42,centered=(True,True,False)).translate((0,0,4)))
    for y in (-48,-22): s=s.cut(slot_xy(x,y,18,4,90))
    # Through-wall strap slots (YZ plane) retain whatever purchased TT body proves to be.
    for z in (18,35): s=s.cut(cq.Workplane("YZ").center(P["axle_y"],z).slot2D(18,4,0).extrude(12,both=True).translate((wall_x,0,0)))
    return s.combine() # 4 mm wall: print/test strength gate before any purchased motor is fitted.

def compute_tray():
    s=rounded_plate(P["tray_w"],P["tray_l"],3,9).translate((0,0,P["tray_z"]))
    s=drill(s,[(x,y) for x in (-85,85) for y in (-65,65)],3.4,110)
    # Official Pi 5 outline datum: holes at x=3.5/61.5 within an 85 mm board.
    # The 58x49 grid centre is 10 mm left of the board centre.
    for dx in (-39,19):
        for y in (-24.5,24.5):
            x=P["pi_x"]+dx
            spacer=cq.Workplane("XY").center(x,y).circle(4).extrude(P["pi_standoff_h"]).translate((0,0,83))
            spacer=spacer.cut(cq.Workplane("XY").center(x,y).circle(1.35).extrude(110))
            s=s.union(spacer).cut(cq.Workplane("XY").center(x,y).circle(1.35).extrude(110))
    # 42x16 service opening routes the declared IDC bend envelope through the tray.
    s=s.cut(slot_xy(0,55,42,16,0,110))
    for x in (10,90):
        for y in (-45,45): s=s.cut(slot_xy(x,y,14,4,0,110)) # host-pack straps on tray
    for x,y,w,l in ((0,-76,180,4),(0,76,180,4),(-96,0,4,140),(96,0,4,140)):
        s=s.union(cq.Workplane("XY").center(x,y).box(w,l,9,centered=(True,True,False)).translate((0,0,83)))
    return s

def tray_posts():
    s=None
    for x in (-85,85):
        for y in (-65,65):
            p=cq.Workplane("XY").center(x,y).circle(6).extrude(76).translate((0,0,4)).cut(cq.Workplane("XY").center(x,y).circle(1.7).extrude(82)); s=p if s is None else s.union(p)
    return s

def vented_shell():
    # Open-bottom ring plus real front-top service panel: 208 mm clears the 200 mm tray.
    outer=rounded_plate(220,236,78,12).translate((0,0,36)); inner=rounded_plate(208,224,81,8).translate((0,0,34)); s=outer.cut(inner)
    panel=rounded_plate(80,36,3,4).translate((0,105,114)).cut(cq.Workplane("XY").center(0,105).circle(11).extrude(120))
    s=s.union(panel) # Ø22 panel material exists at y=+105, z=114.
    # M3 shell feet run down from the front/rear wall onto matching base holes.
    for x in (-80,80):
        for y in (-110,110):
            lug=cq.Workplane("XY").center(x,y).box(8,8,32,centered=(True,True,False)).translate((0,0,4))
            lug=lug.cut(cq.Workplane("XY").center(x,y).circle(1.7).extrude(40))
            s=s.union(lug)
    # Wheel arches and real through-wall side vents, not cuts through the hollow interior.
    s=s.cut(cq.Solid.makeCylinder(38,250,cq.Vector(-125,P["axle_y"],P["axle_z"]),cq.Vector(1,0,0)))
    for x in (-107,107):
        for y in (-45,-15,15,45):
            s=s.cut(cq.Workplane("YZ").center(y,78).slot2D(18,4,90).extrude(20,both=True).translate((x,0,0)))
    return s.cut(cq.Workplane("XY").center(0,-108).box(86,24,35,centered=(True,True,False)).translate((0,0,35))).combine()

def sensor_bracket():
    # One connected part: deck foot, overlap web, and vertical HC-SR04 face (holes face +Y).
    foot=drill(cq.Workplane("XY").center(0,116).box(76,25,4,centered=(True,True,False)).translate((0,0,4)),[(-28,116),(28,116)],3.4)
    web=cq.Workplane("XY").center(0,126).box(64,7,8,centered=(True,True,False)).translate((0,0,4))
    s=foot.union(web).union(cq.Workplane("XY").center(0,129).box(64,3,45,centered=(True,True,False)).translate((0,0,8)))
    for x in (-13,13): s=s.cut(cq.Solid.makeCylinder(8,8,cq.Vector(x,125,33),cq.Vector(0,1,0)))
    return s.combine()

def caster_fixture():
    # Adjustable M3 slot interface; unmeasured caster is an envelope below this plate.
    s=cq.Workplane("XY").center(0,20).box(64,40,4,centered=(True,True,False)).translate((0,0,4))
    for x in (-20,20): s=s.cut(slot_xy(x,20,18,4,90,12))
    return s.combine()

def shrike_module_plate():
    # Connected removable deck plate: four M3 deck screws plus two strap slots for an unmeasured module.
    s=rounded_plate(74,49,4,6).translate((0,65,4))
    s=drill(s,[(x,y) for x in (-28,28) for y in (55,75)],3.4,12)
    for y in (53,77): s=s.cut(slot_xy(0,y,56,4,0,12))
    return s.combine()

def test_stand():
    s=rounded_plate(192,232,6,10).translate((0,0,-48))
    for x in (-50,50):
        for y in (-88,88): s=s.union(cq.Workplane("XY").center(x,y).circle(10).extrude(42).translate((0,0,-42)))
    # Supports structural base underside at pads: never motor axles; opening clears wheels/cables.
    return s.cut(cq.Workplane("XY").box(150,160,20,centered=(True,True,False)).translate((0,0,-45)))

def wheel_envelope(side=1):
    # Starts are -120/+100, so wheels span [-120,-100] and [100,120], centred ±110.
    start=-120 if side<0 else 100
    return cq.Solid.makeCylinder(P["wheel_d"]/2,20,cq.Vector(start,P["axle_y"],P["axle_z"]),cq.Vector(1,0,0))
def envelope(w,l,h,x,y,z): return cq.Workplane("XY").center(x,y).box(w,l,h,centered=(True,True,False)).translate((0,0,z))
def intersection_volume(a,b):
    return (a.val() if hasattr(a,"val") else a).intersect(b.val() if hasattr(b,"val") else b).Volume()
def solid_count(s): return len((s.val() if hasattr(s,"val") else s).Solids())

def write_svg(path):
    sx=lambda x:410+2*x
    sy=lambda y:360-2*y
    path.write_text(f'''<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="700" viewBox="0 0 1000 700"><style>text{{font:14px Arial;fill:#25313b}}.d{{stroke:#f36f21;stroke-width:2;fill:none}}.o{{stroke:#25313b;stroke-width:3;fill:#e8ecee}}.c{{stroke:#78838b;stroke-width:1;fill:none}}.e{{stroke:#6b5b95;stroke-width:1.5;fill:#ece7f3}}.t{{font-weight:bold;font-size:18px}}</style><text x="40" y="35" class="t">AXIOM ROVER — PARAMETRIC MECHANICAL OVERVIEW (mm)</text><rect class="o" x="{sx(-100):g}" y="{sy(130):g}" width="{2*P['base_w']:g}" height="{2*P['base_l']:g}" rx="24"/><rect class="c" x="{sx(-100):g}" y="{sy(80):g}" width="400" height="320" rx="18"/><rect class="c" x="{sx(-120):g}" y="{sy(-50)-65:g}" width="40" height="130"/><rect class="c" x="{sx(100):g}" y="{sy(-50)-65:g}" width="40" height="130"/><line class="d" x1="210" y1="70" x2="610" y2="70"/><path class="d" d="M210 60v20m400-20v20"/><text x="350" y="60">{P['base_w']:g} base outer width</text><line class="d" x1="650" y1="100" x2="650" y2="620"/><path class="d" d="M640 100h20m-20 520h20"/><text x="665" y="370">{P['base_l']:g} base outer length</text><line class="d" x1="190" y1="{sy(P['axle_y']):g}" x2="630" y2="{sy(P['axle_y']):g}"/><text x="345" y="{sy(P['axle_y'])-10:g}">wheel centres ±{P['wheel_x']:g}; axle y={P['axle_y']:g}</text><rect class="e" x="{sx(-45):g}" y="{sy(-75):g}" width="180" height="100"/><rect class="e" x="{sx(-45):g}" y="{sy(107.5):g}" width="180" height="50"/><rect class="e" x="{sx(15):g}" y="{sy(60):g}" width="140" height="240"/><text x="220" y="595">motor pack 90×50</text><text x="430" y="165">base 5V pack 90×25</text><text x="445" y="365">host pack 70×120 on tray</text><text x="250" y="215">tray {P['tray_w']:g} × {P['tray_l']:g}; cable slot y=+55</text><circle class="d" cx="{sx(0):g}" cy="{sy(105):g}" r="22"/><text x="440" y="{sy(105)+5:g}">Ø22 e-stop y=+105</text><rect class="o" x="745" y="215" width="180" height="235" rx="10"/><text x="735" y="190" class="t">Section / clearance</text><text x="755" y="245">ground z={P['ground_z']:g}; wheel/caster low</text><text x="755" y="270">wheel axle z={P['axle_z']:g}</text><text x="755" y="295">PCB bottom z={P['pcb_z']:g}; M3 through/nut</text><text x="755" y="320">PCB {P['pcb_t']:g} + components {P['pcb_component_h']:g}</text><text x="755" y="350">Pi z={P['pi_z']:g}; M2.5 spacers {P['pi_standoff_h']:g}</text><text x="755" y="380">IDC bend {P['idc_bend_h']:g}; tray z={P['tray_z']:g}</text><text x="45" y="670">ENVELOPE ONLY: motors, wheels, caster and all three power packs. Purchase verification required.</text></svg>''')

def preview_png(path,parts):
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    fig=plt.figure(figsize=(11,8),facecolor="#f6f3ed"); ax=fig.add_subplot(111,projection="3d")
    colors={"base_chassis":"#263238","left_motor_bracket":"#f36f21","right_motor_bracket":"#f36f21","tray":"#f36f21","tray_posts":"#34434a","vented_shell":"#263238","sensor_bracket":"#f36f21","caster_fixture":"#f36f21","shrike_module_plate":"#f36f21","test_stand":"#58656b","left_wheel_ENVELOPE":"#1c1c1c","right_wheel_ENVELOPE":"#1c1c1c","left_tt_motor_ENVELOPE":"#888","right_tt_motor_ENVELOPE":"#888","pcb_ENVELOPE":"#19a974","motor_pack_ENVELOPE":"#4e79a7","base5v_pack_ENVELOPE":"#5470a6","host_pack_ENVELOPE":"#6b5b95","pi5_ENVELOPE":"#3a7ca5","shrike_l298_ENVELOPE":"#a06cd5","caster_ENVELOPE":"#777"}
    for name,shape in parts.items():
        solid=shape.val() if hasattr(shape,"val") else shape
        vs,tris=solid.tessellate(1.5); coords=[(v.x,v.y,v.z) for v in vs]; polys=[[coords[i] for i in tri] for tri in tris]
        ax.add_collection3d(Poly3DCollection(polys,facecolor=colors.get(name,"#999"),edgecolor="none",alpha=.78))
    ax.set(xlim=(-155,155),ylim=(-150,150),zlim=(-55,145)); ax.view_init(elev=25,azim=-48); ax.set_box_aspect((310,300,200)); ax.axis("off"); ax.set_title("Axiom Rover mechanical concept — charcoal PETG / orange service parts",color="#263238",pad=18); fig.tight_layout(); fig.savefig(path,dpi=180,facecolor=fig.get_facecolor()); plt.close(fig)

def main(output):
    output.mkdir(parents=True,exist_ok=True)
    printable={"base_chassis":base(),"left_motor_bracket":motor_bracket(-1),"right_motor_bracket":motor_bracket(1),"tray":compute_tray(),"tray_posts":tray_posts(),"vented_shell":vented_shell(),"sensor_bracket":sensor_bracket(),"caster_fixture":caster_fixture(),"shrike_module_plate":shrike_module_plate(),"test_stand":test_stand()}
    pcb_top=P["pcb_z"]+P["pcb_t"]
    harness_z=pcb_top+P["pcb_component_h"]
    env={"left_wheel_ENVELOPE":wheel_envelope(-1),"right_wheel_ENVELOPE":wheel_envelope(1),"left_tt_motor_ENVELOPE":envelope(62,16,30,-64.5,-50,10),"right_tt_motor_ENVELOPE":envelope(62,16,30,64.5,-50,10),"pcb_ENVELOPE":envelope(120,80,P["pcb_t"],0,0,P["pcb_z"]),"pcb_component_ENVELOPE":envelope(120,80,P["pcb_component_h"],0,0,pcb_top),"idc_harness_ENVELOPE":envelope(44,30,P["idc_bend_h"],0,45,harness_z),"idc_tray_corridor_ENVELOPE":envelope(36,12,P["tray_z"]+3-(harness_z+P["idc_bend_h"]),0,55,harness_z+P["idc_bend_h"]),"motor_pack_ENVELOPE":envelope(90,50,25,0,-100,5),"base5v_pack_ENVELOPE":envelope(90,25,20,0,95,10),"host_pack_ENVELOPE":envelope(70,120,30,50,0,83),"pi5_ENVELOPE":envelope(85,56,18,P["pi_x"],0,P["pi_z"]),"shrike_l298_ENVELOPE":envelope(60,35,15,0,65,20),"caster_ENVELOPE":envelope(45,35,P["caster_nominal_h"],0,20,P["ground_z"])}
    parts=printable|env
    for name,shape in printable.items(): exporters.export(shape,str(output/(name+".stl")),tolerance=.12,angularTolerance=.2)
    assy=cq.Assembly()
    for name,shape in parts.items(): assy.add(shape,name=name)
    assy.save(str(output/"axiom_rover_assembly.step")); write_svg(output/"mechanical_overview.svg"); preview_png(output/"assembly_preview.png",parts)
    allowed=set()
    collisions=[]
    for a,b in combinations(parts,2):
        v=intersection_volume(parts[a],parts[b])
        if v>.01: collisions.append({"pair":[a,b],"volume_mm3":round(v,4),"intended":tuple(sorted((a,b))) in allowed})
    unexpected=[c for c in collisions if not c["intended"]]
    solids={name:solid_count(shape) for name,shape in printable.items()}
    pcb_holes=[(-55,-35),(55,-35),(55,35),(-55,35)]
    hole_residual_mm3=[intersection_volume(printable["base_chassis"],cq.Workplane("XY").center(x,y).circle(1.7).extrude(30)) for x,y in pcb_holes]
    wheel_low=[(wheel_envelope(side).BoundingBox().zmin) for side in (-1,1)]
    caster_low=env["caster_ENVELOPE"].val().BoundingBox().zmin
    support_top=printable["base_chassis"].val().BoundingBox().zmax
    # Independent drawing-coordinate check: catch a centred, but misplaced, hole grid.
    pi_holes=[(P["pi_x"]-85/2+x,-56/2+y) for x in (3.5,61.5) for y in (3.5,52.5)]
    for x,y in pi_holes:
        bore=cq.Workplane("XY").center(x,y).circle(1.3).extrude(110)
        assert intersection_volume(printable["tray"],bore)<.01, "Pi 5 mounting bore misplaced"
        spacer=cq.Workplane("XY").center(x,y).circle(3).circle(1.5).extrude(5).translate((0,0,83.5))
        assert abs(intersection_volume(printable["tray"],spacer)-spacer.val().Volume())<.01, "Pi 5 spacer misplaced"
    checks={"base_outer_width_mm":P["base_w"],"base_outer_length_mm":P["base_l"],"tray_width_mm":P["tray_w"],"tray_length_mm":P["tray_l"],"ground_z_mm":P["ground_z"],"wheel_centres_x_mm":[-110,110],"wheel_lowest_z_mm":wheel_low,"caster_lowest_z_mm":caster_low,"pcb_hole_centres":pcb_holes,"pcb_m3_hole_residual_mm3":hole_residual_mm3,"pcb_support_top_z_mm":support_top,"common_mount_centres":[[-85,-65],[-85,65],[85,-65],[85,65]],"intended_intersections":collisions,"unexpected_intersections":unexpected,"printable_solid_counts":solids}
    checks["pi5_drawing_hole_centres"]=pi_holes
    checks["passed"]=not unexpected and all(n==1 for name,n in solids.items() if name!="tray_posts") and solids["tray_posts"]==4 and max(hole_residual_mm3)<.01 and abs(support_top-P["pcb_z"])<.01 and all(abs(z-P["ground_z"])<.01 for z in wheel_low+[caster_low])
    report={"design":"Axiom modular 2WD rover","units":"mm","measured":False,"source_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),"status":"CONCEPT — envelopes require purchase verification","parameters":P,"checks":checks,"parts_printable":list(printable),"parts_envelope_only":list(env)}
    (output/"mechanical_checks.json").write_text(json.dumps(report,indent=2)+"\n")
    if not checks["passed"]: raise RuntimeError("mechanical clearance failure: "+str(checks))
if __name__=="__main__":
    a=argparse.ArgumentParser();a.add_argument("--output",type=Path,required=True);main(a.parse_args().output)
