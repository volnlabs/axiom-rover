# Third-party design sources

`electronics/Rover.pretty/*.kicad_mod` are copies of the KiCad footprint library shipped with KiCad 10.0.6. Original library families are recorded by `electronics/generate.py` and `electronics/out/assembly-bom.csv`; their shapes have not been redrawn. The upstream KiCad Libraries license is [CC BY-SA 4.0 with the KiCad design exception](electronics/Rover.pretty/LICENSE.md). Attribution: [KiCad Libraries contributors](https://gitlab.com/kicad/libraries/kicad-footprints). See the included license for the design exception and conditions on library redistribution.

Shrike pin assignments are derived from the pinned official Vicharak schematic; source URLs and SHA-256 values are in `docs/electrical-contract.md`. The schematic itself is not vendored here. U1/U2 assignments use Texas Instruments datasheets linked there. Raspberry Pi's mechanical drawing is linked in `docs/mechanical.md`. Their product names remain their owners' names; this is an independent reference prototype.

KiCad, Freerouting and CadQuery are external tools, not project dependencies vendored into Git. The ignored `.cache/` directory may contain locally downloaded tooling. No repository-wide public license is chosen on the user's behalf; retain third-party attribution if the project is later published.
