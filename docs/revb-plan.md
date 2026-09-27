# Rev B implementation and evidence ledger

Accepted design: independent 6 V, <=2 kg indoor rover; ThinkRobotics
MOT3001-6V60RPM encoder motors, Pololu 3690 80 mm wheels, onboard
DRV8833PWP with nominal 1 A/channel current regulation, Pi 5 top carrier,
physical Shrike R0.4 sockets, HC-SR04, two encoders and external I2C IMU.
All work stays in this repository. No AxiomOS firmware is changed or flashed.

- [x] Replace electrical carrier, route and run native KiCad ERC/DRC/parity.
- [x] Replace mechanical mounts, integrate controller/socket geometry and inspect clearances.
- [x] Regenerate populated board, assembly, six-sided interactive viewer and drawings.
- [x] Update BOM, harness contract, commissioning and source provenance.
- [x] Independent review and reproducible artifact/browser checks.

Ruling: use a 160 x 100 mm carrier with a cooler aperture and an outboard
Shrike bay. The former 120 x 80 mm harness board did not allocate space for
both mating boards, cooling and motor-current copper. Move the host power
pack below the compute tray. Cost if fit is wrong: revise the carrier/tray
before fabrication; physical dry-fit remains required.

Baseline: commit 57851dc, clean checkout; tools/check-artifacts.py passed.
Branch: hardware/shrike-pi5-revb. Work remains in the user-selected checkout
so existing local viewer URLs and CAD tool cache remain valid.

Physical tests, vendor quotes and orders are not available from CAD work.
Fabrication and motion release stay false until evidence is attached.

Electrical evidence: native KiCad 10.0.6 ERC/DRC/parity reports are clean.
A separate scratch regeneration from `electronics/generate.py` and the saved
router session also produced zero DRC, connectivity and parity findings.
The saved importer includes the local VM connection; unused vias are removed
only by UUIDs in the fresh DRC report.

Final review evidence: `mechanical/out/mechanical_checks.json` and
`mechanical/out/assembly-fit.json` pass with no unexpected intersections.
`viewer/browser-check.json` records 34 passing checks, including every side,
zoom, part hiding and correct stack order in the exploded view.
`tools/check-artifacts.py` passes source/artifact freshness, connector maps,
reference hashes and BOM arithmetic. Independent electrical review and the
parent mechanical review were incorporated; physical release gates remain false.

## Rev B.1 reliability and serviceability review

This is the follow-on layout review; the Rev B evidence above is historical.
Keep the 160 x 100 mm outline, mounting holes, cooler aperture, every connector
position and pinout, 0.20 Ω sense resistors, 12 U3 thermal vias, isolated host
and base grounds, and 0.8 mm motor trunks. Move R7/R8 beside U3 so each sense
trace is at most 7 mm; limit U3-to-capacitor pad-centre routed lengths to
4 mm for VM/VINT and 3 mm for VCP. Add ten top-accessible electrical test pads listed in
[the contract](electrical-contract.md), three top fiducials, low-current
through-hole ground thermal relief and connector pin labels. Reflow SMD before
hand-soldering through-hole parts.

- [x] Regenerate B.1 CAD/artifacts; check placement, routing, ERC/DRC and parity.
- [x] Review assembly access, drawings, viewer and connector labels in CAD.
- [ ] Source exact manufacturer/order codes for generic D1 SMBJ6.0A and C8
      470 µF, 16 V; verify footprints and availability.
- [ ] Record physical fit, partial-power/backfeed, regeneration, thermal,
      stop-path and current-chopping evidence under [commissioning](commissioning.md).

The Rev B.1 review does not release fabrication or powered motion. Physical
evidence and all release-gate values remain pending.

Recorded B.1 CAD evidence (2026-09-27): KiCad 10.0.6 reports zero ERC, DRC,
unconnected-item and schematic-parity findings. A separate scratch regeneration
from the generator and saved session also passes. The saved session includes
the TP5 probe branch; the generator retains the locked driver routes.

| Top-copper pad-centre route | Length | Target |
|---|---:|---:|
| U3–R7, SENSE_L | 5.385 mm | ≤7 mm |
| U3–R8, SENSE_R | 5.385 mm | ≤7 mm |
| U3–C5, VM | 2.462 mm | ≤4 mm |
| U3–C7, VINT | 3.494 mm | ≤4 mm |
| U3–C6, VCP | 2.997 mm | ≤3 mm |

The independent regression freezes all 13 Rev B connector pin maps and checks
placement, outline/cooler arcs, 12 thermal vias, ten probe pads, ground separation,
fiducials, reliefs and route lengths. Injected connector swaps and cut sense
routes are rejected. The populated STEP has no unexpected frame, post or shell
intersections. Viewer checks pass 42/42, UI checks 77/77, and the static bundle's
links, routes, headers and LFS preflight pass. The procurement BOM still has
47 fitted parts; the probe pads and fiducials need no purchased components.
