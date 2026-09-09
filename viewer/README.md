# Interactive Rev B CAD inspection

Start `python3 -m http.server 8765 --bind 127.0.0.1` in the repository root.
Open [the rover](http://127.0.0.1:8765/viewer/) or
[the PCB](http://127.0.0.1:8765/viewer/?mode=pcb).

Drag to rotate, wheel/pinch to zoom, right-drag to pan, or select any of six
sides. Double-click a component to focus it. Hide or fade the enclosure,
separate the assembly, or hide individual components. Copper and schematic
views support zoom and pan. The viewer and its geometry are local.

The 160×100 mm PCB includes a bottom Pi socket, two top Shrike sockets,
onboard DRV8833 and the sensor/encoder/IMU connectors. Geometry comes from
the actual saved PCB and STEP assemblies. Component meshes are grouped by
reference designator, including the individual socket contacts.

The Pi uses official source CAD. The Shrike model derives its outline and
hole positions from the R0.4 PCB; its male header plastic/pins are nominal,
and its component population is not fully modeled. The original Shrike STEP
has a documented header-position mismatch and is excluded from the assembly.
Samtec socket bodies and JST VH plastic are nominal drawing-based models;
other packages use KiCad library references. Motors/wheels use supplier
dimensions. Packs, caster and fit tolerances remain unmeasured envelopes.
This is a review assembly, not a physical fit or fabrication release.

Use [docs/build.md](../docs/build.md) to regenerate CAD, attach local models,
export populated STEP and refresh `meshes.json`. Provenance is in
`model-sources.json` and `../reference/`; hashes reject stale geometry.

[The browser self-test](http://127.0.0.1:8765/viewer/?test=1) checks required
components, the plugged module, every viewing direction, zoom, enclosure
visibility, exploded view, component hiding and schematic switching.
WebGL2 is required.

Three.js 0.180.0 / OrbitControls are vendored under MIT (`vendor/LICENSE`).
KiCad models retain their library license; see [THIRD_PARTY.md](../THIRD_PARTY.md).
