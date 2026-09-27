# Reproduce Rev B.1 review artifacts

Install [Git LFS](https://github.com/git-lfs/git-lfs), then run these commands
from your cloned repository to obtain the large CAD and viewer files:

```sh
git lfs install --local
git lfs pull
git lfs fsck
```

The assembly STEP, Pi reference STEP and `viewer/meshes.json` are tracked in
LFS; their checked-out contents remain the original full files. The six local
commits were migrated before the first successful GitHub push. Historical audit
references retain their original commit IDs; [lfs-commit-map.csv](lfs-commit-map.csv)
maps those IDs to the corresponding migrated commits.

Open `electronics/carrier.kicad_pro` in KiCad 10.0.6. The saved board is editable
and routed. `electronics/generate.py` is the parametric source; regenerating it
overwrites manual KiCad edits and removes routing. Preserve manual revisions
before regenerating. None of these commands authorizes fabrication or motion.

Use CadQuery 2.6.1 from `mechanical/requirements.txt` in a repository-local
`.venv`. Download the pinned [Freerouting 2.4.1 release](https://github.com/freerouting/freerouting/releases/tag/v2.4.1)
to `.cache/cad/freerouting-2.4.1.jar` before routing.

```sh
uv venv --python python3.12 .venv
uv pip install --python .venv/bin/python -r mechanical/requirements.txt
mkdir -p .cache/cad/router
curl -fL https://github.com/freerouting/freerouting/releases/download/v2.4.1/freerouting-2.4.1.jar -o .cache/cad/freerouting-2.4.1.jar

# From the repository root, rebuild mechanical references and printable parts.
.venv/bin/python mechanical/axiom_rover.py --output mechanical/out
.venv/bin/python viewer/export_meshes.py --socket-models-only

# Reproduce the reviewed board using its matching saved routing session.
# The generator locks the short local motor/power routes before export.
.cache/cad/kicad-10.0.6-x86_64-lite.AppImage python3.11 electronics/generate.py
.cache/cad/kicad-10.0.6-x86_64-lite.AppImage python3.11 electronics/generate.py --import-session electronics/out/carrier.ses

# Remove only unused vias identified by a fresh native DRC report; rerun DRC below.
.cache/cad/kicad-10.0.6-x86_64-lite.AppImage kicad-cli pcb drc --format json --schematic-parity -o electronics/out/drc.json electronics/carrier.kicad_pcb
.cache/cad/kicad-10.0.6-x86_64-lite.AppImage python3.11 electronics/generate.py --clean-dangling-vias electronics/out/drc.json
.cache/cad/kicad-10.0.6-x86_64-lite.AppImage kicad-cli pcb drc --format json --schematic-parity -o electronics/out/drc.json electronics/carrier.kicad_pcb

# Export only after the fresh board has been routed and checked.
SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt .cache/cad/kicad-10.0.6-x86_64-lite.AppImage python3.11 tools/prepare-pcb-models.py
python3 tools/export-electronics.py --kicad .cache/cad/kicad-10.0.6-x86_64-lite.AppImage
.venv/bin/python tools/check-assembly-fit.py
.venv/bin/python viewer/export_meshes.py
rsvg-convert -w 3200 electronics/out/schematic/carrier.svg -o electronics/out/schematic/carrier.png
rsvg-convert -w 1600 electronics/out/carrier-top.svg -o electronics/out/carrier-top.png
rsvg-convert -w 1600 electronics/out/carrier-bottom.svg -o electronics/out/carrier-bottom.png
python3 tools/check-viewer.py
python3 tools/check-artifacts.py
python3 -m http.server 8765 --bind 127.0.0.1
```

Stop if a command fails. `check-artifacts.py` checks source hashes, native
ERC/DRC/parity, actual pad/net mappings, mechanical reports, viewer geometry
freshness and BOM arithmetic. Open `http://127.0.0.1:8765/viewer/?test=1` for
the browser controls check. `tools/check-viewer.py` runs it using installed Chromium
and saves `viewer/browser-check.json` plus a screenshot. Logs are evidence
for this revision only.

For a changed layout, route the newly generated DSN instead of importing an
older session:

```sh
java -Djava.awt.headless=true -jar .cache/cad/freerouting-2.4.1.jar --gui.enabled=false -da --api_server.enabled=false --user_data_path=.cache/cad/router -de electronics/out/carrier.dsn -do electronics/out/carrier.ses -mp 25 -mt 1
```

The saved B.1 session includes the completed 0.25 mm TP5 probe branch from the
0.8 mm VM trunk. After a new autoroute, complete any remaining connections and
retain them in the session; require zero native DRC/connectivity/parity findings.
Freerouting can report unconnected fine-pitch escapes that are already locked
in KiCad, so its completion status alone is insufficient.
 Motor breakouts are locked 0.30 mm necks; default motor trunks are
0.8 mm. Do not replace these with unrestricted fine-pitch traces merely to
obtain a successful route.

Use `reference/raspberry-pi-5/connector-sources.md` for socket dimensions,
`docs/electrical-contract.md` and `docs/harness.svg` for wiring, and
`docs/commissioning.md` for physical acceptance. The carrier must be powered
off, lifted at least 7 mm to disengage the Pi header, and removed with its
perimeter frame. Unbolt the Pi, lift it 2 mm, then slide it through the side
opening. Sensor and
power harnesses require rated contacts, polarity checks and strain relief.
