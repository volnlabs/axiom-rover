#!/usr/bin/env node
// Dependency-free browser checks: Node 22+ and installed Chromium.
import assert from 'node:assert/strict';
import {createServer} from 'node:http';
import {spawn} from 'node:child_process';
import {readFile, writeFile, mkdir, mkdtemp, rm} from 'node:fs/promises';
import {resolve, extname, sep} from 'node:path';
import {tmpdir} from 'node:os';
import {once} from 'node:events';

const root = resolve('.vercel/output/static'), reports = resolve('.cache/viewer-ui');
const config = JSON.parse(await readFile(resolve(root, '../config.json')));
for (const file of ['app.js','styles.css','project.html','credits.html']) {
  assert((await readFile(resolve(root,'viewer',file))).equals(await readFile(resolve('viewer',file))), 'Bundle is stale: '+file+'; rebuild before testing');
}
const headers = config.routes.find(route => route.headers).headers;
const profile = await mkdtemp(resolve(tmpdir(), 'rover-ui-'));
const checks = [], errors = [], requests = [];
let failMesh = false, failDrawing = false, browser, ws;
await mkdir(reports, {recursive:true});
const server = createServer(async (req,res) => {
  const pathname = new URL(req.url, 'http://localhost').pathname;
  requests.push(pathname);
  if ((failMesh && pathname.endsWith('.json.gz')) || (failDrawing && pathname.endsWith('.svg') && pathname.includes('/electronics/'))) {
    res.writeHead(503); res.end('Simulated unavailable asset'); return;
  }
  const route = config.routes.find(route => route.dest && new RegExp(route.src).test(pathname));
  let file = resolve(root, '.' + (route?.dest || pathname));
  if (file !== root && !file.startsWith(root+sep)) { res.writeHead(403); res.end(); return; }
  const types = {'.html':'text/html', '.js':'text/javascript', '.css':'text/css', '.svg':'image/svg+xml', '.json':'application/json', '.gz':'application/gzip', '.png':'image/png'};
  try {
    const body = await readFile(file);
    res.writeHead(200, {...headers, 'Content-Type':types[extname(file)] || 'application/octet-stream'});
    res.end(body);
  } catch { res.writeHead(404); res.end('Not found'); }
});
try {
  server.listen(0, '127.0.0.1'); await once(server, 'listening');
  const origin = `http://127.0.0.1:${server.address().port}`;
  browser = spawn('chromium', ['--headless','--no-sandbox','--disable-dev-shm-usage','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--disable-gpu-sandbox','--no-first-run','--remote-debugging-port=0',`--user-data-dir=${profile}`,'about:blank'], {stdio:['ignore','ignore','pipe']});
  const endpoint = await new Promise((ok,fail) => {
    const timer = setTimeout(() => fail(Error('Chromium did not start')), 15000);
    browser.once('error', fail);
    browser.stderr.on('data', data => { const match = String(data).match(/DevTools listening on (ws:\/\/[^\s]+)/); if(match){ clearTimeout(timer); ok(match[1]); } });
  });
  const tabs = await (await fetch(new URL('/json/list', endpoint.replace('ws:', 'http:')))).json();
  ws = new WebSocket(tabs.find(tab => tab.type === 'page').webSocketDebuggerUrl);
  await once(ws, 'open');
  let id = 0;
  const pending = new Map(), events = new Map();
  ws.addEventListener('message', ({data}) => {
    const message = JSON.parse(data);
    if (message.id) {
      const callback = pending.get(message.id); pending.delete(message.id);
      if (callback) { clearTimeout(callback.timer); message.error ? callback.reject(Error(message.error.message)) : callback.resolve(message.result); }
    } else {
      for (const callback of events.get(message.method) || []) callback(message.params);
      events.delete(message.method);
      if (message.method === 'Runtime.exceptionThrown') errors.push(message.params.exceptionDetails.text + ': ' + (message.params.exceptionDetails.exception?.description || ''));
      if (message.method === 'Log.entryAdded' && message.params.entry.level === 'error') errors.push(message.params.entry.text);
    }
  });
  const cdp = (method,params={}) => new Promise((resolve,reject) => {
    const n = ++id, timer = setTimeout(() => { pending.delete(n); reject(Error('CDP timeout: '+method)); }, 30000);
    pending.set(n,{resolve,reject,timer}); ws.send(JSON.stringify({id:n,method,params}));
  });
  const evaluate = async expression => {
    const result = await cdp('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});
    assert(!result.exceptionDetails, JSON.stringify(result.exceptionDetails));
    return result.result.value;
  };
  const waitFor = async expression => {
    const start = Date.now();
    while (Date.now()-start < 90000) { if (await evaluate(expression)) return; await new Promise(r => setTimeout(r,100)); }
    throw Error('Timed out: '+expression);
  };
  const navigate = async path => {
    const loaded = new Promise(ok => events.set('Page.loadEventFired',[ok]));
    await cdp('Page.navigate',{url:origin+path});
    await Promise.race([loaded,new Promise((_,fail) => { const timer=setTimeout(() => fail(Error('Page load timeout')),30000); timer.unref(); })]);
  };
  const check = async (name,expression) => { assert(await evaluate(expression),name); checks.push(name); };
  const click = selector => evaluate(`document.querySelector(${JSON.stringify(selector)}).click()`);
  const screenshot = async name => {
    await new Promise(r => setTimeout(r,150));
    const shot = await cdp('Page.captureScreenshot',{format:'png'});
    await writeFile(resolve(reports,name+'.png'),Buffer.from(shot.data,'base64'));
  };
  await cdp('Page.enable'); await cdp('Runtime.enable'); await cdp('Log.enable');
  await cdp('Emulation.setDeviceMetricsOverride',{width:1440,height:960,deviceScaleFactor:1,mobile:false});
  await navigate('/?test=1');
  await waitFor('Boolean(document.body.dataset.tests)');
  const internalChecks = JSON.parse(await evaluate('document.body.dataset.tests'));
  assert(internalChecks.length >= 42); checks.push(...internalChecks);
  await screenshot('desktop-rover');
  await check('sliders retain accessible labels','["opacity","explode"].every(id => document.getElementById(id).labels.length === 1)');
  await click('.viewport-help summary');
  await check('help expands without covering toolbar','document.querySelector(".viewport-help").open && document.querySelector("#hint").getBoundingClientRect().bottom <= document.querySelector(".zoom-controls").getBoundingClientRect().top');
  await click('.viewport-help summary');
  await evaluate('document.querySelector("#opacity").value="0.5"; document.querySelector("#opacity").dispatchEvent(new Event("input"))');
  await check('opacity readout updates','document.querySelector("#opacity-value").value === "50%"');
  await evaluate('document.querySelector("#opacity").value="1"; document.querySelector("#opacity").dispatchEvent(new Event("input"))');
  await evaluate('document.querySelector("#explode").value="0.5"; document.querySelector("#explode").dispatchEvent(new Event("input"))');
  await check('separation readout updates','document.querySelector("#explode-value").value === "50%"');
  await evaluate('document.querySelector("#explode").value="0"; document.querySelector("#explode").dispatchEvent(new Event("input"))');
  await click('#shell');
  await evaluate('document.querySelector("#status").hidden=true; document.querySelector(".viewport-tools").hidden=true');
  await new Promise(r => setTimeout(r,150));
  const clip = await evaluate('(()=>{const r=document.querySelector("#stage").getBoundingClientRect();return {x:r.x,y:r.y,width:r.width,height:r.height,scale:1};})()');
  const preview = await cdp('Page.captureScreenshot',{format:'png',clip});
  await writeFile(resolve(reports,'rover-preview.png'),Buffer.from(preview.data,'base64'));
  await evaluate('document.querySelector("#status").hidden=false; document.querySelector(".viewport-tools").hidden=false');
  await click('#shell');
  await check('desktop no horizontal overflow','document.documentElement.scrollWidth <= innerWidth');
  await click('[data-mode="pcb"]');
  await check('PCB mode changes URL','new URLSearchParams(location.search).get("mode")==="pcb"');
  await click('[data-drawing="top"]');
  await waitFor('!document.querySelector("#in").disabled');
  await check('top routing loaded','document.querySelector("#drawing img").naturalWidth > 0');
  await screenshot('desktop-routing');
  await click('#board3d'); await screenshot('desktop-pcb');
  await click('[data-mode="schematic"]'); await waitFor('!document.querySelector("#in").disabled');
  const oldTransform = await evaluate('document.querySelector("#drawing img").style.transform');
  await evaluate('document.querySelector("#stage").focus()');
  await cdp('Input.dispatchKeyEvent',{type:'keyDown',key:'+',text:'+'});
  await check('keyboard zooms drawing',`document.querySelector('#drawing img').style.transform!==${JSON.stringify(oldTransform)}`);
  await screenshot('desktop-schematic');
  await cdp('Emulation.setDeviceMetricsOverride',{width:820,height:1180,deviceScaleFactor:1,mobile:false});
  await click('[data-mode="rover"]');
  await check('tablet no horizontal overflow','document.documentElement.scrollWidth <= innerWidth');
  await screenshot('tablet-rover');
  await cdp('Emulation.setDeviceMetricsOverride',{width:375,height:812,deviceScaleFactor:1,mobile:true});
  await click('[data-mode="rover"]');
  await check('mobile model full width','document.querySelector("#stage").clientWidth === innerWidth');
  await check('mobile controls below model','document.querySelector("#controls").getBoundingClientRect().top >= document.querySelector("#stage").getBoundingClientRect().bottom');
  await check('mobile no horizontal overflow','document.documentElement.scrollWidth <= innerWidth');
  await check('mobile zoom controls stay on model','document.querySelector("#stage").contains(document.querySelector("#fit")) && document.querySelector(".zoom-controls").getBoundingClientRect().right <= innerWidth');
  await screenshot('mobile-rover');
  const beforeNavigation = await evaluate('performance.timeOrigin');
  await click('.inspection-bar .mobile-controls');
  await check('Controls link focuses controls','document.activeElement.id === "controls"');
  await check('Controls link preserves loaded page',`performance.timeOrigin === ${beforeNavigation}`);
  await screenshot('mobile-controls');
  await click('#controls .mobile-controls');
  await cdp('Emulation.setDeviceMetricsOverride',{width:320,height:740,deviceScaleFactor:1,mobile:true});
  await check('320px viewer no horizontal overflow','document.documentElement.scrollWidth <= innerWidth');
  await screenshot('small-mobile-rover');
  await click('.viewport-help summary');
  await check('small mobile help fits viewport','document.querySelector("#hint").getBoundingClientRect().right <= innerWidth');
  await click('.viewport-help summary');
  await click('[data-view="bottom"]');
  await check('view selection updates link','new URLSearchParams(location.search).get("view")==="bottom"');
  await click('#shell');
  await check('shell selection updates link','new URLSearchParams(location.search).get("shell")==="0"');
  await click('[data-mode="schematic"]'); await waitFor('!document.querySelector("#in").disabled');
  await evaluate('document.querySelector("canvas").dispatchEvent(new Event("webglcontextlost",{cancelable:true}))');
  await click('[data-mode="rover"]');
  await check('context lost while drawing has recovery on return','!document.querySelector("#load-error").hidden');
  await navigate('/viewer/project.html');
  await check('project content visible','document.querySelector("#release").textContent.includes("Physical tests: not run")');
  await check('320px details no horizontal overflow','document.documentElement.scrollWidth <= innerWidth');
  await screenshot('mobile-project');
  await cdp('Emulation.setDeviceMetricsOverride',{width:1440,height:960,deviceScaleFactor:1,mobile:false});
  await screenshot('desktop-project');
  await navigate('/viewer/credits.html');
  await check('license content visible','document.querySelector("h1").textContent.includes("attribution")');
  await screenshot('desktop-credits');
  // A fresh schematic route must not create a WebGL context or fetch CAD.
  const startRequests = requests.length;
  await navigate('/?mode=schematic');
  await waitFor('!document.querySelector("#in").disabled');
  assert(!requests.slice(startRequests).some(path => path.includes('meshes'))); checks.push('schematic does not download geometry');
  await check('schematic does not initialize WebGL','!document.querySelector("canvas")');
  await check('schematic direction controls disabled','document.querySelector("#view-controls").disabled');
  const transformBeforePinch = await evaluate('document.querySelector("#drawing img").style.transform');
  await cdp('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:[{x:700,y:400,id:1},{x:800,y:400,id:2}]});
  await cdp('Input.dispatchTouchEvent',{type:'touchMove',touchPoints:[{x:660,y:400,id:1},{x:840,y:400,id:2}]});
  await cdp('Input.dispatchTouchEvent',{type:'touchEnd',touchPoints:[]});
  await check('touch pinch zooms drawing',`document.querySelector('#drawing img').style.transform!==${JSON.stringify(transformBeforePinch)}`);
  assert.deepEqual(errors,[], 'Unexpected browser errors during normal flows'); checks.push('normal flows have no browser errors or CSP violations');
  const noGL = await cdp('Page.addScriptToEvaluateOnNewDocument',{source:'HTMLCanvasElement.prototype.getContext = () => null;'});
  await navigate('/viewer/'); await waitFor('!document.querySelector("#load-error").hidden');
  await check('WebGL failure is actionable','document.querySelector("#error-detail").textContent.includes("WebGL2")');
  await click('[data-mode="schematic"]'); await waitFor('!document.querySelector("#in").disabled');
  await check('schematic survives WebGL failure','document.querySelector("#load-error").hidden && !document.querySelector("#drawing").hidden');
  await cdp('Page.removeScriptToEvaluateOnNewDocument',{identifier:noGL.identifier});
  failMesh = true;
  await navigate('/'); await waitFor('!document.querySelector("#load-error").hidden');
  await check('failed CAD download reports HTTP error','document.querySelector("#error-detail").textContent.includes("503")');
  await screenshot('load-error');
  failMesh = false; failDrawing = true;
  await navigate('/?mode=schematic'); await waitFor('document.querySelector("#status").textContent.includes("could not load")');
  await check('failed drawing disables zoom','document.querySelector("#in").disabled');
  failDrawing = false;
  await click('[data-mode="schematic"]'); await waitFor('!document.querySelector("#in").disabled');
  checks.push('failed drawing can retry');
  await cdp('Emulation.setScriptExecutionDisabled',{value:true});
  await navigate('/');
  await check('no-JavaScript fallback visible','Boolean(document.querySelector("noscript img")?.naturalWidth)');
  await navigate('/viewer/project.html');
  await check('project details work without JavaScript','Boolean(document.querySelector("#release"))');
  await writeFile(resolve(reports,'report.json'),JSON.stringify({passed:true,checks,normalFlowErrors:[],screenshots:reports},null,2)+'\n');
  console.log(`Viewer UI: ${checks.length} checks passed; screenshots and report: ${reports}`);
} finally {
  ws?.close();
  if (browser && browser.exitCode === null) { browser.kill(); await once(browser,'exit'); }
  server.closeAllConnections(); await new Promise(ok => server.close(ok));
  await rm(profile,{recursive:true,force:true,maxRetries:10,retryDelay:100});
}
