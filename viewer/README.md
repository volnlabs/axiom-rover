# Interactive CAD inspection

From the repository root:

```sh
python3 -m http.server 8765 --bind 127.0.0.1
```

Open [the rover viewer](http://127.0.0.1:8765/viewer/) or [the populated PCB](http://127.0.0.1:8765/viewer/?mode=pcb). All JavaScript and geometry are local; the viewer does not upload the designs.

Drag to rotate, wheel/pinch to zoom, right-drag to pan, or choose one of the six direction buttons. Double-click a part to focus it. Toggle the enclosure, adjust its opacity, separate parts, or hide individual parts. The PCB view includes component visibility plus zoomable top/bottom copper drawings. The schematic can also be zoomed and panned.

The rover meshes come from the saved STEP assembly. Its purchased hardware remains **unmeasured envelope geometry**, not detailed supplier models; fasteners and wiring are not fully modeled. The actual populated PCB is also displayed inside the rover. Its component geometry comes from the standard KiCad package models used by the existing footprints, not a fabrication-qualified supplier assembly.

`carrier-populated.step` was exported by KiCad 10.0.6 with `--include-pads --include-tracks` and the eight models recorded in `model-sources.json`. Geometry was tessellated with CadQuery 2.6.1. `pcb-layout.json` records reference designators and locations from the PCB for labeling imported component instances. To refresh meshes after refreshing those exports:

```sh
.venv/bin/python viewer/export_meshes.py
```

Three.js 0.180.0 and its OrbitControls are vendored under MIT; see `vendor/LICENSE` and the [Three.js documentation](https://threejs.org/docs/). KiCad component models derive from [KiCad Libraries contributors](https://github.com/KiCad/kicad-packages3D), under the KiCad library CC-BY-SA/design exception described in `../THIRD_PARTY.md`. Their source URLs and downloaded hashes are recorded alongside the viewer.

For a runnable browser check, visit [the self-test](http://127.0.0.1:8765/viewer/?test=1). It checks geometry counts, all camera directions, zoom, visibility, exploded view and schematic mode, and displays the number of passed checks. The tested run passed 22 checks. Use a browser with WebGL2 support.
