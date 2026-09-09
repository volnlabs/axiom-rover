# Vendor reference files

Retrieved 2026-09-09. These are vendor design/reference data, not measurements of the user's hardware. Source hashes are in `sources.json`.

- `shrike-r04/Shrike-lite.kicad_pcb` and `Shrike-lite.step`: unmodified Vicharak files from commit `763d0a7dd9ebdfc3f61de148457d5c34f112f61e`, `hardware/shrike-lite/kicad/v1_r0.4`. Hardware license: included `shrike-r04/LICENSE_HW.md` (CERN OHL v1.2).
- `raspberry-pi-5/*.pdf`: unmodified Raspberry Pi Ltd mechanical drawings, with their original reference-only notes. These have not been re-licensed by this project.

The Shrike R0.4 PCB outline is approximately **25.4×58.5 mm**, corner radius 2 mm. Board-coordinate bounds are approximately X=135.801105…161.201095, Y=75.7536…134.2536 mm. Socket rows J2/J4 have **19 positions each**, **2.54 mm pitch**, and **22.86 mm row separation**. J2 pin 1 is at (137.071095,86.8494); J4 pin 1 at (159.931095,86.8746). Pin numbers increase toward increasing PCB Y. The published rows have a small **0.0252 mm longitudinal offset**; retain source coordinates and assess connector tolerance instead of silently assuming perfect alignment. USB-C is at the low-Y end. Header drill size on the vendor board is 0.9 mm; the carrier socket drill must follow the selected socket's drawing, not copy the module's drill blindly.

The Pi board is 85×56 mm. With the official drawing's lower-left outline as datum, its M2.5 mounting hole centres are (3.5,3.5), (61.5,3.5), (3.5,52.5), (61.5,52.5), with Ø2.7 holes. The hole grid centre is 10 mm left of the board centre. The Rev B model uses board centre (-37.5,2), with hole X positions -76.5/-18.5 and Y positions +26.5/-22.5 mm.

No source dimensions establish socket engagement, soldered header orientation, actual board revision or enclosure fit by themselves.

The Pi STEP archive RP-010083-CA and its extracted STEP retain Raspberry Pi's
included license. The GPIO and Samtec stack datums are recorded in
[connector-sources.md](raspberry-pi-5/connector-sources.md).

The original Shrike STEP header locations differ from the R0.4 PCB by about
9.46 mm longitudinally after matching the board outline and USB orientation.
It is retained as discrepant vendor reference data. The review assembly uses
PCB-derived Shrike geometry instead; it must not imply that the original STEP
proves socket mating. Header plastic/pin lengths remain nominal until measured.
