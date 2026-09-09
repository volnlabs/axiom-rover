#!/usr/bin/env python3
"""Reject stale CAD reports, failed checks and incorrectly totaled procurement CSV."""
import csv, hashlib, json
from decimal import Decimal
from pathlib import Path
root=Path(__file__).resolve().parents[1]
v=json.loads((root/'electronics/out/verification.json').read_text())
for name,expected in v['sources_sha256'].items():
    assert hashlib.sha256((root/name).read_bytes()).hexdigest()==expected, f'Stale electrical verification: {name}'
erc=json.loads((root/'electronics/out/erc.json').read_text())
assert not any(s['violations'] for s in erc['sheets']), 'ERC violations'
drc=json.loads((root/'electronics/out/drc.json').read_text())
assert not any(drc[k] for k in ['violations','unconnected_items','schematic_parity']), 'DRC / connectivity / parity failure'
mechanical=json.loads((root/'mechanical/out/mechanical_checks.json').read_text())
assert mechanical['checks']['passed'], 'Mechanical geometry checks failed'
assert hashlib.sha256((root/'mechanical/axiom_rover.py').read_bytes()).hexdigest()==mechanical['source_sha256'], 'Stale mechanical verification'
with (root/'bom/system-bom.csv').open(newline='') as f: rows=list(csv.DictReader(f))
items=[r for r in rows if r['line']!='TOTAL']; total=next(r for r in rows if r['line']=='TOTAL')
for side in ['low','high']:
    for r in items:
        assert Decimal(r['quantity'])*Decimal(r['unit_cost_inr_'+side])==Decimal(r['extended_inr_'+side]), f'BOM line {r["line"]}'
    amount=sum(Decimal(r['extended_inr_'+side]) for r in items)
    assert amount==Decimal(total['extended_inr_'+side]), f'Incorrect BOM {side} total: {amount}'
print('Artifact checks passed: electrical source hashes, ERC, DRC/parity, mechanical checks and BOM arithmetic.')
g=json.loads((root/'release-gates.json').read_text())
print(f'Fabrication released: {g["fabrication_released"]}; physical tests run: {g["physical_tests_run"]}')
