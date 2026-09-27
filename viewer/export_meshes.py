#!/usr/bin/env python3
"""Tessellate the saved STEP assemblies for inspection, without changing CAD."""
import argparse, hashlib, json, re
from pathlib import Path
import cadquery as cq
p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--output',type=Path,default=Path(__file__).resolve().parent);p.add_argument('--socket-models-only',action='store_true');args=p.parse_args()
if args.socket_models_only:
 out=args.repo/'electronics/models';out.mkdir(exist_ok=True)
 for name,length,width,height,cx,cy,pins,tail in [
  ('SSW-119-01-G-S',48.77,2.41,8.51,0,-22.86,[(0,-i*2.54) for i in range(19)],2.64),
  ('Pi5_Socket_2x20',51.31,4.95,13.59,32.5,3.5,[(8.37+i*2.54,y) for i in range(20) for y in (2.23,4.77)],2.64)]:
  # Bottom-side ESQ model uses +Y; KiCad rotates it 180 degrees about X.
  body=cq.Workplane('XY').box(width if name.startswith('SSW') else length,length if name.startswith('SSW') else width,height,centered=(True,True,False)).translate((cx,cy,0))
  for x,y in pins: body=body.cut(cq.Workplane('XY').center(x,y).rect(.75,.75).extrude(height))
  a=cq.Assembly();a.add(body,name='nominal_socket_body',color=cq.Color(.15,.15,.17))
  for i,(x,y) in enumerate(pins): a.add(cq.Workplane('XY').center(x,y).rect(.64,.64).extrude(-tail),name=f'tail_{i+1}',color=cq.Color(.7,.65,.4))
  a.save(str(out/(name+'.step')))
 # Nominal B2P-VH body/pins from the JST drawing; the latch is only an envelope.
 vh=out/'Connector_JST.3dshapes';vh.mkdir(exist_ok=True)
 a=cq.Assembly();a.add(cq.Workplane('XY').box(7.86,6.8,2,centered=(True,True,False)).translate((1.98,-1.4,0)).union(cq.Workplane('XY').box(5.46,1.7,9.4,centered=(True,True,False)).translate((1.98,2.85,0))),name='nominal_VH_body',color=cq.Color(.9,.9,.85))
 for i in range(2):a.add(cq.Workplane('XY').center(i*3.96,0).rect(1.14,1.14).extrude(14.6).translate((0,0,-3.7)),name=f'pin_{i+1}',color=cq.Color(.7,.7,.7))
 a.save(str(vh/'JST_VH_B2P-VH_1x02_P3.96mm_Vertical.step'))
 print('Nominal Samtec socket models generated; mating tolerances require physical fit.');raise SystemExit
# CadQuery 2.6 rejects repeated KiCad package instance names; suffix import labels only.
original_add=cq.Assembly.add
def unique_add(self,arg,**kw):
 name=kw.get('name')
 if name in self.objects:
  i=2
  while f'{name}__{i}' in self.objects:i+=1
  kw['name']=f'{name}__{i}'
 return original_add(self,arg,**kw)
cq.Assembly.add=unique_add
colors={'base_chassis':'#46555f','vented_shell':'#536875','tray':'#ed742c','tray_posts':'#aeb7bd','test_stand':'#8c969e','sensor_bracket':'#ed742c','caster_fixture':'#ed742c','shrike_module_plate':'#ed742c'}
layout=json.loads((args.output/'pcb-layout.json').read_text())
result={'units':'mm','sources':{},'rover':[],'pcb':[]}
for source in [Path(__file__).resolve(),args.output/'pcb-layout.json']:
 result['sources'][source.name]={'file':str(source.relative_to(args.repo)),'sha256':hashlib.sha256(source.read_bytes()).hexdigest()}
for kind,path in [('rover',args.repo/'mechanical/out/axiom_rover_assembly.step'),('pcb',args.output/'carrier-populated.step')]:
 result['sources'][kind]={'file':str(path.relative_to(args.repo)),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
 groups={};seen=set()
 for shape,name,loc,color in cq.Assembly.load(str(path)):
  full_name=name;name=name.split('/')[-1];shape=shape.moved(loc)
  if kind=='rover':
   col=colors.get(name,'#e78437' if 'bracket' in name else '#7696b2' if 'pack' in name else '#334b39' if 'pi5' in name or 'pcb_' in name else '#32383c' if 'wheel' in name else '#bea35e')
  else:
   segments={re.sub(r'(__|_)\d+$','',n) for n in full_name.split('/')}; b=shape.BoundingBox()
   candidates=[f for f in layout if f['package'] in segments]
   if candidates:
    f=min(candidates,key=lambda f:(f['x']-(b.xmin+b.xmax)/2)**2+(f['y']-(b.ymin+b.ymax)/2)**2)
    name=f['ref']+' — '+f['value'];seen.add(f['ref']);col='#242830' if f['ref'] in ('J1','J2','J4') else '#e9e5d9' if f['ref'].startswith('J') else '#bc935c' if f['ref'].startswith('C') else '#303338'
   elif 'shrike-module' in full_name:name='Shrike R0.4 — PCB-derived reference';col='#236d47'
   elif abs(b.xlen-160)<.1 and abs(b.ylen-100)<.1:name='PCB substrate';col='#256844'
   else:name='Copper';col='#bca469'
  groups.setdefault(name,{'color':col,'shapes':[]})['shapes'].append(shape)
 if kind=='pcb':
  # Mounting holes, probe pads and fiducials are board geometry, not fitted parts.
  expected={f['ref'] for f in layout if not f['ref'].startswith(('H','TP','FID'))}
  assert expected<=seen, ('Missing 3D component models',expected-seen)
 for name,g in groups.items():
  shape=cq.Compound.makeCompound(g['shapes']);vs,ts=shape.tessellate(.18,.25)
  positions=[round(c,5) for v in vs for c in v.toTuple()];indices=[i for t in ts for i in t]
  assert positions and len(positions)%3==0 and indices and max(indices)<len(vs)
  result[kind].append({'name':name,'color':g['color'],'positions':positions,'indices':indices})
assert len(result['rover'])>=24 and len(result['pcb'])>=42
args.output.mkdir(exist_ok=True);(args.output/'meshes.json').write_text(json.dumps(result,separators=(',',':')))
print({k:len(result[k]) for k in ['rover','pcb']})
