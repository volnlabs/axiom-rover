#!/usr/bin/env python3
"""Attach local STEP models and export actual pad coordinates with KiCad Python."""
import hashlib, json, urllib.request
from pathlib import Path
import pcbnew as k

root=Path(__file__).resolve().parents[1]; e=root/'electronics'; models=e/'models'
models.mkdir(exist_ok=True); b=k.LoadBoard(str(e/'carrier.kicad_pcb'))
sources=[]; layout=[]; pads={}
for fp in b.GetFootprints():
    ref=fp.GetReference(); package=str(fp.GetFPID().GetLibItemName())
    layout.append({'ref':ref,'value':fp.GetValue(),'package':package,'x':k.ToMM(fp.GetPosition().x),'y':-k.ToMM(fp.GetPosition().y)})
    pads[ref]={'side':fp.GetLayerName(),'x':k.ToMM(fp.GetPosition().x),'y':k.ToMM(fp.GetPosition().y),'angle':fp.GetOrientationDegrees(),'pins':{p.GetNumber():{'x':k.ToMM(p.GetPosition().x),'y':k.ToMM(p.GetPosition().y),'net':p.GetNetname().removeprefix('/'),'drill':k.ToMM(p.GetDrillSize().x),'thermal_relief':p.GetLocalZoneConnection()==k.ZONE_CONNECTION_THERMAL} for p in fp.Pads() if p.GetNumber()}}
    if ref=='U3':
        pads[ref]['thermal_vias']=[{'x':k.ToMM(p.GetPosition().x),'y':k.ToMM(p.GetPosition().y),'net':p.GetNetname().removeprefix('/'),'drill':k.ToMM(p.GetDrillSize().x)} for p in fp.Pads() if p.GetNumber()=='17' and p.GetDrillSize().x>0]
    if ref.startswith('H'): pads[ref]['hole_drill']=k.ToMM(next(iter(fp.Pads())).GetDrillSize().x)
    if ref in ('J1','J2','J4'):
        model=k.FP_3DMODEL(); model.m_Filename='${KIPRJMOD}/models/'+package+'.step'; fp.Models().clear(); fp.Models().push_back(model)
        if ref=='J2' and (root/'mechanical/out/shrike-module.step').exists():
            module=k.FP_3DMODEL();module.m_Filename='${KIPRJMOD}/../mechanical/out/shrike-module.step';module.m_Offset.z=11.05;fp.Models().push_back(module)
    else:
        for index,model in enumerate(fp.Models()):
            path=model.m_Filename.split('}/')[-1].replace('.wrl','.step')
            if path.startswith('models/'): path=path.removeprefix('models/')
            path=path.replace('HTSSOP-16-1EP_4.4x5mm_P0.65mm_EP3.4x5mm_Mask2.46x2.31mm.step','TSSOP-16-1EP_4.4x5mm_Pitch0.65mm_EP3.4x5mm.step')
            dest=models/path; dest.parent.mkdir(parents=True,exist_ok=True)
            url='https://raw.githubusercontent.com/KiCad/kicad-packages3D/master/'+path
            if not dest.exists():
                print('Downloading '+path,flush=True)
                cached=Path('/tmp/rover-models')/path
                dest.write_bytes(cached.read_bytes() if cached.exists() else urllib.request.urlopen(url,timeout=45).read())
            sources.append({'path':str(dest.relative_to(root)),'url':'https://www.jst-mfg.com/product/pdf/eng/eVH.pdf' if 'JST_VH_' in path else url,'geometry':'nominal drawing envelope' if 'JST_VH_' in path else 'KiCad library package reference','sha256':hashlib.sha256(dest.read_bytes()).hexdigest()})
            model.m_Filename='${KIPRJMOD}/models/'+path
            fp.Models()[index]=model
    if fp.Models(): layout[-1]['package']=Path(fp.Models()[0].m_Filename).stem
    # Preserve bottom-side custom footprint coordinates when updating model paths.
    local=e/'Rover.pretty'/(package+'.kicad_mod')
    s=local.read_text().replace('${KICAD10_3DMODEL_DIR}/','${KIPRJMOD}/models/')
    s=s.replace('HTSSOP-16-1EP_4.4x5mm_P0.65mm_EP3.4x5mm_Mask2.46x2.31mm.step','TSSOP-16-1EP_4.4x5mm_Pitch0.65mm_EP3.4x5mm.step')
    if ref in ('J1','J2','J4') and '(model ' not in s:
        s=s.rstrip()[:-1]+f'(model "${{KIPRJMOD}}/models/{package}.step" (offset (xyz 0 0 0)) (scale (xyz 1 1 1)) (rotate (xyz 0 0 0))))\n'
    local.write_text(s)
k.SaveBoard(str(e/'carrier.kicad_pcb'),b)
(root/'viewer/model-sources.json').write_text(json.dumps(list({x['path']:x for x in sources}.values()),indent=2)+'\n')
(root/'viewer/pcb-layout.json').write_text(json.dumps(layout,indent=2)+'\n')
def xy(p): return [round(k.ToMM(p.x),6),round(k.ToMM(p.y),6)]
tracks=[{'net':t.GetNetname().removeprefix('/'),'start':xy(t.GetStart()),'end':xy(t.GetEnd()),'width':k.ToMM(t.GetWidth()),'layer':t.GetLayerName()} for t in b.GetTracks() if not isinstance(t,k.PCB_VIA)]
edges=[{'shape':s.GetShapeStr(),'start':xy(s.GetStart()),'end':xy(s.GetEnd()),**({'mid':xy(s.GetArcMid())} if s.GetShape()==k.SHAPE_T_ARC else {})} for s in b.GetDrawings() if s.GetLayer()==k.Edge_Cuts]
(e/'out/pad-geometry.json').write_text(json.dumps({'board_sha256':hashlib.sha256((e/'carrier.kicad_pcb').read_bytes()).hexdigest(),'footprints':pads,'tracks':tracks,'edges':edges},indent=2)+'\n')
print(f'Attached local STEP models; exported {len(pads)} footprint pad maps.')
