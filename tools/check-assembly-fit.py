#!/usr/bin/env python3
"""Bounded populated-carrier STEP checks against the mechanical assembly."""
import hashlib, importlib.util, json
from pathlib import Path
from cadquery import importers

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("rover",ROOT/"mechanical/axiom_rover.py")
rover=importlib.util.module_from_spec(spec); spec.loader.exec_module(rover)
source=ROOT/"viewer/carrier-populated.step"
carrier=importers.importStep(str(source)).translate((-80.,50.,107.1))

def overlaps(a,b):
    return a.xmin<b.xmax and a.xmax>b.xmin and a.ymin<b.ymax and a.ymax>b.ymin and a.zmin<b.zmax and a.zmax>b.zmin

def check(name,target):
    target_shape=target.val(); tb=target_shape.BoundingBox(); support=[]; unexpected=[]; candidates=0
    for solid in carrier.val().Solids():
        if not overlaps(solid.BoundingBox(),tb): continue
        candidates+=1; volume=solid.intersect(target_shape).Volume()
        if volume>.01:
            hit=round(volume,6)
            # The frame is meant to contact the carrier underside/copper stack; below that is a component or tail conflict.
            (support if name=="carrier_frame" and solid.BoundingBox().zmin>=107.0 else unexpected).append(hit)
    return {"part":name,"candidate_solids":candidates,"intended_pcb_support_contact_volume_mm3":round(sum(support),6),"unexpected_intersection_volume_mm3":round(sum(unexpected),6),"intersecting_solids":len(support)+len(unexpected)}

targets={"carrier_frame":rover.carrier_frame(),"carrier_posts":rover.carrier_posts(),"vented_shell":rover.vented_shell()}
results=[check(name,target) for name,target in targets.items()]
b=carrier.val().BoundingBox()
out={"status":"CAD INTERSECTION CHECK — not physical-fit validation","carrier_source":"viewer/carrier-populated.step","carrier_source_sha256":hashlib.sha256(source.read_bytes()).hexdigest(),"mechanical_source_sha256":hashlib.sha256((ROOT/"mechanical/axiom_rover.py").read_bytes()).hexdigest(),"world_transform_mm":[-80.,50.,107.1],"carrier_world_bbox_mm":[b.xmin,b.ymin,b.zmin,b.xmax,b.ymax,b.zmax],"checks":results,"unexpected_intersections":[r for r in results if r["unexpected_intersection_volume_mm3"]>.01]}
out["checker_sha256"]=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
out["passed"]=not out["unexpected_intersections"]
(ROOT/"mechanical/out/assembly-fit.json").write_text(json.dumps(out,indent=2)+"\n")
print(json.dumps(out,indent=2))

assert out["passed"], "Populated carrier collides with mechanical parts"
