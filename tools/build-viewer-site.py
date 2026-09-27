#!/usr/bin/env python3
"""Package only the public CAD viewer using Vercel's static Build Output API."""
import base64
import gzip
import hashlib
import json
import re
import shutil
from pathlib import Path

root = Path(__file__).resolve().parents[1]
output = root / '.vercel/output'
static = output / 'static'
# A fixed allowlist prevents uploading the repository, tooling or credentials.
files = [
    'viewer/index.html', 'viewer/app.js', 'viewer/styles.css',
    'viewer/project.html', 'viewer/credits.html', 'viewer/favicon.svg',
    'viewer/rover-preview.png',
    'viewer/carrier-populated.step', 'viewer/model-sources.json', 'viewer/model-licenses.txt',
    'viewer/vendor/three.module.js', 'viewer/vendor/three.core.js',
    'viewer/vendor/OrbitControls.js', 'viewer/vendor/LICENSE',
    'electronics/out/carrier-top.svg', 'electronics/out/carrier-bottom.svg',
    'electronics/out/schematic/carrier.svg', 'electronics/Rover.pretty/LICENSE.md',
    'reference/shrike-r04/LICENSE_HW.md', 'reference/shrike-r04/Shrike-lite.kicad_pcb',
    'reference/raspberry-pi-5/LICENSE.txt',
    'release-gates.json', 'bom/system-bom.csv', 'docs/harness.svg',
    'docs/electrical-contract.md', 'docs/commissioning.md', 'docs/mechanical.md',
    'docs/bench.md', 'docs/build.md',
]
for name in [*files, 'viewer/meshes.json']:
    source = root / name
    if not source.is_file() or source.is_symlink():
        raise SystemExit('Missing or symlinked viewer asset: ' + name)
    with source.open('rb') as asset:
        if asset.read(64).startswith(b'version https://git-lfs.github.com/spec/v1'):
            raise SystemExit('Git LFS asset is a pointer; fetch it before building: ' + name)
raw = (root / 'viewer/meshes.json').read_bytes()
compressed = gzip.compress(raw, compresslevel=9, mtime=0)
assert gzip.decompress(compressed) == raw, 'Geometry compression changed source bytes'
index = (root / 'viewer/index.html').read_text()
assert index.count('<html lang="en"') == 1 and index.count('<head>') == 1
importmaps = re.findall(r'<script type="importmap">(.*?)</script>', index, re.S)
assert len(importmaps) == 1, 'Expected one inline import map for the CSP hash'
importmap_hash = base64.b64encode(hashlib.sha256(importmaps[0].encode()).digest()).decode()
if output.exists():
    shutil.rmtree(output)
for name in files:
    target = static / name
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(root / name, target)
index = index.replace('<html lang="en"', '<html lang="en" data-mesh-source="./meshes.json.gz"')
index = index.replace('<head>', '<head><base href="/viewer/">')
(static / 'viewer/index.html').write_text(index)
(static / 'index.html').write_text(index)
(static / 'viewer/meshes.json.gz').write_bytes(compressed)
config = {
    'version': 3,
    'routes': [
        {'src': '^/.*$', 'headers': {
            'Cache-Control': 'public, max-age=0, must-revalidate',
            'X-Content-Type-Options': 'nosniff',
            'Referrer-Policy': 'strict-origin-when-cross-origin',
            'X-Frame-Options': 'DENY',
            'Content-Security-Policy': (
                "default-src 'self'; script-src 'self' 'sha256-" + importmap_hash +
                "'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; "
                "connect-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'none'"
            ),
        }, 'continue': True},
        {'src': '^/$', 'dest': '/index.html'},
        {'src': '^/viewer/?$', 'dest': '/viewer/index.html'},
    ],
}
(output / 'config.json').write_text(json.dumps(config, indent=2) + '\n')
assert {str(p.relative_to(static)) for p in static.rglob('*') if p.is_file()} == set(files) | {'index.html', 'viewer/meshes.json.gz'}
total = sum(p.stat().st_size for p in output.rglob('*') if p.is_file())
assert total < 100_000_000, 'Static bundle exceeds the conservative 100 MB upload budget'
print(json.dumps({'output': str(output), 'bytes': total, 'mesh_bytes': len(raw),
                  'mesh_gzip_bytes': len(compressed),
                  'mesh_sha256': hashlib.sha256(raw).hexdigest()}, indent=2))
