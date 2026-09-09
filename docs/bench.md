# Rev B controller bench

This fixture belongs to the rover repository. AxiomOS remains the owner of the
host, RP2040 firmware and FPGA implementation; this work does not edit, replace
or flash them. The first milestone is **motor power disconnected**, with measured
logic behavior. Generated traffic and synthetic traces are software test inputs,
not measurements of a Pi, Shrike or motor.

## Control contract

Use the existing isolated Pi UART to RP2040 and Shrike's existing internal
RP2040-to-FPGA bus. RP2040 is the sole command authority for Rev B. The FPGA
generates the two PWM gates and expires commands using its local clock. Runtime
SPI on the internal configuration wires requires explicit ownership after FPGA
configuration; merely loading a bitstream does not implement a runtime interface.

Direction and PWM must refer to the same accepted command. For each update that
changes direction: mask PWM, obtain confirmation that it is disabled, change
direction, observe the specified settling interval, and only then enable the
matching unexpired command. Stop, fault, expiry or reset cancels an in-progress
update. An old acknowledgement must never enable a newer command. RP2040 must
not keep renewing a motion lease after host commands expire.

Startup, unconfigured FPGA, expired commands and controller resets must leave
the gates low. Emergency stop and driver fault latch a stopped state; releasing
the input does not authorize motion. Require explicit rearm and a fresh command.
After hardware nSLEEP rises, allow at least the DRV8833's specified 1 ms wake-up
time before enabling PWM. Reject incomplete, malformed, repeated and reordered
commands without extending an existing lease.

The FPGA watchdog cannot detect loss of its own clock. The independent physical
stop still removes motor power. Automatic protection against a frozen FPGA would
require an independently clocked watchdog or equivalent hardware; Rev B does not
claim that coverage. Direct Pi-to-FPGA SPI is deferred until the existing path is
measured and a separate carrier revision is justified.

### Interface baseline and handoff to AxiomOS

The inspected committed interface is AxiomOS
`4f5aa9037832b9ee27145c5ffc87f4c3ca707e18`. Wire compatibility is checked against
that immutable snapshot, not the concurrently edited AxiomOS working tree.
UART is 115200 8N1, with `7e 01 TYPE LEN PAYLOAD CRC_LE` and CRC16-CCITT/FALSE
over version through payload. The existing protocol has no separate ARM opcode:
soft-stop release followed by a strictly newer setpoint is its rearm sequence.

There are runtime prerequisites that a matching packet format does not resolve:

- The current RP2040 entry point intentionally remains safe-low without a
  validated bitstream/timing manifest and atomic adapter.
- The current generic link watchdog refreshes liveness on heartbeats; this can
  retain the last setpoint. The completed control path must demonstrate bounded
  command authority when heartbeats continue but fresh motor intent stops.
- The current SPI READY/COMMAND_VALID status does not itself prove that PWM was
  masked before an RP direction update. The completed adapter/FPGA must expose
  and honor that confirmation, or supply an equivalent measured interlock.
- Runtime reset, driver-fault recovery and rearm semantics must be verified
  end-to-end. The fixture does not add a new protocol or emulate missing firmware.

These are acceptance requirements for the separately completed AxiomOS work,
not changes made by this repository. A physical run must identify the actual
flashed artifacts, even when they are newer than this wire snapshot.

## Before capturing

Copy [the case template](../bench/case-template.json) for each acquisition. Its
null fields deliberately fail validation: fill them with the actual identities
and predeclared timing limits. `event_us`, `stop_deadline_us` and
`observe_until_us` are **absolute timestamps on the capture's microsecond axis**;
the permitted stop latency is `stop_deadline_us - event_us`. Extend the hold
window through stop/fault release to check that releasing it does not restart.
Set each case's `max_pre_event_drive_gap_us` from the validated PWM period and
acquisition margin. The checker requires a recent drive-high observation within
that distance before the stimulus, with the corresponding direction still active
immediately before it. This allows a normal PWM low phase while rejecting drive
activity that ended well before the test event.
For a startup-only acquisition, use `off_intervals: []`; the report then checks
startup without claiming any active-stop case passed. Choose a positive startup
observation window that covers the controller's specified boot behavior.

For physical traces the checker reserves
`2 * max(time_resolution_us + timing_uncertainty_us)` across the listed
instruments. Measured mask/settling and wake-up intervals must exceed their limits
by that margin, stopping must occur that much before the deadline, and the capture
must extend that much beyond the hold window. `max_sample_gap_us` is the largest
permitted gap between recorded samples; choose it from the shortest event that
must be resolved. A declared gap allowance is not proof that no pulse was missed.

Follow [commissioning](commissioning.md) for unpowered continuity, delivered-board
pin verification, independent supplies and partial-power checks. Leave the motor
6 V input physically disconnected for this phase. No connected Shrike/serial
adapter was visible during fixture preparation on 2026-09-10; physical cases are
NOT RUN.

Record carrier and Shrike revision, Pi model, software commits, flashed binary
and bitstream SHA-256, timing manifest, power conditions, instrument model and
firmware, probe threshold, sample interval, timing uncertainty and calibration.
Set acceptance bounds from the controller timing manifest and component limits
**before** acquiring a trace. Preserve raw instrument exports alongside any
normalized CSV; retain the conversion command and channel mapping.

Probe the base side of the isolator with a base-referenced logic analyzer. Do not
bridge host and base grounds with analyzer leads or a shared, non-isolated USB
ground. A typical eight-channel analyzer cannot simultaneously record all signals
used by the full checker; use sufficient channels or a qualified synchronized
capture arrangement. Separate unsynchronized acquisitions do not prove ordering.

## Physical cases

| Case | Stimulus and required observation |
|---|---|
| Startup | Power/reset with no valid command: PWM and gated driver inputs remain low. |
| Command path | A fresh authorized command reaches the intended direction and PWM; retain UART and internal-bus captures as well as output traces. |
| Reverse | Both directions tested per wheel; PWM is confirmed low before direction changes and stays masked for the declared interval. |
| Expiry / UART loss | Establish active output, then stop valid host traffic; gates fall within the declared bound and remain off. |
| Intent loss with live link | Establish active output, then continue heartbeats but stop fresh motor intent; the declared command-authority bound still expires. |
| Invalid traffic | While active, inject a bad checksum, incomplete frame, duplicate and reordered command; none extends the valid command's expiry. |
| Controller resets | Reset RP2040 and FPGA separately from active output; stop within the declared bound, with no automatic restart. |
| Emergency stop | Open and break the NC loop; nSLEEP follows the physical stop and PWM/output gates become low within their bounds. Releasing the loop leaves motion disarmed. |
| Driver fault | Assert fault from active output; both receivers observe it and gates remain off after fault clears, until explicit rearm. |
| Rearm | A deliberate rearm followed by a fresh command can restart only after the required wake-up and interlock delays. |

For a stop test, start the capture before active output and keep recording through
the entire specified hold window, including stop/fault release where applicable.
An all-zero recording cannot demonstrate that an active controller stopped.
Digital logic captures do not measure motor-current removal, contact opening,
analog backfeed, thermal limits or stopping distance.

The automated checker evaluates the declared output windows and wiring/interlock
rules. It cannot infer a correct stimulus from a case name, authenticate instrument
metadata, or prove that the requested PWM duty was applied. Correlate the raw
command and acknowledgement captures, measure duty/frequency, and record the
stimulus independently before accepting the end-to-end case. A matching wire
codec alone does not prove the AxiomOS host or its RP1 UART driver worked.

## Run the fixture

From the rover repository root:

```sh
python3 -m unittest discover -s bench -v

# Optional integration test against the external, read-only interface snapshot.
AXIOMOS_REPO=/home/utkarsh/Work/axiomOS python3 -m unittest discover -s bench -v

# Print synthetic packets only; neither command opens a serial device.
python3 bench/wire.py vectors
python3 bench/wire.py encode '{"type":"estop","assert":true}'

# A supplied synthetic recording exercises the checker without hardware.
python3 bench/trace.py bench/examples/synthetic-case.json \
  bench/examples/synthetic-capture.csv --output /tmp/rover-synthetic-report.json

# Decode a raw byte capture from one UART direction (binary, not ASCII hex).
python3 bench/wire.py decode /path/to/base-rx.bin

# Read a committed interface snapshot, compile its codec in this repo's cache,
# and compare it to the fixture. Requires git and rustc; AxiomOS is read-only.
python3 bench/check_compat.py --repo /home/utkarsh/Work/axiomOS \
  --commit 4f5aa9037832b9ee27145c5ffc87f4c3ca707e18

# After filling a copied manifest and acquiring the corresponding capture:
python3 bench/trace.py /path/to/case.json /path/to/capture.csv \
  --output /path/to/report.json
```

The logic CSV must have exactly these columns. Times are microseconds and signal
values are `0` or `1`; retain an initial sample and an explicit final sample.

```text
time_us,estop_n,fault_n,pwm_l,pwm_r,l_in1,l_in2,r_in3,r_in4,drv_ain1,drv_ain2,drv_bin1,drv_bin2,nsleep
```

`estop_n` is the hardware stop source, `fault_n` is the driver's fault source,
`pwm_l/r` are the FPGA gate outputs, and `l_in1/l_in2/r_in3/r_in4` are the RP
direction signals. The four `drv_*` signals are U4's gated outputs at U3.
`nsleep` is U3's stop input; software expiry must stop PWM even while this
hardware-stop input stays high. Check each buffered stop/fault receiver separately
as required by commissioning; those receiver channels are not in this CSV.

The saved [wire comparison](../bench/evidence/wire-compatibility.json) identifies
the inspected AxiomOS commit, source digest, fixture hashes and Rust compiler.
It covers six UART encodings and twelve decoder streams, including corruption,
resynchronization, incomplete frames and an in-payload sync byte. It establishes
software wire compatibility for those cases only. The FPGA packet fixture is
checked against the published source golden vector; this is not a synthesized
bitstream or a physical SPI timing result.

The [worked capture](../bench/examples/synthetic-capture.csv),
[case definition](../bench/examples/synthetic-case.json) and
[saved report](../bench/examples/synthetic-report.json) are synthetic. Their
short timing values exercise software branches and must not be used as physical
acceptance limits. No firmware or RTL executes when generating those signals.

## Progression

1. Exercise the fixture's offline tests and check compatibility with the supplied
   AxiomOS interface snapshot, without building in or writing to AxiomOS.
2. When its firmware and validated bitstream are available, complete the
   disconnected-motor cases above and retain their raw evidence.
3. Qualify one motor, then both, on the raised-wheel stand with a current-limited
   supply and the independent stop. Measure current, temperature, encoder phase,
   counts and stop/reverse rail behavior using the commissioning procedure.
4. Confirm actual Pi/Shrike/socket/cooler fit and use those measurements to settle
   any PCB or enclosure revision before fabrication release.

The fixture never sets `release-gates.json`. Physical release remains a separate
evidence review. Linux serial traffic proves the transport only; an AxiomOS
release test must identify the AxiomOS build that mediated the commands.

Sources: [Rev B electrical contract](electrical-contract.md),
[Vicharak internal bus guide](https://blog.vicharak.in/7-ways-your-mcu-can-talk-to-fpga-on-shrike/),
[TI DRV8833 datasheet](https://www.ti.com/lit/ds/symlink/drv8833.pdf).
