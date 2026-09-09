# First article, assembly and release evidence

## Procurement release

Revision A outputs in `electronics/out/fabrication-review/` are review Gerbers and separate plated/non-plated drill files, not an order authorization. Request PCBA and PETG printing quotes from the editable sources plus BOM, assembly positions and STEP/STL package. No automatic ordering workflow exists.

Before a production order, resolve actual Shrike, TT motor, caster, L298N, switch/contact-block, pack and compute dimensions against the CAD. Select exact connector housings, contacts and wire sizes. Match PCB library dimensions to the chosen manufacturer drawing, particularly the 16-pin keyed IDC and JST XH vertical headers. The Shrike uses a measured, removable harness adapter; no invented board socket is included. Dry-fit a cheap template or partial print before paying for the full enclosure.

PCB quote basis: 120 × 80 mm, 2-layer FR-4, 1.6 mm nominal, 1 oz copper, 0.25 mm minimum signal width/clearance, 0.7/0.3 mm vias, four 3.2 mm NPTH mounting holes, solder mask both sides, top legend. All parts are on top; 0805 passives, SOIC-8 U1 and SOT-23-5 U2 are SMT, connectors are through-hole. Use exact ISO7721DR **non-F**, not default-low or wide-body substitutions. Review SMT rotation conventions and pin 1 against the assembly drawing before loading an assembler's machine. The included footprint copies are pinned for portability; see `THIRD_PARTY.md`.

Motor current is excluded from the PCB design. Measure or obtain each motor's stall current under a current-limited supply; avoid prolonged stalls. Select a commercial externally charged pack whose full charged-to-empty voltage range is compatible with the motor/driver, then qualify relay DC inductive ratings, fuse, connector and wire ampacity. A nominal 6 V label or an AC relay contact rating does not establish those limits. Independently qualify the base 5 V source and the Pi/Jetson host supply under peak load.

Target the first vendor order at ≤₹24,000 to preserve ₹6,000 (20% of the ₹30,000 cap) for revisions. Current allowances are not quotes and do not guarantee this target; resolve the BOM before ordering.

## Assembly sequence

1. Inspect unpowered PCBA against the schematic and position file: pin 1, component markings, NC pads, echo resistor values and connector order. Check for shorts within each power domain and confirm no host/base ground connection. Do not megger the populated logic board.
2. Fit the board and measured controller/driver fixtures to the base. Keep screws/washers away from the host/base isolation strip and copper. Install motor brackets, sensor bracket, caster and the guarded dual-NC latching stop. Check harness bend radius and access with the tray installed.
3. Build J1–J6 according to the electrical contract, checking numbered pads rather than apparent left/right on a mating plug. Tag both ends. J1 and J3 both have four pins but different meanings: use distinct cable colours/labels and physically segregated routing. Never interchange them.
4. Feed Shrike through its USB power lead from the base 5 V source. J6 supplies only the sensor branch. Supply L298N logic in its documented external-5-V mode, if required. Remove ENA/ENB force-high jumpers and install R5H/R6H directly at the driver's enable inputs so an unplugged carrier harness leaves both low.
5. Wire S1A through J5 to the FPGA and RP2040 observe input. Wire the electrically separate S1B, F1 and K1 to interrupt motor power. Test contact action and wire-break behavior before connecting motors. Route the motor loop separately; its return meets base ground at the L298N, never at host ground.
6. Complete logic-only checks below before fitting the wheels-raised stand and enabling any motor supply. Install and remove battery packs with power off; use commercial external chargers away from the robot. Fasten packs so they cannot contact circuitry or shift into wheels.

## Bench evidence matrix

All rows start **NOT RUN**. Record an explicit acceptance limit before a powered test; unresolved limits are release blockers, not automatic passes. Logic-low/high limits come from the selected receiver datasheet and FPGA timing limits from the versioned firmware/bitstream contract. No timing maximum is inferred from this CAD.

| Case | Injection and measurement | Required observation |
|---|---|---|
| Unpowered continuity | Meter all harness pins, NC pins, rails and ground domains | Exact pin map; no short or cross-domain ground tie |
| Partial power | Host-only, base-only, sensor-5-V-only and both powered | No unacceptable backfeed; U1 idle state correct; U2 output does not power the unpowered 3.3 V domain |
| Safe start | FPGA blank/reset, RP reset, host reboot, stop pressed | ENA/ENB remain low; no motor motion |
| UART transport | ≥1,000 qualified protocol frames plus malformed/truncated/replayed/stale frames | Valid frames accepted as defined; rejected traffic never renews authority |
| Physical logic stop | Open S1A or break its wire with commands active | Both gated outputs low within the declared FPGA contract |
| Independent power stop | Open S1B with logic still commanding motion | K1 removes VS; record coil/VS/current drop-out and wheel coast-down |
| Watchdog/lease | Stop host traffic, stall Linux work and reset RP | Enable-low occurs within the declared expiry bound without renewed motion on reconnection |
| Driver unplug | Remove J4 with logic power present, motor supply disabled | Driver-end resistors hold both enables low |
| Sensor | Known distances, no echo, stuck echo and sensor power cycling | Calibrated error recorded; invalid/stale measurements cause the policy's bounded fallback |
| Wheels raised | Start/stop/reverse at initially limited duty/current | Correct direction; acceptable current, voltage sag and driver temperature |
| Compute swap | Power down, replace tray, rerun preceding cases | Same actuator wiring and safety behavior; new compute identity recorded |
| Floor run | Only after prior rows pass, supervised clear test area | Stable caster/traction, stop access, secured packs and measured stopping distance |

Use a logic analyzer on J2 breakout pins 3/12 (stop), 13/14 (gated enables), 10/11 (UART), and base ground. The internal RP GPIO14/15 raw-PWM-to-FPGA link is **not** brought onto this carrier: observe only at a qualified Shrike test pad/fixture and do not reroute it to the driver. Avoid clipping an earth-referenced instrument across the isolation domains. Capture motor VS/current separately with appropriately rated instrumentation.

For each run save: UTC time; board, harness and mechanical revisions; AxiomOS commit; RP firmware and FPGA bitstream SHA-256; timing manifest; host/SoC/Linux/driver versions; pack voltage/state; current limit; sensor calibration; instrument/sample rate; case, bound, measured maximum and verdict; raw UART/analyzer/scope files. Store real evidence under `evidence/<run-id>/`. No synthetic readings or emulator results count as physical passes.

## Software gate

The existing AxiomOS Shrike code explicitly remains safe-low pending the validated FPGA and runtime integration. Keep it that way until those gates pass. This standalone repository supplies hardware and test procedures; it does not claim to implement or flash that missing software. Update `release-gates.json` only with links to real review or measurement evidence, never because a CAD checker returned zero errors.
