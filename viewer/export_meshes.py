#!/usr/bin/env python3
"""Tessellate the saved STEP assemblies for inspection, without changing CAD."""
import argparse, hashlib, json
from pathlib import Path
import cadquery as cq
p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--output',type=Path,default=Path(__file__).resolve().parent);args=p.parse_args()
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
for kind,path in [('rover',args.repo/'mechanical/out/axiom_rover_assembly.step'),('pcb',args.output/'carrier-populated.step')]:
 result['sources'][kind]={'file':path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
 for shape,name,loc,color in cq.Assembly.load(str(path)):
  full_name=name;name=name.split('/')[-1];shape=shape.moved(loc); vs,ts=shape.tessellate(.18,.25)
  positions=[round(c,5) for v in vs for c in v.toTuple()]; indices=[i for t in ts for i in t]
  assert positions and len(positions)%3==0 and indices and max(indices)<len(vs)
  if kind=='rover':
   col=colors.get(name,'#e78437' if 'bracket' in name else '#7696b2' if 'pack' in name else '#334b39' if 'pi5' in name or 'pcb_' in name else '#32383c' if 'wheel' in name else '#bea35e')
  else:
   package=full_name.split('/')[-2].split('__')[0]; b=shape.BoundingBox()
   candidates=[f for f in layout if f['package']==package]
   if candidates:
    f=min(candidates,key=lambda f:(f['x']-(b.xmin+b.xmax)/2)**2+(f['y']-(b.ymin+b.ymax)/2)**2)
    name=f['ref']+' — '+f['value'];col='#e9e5d9' if f['ref'].startswith('J') else '#bc935c' if f['ref'].startswith('C') else '#303338'
   elif abs(b.xlen-120)<.1 and abs(b.ylen-80)<.1:name='PCB substrate';col='#256844'
   else:name='Copper '+str(len(result[kind]));col='#bca469' 
  result[kind].append({'name':name,'color':col,'positions':positions,'indices':indices})
assert len(result['rover'])>=24 and len(result['pcb'])>=18
args.output.mkdir(exist_ok=True);(args.output/'meshes.json').write_text(json.dumps(result,separators=(',',':')))
print({k:len(result[k]) for k in ['rover','pcb']})
