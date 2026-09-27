#!/usr/bin/env python3
"""Check the public Vercel bundle without a browser or network access."""
import ast
import base64
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import subprocess
import tempfile
from urllib.parse import urljoin, urlsplit

root = Path(__file__).resolve().parents[1]
static = root / '.vercel/output/static'
builder = root / 'tools/build-viewer-site.py'
tree = ast.parse(builder.read_text())
files = ast.literal_eval(next(node.value for node in tree.body if isinstance(node, ast.Assign)
                              and any(isinstance(target, ast.Name) and target.id == 'files' for target in node.targets)))
for name in files:
    if name != 'viewer/index.html':
        assert (static / name).read_bytes() == (root / name).read_bytes(), 'Bundle is stale: ' + name
config = json.loads((static.parent / 'config.json').read_text())
assert config['version'] == 3
routes = config['routes']
headers = routes[0]['headers']
assert routes[0]['continue'] and all(re.fullmatch(routes[0]['src'], path) for path in ('/', '/viewer/', '/viewer/project.html'))
assert headers['X-Content-Type-Options'] == 'nosniff'
assert headers['Cache-Control'] == 'public, max-age=0, must-revalidate'
for path, target in (('/', '/index.html'), ('/viewer', '/viewer/index.html'), ('/viewer/', '/viewer/index.html')):
    assert any(route.get('dest') == target and re.fullmatch(route['src'], path) for route in routes[1:]), path

index = (static / 'index.html').read_text()
assert index == (static / 'viewer/index.html').read_text()
importmap = re.search(r'<script type="importmap">(.*?)</script>', index, re.S)
assert importmap
digest = base64.b64encode(hashlib.sha256(importmap[1].encode()).digest()).decode()
assert "'sha256-" + digest + "'" in headers['Content-Security-Policy']
assert (static / 'viewer/meshes.json.gz').is_file()

class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.base = None
        self.refs = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'base':
            self.base = attrs.get('href')
        for key in ('href', 'src'):
            if attrs.get(key):
                self.refs.append(attrs[key])

for html in static.rglob('*.html'):
    parser = Links()
    parser.feed(html.read_text())
    page = 'https://axiom-rover.local/' + html.relative_to(static).as_posix()
    base = urljoin(page, parser.base) if parser.base else page
    for ref in parser.refs:
        url = urlsplit(urljoin(base, ref))
        if url.netloc != 'axiom-rover.local':
            continue
        path = url.path.lstrip('/')
        if not path or path.endswith('/'):
            path += 'index.html'
        assert (static / path).is_file(), f'{html.relative_to(static)}: missing {ref} ({path})'

# A pointer must stop the builder before it removes a previous upload bundle.
with tempfile.TemporaryDirectory() as temp:
    test_root = Path(temp)
    script = test_root / 'tools/build-viewer-site.py'
    script.parent.mkdir(parents=True)
    script.write_bytes(builder.read_bytes())
    for name in [*files, 'viewer/meshes.json']:
        asset = test_root / name
        asset.parent.mkdir(parents=True, exist_ok=True)
        asset.write_bytes(b'asset')
    (test_root / 'viewer/meshes.json').write_text('version https://git-lfs.github.com/spec/v1\n')
    marker = test_root / '.vercel/output/keep'
    marker.parent.mkdir(parents=True)
    marker.write_text('prior bundle')
    result = subprocess.run(['python3', str(script)], capture_output=True, text=True)
    assert result.returncode and 'Git LFS asset is a pointer' in result.stderr
    assert marker.read_text() == 'prior bundle'

print('Viewer site bundle, links, routes, headers, and LFS preflight: OK')
