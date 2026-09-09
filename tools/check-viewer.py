#!/usr/bin/env python3
"""Run the local viewer's inspection checks in installed Chromium."""
import functools, hashlib, html, http.server, json, re, subprocess, tempfile, threading
from pathlib import Path

root=Path(__file__).resolve().parents[1]
class Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self,*args): pass

with http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Handler,directory=str(root))) as server, tempfile.TemporaryDirectory(prefix='rover-browser-') as profile:
    threading.Thread(target=server.serve_forever,daemon=True).start()
    result=subprocess.run(['chromium','--headless','--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--disable-gpu-sandbox','--user-data-dir='+profile,'--window-size=1500,1000','--virtual-time-budget=25000','--dump-dom','--screenshot='+str(root/'viewer/inspection.png'),f'http://127.0.0.1:{server.server_port}/viewer/?test=1'],capture_output=True,text=True,timeout=90)
    server.shutdown()
    (root/'viewer/browser-check.log').write_text(result.stderr)
    assert result.returncode==0, 'Chromium failed; see viewer/browser-check.log'
    match=re.search(r'data-tests="([^"]+)"',result.stdout)
    assert match, 'Viewer self-test did not finish: '+str(re.findall(r'Could not[^<]+',result.stdout))
    checks=json.loads(html.unescape(match.group(1)))
    assert len(checks)>=34 and {'hide Shrike with components','exploded carrier above Pi'}<=set(checks)
    report={'browser':subprocess.check_output(['chromium','--version'],text=True).strip(),'passed':True,'checks':checks,'sources_sha256':{str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [root/'viewer/app.js',root/'viewer/index.html',root/'viewer/meshes.json']}}
    (root/'viewer/browser-check.json').write_text(json.dumps(report,indent=2)+'\n')
    print(f'Viewer: {len(checks)} checks passed, including all sides, zoom and component controls.')
