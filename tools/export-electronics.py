#!/usr/bin/env python3
"""Run native CAD checks before exporting review files; never authorizes fabrication."""
import argparse, hashlib, json, subprocess, zipfile
from pathlib import Path
root=Path(__file__).resolve().parents[1]
a=argparse.ArgumentParser(); a.add_argument('--kicad',default='kicad-cli'); args=a.parse_args()
cmd=[args.kicad]+(['kicad-cli'] if args.kicad.endswith('.AppImage') else [])
e=root/'electronics'; out=e/'out'; out.mkdir(exist_ok=True)

def run(name,*argv):
    result=subprocess.run(cmd+list(map(str,argv)),capture_output=True,text=True)
    (out/(name+'.log')).write_text(result.stdout+result.stderr)
    if result.returncode: raise SystemExit(f'{name} failed ({result.returncode}); see electronics/out/{name}.log')
    print(name+' passed')

run('erc','sch','erc','--format','json','--exit-code-violations','-o',out/'erc.json',e/'carrier.kicad_sch')
run('drc','pcb','drc','--format','json','--schematic-parity','--exit-code-violations','-o',out/'drc.json',e/'carrier.kicad_pcb')
run('schematic','sch','export','svg','-o',out/'schematic',e/'carrier.kicad_sch')
run('netlist','sch','export','netlist','--format','kicadxml','-o',out/'carrier.xml',e/'carrier.kicad_sch')
for side,layers in [('top','F.Cu,F.SilkS,Edge.Cuts'),('bottom','B.Cu,B.SilkS,Edge.Cuts'),('assembly','F.Fab,Edge.Cuts')]:
    run(side,'pcb','export','svg','--mode-single','--page-size-mode','2','--exclude-drawing-sheet','--layers',layers,'-o',out/('carrier-'+side+'.svg'),e/'carrier.kicad_pcb')
run('gerbers','pcb','export','gerbers','--layers','F.Cu,B.Cu,F.Mask,B.Mask,F.SilkS,B.SilkS,F.Paste,Edge.Cuts','-o',out/'fabrication-review',e/'carrier.kicad_pcb')
run('drill','pcb','export','drill','--excellon-separate-th','--generate-map','--map-format','svg','-o',out/'fabrication-review',e/'carrier.kicad_pcb')
run('positions','pcb','export','pos','--format','csv','--units','mm','--smd-only','-o',out/'smt-positions.csv',e/'carrier.kicad_pcb')
run('board-step','pcb','export','step','--board-only','--force','-o',out/'carrier-bare-board.step',e/'carrier.kicad_pcb')
run('populated-step','pcb','export','step','--force','--include-pads','--include-tracks','-o',root/'viewer/carrier-populated.step',e/'carrier.kicad_pcb')
sources=[root/'tools/export-electronics.py',root/'mechanical/out/shrike-module.step',e/'generate.py',root/'tools/prepare-pcb-models.py',e/'carrier.kicad_sch',e/'carrier.kicad_pcb',e/'carrier.kicad_pro',e/'Rover.kicad_sym',e/'sym-lib-table',e/'fp-lib-table',e/'out/net-contract.json',e/'out/pad-geometry.json',*sorted((e/'Rover.pretty').glob('*.kicad_mod')),*sorted((e/'models').rglob('*.step'))]
manifest={"kicad_version":subprocess.check_output(cmd+['version'],text=True).strip(),"sources_sha256":{str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},"erc_violations":0,"drc_violations":0,"unconnected":0,"schematic_parity_issues":0,"fabrication_released":False}
manifest['artifacts_sha256']={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [root/'viewer/carrier-populated.step',out/'carrier-bare-board.step',out/'erc.json',out/'drc.json']}
(out/'verification.json').write_text(json.dumps(manifest,indent=2)+'\n')
notice='DESIGN REVIEW ONLY — not released for fabrication. Read docs/commissioning.md and release-gates.json. Exact vendor order codes, power ratings and physical fit remain unqualified.\n'
(out/'fabrication-review/README.txt').write_text(notice)
with zipfile.ZipFile(out/'carrier-fabrication-review.zip','w',zipfile.ZIP_DEFLATED) as archive:
    for p in sorted((out/'fabrication-review').iterdir()): archive.write(p,'fabrication-review/'+p.name)
    for name in ['assembly-bom.csv','smt-positions.csv','carrier-assembly.svg']: archive.write(out/name,name)
print('Review exports complete; physical commissioning is still required.')
