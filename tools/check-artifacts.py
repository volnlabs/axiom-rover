#!/usr/bin/env python3
"""Reject stale CAD reports, failed checks and incorrectly totaled procurement CSV."""
import csv, hashlib, json, subprocess, sys
from decimal import Decimal
from pathlib import Path
root=Path(__file__).resolve().parents[1]
reference=json.loads((root/'reference/sources.json').read_text())
for name,data in reference['files'].items():
    assert hashlib.sha256((root/'reference'/name).read_bytes()).hexdigest()==data['sha256'], 'Reference source hash changed: '+name
v=json.loads((root/'electronics/out/verification.json').read_text())
for name,expected in (v['sources_sha256'] | v['artifacts_sha256']).items():
    assert hashlib.sha256((root/name).read_bytes()).hexdigest()==expected, f'Stale electrical verification: {name}'
erc=json.loads((root/'electronics/out/erc.json').read_text())
assert not any(s['violations'] for s in erc['sheets']), 'ERC violations'
drc=json.loads((root/'electronics/out/drc.json').read_text())
assert not any(drc[k] for k in ['violations','unconnected_items','schematic_parity']), 'DRC / connectivity / parity failure'
mechanical=json.loads((root/'mechanical/out/mechanical_checks.json').read_text())
assert mechanical['checks']['passed'], 'Mechanical geometry checks failed'
assert hashlib.sha256((root/'mechanical/axiom_rover.py').read_bytes()).hexdigest()==mechanical['source_sha256'], 'Stale mechanical verification'
fit=json.loads((root/'mechanical/out/assembly-fit.json').read_text())
assert fit['passed'], 'Populated PCB assembly collisions'
for name,key in [('viewer/carrier-populated.step','carrier_source_sha256'),('mechanical/axiom_rover.py','mechanical_source_sha256'),('tools/check-assembly-fit.py','checker_sha256')]:
    assert hashlib.sha256((root/name).read_bytes()).hexdigest()==fit[key], 'Stale assembly-fit report: '+name
subprocess.run([sys.executable,str(root/'tools/check-revb.py')],check=True)
meshes=json.loads((root/'viewer/meshes.json').read_text())
for data in meshes['sources'].values():
    assert hashlib.sha256((root/data['file']).read_bytes()).hexdigest()==data['sha256'], 'Stale viewer meshes: '+data['file']
browser=json.loads((root/'viewer/browser-check.json').read_text())
assert browser['passed'] and len(browser['checks'])>=34, 'Browser checks failed'
for name,expected in browser['sources_sha256'].items():
    assert hashlib.sha256((root/name).read_bytes()).hexdigest()==expected, 'Stale browser verification: '+name
with (root/'bom/system-bom.csv').open(newline='') as f: rows=list(csv.DictReader(f))
items=[r for r in rows if r['line']!='TOTAL']; total=next(r for r in rows if r['line']=='TOTAL')
for side in ['low','high']:
    for r in items:
        assert Decimal(r['quantity'])*Decimal(r['unit_cost_inr_'+side])==Decimal(r['extended_inr_'+side]), f'BOM line {r["line"]}'
    amount=sum(Decimal(r['extended_inr_'+side]) for r in items)
    assert amount==Decimal(total['extended_inr_'+side]), f'Incorrect BOM {side} total: {amount}'
print('Artifact checks passed: electrical source hashes, ERC, DRC/parity, mechanical/assembly fit, viewer controls and BOM arithmetic.')
g=json.loads((root/'release-gates.json').read_text())
print(f'Fabrication released: {g["fabrication_released"]}; physical tests run: {g["physical_tests_run"]}')
