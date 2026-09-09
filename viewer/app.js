import * as T from 'three';
import {OrbitControls} from './vendor/OrbitControls.js';
const $=s=>document.querySelector(s), stage=$('#stage'), status=$('#status');
const renderer=new T.WebGLRenderer({antialias:true,preserveDrawingBuffer:true});
renderer.setPixelRatio(Math.min(devicePixelRatio,2));renderer.setClearColor(0xe9edf0);stage.prepend(renderer.domElement);
const scene=new T.Scene(), camera=new T.OrthographicCamera(-200,200,200,-200,.1,10000);camera.up.set(0,0,1);
const controls=new OrbitControls(camera,renderer.domElement);controls.enableDamping=true;controls.dampingFactor=.12;controls.minZoom=.15;controls.maxZoom=80;
const ambient=new T.HemisphereLight(0xffffff,0x697987,2.1);ambient.position.set(0,0,1);scene.add(ambient);
const key=new T.DirectionalLight(0xffffff,2.7);key.position.set(250,150,450);scene.add(key);
const fill=new T.DirectionalLight(0xd3e7ff,1.3);fill.position.set(-150,-250,-150);scene.add(fill);
const grid=new T.GridHelper(700,28,0xb7c3cb,0xd2dae0);grid.rotation.x=Math.PI/2;grid.position.z=-50;scene.add(grid);
const rover=new T.Group(), pcb=new T.Group(), assemblyPCB=new T.Group();rover.add(assemblyPCB);assemblyPCB.position.set(-60,40,18);scene.add(rover,pcb);pcb.visible=false;
let mode='rover', active=rover, parts=[], boardParts=[], direction='iso';
const drawing=$('#drawing'), drawingImg=$('#drawing img');let drawScale=1,drawX=0,drawY=0;
function drawTransform(){drawingImg.style.transform=`translate(calc(-50% + ${drawX}px),calc(-50% + ${drawY}px)) scale(${drawScale})`;}
function fitDrawing(){drawScale=Math.min(stage.clientWidth/(drawingImg.naturalWidth||1000),stage.clientHeight/(drawingImg.naturalHeight||700))*.9;drawX=drawY=0;drawTransform();}
function showDrawing(url,label){drawing.style.display='block';drawingImg.onload=fitDrawing;drawingImg.src=url;status.textContent=label+' · wheel to zoom / drag to pan';$('#hint').textContent='Scroll / pinch to zoom · drag to pan · Fit / reset to show the whole drawing';}
function closeDrawing(){drawing.style.display='none';$('#hint').innerHTML='Drag to rotate · wheel / pinch to zoom · right-drag to pan<br>Double-click a part to focus. Front = sensor side (+Y).';}
function isDrawing(){return drawing.style.display==='block';}
const directions={iso:[1,1,.8],top:[0,.001,1],bottom:[0,-.001,-1],front:[0,1,0],back:[0,-1,0],left:[-1,0,0],right:[1,0,0]};
function bounds(object=active){object.updateMatrixWorld(true);const b=new T.Box3();object.traverse(o=>{if(o.isMesh&&o.visible){let p=o.parent;while(p&&p.visible)p=p.parent;if(!p)b.expandByObject(o);}});return b;}
function fit(object=active){const b=bounds(object);if(b.isEmpty())return;const center=b.getCenter(new T.Vector3()),size=b.getSize(new T.Vector3());controls.target.copy(center);const span=Math.max(size.x,size.y,size.z,20)*1.35;camera.zoom=1;camera.userData.span=span;resize();view(direction);}
function view(which){direction=which;const d=new T.Vector3(...directions[which]).normalize();camera.position.copy(controls.target).addScaledVector(d,900);camera.up.set(0,0,1);if(which==='top'||which==='bottom')camera.up.set(0,1,0);camera.lookAt(controls.target);controls.update();}
function resize(){const w=stage.clientWidth,h=stage.clientHeight,span=camera.userData.span||400,aspect=w/h;camera.left=-span/2*Math.max(1,aspect);camera.right=-camera.left;camera.top=span/2*Math.max(1,1/aspect);camera.bottom=-camera.top;camera.updateProjectionMatrix();renderer.setSize(w,h);}
new ResizeObserver(resize).observe(stage);
function zoom(factor){if(isDrawing()){drawScale=Math.max(.05,Math.min(40,drawScale*factor));drawTransform();}else{camera.zoom=T.MathUtils.clamp(camera.zoom*factor,.15,80);camera.updateProjectionMatrix();}}
$('#in').onclick=()=>zoom(1.35);$('#out').onclick=()=>zoom(1/1.35);$('#fit').onclick=()=>isDrawing()?fitDrawing():fit();$('#iso').onclick=()=>{closeDrawing();view('iso');};
document.querySelectorAll('[data-view]').forEach(b=>b.onclick=()=>{if(mode==='schematic')return;closeDrawing();view(b.dataset.view);});
function mesh(data){const g=new T.BufferGeometry();g.setAttribute('position',new T.Float32BufferAttribute(data.positions,3));g.setIndex(data.indices);g.computeVertexNormals();const color=Array.isArray(data.color)?new T.Color(...data.color):new T.Color(data.color);const mat=new T.MeshStandardMaterial({color,roughness:.58,metalness:.08,side:T.DoubleSide});const m=new T.Mesh(g,mat);m.name=data.name;m.userData.enabled=true;return m;}
function reserve(n){return /component_ENVELOPE|idc_/.test(n);}
function apply(){grid.position.z=$('#stand').checked?-48:-15;const e=Number($('#explode').value);for(const m of parts){const n=m.name;m.visible=n!=='pcb_ENVELOPE'&&m.userData.enabled&&(!n.includes('ENVELOPE')||$('#envelopes').checked)&&(!reserve(n)||$('#reserves').checked)&&(n!=='vented_shell'||$('#shell').checked)&&(n!=='test_stand'||$('#stand').checked);m.position.set(0,0,0);if(n==='vented_shell')m.position.z=e*170;else if(n==='tray'||n==='host_pack_ENVELOPE'||n==='pi5_ENVELOPE')m.position.z=e*110;else if(n==='tray_posts')m.position.z=e*50;else if(n.includes('wheel'))m.position.x=(n.includes('left')?-1:1)*e*80;else if(n.includes('pack')||n.includes('module_plate')||n.includes('shrike'))m.position.z=e*55;
const opacity=n==='vented_shell'?Number($('#opacity').value):reserve(n)?.2:1;m.material.opacity=opacity;m.material.transparent=opacity<1;m.material.depthWrite=opacity===1;
}
assemblyPCB.position.z=18+e*65;
for(const m of boardParts)m.visible=m.userData.enabled&&($('#components').checked||m.userData.board);
}
function listParts(){const container=$('#parts');container.replaceChildren();const h=document.createElement('h2');h.textContent='Individual parts';container.append(h);if(mode==='schematic')return;for(const m of mode==='rover'?parts.filter(m=>m.name!=='pcb_ENVELOPE'):boardParts.filter(m=>!m.userData.copper)){const label=document.createElement('label'),input=document.createElement('input');input.type='checkbox';input.checked=m.userData.enabled;input.onchange=()=>{m.userData.enabled=input.checked;apply();};label.append(input,document.createTextNode(' '+m.name.replaceAll('_',' ')));container.append(label);}}
function setMode(next){mode=next;document.querySelectorAll('[data-mode]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.mode===mode)));$('#rover-options').hidden=mode!=='rover';$('#pcb-options').hidden=mode!=='pcb';rover.visible=mode==='rover';pcb.visible=mode==='pcb';grid.visible=mode==='rover';active=mode==='rover'?rover:pcb;closeDrawing();if(mode==='schematic'){showDrawing('../electronics/out/schematic/carrier.svg','Electrical schematic');}else{direction='iso';fit();status.textContent=mode==='rover'?'Rover assembly · 200 × 260 mm base':'Populated PCB · 120 × 80 mm · standard library component models';}$('#disclaimer').textContent=mode==='rover'?'Incomplete robot design: no Shrike socket or Pi header adapter. Purchased hardware uses unmeasured placeholders; mounts, wiring and fit still need qualification.':'Harness adapter only: no physical Shrike socket or Pi 40-pin connector. KiCad checks passed; the complete robot interface and supplier fit remain unqualified.';listParts();}
document.querySelectorAll('[data-mode]').forEach(b=>b.onclick=()=>setMode(b.dataset.mode));document.querySelectorAll('[data-drawing]').forEach(b=>b.onclick=()=>showDrawing(`../electronics/out/carrier-${b.dataset.drawing}.svg`,`${b.dataset.drawing} copper routing`));$('#board3d').onclick=()=>{closeDrawing();fit();};
for(const id of ['shell','opacity','explode','envelopes','reserves','stand','components'])$('#'+id).addEventListener('input',()=>{apply();if(id==='explode')fit();});
const ray=new T.Raycaster();renderer.domElement.ondblclick=event=>{const r=renderer.domElement.getBoundingClientRect();ray.setFromCamera(new T.Vector2((event.clientX-r.left)/r.width*2-1,-(event.clientY-r.top)/r.height*2+1),camera);const hits=ray.intersectObjects(active.children,true).filter(h=>h.object.visible);if(hits[0]){fit(hits[0].object);status.textContent=hits[0].object.name.replaceAll('_',' ');}};
drawing.addEventListener('wheel',e=>{e.preventDefault();zoom(Math.exp(-e.deltaY*.001));},{passive:false});let pointer=null;drawing.onpointerdown=e=>{pointer=[e.clientX,e.clientY];drawing.setPointerCapture(e.pointerId);};drawing.onpointermove=e=>{if(!pointer)return;drawX+=e.clientX-pointer[0];drawY+=e.clientY-pointer[1];pointer=[e.clientX,e.clientY];drawTransform();};drawing.onpointerup=drawing.onpointercancel=()=>pointer=null;
try{const response=await fetch('./meshes.json');if(!response.ok)throw Error(`CAD data HTTP ${response.status}`);const data=await response.json();for(const item of data.rover){const m=mesh(item);parts.push(m);rover.add(m);}for(const item of data.pcb){const m=mesh(item);m.userData.copper=/track|pad|via|copper/i.test(m.name);m.userData.board=m.userData.copper||/board|PCB|carrier/i.test(m.name);boardParts.push(m);pcb.add(m);assemblyPCB.add(m.clone());}const box=new T.Box3().setFromObject(pcb),center=box.getCenter(new T.Vector3());pcb.position.sub(center);apply();setMode('rover');window.viewerReady=true;window.viewerStats={rover:parts.length,pcb:boardParts.length};const q=new URLSearchParams(location.search);if(['rover','pcb','schematic'].includes(q.get('mode')))setMode(q.get('mode'));if(q.get('view') in directions)view(q.get('view'));document.body.dataset.ready='true';if(q.has('test'))selfTest();}catch(error){status.textContent='Could not load viewer: '+error.message;console.error(error);}
renderer.setAnimationLoop(()=>{controls.update();key.position.copy(camera.position);renderer.render(scene,camera);});

function selfTest(){
 const checks=[];const check=(name,ok)=>{if(!ok)throw Error('Test failed: '+name);checks.push(name);};
 check('complete data',parts.length===24&&boardParts.length===21);
 for(const next of ['rover','pcb']){setMode(next);for(const side of Object.keys(directions)){view(side);check(next+' '+side,[...camera.position.toArray(),...camera.quaternion.toArray()].every(Number.isFinite));}}
 setMode('rover');const before=camera.zoom;$('#in').click();check('zoom in',camera.zoom>before);$('#out').click();check('zoom out',Math.abs(camera.zoom-before)<1e-8);
 $('#shell').checked=false;apply();check('hide shell',!parts.find(m=>m.name==='vented_shell').visible);$('#shell').checked=true;
 $('#explode').value=1;apply();check('explode shell',parts.find(m=>m.name==='vented_shell').position.z===170);$('#explode').value=0;apply();
 setMode('pcb');$('#components').checked=false;apply();check('hide components',boardParts.filter(m=>!m.userData.board).every(m=>!m.visible));check('retain board',boardParts.some(m=>m.userData.board&&m.visible));$('#components').checked=true;apply();
 setMode('schematic');check('schematic',isDrawing());setMode('rover');
 document.body.dataset.tests=JSON.stringify(checks);status.textContent='Inspection controls checked · '+checks.length+' checks passed';
}
