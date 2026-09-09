# Reproduce and edit

Open `electronics/carrier.kicad_pro` in **KiCad 10.0.6**. The schematic, routed board, custom symbol library and copied footprints are editable and self-contained. No AxiomOS checkout is required. `mechanical/axiom_rover.py` is editable parametric **CadQuery 2.6.1** source; STEP is exchange CAD, STL is the print mesh. No `.blend` file or FreeCAD constraint tree is claimed.

## Check and export an edited board

```sh
python3 tools/export-electronics.py --kicad kicad-cli
python3 tools/check-artifacts.py
```

The export script first requires zero ERC and zero DRC/connectivity/schematic-parity issues, then exports SVG, XML netlist, Gerbers, separate PTH/NPTH drill files, SMT positions, bare-board STEP (no component models), source SHA-256 manifest and a **review-only** fabrication ZIP. Logs preserve native checker output. It does not approve ordering. `check-artifacts.py` detects stale electrical reports and mis-totaled cost rows as well as failed reports.

For the locally downloaded portable KiCad, use:

```sh
python3 tools/export-electronics.py --kicad .cache/cad/kicad-10.0.6-x86_64-lite.AppImage
```

The cache is ignored by Git; a clone needs its own KiCad installation. On this laptop the AppImage supplies both `kicad-cli` and `python3.11` with `pcbnew`, avoiding a system-wide install. Native Linux `kicad-cli` and a Python interpreter with `pcbnew` work too. See [official KiCad downloads](https://www.kicad.org/download/linux/) and [CLI documentation](https://docs.kicad.org/10.0/en/cli/cli.html).

## Regenerate initial layout (overwrites CAD edits)

Only run this when changing the generator, not after manually editing the KiCad board. Save your edits in Git first.

```sh
.cache/cad/kicad-10.0.6-x86_64-lite.AppImage python3.11 electronics/generate.py
java -Djava.awt.headless=true -jar /path/to/freerouting-2.4.1.jar \
  --gui.enabled=false -da --api_server.enabled=false \
  --user_data_path=/tmp/axiom-rover-router \
  -de electronics/out/carrier.dsn -do electronics/out/carrier.ses -mp 10 -mt 1
.cache/cad/kicad-10.0.6-x86_64-lite.AppImage python3.11 electronics/generate.py \
  --import-session electronics/out/carrier.ses
python3 tools/export-electronics.py --kicad .cache/cad/kicad-10.0.6-x86_64-lite.AppImage
```

The generator uses the installed KiCad footprint libraries on the initial rebuild (bundled in the portable package). Net/pin identities are deterministic. Freerouting performs the routing; its automatic neck-downs are widened to the specified 0.25 mm minimum during import, then checked by KiCad. Never assume an arbitrary new placement will pass after routing. The full-height 2 mm copper keepout under U1 must remain intact on both layers; it is functional low-voltage domain separation, not a high-voltage insulation certification. [Freerouting CLI documentation](https://github.com/freerouting/freerouting/blob/master/docs/command_line_arguments.md).

`--schematic-only` regenerates the schematic without changing routed PCB geometry; export checks will catch changed connectivity. The generators are convenient source for this prototype, not a replacement CAD framework.

## Mechanical regeneration

Use Python 3.12 with a virtual environment:

```sh
python3.12 -m venv .venv
.venv/bin/pip install -r mechanical/requirements.txt
.venv/bin/python mechanical/axiom_rover.py --output mechanical/out
python3 tools/check-artifacts.py
```

The generator exports a named STEP assembly, separate STL print parts, SVG drawing, PNG preview and geometric-check JSON. Hardware envelopes remain unmeasured placeholders until the actual supplier parts are fitted. Geometry checks do not establish print tolerances, strength, stop access under load, motor ratings or thermal behavior.

Optional preview regeneration uses an installed SVG renderer:

```sh
rsvg-convert -w 1800 -o electronics/out/carrier-top.png electronics/out/carrier-top.svg
rsvg-convert -w 2200 -o electronics/out/schematic/carrier.png electronics/out/schematic/carrier.svg
```

Tool versions used for this review: KiCad 10.0.6, Freerouting 2.4.1, CadQuery 2.6.1, Matplotlib 3.10.6, Pillow 11.3.0. Generated hardware files are committed; caches, CAD lock files and personal settings are ignored. Local working directories or absolute paths appearing in native tool logs are provenance only, not project dependencies.
