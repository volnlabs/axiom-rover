#!/usr/bin/env python3
"""Parametric Rev B mechanical CAD for the Axiom 2WD rover (all units mm)."""
from __future__ import annotations
import argparse, hashlib, json, subprocess
from itertools import combinations
from pathlib import Path
import cadquery as cq
from cadquery import exporters, importers

P={"base_w":200.,"base_l":260.,"base_t":4.,"ground_z":-17.5,"axle_y":-50.,"axle_z":22.5,"wheel_x":120.,"wheel_d":80.,"wheel_w":10.,"caster_nominal_h":17.5,"tray_w":200.,"tray_l":160.,"tray_z":80.,"tray_t":3.,"pi_bottom_z":89.,"pi_t":1.6,"pi_cooler_max_h":13.7,"carrier_service_lift":7.,"pcb_w":160.,"pcb_l":100.,"pcb_t":1.6,"pcb_bottom_z":107.1,"carrier_frame_t":3.,"carrier_post_od":8.,"motor_gearbox_d":25.,"motor_gearbox_l":23.,"motor_body_d":24.4,"motor_body_l":31.,"motor_encoder_l":9.,"motor_shaft_d":4.,"motor_shaft_l":12.}
PCB_ORIGIN=(-80.,50.) # KiCad (0,0) -> world; KiCad +y is world -y.
PI_HOLES_LOCAL=((3.5,23.5),(61.5,23.5),(3.5,72.5),(61.5,72.5))
PCB_SUPPORTS_LOCAL=((5.,5.),(155.,5.),(155.,95.),(5.,95.))
TRAY_MOUNTS=((-70.,-75.),(-70.,65.),(70.,-75.),(70.,65.))
COOLER_WINDOW_LOCAL=(8.,32.,68.,66.)
SHRIKE_BAY_LOCAL=(99.,10.,124.4,68.5)
SHRIKE_SOCKET_PINS_LOCAL={"left":(100.27,21.0958),"right":(123.13,21.1210)}
PI_SOCKET_BODY_LOCAL=(6.845,21.025,58.155,25.975) # ESQ-120 51.31 x 4.95; Pi pin 1/2 from official STEP datum.

def pcb_world(x,y): return PCB_ORIGIN[0]+x,PCB_ORIGIN[1]-y
def rounded_plate(w,l,t,r=10):
    s=cq.Workplane("XY").box(w-2*r,l,t,centered=(True,True,False)).union(cq.Workplane("XY").box(w,l-2*r,t,centered=(True,True,False)))
    for x in (-w/2+r,w/2-r):
        for y in (-l/2+r,l/2-r): s=s.union(cq.Workplane("XY").center(x,y).circle(r).extrude(t))
    return s
def slot_xy(x,y,length,width,angle=90,z=20): return cq.Workplane("XY").center(x,y).slot2D(length,width,angle).extrude(z)
def drill(s,holes,d,z=30):
    for x,y in holes: s=s.cut(cq.Workplane("XY").center(x,y).circle(d/2).extrude(z))
    return s
def envelope(w,l,h,x,y,z): return cq.Workplane("XY").center(x,y).box(w,l,h,centered=(True,True,False)).translate((0,0,z))
def motor_axis_x(side): return side*(P["wheel_x"]-P["wheel_w"]/2-P["motor_shaft_l"]-P["motor_gearbox_l"]/2)
def motor_mount_holes(side): return [(motor_axis_x(side),P["axle_y"]+dy) for dy in (-22.,22.)]

def base():
    s=rounded_plate(P["base_w"],P["base_l"],P["base_t"],12)
    s=drill(s,TRAY_MOUNTS,3.4)
    for side in (-1,1): s=drill(s,motor_mount_holes(side),3.4)
    for x in (-20,20): s=s.cut(slot_xy(x,20,18,4,90))
    s=drill(s,[(-28,116),(28,116)]+[(x,y) for x in (-80,80) for y in (-110,110)],3.4)
    for x in (-48,48):
        for y in (-112,-88): s=s.cut(slot_xy(x,y,14,4,0))
        for y in (88,102): s=s.cut(slot_xy(x,y,14,4,0))
    for x in (-42,42):
        for y in (-38,38): s=s.cut(slot_xy(x,y,14,4,0)) # Central below-tray host-pack straps; fit remains unqualified.
    for x in (-78,78): s=s.union(cq.Workplane("XY").center(x,0).box(4,190,7,centered=(True,True,False)).translate((0,0,-3)))
    return s.combine()

def clamp_half(side,upper):
    """One half of a bolted split clamp for the vendor-dimensioned 25 mm gearbox."""
    cx,cy,cz=motor_axis_x(side),P["axle_y"],P["axle_z"]; d=cq.Vector(side,0,0)
    start=cq.Vector(cx-side*(P["motor_gearbox_l"]/2+.3),cy,cz)
    ring=cq.Solid.makeCylinder(16.,P["motor_gearbox_l"]+.6,start,d).cut(cq.Solid.makeCylinder(P["motor_gearbox_d"]/2+.35,P["motor_gearbox_l"]+2,start-d*.5,d))
    # A 1 mm horizontal split leaves a clamp closure range around the 25.70 mm nominal bore.
    ring=ring.intersect(envelope(40,50,30 if upper else 29.5,cx,cy,cz+.5 if upper else cz-30).val())
    ears=None
    for y in (cy-17,cy+17):
        ear=envelope(P["motor_gearbox_l"]+.6,5,8 if upper else 4,cx,y,cz+.5 if upper else cz-8); ears=ear if ears is None else ears.union(ear)
    s=cq.Workplane("XY").newObject([ring]).union(ears)
    if not upper: s=drill(s.union(envelope(24,52,4,cx,cy,P["base_t"])),motor_mount_holes(side),3.4,30)
    for y in (cy-17,cy+17): s=s.cut(cq.Workplane("XY").center(cx,y).circle(1.7).extrude(50).translate((0,0,cz-20)))
    return s.combine()

def motor_reference(side):
    """Vendor-dimension reference only; not a measured procurement fit."""
    cx,cy,cz=motor_axis_x(side),P["axle_y"],P["axle_z"]; d=cq.Vector(side,0,0)
    gear=cq.Vector(cx-side*P["motor_gearbox_l"]/2,cy,cz); body=gear-d*P["motor_body_l"]; encoder=body-d*P["motor_encoder_l"]; shaft=gear+d*P["motor_gearbox_l"]
    return cq.Workplane("XY").newObject([cq.Solid.makeCylinder(P["motor_gearbox_d"]/2,P["motor_gearbox_l"],gear,d),cq.Solid.makeCylinder(P["motor_body_d"]/2,P["motor_body_l"],body,d),cq.Solid.makeCylinder(7.05,P["motor_encoder_l"],encoder,d),cq.Solid.makeCylinder(P["motor_shaft_d"]/2,P["motor_shaft_l"],shaft,d)]).combine()

def compute_tray():
    s=rounded_plate(P["tray_w"],P["tray_l"],P["tray_t"],9).translate((0,0,P["tray_z"]))
    s=drill(s,TRAY_MOUNTS,3.4,110)
    # The Pi can slide through this opening only after the carrier is lifted to disengage GPIO.
    for x,y in (pcb_world(*p) for p in PI_HOLES_LOCAL):
        spacer=cq.Workplane("XY").center(x,y).circle(4).extrude(P["pi_bottom_z"]-(P["tray_z"]+P["tray_t"])).translate((0,0,P["tray_z"]+P["tray_t"]))
        s=s.union(spacer).cut(cq.Workplane("XY").center(x,y).circle(1.4).extrude(110))
    return s.combine()

def tray_posts():
    s=None
    for x,y in TRAY_MOUNTS:
        p=cq.Workplane("XY").center(x,y).circle(6).extrude(P["tray_z"]-P["base_t"]).translate((0,0,P["base_t"])).cut(cq.Workplane("XY").center(x,y).circle(1.7).extrude(90)); s=p if s is None else s.union(p)
    return s

def carrier_frame():
    z=P["pcb_bottom_z"]-P["carrier_frame_t"]
    # Open centre clears all PCB underside tails and the DRV thermal-pad back. The 3 mm rim carries only the perimeter.
    s=rounded_plate(P["pcb_w"],P["pcb_l"],P["carrier_frame_t"],4).translate((0,0,z)).cut(rounded_plate(P["pcb_w"]-6,P["pcb_l"]-6,10,2).translate((0,0,z-1)))
    for x,y in (pcb_world(*p) for p in PCB_SUPPORTS_LOCAL): s=s.union(cq.Workplane("XY").center(x,y).circle(P["carrier_post_od"]/2).extrude(P["carrier_frame_t"]).translate((0,0,z)))
    s=drill(s,[pcb_world(*p) for p in PCB_SUPPORTS_LOCAL],3.4,120)
    return drill(s,[pcb_world(*p) for p in PI_HOLES_LOCAL],5.,120).combine()

def carrier_posts():
    s=None; h=P["pcb_bottom_z"]-P["carrier_frame_t"]-(P["tray_z"]+P["tray_t"])
    for x,y in (pcb_world(*p) for p in PCB_SUPPORTS_LOCAL):
        p=cq.Workplane("XY").center(x,y).circle(P["carrier_post_od"]/2).extrude(h).translate((0,0,P["tray_z"]+P["tray_t"])).cut(cq.Workplane("XY").center(x,y).circle(1.7).extrude(120)); s=p if s is None else s.union(p)
    return s

def vented_shell():
    outer=rounded_plate(220,236,105,12).translate((0,0,36)); inner=rounded_plate(208,224,108,8).translate((0,0,34)); s=outer.cut(inner)
    panel=rounded_plate(80,36,3,4).translate((0,105,130)).cut(cq.Workplane("XY").center(0,105).circle(11).extrude(150)); s=s.union(panel)
    for x in (-80,80):
        for y in (-110,110): s=s.union(cq.Workplane("XY").center(x,y).box(8,8,32,centered=(True,True,False)).translate((0,0,4)).cut(cq.Workplane("XY").center(x,y).circle(1.7).extrude(40)))
    s=s.cut(cq.Solid.makeCylinder(P["wheel_d"]/2+4,250,cq.Vector(-125,P["axle_y"],P["axle_z"]),cq.Vector(1,0,0)))
    for x in (-107,107):
        for y in (-45,-15,15,45): s=s.cut(cq.Workplane("YZ").center(y,86).slot2D(18,4,90).extrude(20,both=True).translate((x,0,0)))
    # Left service opening is used after lifting the carrier to disengage GPIO.
    s=s.cut(envelope(24,70,34,-108,2,76)) # z=76..110 clears the raised full Pi source envelope.
    return s.cut(cq.Workplane("XY").center(0,-108).box(86,24,35,centered=(True,True,False)).translate((0,0,35))).combine()

def sensor_bracket():
    foot=drill(cq.Workplane("XY").center(0,116).box(76,25,4,centered=(True,True,False)).translate((0,0,4)),[(-28,116),(28,116)],3.4); web=cq.Workplane("XY").center(0,126).box(64,7,8,centered=(True,True,False)).translate((0,0,4)); s=foot.union(web).union(cq.Workplane("XY").center(0,129).box(64,3,45,centered=(True,True,False)).translate((0,0,8)))
    for x in (-13,13): s=s.cut(cq.Solid.makeCylinder(8,8,cq.Vector(x,125,33),cq.Vector(0,1,0)))
    return s.combine()
def caster_fixture(): return cq.Workplane("XY").center(0,20).box(64,40,4,centered=(True,True,False)).translate((0,0,4)).cut(slot_xy(-20,20,18,4,90,12)).cut(slot_xy(20,20,18,4,90,12)).combine()
def test_stand():
    s=rounded_plate(192,232,6,10).translate((0,0,-48))
    for x in (-50,50):
        for y in (-88,88): s=s.union(cq.Workplane("XY").center(x,y).circle(10).extrude(42).translate((0,0,-42)))
    return s.cut(cq.Workplane("XY").box(150,160,20,centered=(True,True,False)).translate((0,0,-45)))
def wheel_reference(side): return cq.Workplane("XY").newObject([cq.Solid.makeCylinder(P["wheel_d"]/2,P["wheel_w"],cq.Vector(side*(P["wheel_x"]-P["wheel_w"]/2),P["axle_y"],P["axle_z"]),cq.Vector(side,0,0))])

def shrike_actual_reference():
    # Rotate, never mirror: the USB is at source -Y and must face contracted low PCB-Y/world +Y.
    source=importers.importStep("reference/shrike-r04/Shrike-lite.step").rotate((0,0,0),(0,0,1),180); full=source.val().BoundingBox()
    # The 25.45 x 58.55008 x 1.51 substrate solid is the datum; the full assembly bbox includes connectors/components.
    board=next(x for x in source.val().Solids() if 25.<x.BoundingBox().xlen<26. and 58.<x.BoundingBox().ylen<59. and x.BoundingBox().zlen<2.)
    b=board.BoundingBox(); socket_top=P["pcb_bottom_z"]+P["pcb_t"]+8.51; bottom=socket_top+2.54
    target=(pcb_world(SHRIKE_BAY_LOCAL[0],SHRIKE_BAY_LOCAL[3])[0],pcb_world(SHRIKE_BAY_LOCAL[0],SHRIKE_BAY_LOCAL[3])[1],bottom); shift=(target[0]-b.xmin,target[1]-b.ymin,target[2]-b.zmin)
    j2=pcb_world(*SHRIKE_SOCKET_PINS_LOCAL["left"]); j4=pcb_world(*SHRIKE_SOCKET_PINS_LOCAL["right"]); module_shift=(shift[0]-j2[0],shift[1]-j2[1])
    rows={}
    for label,x,expected in (("J2",-11.43,(0.,0.)),("J4",11.43,(j4[0]-j2[0],j4[1]-j2[1]))):
        ys=sorted({round(e.Center().y,4) for e in board.Edges() if e.geomType()=="CIRCLE" and abs(e.radius()-.45)<.01 and abs(e.Center().z)<.01 and abs(e.Center().x-x)<.02},reverse=True)
        start=(x+module_shift[0],ys[0]+module_shift[1]); end=(x+module_shift[0],ys[-1]+module_shift[1])
        rows[label]={"pin1_usb_end_model_mm":list(start),"pin19_model_mm":list(end),"expected_pin1_model_mm":list(expected),"pin1_delta_mm":[round(start[0]-expected[0],4),round(start[1]-expected[1],4)],"pitch_span_mm":round(start[1]-end[1],4)}
    return source.translate(shift),{"source_full_bbox_mm":[full.xmin,full.ymin,full.zmin,full.xmax,full.ymax,full.zmax],"source_board_bbox_mm":[b.xmin,b.ymin,b.zmin,b.xmax,b.ymax,b.zmax],"translate_mm":list(shift),"socket_top_z_mm":socket_top,"shrike_board_bottom_z_mm":bottom,"header_hole_alignment":rows}

def pi_actual_reference():
    source=importers.importStep("reference/raspberry-pi-5/rpi-5b_no_graphics.step"); full=source.val().BoundingBox()
    board=next(x for x in source.val().Solids() if 84.<x.BoundingBox().xlen<86. and 55.<x.BoundingBox().ylen<57. and x.BoundingBox().zlen<2.)
    b=board.BoundingBox()
    # Native source orientation already maps its bottom-left to world (-80,-26); no reflection of vendor geometry.
    shift=(-80.-b.xmin,-26.-b.ymin,P["pi_bottom_z"]-b.zmin)
    return source.translate(shift),{"source_full_bbox_mm":[full.xmin,full.ymin,full.zmin,full.xmax,full.ymax,full.zmax],"source_board_bbox_mm":[b.xmin,b.ymin,b.zmin,b.xmax,b.ymax,b.zmax],"translate_mm":list(shift)}

def local_reference_box(bounds,h,z):
    x0,y0,x1,y1=bounds; x,y=pcb_world((x0+x1)/2,(y0+y1)/2)
    return envelope(x1-x0,y1-y0,h,x,y,z)

def shrike_socket_references():
    top=P["pcb_bottom_z"]+P["pcb_t"]+8.51; bottom=top-8.51; s={}
    for side,(x,y) in SHRIKE_SOCKET_PINS_LOCAL.items():
        # 48.77 mm long SSW body, with its 1.525 mm end overhang on the supplied pin-1 row datum.
        s[f"shrike_{side}_socket_REFERENCE"]=local_reference_box((x-2.41/2,y-1.525,x+2.41/2,y-1.525+48.77),8.51,bottom)
    return s

def shrike_component_reserves():
    """Opt-in clearance references; neither represents a measured Shrike component."""
    bottom=P["pcb_bottom_z"]+P["pcb_t"]+8.51+2.54
    return {
        "shrike_component_UNMEASURED_ENVELOPE":local_reference_box(SHRIKE_BAY_LOCAL,8.,bottom),
        # Low KiCad Y maps to world +Y: preserve a USB plug/wire routing volume on that side.
        "shrike_usb_wire_UNMEASURED_ENVELOPE":local_reference_box((97.,-25.,127.,10.),12.,bottom),
    }

def export_shrike_pcb_step(path):
    subprocess.run([".cache/cad/kicad-10.0.6-x86_64-lite.AppImage","kicad-cli","pcb","export","step","--board-only","--include-pads","--force","-o",str(path),"reference/shrike-r04/Shrike-lite.kicad_pcb"],check=True)

def shrike_pcb_derived_reference(path):
    """Native KiCad board-only STEP, normalized to J2 pin 1 and board bottom."""
    native=importers.importStep(str(path)); b=native.val().BoundingBox()
    # KiCad native J2 pin 1 is (137.071095, -86.8494); native board underside is z=-0.04.
    module=native.translate((-137.071095,86.8494,-b.zmin))
    native_holes={(round(e.Center().x,3),round(e.Center().y,3)) for e in module.val().Edges() if e.geomType()=="CIRCLE" and .42<e.radius()<.46}
    for x,y0 in ((0.,0.),(22.86,-.0252)):
        for i in range(19): assert (round(x,3),round(y0-2.54*i,3)) in native_holes,"native Shrike header-hole row missing"
    plastic=None; pins=[]
    for x,y0 in ((0.,0.),(22.86,-.0252)):
        p=envelope(2.54,48.26,2.54,x,y0-22.86,-2.54); plastic=p if plastic is None else plastic.union(p)
        for i in range(19): pins.append(cq.Workplane("XY").center(x,y0-2.54*i).box(.64,.64,6,centered=(True,True,False)).translate((0,0,-8.54)).val())
    pins=cq.Workplane("XY").newObject([cq.Compound.makeCompound(pins)])
    companion=cq.Workplane("XY").newObject([cq.Compound.makeCompound([module.val(),plastic.val(),pins.val()])])
    companion_box=companion.val().BoundingBox()
    assert len(pins.val().Solids())==38 and abs(companion_box.zmin+8.54)<.01,"Shrike companion is missing nominal male pins"
    j2=pcb_world(*SHRIKE_SOCKET_PINS_LOCAL["left"]); bottom=P["pcb_bottom_z"]+P["pcb_t"]+8.51+2.54; world_shift=(*j2,bottom)
    return module.translate(world_shift),plastic.translate(world_shift),pins.translate(world_shift),companion,{"native_bbox_mm":[b.xmin,b.ymin,b.zmin,b.xmax,b.ymax,b.zmax],"j2_native_mm":[137.071095,-86.8494],"module_board_bottom_z_mm":0.,"companion_bbox_mm":[companion_box.xmin,companion_box.ymin,companion_box.zmin,companion_box.xmax,companion_box.ymax,companion_box.zmax],"companion_pin_solid_count":len(pins.val().Solids()),"header_holes_verified":True}
def intersection_volume(a,b): return (a.val() if hasattr(a,"val") else a).intersect(b.val() if hasattr(b,"val") else b).Volume()
def solid_count(s): return len((s.val() if hasattr(s,"val") else s).Solids())

def write_svg(path):
    sx,sy=lambda x:410+2*x,lambda y:360-2*y
    path.write_text(f'''<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="700" viewBox="0 0 1000 700"><style>text{{font:14px Arial;fill:#25313b}}.d{{stroke:#f36f21;stroke-width:2;fill:none}}.o{{stroke:#25313b;stroke-width:3;fill:#e8ecee}}.c{{stroke:#78838b;stroke-width:1;fill:none}}.r{{stroke:#6b5b95;stroke-width:1.5;fill:#ece7f3}}.t{{font-weight:bold;font-size:18px}}</style><text x="40" y="35" class="t">AXIOM ROVER — REV B MECHANICAL OVERVIEW (mm)</text><rect class="o" x="{sx(-100):g}" y="{sy(130):g}" width="400" height="520" rx="24"/><rect class="c" x="{sx(-100):g}" y="{sy(80):g}" width="400" height="320" rx="18"/><rect class="c" x="{sx(-115):g}" y="{sy(-50)-80:g}" width="20" height="160"/><rect class="c" x="{sx(105):g}" y="{sy(-50)-80:g}" width="20" height="160"/><rect class="r" x="{sx(-35):g}" y="{sy(25):g}" width="140" height="240"/><text x="250" y="215">below-tray host pack 70×120×30</text><rect class="r" x="{sx(-80):g}" y="{sy(50):g}" width="320" height="200"/><rect class="d" x="{sx(-72):g}" y="{sy(18):g}" width="120" height="68"/><text x="205" y="112">160×100 carrier; 60×34 airflow aperture</text><line class="d" x1="190" y1="{sy(P['axle_y']):g}" x2="630" y2="{sy(P['axle_y']):g}"/><text x="315" y="{sy(P['axle_y'])-10:g}">80 mm wheels; axle z={P['axle_z']:g}</text><rect class="o" x="735" y="185" width="220" height="295" rx="10"/><text x="750" y="215" class="t">Section / contracts</text><text x="755" y="245">ground z={P['ground_z']:g}; wheel low</text><text x="755" y="275">Pi bottom/top 89 / 90.6</text><text x="755" y="305">carrier PCB bottom {P['pcb_bottom_z']:g}</text><text x="755" y="335">Pi-to-PCB gap 16.5</text><text x="755" y="365">airflow aperture 60×34</text><text x="755" y="395">cooler envelope 63.5×42.5×13.7</text><text x="755" y="425">Shrike socket top {P['pcb_bottom_z']+P['pcb_t']+8.51:g}</text><text x="755" y="455">source / unmeasured items labelled</text><text x="45" y="670">VENDOR REFERENCE: ThinkRobotics motor / Pololu 3690 wheel. PACKS, CASTER AND SOCKET PLASTIC ARE UNQUALIFIED.</text></svg>''')

def preview_png(path,parts):
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    fig=plt.figure(figsize=(11,8),facecolor="#f6f3ed"); ax=fig.add_subplot(111,projection="3d")
    colors={"base_chassis":"#263238","left_motor_bracket":"#f36f21","right_motor_bracket":"#f36f21","left_motor_clamp_cap":"#f9a65a","right_motor_clamp_cap":"#f9a65a","tray":"#f36f21","tray_posts":"#34434a","carrier_frame":"#f36f21","carrier_posts":"#34434a","vented_shell":"#263238","sensor_bracket":"#f36f21","caster_fixture":"#f36f21","test_stand":"#58656b","left_wheel_VENDOR_REFERENCE":"#1c1c1c","right_wheel_VENDOR_REFERENCE":"#1c1c1c","left_motor_VENDOR_REFERENCE":"#888","right_motor_VENDOR_REFERENCE":"#888","carrier_pcb_CONTRACT_REFERENCE":"#19a974","pi5_REFERENCE":"#3a7ca5","shrike_actualCAD_REFERENCE":"#a06cd5"}
    for name,shape in parts.items():
        if name=="pi5_actualCAD_REFERENCE": continue # Assembly retains the official CAD; its dense tessellation adds nothing to this overview.
        solid=shape.val() if hasattr(shape,"val") else shape; vs,tris=solid.tessellate(1.5); coords=[(v.x,v.y,v.z) for v in vs]; ax.add_collection3d(Poly3DCollection([[coords[i] for i in tri] for tri in tris],facecolor=colors.get(name,"#999"),edgecolor="none",alpha=.78))
    ax.set(xlim=(-155,155),ylim=(-150,150),zlim=(-55,150)); ax.view_init(elev=25,azim=-48); ax.set_box_aspect((310,300,205)); ax.axis("off"); ax.set_title("Axiom Rover Rev B — charcoal PETG / orange service parts",color="#263238",pad=18); fig.tight_layout(); fig.savefig(path,dpi=180,facecolor=fig.get_facecolor()); plt.close(fig)

def main(output):
    output.mkdir(parents=True,exist_ok=True)
    export_shrike_pcb_step(output/"shrike-pcb-derived.step")
    printable={"base_chassis":base(),"left_motor_bracket":clamp_half(-1,False),"right_motor_bracket":clamp_half(1,False),"left_motor_clamp_cap":clamp_half(-1,True),"right_motor_clamp_cap":clamp_half(1,True),"tray":compute_tray(),"tray_posts":tray_posts(),"carrier_frame":carrier_frame(),"carrier_posts":carrier_posts(),"vented_shell":vented_shell(),"sensor_bracket":sensor_bracket(),"caster_fixture":caster_fixture(),"test_stand":test_stand()}
    shrike_vendor,shrike_transform=shrike_actual_reference(); shrike_pcb,shrike_plastic,shrike_pins,shrike_module,shrike_native_transform=shrike_pcb_derived_reference(output/"shrike-pcb-derived.step"); pi_actual,pi_transform=pi_actual_reference(); pi_cx,pi_cy=pcb_world(42.5,48.); cooler_cx,cooler_cy=pcb_world(38.,49.); pi_box=pi_actual.val().BoundingBox(); service_sweep=envelope(pi_box.xmax+150,pi_box.ylen,pi_box.zlen,(pi_box.xmax-150)/2,(pi_box.ymin+pi_box.ymax)/2,pi_box.zmin+2)
    reference={"left_wheel_VENDOR_REFERENCE":wheel_reference(-1),"right_wheel_VENDOR_REFERENCE":wheel_reference(1),"left_motor_VENDOR_REFERENCE":motor_reference(-1),"right_motor_VENDOR_REFERENCE":motor_reference(1),"carrier_pcb_CONTRACT_REFERENCE":envelope(P["pcb_w"],P["pcb_l"],P["pcb_t"],0,0,P["pcb_bottom_z"]),"pi5_DRAWING_REFERENCE":envelope(85,56,P["pi_t"],pi_cx,pi_cy,P["pi_bottom_z"]),"pi5_actualCAD_REFERENCE":pi_actual,"pi_socket_ESQ_REFERENCE":local_reference_box(PI_SOCKET_BODY_LOCAL,13.59,P["pcb_bottom_z"]-13.59),"pi_cooler_max_ENVELOPE":envelope(60,34,P["pi_cooler_max_h"],cooler_cx,cooler_cy,P["pi_bottom_z"]+P["pi_t"]),"pi5_after_carrier_lift_removal_SWEEP":envelope(111,56,P["pi_t"],-50.5,pi_cy,P["pi_bottom_z"]),"shrike_pcbCAD_REFERENCE":shrike_pcb,"shrike_male_plastic_UNMEASURED":shrike_plastic,"shrike_male_pins_UNMEASURED":shrike_pins,"motor_pack_UNQUALIFIED_ENVELOPE":envelope(90,50,25,0,-100,5),"base5v_pack_UNQUALIFIED_ENVELOPE":envelope(90,25,20,0,95,10),"host_pack_UNQUALIFIED_ENVELOPE":envelope(70,120,30,0,0,10),"caster_UNQUALIFIED_ENVELOPE":envelope(45,35,P["caster_nominal_h"],0,20,P["ground_z"])}|shrike_socket_references()
    del reference["pi5_after_carrier_lift_removal_SWEEP"]
    reference["pi5_after_carrier_removal_service_SWEEP"]=service_sweep
    reference|=shrike_component_reserves()
    pad_map=Path("electronics/out/pad-geometry.json")
    if not pad_map.exists(): raise RuntimeError("missing carrier THT-tail geometry: "+str(pad_map))
    tail_solids=[]
    for ref,data in json.loads(pad_map.read_text())["footprints"].items():
        if not ref.startswith("J"): continue
        for pin in data["pins"].values():
            if pin["drill"]>0:
                x,y=pcb_world(pin["x"],pin["y"])
                tail_solids.append(cq.Solid.makeCylinder(pin["drill"]/2+.3,6.,cq.Vector(x,y,P["pcb_bottom_z"]-6),cq.Vector(0,0,1)))
    reference["carrier_tails_CLEARANCE_REFERENCE"]=cq.Workplane("XY").newObject([cq.Compound.makeCompound(tail_solids)])
    parts=printable|reference
    for name,shape in printable.items(): exporters.export(shape,str(output/(name+".stl")),tolerance=.12,angularTolerance=.2)
    assy=cq.Assembly()
    for name,shape in parts.items(): assy.add(shape,name=name)
    assy.save(str(output/"axiom_rover_assembly.step")); write_svg(output/"mechanical_overview.svg"); preview_png(output/"assembly_preview.png",parts)
    # KiCad companion: PCB-derived geometry, J2 pin 1 origin and substrate bottom z=0.
    module=cq.Assembly(); module.add(shrike_module,name="shrike_pcbCAD"); module.save(str(output/"shrike-module.step"))
    allowed={tuple(sorted(pair)) for pair in (("left_wheel_VENDOR_REFERENCE","left_motor_VENDOR_REFERENCE"),("right_wheel_VENDOR_REFERENCE","right_motor_VENDOR_REFERENCE"),("shrike_male_pins_UNMEASURED","shrike_left_socket_REFERENCE"),("shrike_male_pins_UNMEASURED","shrike_right_socket_REFERENCE"))}
    # Native KiCad board export has hundreds of pads/solids; verify its complete bay buffer below, not O(N) booleans.
    collision_parts=printable|{k:v for k,v in reference.items() if not k.endswith("SWEEP") and k not in {"pi5_actualCAD_REFERENCE","shrike_pcbCAD_REFERENCE","carrier_tails_CLEARANCE_REFERENCE","shrike_component_UNMEASURED_ENVELOPE","shrike_usb_wire_UNMEASURED_ENVELOPE"}}; collisions=[]
    for a,b in combinations(collision_parts,2):
        v=intersection_volume(collision_parts[a],collision_parts[b])
        if v>.01: collisions.append({"pair":[a,b],"volume_mm3":round(v,4),"classification":"INTENDED_INTERFACE" if tuple(sorted((a,b))) in allowed else "UNEXPECTED"})
    unexpected=[c for c in collisions if c["classification"]=="UNEXPECTED"]; supports=[pcb_world(*p) for p in PCB_SUPPORTS_LOCAL]; pi_holes=[pcb_world(*p) for p in PI_HOLES_LOCAL]; wheel_low=[wheel_reference(side).val().BoundingBox().zmin for side in (-1,1)]; caster_low=reference["caster_UNQUALIFIED_ENVELOPE"].val().BoundingBox().zmin
    frame=printable["carrier_frame"]; cooler=reference["pi_cooler_max_ENVELOPE"]; service=reference["pi5_after_carrier_removal_service_SWEEP"]; tails=reference["carrier_tails_CLEARANCE_REFERENCE"]; vendor_shrike_box=shrike_vendor.val().BoundingBox(); pi_socket=reference["pi_socket_ESQ_REFERENCE"]; native_shrike_box=shrike_pcb.val().BoundingBox(); shrike_component_box=reference["shrike_component_UNMEASURED_ENVELOPE"].val().BoundingBox(); shrike_usb_box=reference["shrike_usb_wire_UNMEASURED_ENVELOPE"].val().BoundingBox()
    assert intersection_volume(frame,cooler)<.01,"cooler projection does not clear carrier window"
    assert intersection_volume(frame,pi_socket)<.01,"Pi ESQ body does not clear carrier frame"
    assert intersection_volume(frame,tails)<.01,"carrier frame blocks a connector THT tail"
    for x,y in (pcb_world(*p) for p in PCB_SUPPORTS_LOCAL):
        hole=cq.Workplane("XY").center(x,y).circle(1.7).extrude(10).translate((0,0,P["pcb_bottom_z"]-5))
        boss=cq.Workplane("XY").center(x,y).circle(P["carrier_post_od"]/2).extrude(P["carrier_frame_t"]).translate((0,0,P["pcb_bottom_z"]-P["carrier_frame_t"]))
        assert intersection_volume(frame,hole)<.01 and intersection_volume(frame,boss)>1.,"carrier support hole/boss invalid"
    for side in (-1,1):
        lower=printable["left_motor_bracket" if side<0 else "right_motor_bracket"]; upper=printable["left_motor_clamp_cap" if side<0 else "right_motor_clamp_cap"]
        gap=envelope(P["motor_gearbox_l"]+.6,29,.98,motor_axis_x(side),P["axle_y"],P["axle_z"]-.49)
        assert intersection_volume(lower,gap)<.01 and intersection_volume(upper,gap)<.01,"motor clamp split gap is below 0.98 mm"
        for x,y in motor_mount_holes(side):
            bolt=cq.Workplane("XY").center(x,y).circle(1.7).extrude(40).translate((0,0,P["base_t"]-1))
            assert intersection_volume(lower,bolt)<.01 and intersection_volume(upper,bolt)<.01,"motor deck bolt is obstructed"
    assert all(intersection_volume(service,p)<.01 for name,p in printable.items() if name!="carrier_frame"),"Pi service sweep obstructed after carrier/frame removal"
    assert P["pcb_bottom_z"]-13.59+P["carrier_service_lift"]>P["pi_bottom_z"]+P["pi_t"]+8.54,"carrier lift does not disengage Pi GPIO"
    assert abs(native_shrike_box.xmin-19.)<.01 and abs(native_shrike_box.xmax-44.4)<.01 and abs(native_shrike_box.ymin+18.5)<.01 and abs(native_shrike_box.ymax-40.)<.01,"native Shrike board misses contracted bay"
    assert abs(native_shrike_box.zmin-(P["pcb_bottom_z"]+P["pcb_t"]+8.51+2.54))<.01 and native_shrike_box.zmax<135.,"native Shrike stack misses height buffer"
    assert len(shrike_pins.val().Solids())==38,"Shrike nominal pin compound is incomplete"
    assert abs(shrike_component_box.zmin-native_shrike_box.zmin)<.01 and shrike_component_box.zmax<135.,"Shrike component reserve misses enclosure buffer"
    assert shrike_usb_box.ymax>shrike_component_box.ymax and shrike_usb_box.zmax<135.,"Shrike USB reserve does not point to low PCB Y/world +Y"
    counts={name:solid_count(shape) for name,shape in printable.items()}
    checks={"base_outer_width_mm":P["base_w"],"base_outer_length_mm":P["base_l"],"ground_z_mm":P["ground_z"],"wheel_centres_x_mm":[-P["wheel_x"],P["wheel_x"]],"wheel_lowest_z_mm":wheel_low,"caster_lowest_z_mm":caster_low,"pcb_origin_world_mm":list(PCB_ORIGIN)+[P["pcb_bottom_z"]],"pcb_support_centres_world_mm":supports,"pi5_drawing_hole_centres_world_mm":pi_holes,"pi5_centre_world_mm":[pi_cx,pi_cy],"pi5_to_carrier_pcb_bottom_gap_mm":P["pcb_bottom_z"]-(P["pi_bottom_z"]+P["pi_t"]),"carrier_service_lift_mm":P["carrier_service_lift"],"pi_socket_esq_body_mm":[51.31,4.95,13.59],"cooler_window_local_mm":list(COOLER_WINDOW_LOCAL),"cooler_projection_mm":[60,34,P["pi_cooler_max_h"],"airflow_window_only"],"shrike_bay_local_mm":list(SHRIKE_BAY_LOCAL),"shrike_socket_pin1_local_mm":SHRIKE_SOCKET_PINS_LOCAL,"shrike_native_pcb_transform":shrike_native_transform,"shrike_vendor_step_transform":shrike_transform,"pi_step_transform":pi_transform,"shrike_vendor_bbox_world_mm":[vendor_shrike_box.xmin,vendor_shrike_box.ymin,vendor_shrike_box.zmin,vendor_shrike_box.xmax,vendor_shrike_box.ymax,vendor_shrike_box.zmax],"source_shrike_component_y_overhang_mm":round(shrike_transform["source_full_bbox_mm"][4]-shrike_transform["source_full_bbox_mm"][1]-(SHRIKE_BAY_LOCAL[3]-SHRIKE_BAY_LOCAL[1]),4),"collisions":collisions,"unexpected_intersections":unexpected,"printable_solid_counts":counts}
    checks["carrier_tail_drill_count"]=len(tail_solids)
    checks["shrike_component_reserve_world_bbox_mm"]=[shrike_component_box.xmin,shrike_component_box.ymin,shrike_component_box.zmin,shrike_component_box.xmax,shrike_component_box.ymax,shrike_component_box.zmax]
    checks["shrike_usb_wire_reserve_world_bbox_mm"]=[shrike_usb_box.xmin,shrike_usb_box.ymin,shrike_usb_box.zmin,shrike_usb_box.xmax,shrike_usb_box.ymax,shrike_usb_box.zmax]
    checks["passed"]=not unexpected and all(n==1 for name,n in counts.items() if name not in {"tray_posts","carrier_posts"}) and counts["tray_posts"]==4 and counts["carrier_posts"]==4 and all(abs(z-P["ground_z"])<.01 for z in wheel_low+[caster_low])
    report={"design":"Axiom Rover Rev B","units":"mm","revision":"hardware/shrike-pi5-revb","source_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),"status":"CAD VALIDATED — vendor dimensions and explicit unqualified reserves are not physical-fit validation","parameters":P,"classification":{"printable":list(printable),"vendor_reference_unmeasured":["left_wheel_VENDOR_REFERENCE","right_wheel_VENDOR_REFERENCE","left_motor_VENDOR_REFERENCE","right_motor_VENDOR_REFERENCE"],"contract_reference":["carrier_pcb_CONTRACT_REFERENCE","pi5_DRAWING_REFERENCE","pi5_actualCAD_REFERENCE","pi_socket_ESQ_REFERENCE","shrike_pcbCAD_REFERENCE","shrike_left_socket_REFERENCE","shrike_right_socket_REFERENCE","carrier_tails_CLEARANCE_REFERENCE"],"unmeasured_shrike_header":["shrike_male_plastic_UNMEASURED","shrike_male_pins_UNMEASURED"],"unmeasured_shrike_component_reserves":["shrike_component_UNMEASURED_ENVELOPE","shrike_usb_wire_UNMEASURED_ENVELOPE"],"vendor_step_mismatch_reference":"Shrike-lite.step (reported only; excluded from assembly)","unqualified_envelopes":["motor_pack_UNQUALIFIED_ENVELOPE","base5v_pack_UNQUALIFIED_ENVELOPE","host_pack_UNQUALIFIED_ENVELOPE","caster_UNQUALIFIED_ENVELOPE"],"datums_and_service":["pi5_after_carrier_removal_service_SWEEP","shrike_socket_pin1_local_mm"]},"checks":checks}
    (output/"mechanical_checks.json").write_text(json.dumps(report,indent=2)+"\n")
    if not checks["passed"]: raise RuntimeError("mechanical clearance failure: "+str(checks))
if __name__=="__main__":
    a=argparse.ArgumentParser(); a.add_argument("--output",type=Path,required=True); main(a.parse_args().output)
