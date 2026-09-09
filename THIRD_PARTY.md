# Third-party design sources

`electronics/Rover.pretty/*.kicad_mod` are copies of the KiCad footprint library shipped with KiCad 10.0.6, except `Pi5_Socket_2x20` and `SSW-119-01-G-S`, which are original local footprints derived from the cited Samtec dimensions and Pi STEP datum. Original library families are recorded by `electronics/generate.py` and `electronics/out/assembly-bom.csv`; Standard-library pad shapes have not been redrawn; local model paths are updated. The upstream KiCad Libraries license is [CC BY-SA 4.0 with the KiCad design exception](electronics/Rover.pretty/LICENSE.md). Attribution: [KiCad Libraries contributors](https://gitlab.com/kicad/libraries/kicad-footprints). See the included license for the design exception and conditions on library redistribution.

Shrike pin assignments are derived from the pinned official Vicharak schematic; source URLs and SHA-256 values are in `docs/electrical-contract.md`. The pinned vendor PCB and STEP files are retained under `reference/`. U1/U2 assignments use Texas Instruments datasheets linked there. Raspberry Pi's mechanical drawing is linked in `docs/mechanical.md`. Their product names remain their owners' names; this is an independent reference prototype.

Unmodified official Shrike R0.4 PCB/STEP files and their CERN OHL v1.2 license, and unmodified Raspberry Pi Ltd reference mechanical PDFs, are retained in `reference/`. See its README and `sources.json` for provenance and hashes. The Raspberry Pi drawings retain their original notices and are not covered by the Shrike license.

KiCad, Freerouting and CadQuery are external tools, not project dependencies vendored into Git. The ignored `.cache/` directory may contain locally downloaded tooling. No repository-wide public license is chosen on the user's behalf; retain third-party attribution if the project is later published.

`electronics/models/` includes KiCad library package STEP references, attributed
in `viewer/model-sources.json`. Most carry CC BY-SA 4.0 with the KiCad design
exception. `D_SMB.step` and `CP_Radial_D8.0mm_P3.50mm.step` instead carry
GPLv3-or-later with the design exception embedded in their headers. Original
model notices and GPLv3 are retained in [viewer/model-licenses.txt](viewer/model-licenses.txt).
Samtec
socket bodies and the simplified JST VH body are original nominal geometry
created by `viewer/export_meshes.py` from cited manufacturer dimensions; they
are not manufacturer-certified STEP assemblies. The DRV8833 uses KiCad's
TSSOP-16-1EP 4.4×5 mm / EP3.4×5 mm reference model for the matching package
body; its exact PWP land pattern remains the separate PCB footprint.
