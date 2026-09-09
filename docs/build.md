# Reproduce Rev B review artifacts

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

Use CadQuery 2.6.1 with `mechanical/requirements.txt`; the working environment
for this revision is `/tmp/axiom-cad-tools/venv/bin/python`. A normal local venv
installed from that requirements file can replace it.

```sh
# From the repository root, rebuild mechanical references and printable parts.
/tmp/axiom-cad-tools/venv/bin/python mechanical/axiom_rover.py --output mechanical/out
/tmp/axiom-cad-tools/venv/bin/python viewer/export_meshes.py --socket-models-only

# Recreate the source board, then import the matching saved routing session.
# The importer completes the short local 0.8 mm VM connection.
.cache/cad/kicad-10.0.6-x86_64-lite.AppImage python3.11 electronics/generate.py
.cache/cad/kicad-10.0.6-x86_64-lite.AppImage python3.11 electronics/generate.py --import-session electronics/out/carrier.ses

# Remove only unused vias identified by a fresh native DRC report; rerun DRC below.
.cache/cad/kicad-10.0.6-x86_64-lite.AppImage kicad-cli pcb drc --format json --schematic-parity -o electronics/out/drc.json electronics/carrier.kicad_pcb
.cache/cad/kicad-10.0.6-x86_64-lite.AppImage python3.11 electronics/generate.py --clean-dangling-vias electronics/out/drc.json

# Attach local models and export the physical pad coordinates.
SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt .cache/cad/kicad-10.0.6-x86_64-lite.AppImage python3.11 tools/prepare-pcb-models.py
python3 tools/export-electronics.py --kicad .cache/cad/kicad-10.0.6-x86_64-lite.AppImage
/tmp/axiom-cad-tools/venv/bin/python tools/check-assembly-fit.py
/tmp/axiom-cad-tools/venv/bin/python viewer/export_meshes.py
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

For a changed layout, route the newly generated DSN with Freerouting 2.4.1,
then import its resulting session instead of the old one. Motor breakouts are
locked 0.30 mm necks; default motor trunks are 0.8 mm. Do not replace these
with unrestricted fine-pitch traces just to obtain a successful route.

```sh
java -Djava.awt.headless=true -jar /tmp/axiom-cad-tools/freerouting.jar --gui.enabled=false -da --api_server.enabled=false --user_data_path=/tmp/axiom-rover-router -de electronics/out/carrier.dsn -do electronics/out/carrier.ses -mp 25 -mt 1
```

Use `reference/raspberry-pi-5/connector-sources.md` for socket dimensions,
`docs/electrical-contract.md` and `docs/harness.svg` for wiring, and
`docs/commissioning.md` for physical acceptance. The carrier must be powered
off, lifted at least 7 mm to disengage the Pi header, and removed with its
perimeter frame. Unbolt the Pi, lift it 2 mm, then slide it through the side
opening. Sensor and
power harnesses require rated contacts, polarity checks and strain relief.
