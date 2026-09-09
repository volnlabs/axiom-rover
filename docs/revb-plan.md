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
