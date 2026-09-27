import * as T from 'three';
import {OrbitControls} from './vendor/OrbitControls.js';

const $ = s => document.querySelector(s);
const stage = $('#stage'), status = $('#status');
const drawing = $('#drawing'), drawingImg = $('#drawing img');
const scene = new T.Scene();
const camera = new T.OrthographicCamera(-200, 200, 200, -200, .1, 10000);
camera.up.set(0, 0, 1);
const ambient = new T.HemisphereLight(0xffffff, 0x697987, 2.1);
ambient.position.set(0, 0, 1);
const key = new T.DirectionalLight(0xffffff, 2.7);
const fill = new T.DirectionalLight(0xd3e7ff, 1.3);
fill.position.set(-150, -250, -150);
scene.add(ambient, key, fill);
const grid = new T.GridHelper(700, 28, 0xb7c3cb, 0xd2dae0);
grid.rotation.x = Math.PI / 2;
grid.position.z = -50;
scene.add(grid);
const rover = new T.Group(), pcb = new T.Group(), assemblyPCB = new T.Group();
rover.add(assemblyPCB);
assemblyPCB.position.set(-80, 50, 107.1);
scene.add(rover, pcb);
pcb.visible = false;
let renderer, controls, frame = 0, loading;
let mode = 'rover', active = rover, parts = [], boardParts = [], direction = 'iso';
let drawScale = 1, drawX = 0, drawY = 0, drawingReady = false;
const directions = {iso:[1,1,.8], top:[0,.001,1], bottom:[0,-.001,-1], front:[0,1,0], back:[0,-1,0], left:[-1,0,0], right:[1,0,0]};
const hint3D = 'Drag to rotate · pinch or scroll to zoom · right-drag to pan. Keyboard: arrows choose sides, + / − zoom, Home fits. Double-click a part to focus.';

function requestRender() {
  if (!renderer || frame || document.hidden || isDrawing()) return;
  frame = requestAnimationFrame(() => {
    frame = 0;
    const changed = controls.update();
    key.position.copy(camera.position);
    renderer.render(scene, camera);
    if (changed) requestRender();
  });
}
function initRenderer() {
  if (renderer) return;
  try { renderer = new T.WebGLRenderer({antialias:true}); }
  catch { throw Error('This browser cannot start WebGL2. Enable hardware acceleration or try another browser. The schematic and downloads are still available.'); }
  renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
  renderer.setClearColor(0xe9edf0);
  renderer.domElement.setAttribute('aria-label', 'Interactive reference CAD. Use the view controls or keyboard to inspect each side.');
  renderer.domElement.setAttribute('role', 'img');
  stage.prepend(renderer.domElement);
  controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = !matchMedia('(prefers-reduced-motion: reduce)').matches;
  controls.dampingFactor = .12;
  controls.minZoom = .15;
  controls.maxZoom = 80;
  controls.addEventListener('change', requestRender);
  renderer.domElement.addEventListener('webglcontextlost', event => {
    event.preventDefault();
    window.viewerReady = false;
    document.body.dataset.loadError = 'true';
    updateControls();
    if (!isDrawing()) showError('The graphics context was lost. Reload to restore 3D inspection; drawings and downloads are still available.');
  });
  renderer.domElement.ondblclick = event => {
    const r = renderer.domElement.getBoundingClientRect();
    const ray = new T.Raycaster();
    ray.setFromCamera(new T.Vector2((event.clientX-r.left)/r.width*2-1, -(event.clientY-r.top)/r.height*2+1), camera);
    const hit = ray.intersectObjects(active.children, true).find(h => {
      for (let p = h.object; p; p = p.parent) if (!p.visible) return false;
      return true;
    });
    if (hit) { fit(hit.object); status.textContent = hit.object.name.replaceAll('_', ' '); }
  };
  resize();
}
function showError(message) {
  status.textContent = '3D inspection unavailable';
  $('#error-detail').textContent = message;
  $('#load-error').hidden = false;
}
$('#retry').onclick = () => location.reload();
function isDrawing() { return !drawing.hidden; }
function drawTransform() {
  drawingImg.style.transform = `translate(calc(-50% + ${drawX}px),calc(-50% + ${drawY}px)) scale(${drawScale})`;
}
function fitDrawing() {
  if (!drawingReady) return;
  drawScale = Math.min(stage.clientWidth/drawingImg.naturalWidth, stage.clientHeight/drawingImg.naturalHeight) * .85;
  drawX = drawY = 0;
  drawTransform();
}
function showDrawing(url, label) {
  drawing.hidden = false;
  drawingReady = false;
  drawingImg.hidden = true;
  $('#load-error').hidden = true;
  status.textContent = 'Loading ' + label.toLowerCase() + '…';
  drawingImg.alt = label + ' for the Rev B carrier';
  drawingImg.onload = () => {
    if (!isDrawing()) return;
    drawingReady = true;
    drawingImg.hidden = false;
    fitDrawing();
    status.textContent = label;
    updateControls();
  };
  drawingImg.onerror = () => {
    if (!isDrawing()) return;
    status.textContent = 'Drawing could not load. Check your connection and select the drawing again to retry.';
    updateControls();
  };
  drawingImg.src = url;
  $('#hint').textContent = 'Pinch / scroll to zoom · drag to pan. Keyboard: arrows pan, + / − zoom, Home fits.';
  document.querySelectorAll('[data-drawing]').forEach(b => b.setAttribute('aria-pressed', String(url.endsWith('carrier-' + b.dataset.drawing + '.svg'))));
  updateControls();
}
function closeDrawing() {
  drawing.hidden = true;
  drawingReady = false;
  $('#hint').textContent = hint3D;
  document.querySelectorAll('[data-drawing]').forEach(b => b.setAttribute('aria-pressed', 'false'));
  updateControls();
  requestRender();
}
function bounds(object=active) {
  object.updateMatrixWorld(true);
  const b = new T.Box3();
  object.traverse(o => {
    if (!o.isMesh || !o.visible) return;
    let p = o.parent;
    while (p && p.visible) p = p.parent;
    if (!p) b.expandByObject(o);
  });
  return b;
}
function fit(object=active) {
  if (!controls) return;
  const b = bounds(object);
  if (b.isEmpty()) return;
  const center = b.getCenter(new T.Vector3()), size = b.getSize(new T.Vector3());
  controls.target.copy(center);
  camera.zoom = 1;
  camera.userData.span = Math.max(size.x, size.y, size.z, 20) * 1.35;
  resize();
  view(direction);
}
function view(which) {
  if (!controls || !Object.hasOwn(directions, which)) return;
  direction = which;
  camera.position.copy(controls.target).addScaledVector(new T.Vector3(...directions[which]).normalize(), 900);
  camera.up.set(0, 0, 1);
  if (which === 'top' || which === 'bottom') camera.up.set(0, 1, 0);
  camera.lookAt(controls.target);
  controls.update();
  document.querySelectorAll('[data-view]').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.view === which)));
  $('#iso').setAttribute('aria-pressed', String(which === 'iso'));
  requestRender();
}
function resize() {
  const w = stage.clientWidth, h = stage.clientHeight;
  if (!w || !h) return;
  if (renderer) {
    const span = camera.userData.span || 400, aspect = w/h;
    camera.left = -span/2 * Math.max(1, aspect);
    camera.right = -camera.left;
    camera.top = span/2 * Math.max(1, 1/aspect);
    camera.bottom = -camera.top;
    camera.updateProjectionMatrix();
    renderer.setSize(w, h);
    requestRender();
  }
  if (isDrawing()) fitDrawing();
}
new ResizeObserver(resize).observe(stage);
document.addEventListener('visibilitychange', requestRender);
function zoom(factor) {
  if (isDrawing()) {
    if (!drawingReady) return;
    drawScale = Math.max(.01, Math.min(40, drawScale * factor));
    drawTransform();
  } else if (window.viewerReady) {
    camera.zoom = T.MathUtils.clamp(camera.zoom * factor, .15, 80);
    camera.updateProjectionMatrix();
    requestRender();
  }
}
function updateControls() {
  const ready = Boolean(window.viewerReady);
  $('#view-controls').disabled = !ready || mode === 'schematic';
  $('#rover-options').disabled = !ready;
  $('#pcb-options').disabled = !ready;
  for (const id of ['fit', 'in', 'out']) $('#'+id).disabled = isDrawing() ? !drawingReady : !ready;
}
$('#in').onclick = () => zoom(1.35);
$('#out').onclick = () => zoom(1/1.35);
$('#fit').onclick = () => isDrawing() ? fitDrawing() : fit();
$('#iso').onclick = () => { if (mode === 'schematic') return; closeDrawing(); view('iso'); updateURL('view', null); };
document.querySelectorAll('[data-view]').forEach(b => b.onclick = () => { closeDrawing(); view(b.dataset.view); updateURL('view', b.dataset.view); });
function mesh(data){const g=new T.BufferGeometry();g.setAttribute('position',new T.Float32BufferAttribute(data.positions,3));g.setIndex(data.indices);g.computeVertexNormals();const color=Array.isArray(data.color)?new T.Color(...data.color):new T.Color(data.color);const mat=new T.MeshStandardMaterial({color,roughness:.58,metalness:.08,side:T.DoubleSide});const m=new T.Mesh(g,mat);m.name=data.name;m.userData.enabled=true;return m;}
function reserve(n){return /SWEEP|cooler|shrike_.*UNMEASURED_ENVELOPE|socket.*REFERENCE|DRAWING_REFERENCE|CONTRACT_REFERENCE/.test(n);}
function replaced(n){return /carrier_tails_CLEARANCE_REFERENCE|carrier_pcb_CONTRACT|shrike_actualCAD|shrike_pcbCAD|shrike_male_|shrike_.*socket_REFERENCE|pi_socket_ESQ_REFERENCE|pi5_DRAWING_REFERENCE/.test(n);}
function apply(){grid.position.z=$('#stand').checked?-48:-15;const e=Number($('#explode').value);for(const m of parts){const n=m.name;m.visible=!replaced(n)&&m.userData.enabled&&(!n.includes('ENVELOPE')||$('#envelopes').checked)&&(!reserve(n)||$('#reserves').checked)&&(n!=='vented_shell'||$('#shell').checked)&&(n!=='test_stand'||$('#stand').checked);m.position.set(0,0,0);if(n==='vented_shell')m.position.z=e*170;else if(n==='tray'||n.startsWith('pi5_')||n==='pi_cooler_max_ENVELOPE')m.position.z=e*60;else if(n==='carrier_frame')m.position.z=e*95;else if(n==='carrier_posts')m.position.z=e*60;else if(n==='tray_posts')m.position.z=e*30;else if(n.includes('wheel'))m.position.x=(n.includes('left')?-1:1)*e*80;else if(n.includes('shrike'))m.position.z=e*95;else if(n.includes('pack'))m.position.z=e*20;
const opacity=n==='vented_shell'?Number($('#opacity').value):reserve(n)?.2:1;m.material.opacity=opacity;m.material.transparent=opacity<1;m.material.depthWrite=opacity===1;
}
assemblyPCB.position.z=107.1+e*95;
for(const m of boardParts)m.visible=m.userData.enabled&&($('#components').checked||m.userData.board);
requestRender();
}

function listParts() {
  const container = $('#parts');
  container.replaceChildren();
  $('#parts-panel').hidden = mode === 'schematic';
  if (!window.viewerReady || mode === 'schematic') return;
  const items = mode === 'rover' ? parts.filter(m => !replaced(m.name)) : boardParts.filter(m => !m.userData.copper);
  if (mode === 'pcb') {
    const priority = m => m.name.startsWith('Shrike') ? 0 : /^J(1|2|4) —/.test(m.name) ? 1 : 2;
    items.sort((a,b) => priority(a)-priority(b) || a.name.localeCompare(b.name, undefined, {numeric:true}));
  }
  for (const m of items) {
    const label = document.createElement('label'), input = document.createElement('input');
    input.type = 'checkbox';
    input.checked = m.userData.enabled;
    input.onchange = () => { m.userData.enabled = input.checked; apply(); };
    label.append(input, document.createTextNode(' '+m.name.replaceAll('_', ' ')));
    container.append(label);
  }
}
function readyMode() {
  if (mode === 'schematic') return;
  $('#load-error').hidden = true;
  direction = 'iso';
  fit();
  status.textContent = mode === 'rover' ? 'Rover assembly · 200 × 260 mm base' : 'Rev B PCB · 160 × 100 mm · Pi below / Shrike above';
  const q = new URLSearchParams(location.search);
  if (Object.hasOwn(directions, q.get('view'))) view(q.get('view'));
  updateControls();
  listParts();
}
async function loadCAD() {
  if (window.viewerReady) return;
  if (loading) return loading;
  loading = (async () => {
    try {
      initRenderer();
      const meshSource = document.documentElement.dataset.meshSource || './meshes.json';
      if (meshSource.endsWith('.gz') && !('DecompressionStream' in window)) throw Error('This browser cannot unpack the CAD geometry. Use a current browser, or open the schematic and downloads.');
      const response = await fetch(meshSource, {signal:AbortSignal.timeout(120000)});
      if (!response.ok) throw Error(`CAD download failed (HTTP ${response.status}). Check your connection and retry.`);
      const decoded = meshSource.endsWith('.gz') ? new Response(response.body.pipeThrough(new DecompressionStream('gzip'))) : response;
      const data = await decoded.json();
      if (!isDrawing()) status.textContent = 'Preparing geometry…';
      await new Promise(resolve => setTimeout(resolve, 0));
      for (const item of data.rover) { const m = mesh(item); parts.push(m); rover.add(m); }
      for (const item of data.pcb) {
        const m = mesh(item);
        m.userData.copper = /track|pad|via|copper/i.test(m.name);
        m.userData.board = m.userData.copper || m.name === 'PCB substrate';
        boardParts.push(m); pcb.add(m); assemblyPCB.add(m.clone());
      }
      pcb.position.sub(new T.Box3().setFromObject(pcb).getCenter(new T.Vector3()));
      window.viewerReady = true;
      window.viewerStats = {rover:parts.length, pcb:boardParts.length};
      apply();
      readyMode();
      document.body.dataset.ready = 'true';
    } catch (error) {
      document.body.dataset.loadError = 'true';
      if (!isDrawing()) showError(error.message || 'CAD could not load. Check your connection and retry.');
      updateControls();
      console.error(error);
    }
  })();
  return loading;
}
function updateURL(key, value) {
  const url = new URL(location.href);
  if (value === null) url.searchParams.delete(key);
  else url.searchParams.set(key, value);
  history.replaceState(null, '', url);
}
function setMode(next, updateLocation=false) {
  if (!['rover', 'pcb', 'schematic'].includes(next)) next = 'rover';
  mode = next;
  if (updateLocation) {
    const url = new URL(location.href);
    url.searchParams.set('mode', mode);
    url.searchParams.delete('view');
    history.replaceState(null, '', url);
  }
  document.querySelectorAll('[data-mode]').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.mode === mode)));
  $('#rover-options').hidden = mode !== 'rover';
  $('#pcb-options').hidden = mode !== 'pcb';
  rover.visible = mode === 'rover'; pcb.visible = mode === 'pcb'; grid.visible = mode === 'rover';
  active = mode === 'rover' ? rover : pcb;
  $('#disclaimer').textContent = mode === 'rover'
    ? 'Saved CAD in millimetres. Purchased parts, socket engagement and printed fit need physical qualification. Front is the sensor side (+Y).'
    : 'Reference CAD only. Shrike chips and its USB body are omitted from the model. Fabrication and powered motion remain unreleased.';
  if (mode === 'schematic') showDrawing('../electronics/out/schematic/carrier.svg', 'Electrical schematic');
  else {
    closeDrawing();
    if (window.viewerReady) readyMode();
    else if (document.body.dataset.loadError) showError('3D could not initialize. Reload to retry, or use the schematic and downloads.');
    else { status.textContent = 'Loading CAD geometry… Large models may take a moment.'; loadCAD(); }
  }
  listParts();
}
document.querySelectorAll('[data-mode]').forEach(b => b.onclick = () => setMode(b.dataset.mode, true));
document.querySelectorAll('[data-drawing]').forEach(b => b.onclick = () => showDrawing(`../electronics/out/carrier-${b.dataset.drawing}.svg`, `${b.dataset.drawing === 'top' ? 'Top' : 'Bottom'} copper routing`));
$('#board3d').onclick = () => { closeDrawing(); fit(); status.textContent = 'Rev B PCB · 160 × 100 mm'; };
for (const id of ['shell','opacity','explode','envelopes','reserves','stand','components']) {
  $('#'+id).addEventListener('input', () => {
    apply();
    if (id === 'explode') fit();
    if (id === 'shell') updateURL('shell', $('#shell').checked ? null : '0');
  });
}
// Two pointers scale the drawing; one pointer pans it.
const pointers = new Map();
drawing.addEventListener('wheel', event => { event.preventDefault(); zoom(Math.exp(-event.deltaY * .001)); }, {passive:false});
drawing.onpointerdown = event => { pointers.set(event.pointerId, [event.clientX,event.clientY]); drawing.setPointerCapture(event.pointerId); };
drawing.onpointermove = event => {
  if (!pointers.has(event.pointerId)) return;
  const before = [...pointers.values()];
  const previous = pointers.get(event.pointerId);
  pointers.set(event.pointerId, [event.clientX,event.clientY]);
  if (pointers.size === 2) {
    const after = [...pointers.values()];
    const distance = points => Math.hypot(points[0][0]-points[1][0], points[0][1]-points[1][1]);
    if (distance(before) > 0) zoom(distance(after)/distance(before));
  } else if (pointers.size === 1) { drawX += event.clientX-previous[0]; drawY += event.clientY-previous[1]; drawTransform(); }
};
drawing.onpointerup = drawing.onpointercancel = drawing.onlostpointercapture = event => pointers.delete(event.pointerId);
stage.onkeydown = event => {
  if (event.target !== stage && event.target !== renderer?.domElement) return;
  const arrows = {ArrowLeft:'left', ArrowRight:'right', ArrowUp:'top', ArrowDown:'bottom'};
  if (!(event.key in arrows) && !['+','=','-','Home'].includes(event.key)) return;
  event.preventDefault();
  if (event.key === '+' || event.key === '=') zoom(1.35);
  else if (event.key === '-') zoom(1/1.35);
  else if (event.key === 'Home') isDrawing() ? fitDrawing() : fit();
  else if (isDrawing()) {
    if (event.key === 'ArrowLeft') drawX -= 30;
    if (event.key === 'ArrowRight') drawX += 30;
    if (event.key === 'ArrowUp') drawY -= 30;
    if (event.key === 'ArrowDown') drawY += 30;
    drawTransform();
  } else if (window.viewerReady) view(arrows[event.key]);
};
// Hosted root uses a base URL for assets; fragment links must stay on this page.
document.querySelectorAll('a[href^="#"]').forEach(link => link.addEventListener('click', event => {
  const target = document.getElementById(link.getAttribute('href').slice(1));
  if (target) { event.preventDefault(); target.focus({preventScroll:true}); target.scrollIntoView(); }
}));
const query = new URLSearchParams(location.search);
if (query.get('shell') === '0') $('#shell').checked = false;
setMode(query.get('mode') || 'rover');
if (query.has('test')) {
  await loadCAD();
  if (window.viewerReady) selfTest();
}

function selfTest(){
 const checks=[];const check=(name,ok)=>{if(!ok)throw Error('Test failed: '+name);checks.push(name);};
 check('rover geometry',parts.some(m=>m.name==='vented_shell')&&parts.some(m=>m.name==='carrier_frame'));
 for(const ref of ['J1','J2','J4','J10','J11','J13','U3','U4','U5'])check('PCB '+ref,boardParts.some(m=>m.name.startsWith(ref+' — ')));
 check('plugged Shrike',boardParts.some(m=>m.name.startsWith('Shrike R0.4')));
 for(const next of ['rover','pcb']){setMode(next);for(const side of Object.keys(directions)){view(side);check(next+' '+side,[...camera.position.toArray(),...camera.quaternion.toArray()].every(Number.isFinite));}}
 setMode('rover');const before=camera.zoom;$('#in').click();check('zoom in',camera.zoom>before);$('#out').click();check('zoom out',Math.abs(camera.zoom-before)<1e-8);
 $('#shell').checked=false;apply();check('hide shell',!parts.find(m=>m.name==='vented_shell').visible);$('#shell').checked=true;
 $('#explode').value=1;apply();check('explode shell',parts.find(m=>m.name==='vented_shell').position.z===170);check('exploded carrier above Pi',new T.Box3().setFromObject(assemblyPCB).min.z>new T.Box3().setFromObject(parts.find(m=>m.name==='pi5_actualCAD_REFERENCE')).max.z);$('#explode').value=0;apply();
 setMode('pcb');$('#components').checked=false;apply();check('hide components',boardParts.filter(m=>!m.userData.board).every(m=>!m.visible));check('retain board',boardParts.some(m=>m.userData.board&&m.visible));check('hide Shrike with components',!boardParts.find(m=>m.name.startsWith('Shrike R0.4')).visible);$('#components').checked=true;apply();
 setMode('schematic');check('schematic',isDrawing());check('schematic disables 3D views',$('#view-controls').disabled);check('schematic hides rover controls',$('#rover-options').hidden);check('schematic hides parts',$('#parts-panel').hidden);setMode('rover');check('rover restores view controls',!$('#view-controls').disabled);view('bottom');check('view button state',$('[data-view=bottom]').getAttribute('aria-pressed')==='true');view('iso');check('isometric button state',$('#iso').getAttribute('aria-pressed')==='true');check('invalid direction ignored',(view('toString'),direction==='iso'));check('canvas accessible',renderer.domElement.getAttribute('role')==='img');
 document.body.dataset.tests=JSON.stringify(checks);status.textContent='Inspection controls checked · '+checks.length+' checks passed';
}
