# Interactive Rev B.1 CAD inspection

Hosted on Vercel: [rover and enclosure](https://axiom-rover.vercel.app/),
[PCB](https://axiom-rover.vercel.app/?mode=pcb),
[schematic](https://axiom-rover.vercel.app/?mode=schematic).

Start `python3 -m http.server 8765 --bind 127.0.0.1` in the repository root.
Open [the rover](http://127.0.0.1:8765/viewer/) or
[the PCB](http://127.0.0.1:8765/viewer/?mode=pcb).

Drag to rotate, wheel/pinch to zoom, right-drag to pan, or select any of six
sides. Double-click a component to focus it. Hide or fade the enclosure,
separate the assembly, or hide individual components. Copper and schematic
views support zoom and pan. The same viewer works locally and as a static Vercel deployment.

The 160×100 mm Rev B.1 PCB includes a bottom Pi socket, two top Shrike sockets,
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

## Vercel hosting

From the repository root, build and check the upload bundle:

```sh
python3 tools/build-viewer-site.py
python3 tools/check-viewer-site.py
node tools/check-viewer-ui.mjs
python3 tools/check-viewer.py --site-root .vercel/output/static --report-dir .cache/viewer-site-check
npx --yes vercel@59.15.0 link --yes --project axiom-rover --scope utkarshs-projects-88519d03
npx --yes vercel@59.15.0 deploy --prebuilt --prod --yes
```

The builder emits Vercel's [static Build Output API](https://vercel.com/docs/build-output-api)
under ignored `.vercel/output/`. Its fixed allowlist contains the viewer and project
pages, the CAD and circuit downloads linked from them, provenance, and licenses.
It rejects missing files and Git LFS pointers before replacing the output; run
`git lfs pull` if the geometry is still a pointer. Only files listed in the
builder reach the public site. `.vercel/project.json` is local account/project
configuration and stays ignored. Deploy the prebuilt output; a source deployment
from the repository root would upload unrelated CAD.

The output configuration serves `/viewer/` explicitly and applies a same-origin
content policy, basic security headers, and revalidation caching. Revalidation
matters because the asset URLs do not contain content hashes. The inline import
map is allowed by a hash generated from the source HTML during packaging.
The UI check uses Node.js 22+ and `chromium` on `PATH`; it runs against the
packaged site and writes browser reports under `.cache/viewer-ui/`.

The geometry is compressed losslessly from about 100 MB to 17 MB; the complete
bundle is about 40 MB. The hosted entry point uses the browser's native
[DecompressionStream](https://developer.mozilla.org/en-US/docs/Web/API/DecompressionStream).
A current browser with WebGL2 is required. Local viewing still loads the original
`meshes.json`. Both `/` and `/viewer/` support the existing `?mode=pcb`,
`?mode=schematic`, `?view=bottom`, and `?shell=0` links.

After deploying, check the public URL with the same browser test:

```sh
python3 tools/check-viewer.py --site-root .vercel/output/static \
  --report-dir .cache/vercel-live-check --url 'https://axiom-rover.vercel.app/'
```

The source hashes in that report describe the local bundle; verify downloaded
asset hashes separately when tying a remote deployment to this checkout. Hosting
does not change fabrication or physical-test release status.
