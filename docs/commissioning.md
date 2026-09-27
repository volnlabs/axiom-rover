# Rev B.1 first article and commissioning

All entries are **NOT RUN**. This procedure creates evidence; it does not
authorize fabrication, energizing a motor, or a release until the recorded
acceptance limits pass.

## Before power

1. Inspect the 160 x 100 mm carrier, bottom-side `ESQ-120-24-G-D`, and both
   `SSW-119-01-G-S` Shrike sockets against the current schematic and
   `reference/raspberry-pi-5/connector-sources.md`. Check connector pin labels,
   three top fiducials and low-current through-hole ground thermal relief.
2. Dry-fit Pi 5, carrier, and Shrike. Confirm the nominal 16.5 mm carrier
   underside gap, socket engagement, no cooler collision, and J1/J2/J4 pin-1
   orientation. To remove Pi, power off, lift the unscrewed carrier at least
   7 mm to disengage J1, remove the carrier and perimeter frame, unbolt the Pi,
   lift it 2 mm, then slide it left through the service opening. Do not slide a
   mated header sideways or force sockets.
3. Meter every J2/J4 connection in `electrical-contract.md` against the
   delivered Shrike. Confirm buffered `FAULT_FPGA_N` reaches J2-19/F_GPIO7 and
   `FAULT_RP_N` reaches J4-4/RP GPIO28. Confirm Pi pins 2 and 4 are NC.
4. Confirm continuity and polarity for motor, encoder, HC-SR04, IMU, fuse,
   stop contact, and relay coil. Motor lead order, encoder phase, and encoder
   CPR are unknown until measured.
5. With no power attached, verify no short between `H_GND` and `BASE_GND`, no
   6 V-to-logic short, and correct NC stop behavior at J5/U3 `nSLEEP`.
6. Inspect top-accessible `H_GND`, `BASE_GND`, `HOST_3V3`, `BASE_3V3`,
   `BASE_5V`, `MOTOR_6V`, `ESTOP_N`, `DRV_FAULT_N`, `SENSE_L` and `SENSE_R`
   pads. Meter their net identity and check probe clearance before power.

## Power and safety sequence

1. Power Shrike only through USB-C. Keep Pi 5 V pins 2/4 disconnected.
2. Power Pi and base logic separately. Check isolated UART, HC-SR04 echo
   buffer, encoder 3.3 V, and IMU I2C pull-ups before attaching 6 V.
3. Test open stop-loop, broken stop-loop, and reset with motor 6 V disabled.
   U3 `nSLEEP` must be a stop level; it must not carry PWM.
4. Verify the independent fuse/relay stop path removes `MOTOR_6V` at J7 while
   logic remains powered. Record relay drop-out and rail decay.
5. On a wheels-raised stand, use a current-limited 6 V source and low duty.
   Establish motor polarity and encoder phase. Do not run a prolonged stall.

## Evidence matrix

| Case | Record | Required result |
|---|---|---|
| Socket fit | gap, engagement, photos | no interference or forced seating |
| Unpowered continuity | full connector pin map | exact net map; no host/base ground tie |
| Assembly | solder and inspection record | reflow SMD first, hand-solder through-hole parts afterward; inspect joints and labels |
| Probe access | pad identities and photos | all ten top pads reachable without bridging adjacent nets |
| Partial power | Pi-only, Shrike-only, sensor-5-V-only | no unacceptable backfeed |
| Fault observation | force/observe DRV fault | both F_GPIO7 and RP GPIO28 see their buffered active-low fault |
| Logic stop | open/break J5 loop | `nSLEEP` stop level and gated inputs low |
| Independent stop | open external stop path | J7 motor 6 V removed without software participation |
| Sensors | distance, no/stuck echo; IMU/INT | measured behavior and stated limit |
| Encoder | low-energy rotation both directions | measured phase/order; CPR recorded if derived |
| Wheels raised | low-duty start/stop/reverse | direction, current, sag, temperature, fault state |
| Floor run | supervised run after prior passes | stop distance and stable wiring |

For each run retain time, carrier/harness revision, available Pi/Shrike/FPGA
software identifiers, source voltage, current limit, instrument, acceptance
limit, raw captures, measurement, and verdict. A CAD check or software build
cannot substitute for physical records.

## Release state

Fabrication, physical test, and motion release remain **false** until real
evidence is attached. No Pi, RP2040, or FPGA firmware is claimed implemented
or flashed by this hardware repository.

## Controller and measurement acceptance

Use the independent [bench fixture](bench.md) to prepare wire vectors and check
logic captures. Offline fixture success is not a physical acceptance result.

Motion remains blocked until the existing AxiomOS host, RP2040 adapter and FPGA
bitstream have a validated timing manifest, atomic command/watchdog/e-stop
handling, explicit rearm after stop or driver fault, and real Pi RP1-UART support.
Record expiry/watchdog/stop bounds before testing; use the tighter specified
bound as the limit, not the best observed trace. After `nSLEEP` rises, allow
at least the DRV8833 datasheet wake-up time (1 ms) before permitting PWM.

Exercise expired, malformed, repeated and out-of-order commands, UART unplug,
host reset/stall, RP reset, FPGA unconfigured/reset, and stop release without
rearm. Each must preserve or enter the specified coast/off state. Capture all
four DRV inputs, nSLEEP, motor current and the independent relay response.
With motor power absent, deliberately drive each observation GPIO incorrectly
through its 1 kΩ resistor and confirm it cannot raise hardware nSLEEP or mask
the other controller's stop/fault signal. Restore inputs before motion tests.

Calibrate left/right wheel circumference and quadrature counts per output
revolution; do not infer x4 counts from the seller's “11 pulses” wording. Record
IMU axis orientation/bias and HC-SR04 timeout/no-echo behavior. Start below
0.2 m/s on an indoor level floor and keep total rover mass at or below 2 kg;
these are design targets to qualify, not measured capabilities.

Use a current-limited bench supply first. Measure nominal 1 A current chopping,
start current, both-channel driver/sense-resistor temperatures, VM ripple and
stop/reverse overshoot before choosing a commercial motor pack/regulator.
C8 470 µF, 16 V and D1 SMBJ6.0A still need exact manufacturer/order-code
selection before fabrication. Verify the Rev B.1 sense and capacitor placement
targets in CAD; bench captures are still required for electrical acceptance.
C5's effective ceramic capacitance at bias, C8's energy/rail-decay behavior,
and D1's pulse temperature need qualification. Keep every rail within its part's
recommended limits, not merely absolute maximum ratings. A nominally 6 V
battery label does not establish a regulated 6 V output.

For partial-power cases, compare measured leakage, rail rise and receiver
levels to the selected parts' datasheet limits and record the actual limits in
the test log. For Pi, also capture USB-C voltage/current under sustained compute
load. Check the stop button, fuse, coil clamp and K1 normally-open contact with
host and controller absent: software must not be necessary to remove motor power.
