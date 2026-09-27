#!/usr/bin/env python3
"""Run the local viewer's inspection checks in installed Chromium."""
import argparse, functools, hashlib, html, http.server, json, re, subprocess, tempfile, threading
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

root=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--site-root',type=Path,default=root)
parser.add_argument('--report-dir',type=Path,default=root/'viewer')
parser.add_argument('--url',help='Check a deployed URL; source hashes still refer to --site-root')
args=parser.parse_args()
site=args.site_root.resolve(); reports=args.report_dir.resolve(); reports.mkdir(parents=True,exist_ok=True)
class Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self,*args): pass

with http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Handler,directory=str(site))) as server, tempfile.TemporaryDirectory(prefix='rover-browser-') as profile:
    threading.Thread(target=server.serve_forever,daemon=True).start()
    parts=urlsplit(args.url or f'http://127.0.0.1:{server.server_port}/viewer/')
    query=[(k,v) for k,v in parse_qsl(parts.query,keep_blank_values=True) if k!='test']
    url=urlunsplit(parts._replace(query=urlencode(query+[('test','1')])))
    result=subprocess.run(['chromium','--headless','--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--disable-gpu-sandbox','--user-data-dir='+profile,'--window-size=1500,1000','--virtual-time-budget=25000','--dump-dom','--screenshot='+str(reports/'inspection.png'),url],capture_output=True,text=True,timeout=90)
    server.shutdown()
    (reports/'browser-check.log').write_text(result.stderr)
    assert result.returncode==0, 'Chromium failed; see viewer/browser-check.log'
    match=re.search(r'data-tests="([^"]+)"',result.stdout)
    assert match, 'Viewer self-test did not finish: '+str(re.findall(r'Could not[^<]+',result.stdout))
    checks=json.loads(html.unescape(match.group(1)))
    assert len(checks)>=42 and {'hide Shrike with components','exploded carrier above Pi'}<=set(checks)
    mesh=site/'viewer/meshes.json'
    if not mesh.exists(): mesh=site/'viewer/meshes.json.gz'
    report={'browser':subprocess.check_output(['chromium','--version'],text=True).strip(),'passed':True,'checks':checks,'sources_sha256':{str(p.relative_to(site)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [site/'viewer/app.js',site/'viewer/index.html',site/'viewer/styles.css',mesh]}}
    if args.url: report['url']=url
    (reports/'browser-check.json').write_text(json.dumps(report,indent=2)+'\n')
    print(f'Viewer: {len(checks)} checks passed, including all sides, zoom and component controls.')
