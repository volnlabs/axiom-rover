#!/usr/bin/env python3
"""Package only the public CAD viewer using Vercel's static Build Output API."""
import gzip
import hashlib
import json
import shutil
from pathlib import Path

root = Path(__file__).resolve().parents[1]
output = root / '.vercel/output'
static = output / 'static'
# A fixed allowlist prevents uploading the repository, tooling or credentials.
files = [
    'viewer/index.html', 'viewer/app.js', 'viewer/credits.html',
    'viewer/carrier-populated.step', 'viewer/model-sources.json', 'viewer/model-licenses.txt',
    'viewer/vendor/three.module.js', 'viewer/vendor/three.core.js',
    'viewer/vendor/OrbitControls.js', 'viewer/vendor/LICENSE',
    'electronics/out/carrier-top.svg', 'electronics/out/carrier-bottom.svg',
    'electronics/out/schematic/carrier.svg', 'electronics/Rover.pretty/LICENSE.md',
    'reference/shrike-r04/LICENSE_HW.md', 'reference/shrike-r04/Shrike-lite.kicad_pcb',
    'reference/raspberry-pi-5/LICENSE.txt',
]
for name in files:
    if not (root / name).is_file():
        raise SystemExit('Missing viewer asset: ' + name)
raw = (root / 'viewer/meshes.json').read_bytes()
compressed = gzip.compress(raw, compresslevel=9, mtime=0)
assert gzip.decompress(compressed) == raw, 'Geometry compression changed source bytes'
if output.exists():
    shutil.rmtree(output)
for name in files:
    target = static / name
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(root / name, target)
index = (static / 'viewer/index.html').read_text()
assert index.count('<html lang="en"') == 1 and index.count('<head>') == 1
index = index.replace('<html lang="en"', '<html lang="en" data-mesh-source="./meshes.json.gz"')
index = index.replace('<head>', '<head><base href="/viewer/">')
(static / 'viewer/index.html').write_text(index)
(static / 'index.html').write_text(index)
(static / 'viewer/meshes.json.gz').write_bytes(compressed)
(output / 'config.json').write_text('{"version":3}\n')
assert {str(p.relative_to(static)) for p in static.rglob('*') if p.is_file()} == set(files) | {'index.html', 'viewer/meshes.json.gz'}
total = sum(p.stat().st_size for p in output.rglob('*') if p.is_file())
assert total < 100_000_000, 'Static bundle exceeds the conservative 100 MB upload budget'
print(json.dumps({'output': str(output), 'bytes': total, 'mesh_bytes': len(raw),
                  'mesh_gzip_bytes': len(compressed),
                  'mesh_sha256': hashlib.sha256(raw).hexdigest()}, indent=2))
