# Axiom rover electrical contract — reference prototype

**Revision:** 2026-09-09. This is a build contract for a 120 mm × 80 mm
low-current carrier and removable harnesses, not an assembled-board claim.
It deliberately keeps the existing L298N module, motor current, fuse, relay,
and battery wiring off the carrier.

## Locked boundaries

- Two existing 3–6 V TT geared DC motors, existing replaceable L298N module,
  and one HC-SR04.
- Shrike-lite V1.0/R0.4 is the base controller. Raspberry Pi 5 is the first
  removable host tray; later Linux/Jetson trays use the same `HOST_3V3`,
  `H_GND`, `H_TX`, `H_RX` connector contract.
- `BASE_5V` feeds the Shrike **through its own USB power lead** and the HC-SR04.
  Do not also inject 5 V into a Shrike header or leave USB connected while an
  alternate 5 V path is fitted. `BASE_5V` is not a host supply.
- The host and base are independently powered and have **no carrier ground
  tie**. The UART uses a split-supply isolator; a direct three-wire UART is
  prohibited.
- The compute tray has its own externally charged commercial host-power pack
  or regulated supply. For Pi 5, verify a 5 V / 5 A-capable USB-C PD source at
  the Pi plug under sustained load; an arbitrary USB power bank is not an
  acceptable substitute. [Raspberry Pi's power requirement](https://www.raspberrypi.com/documentation/computers/getting-started.html).
- No 9 V rectangular battery is permitted on the motor or base rails.

## Verified Shrike source and header facts

The source of record is Vicharak Shrike commit
[`763d0a7dd9ebdfc3f61de148457d5c34f112f61e`](https://github.com/vicharak-in/shrike/tree/763d0a7dd9ebdfc3f61de148457d5c34f112f61e),
specifically its [V1/R0.4 schematic directory](https://github.com/vicharak-in/shrike/tree/763d0a7dd9ebdfc3f61de148457d5c34f112f61e/hardware/shrike-lite/kicad/v1_r0.4).
The pinned `Shrike-lite.kicad_sch` SHA-256 is
`4b6cfad3b61666571e231d880c920bc2bb89721aebf7353f8c989fec17f877eb`;
the exported schematic PDF SHA-256 is
`33a022c13739b48370e783fa59b5fccbdfcea8c52b85f8224da0183cdb484140`.
The local pinned-source manifest is
`firmware/shrike/vendor/vicharak-shrike/763d0a7/SOURCE.toml` in AxiomOS.

Vicharak documents that the header and FPGA I/O are 3.3 V only and that
GPIO14/15 are normally internally connected to FPGA GPIO18/17; do not use
them externally. [Official pinout](https://vicharak-in.github.io/shrike/shrike_pinouts.html)
and [hardware overview](https://vicharak-in.github.io/shrike/hardware_overview.html).

The current AxiomOS R0.4 profile, rather than an old roadmap table, assigns:

| Function | Shrike header / net | RP2040 function |
|---|---|---|
| E-stop observe | J2-3 `GPIO5` | input, defense-in-depth telemetry |
| Left direction | J2-4/5 `GPIO6`/`GPIO7` | L298N `IN1`/`IN2` |
| Right direction | J2-6/7 `GPIO8`/`GPIO9` | L298N `IN3`/`IN4` |
| HC-SR04 | J2-9 `GPIO10`, J2-10 `GPIO11` | trigger, echo |
| Base UART | J4-18 `GPIO16`, J4-17 `GPIO17` | RP2040 TX, RX |
| FPGA e-stop | J2-16 `F_GPIO0` | dedicated FPGA input |
| FPGA PWM outputs | J2-17 `F_GPIO1`, J2-18 `F_GPIO2` | left `ENA`, right `ENB` |
| Reserved/no connect | J2-11/12 `GPIO14/15`, J4-15/16 `GPIO19/18` | none on carrier |

J2/J4 are the two 1×19 headers shown in the pinned schematic. The carrier
has an IDC harness connector only; the proposed interposer has **not** been
designed. There is no physical Shrike socket on this PCB. The 2026-09-09
[audit](hardware-audit.md) located the official PCB/STEP: 25.4×58.5 mm outline,
2.54 mm header pitch, 22.86 mm row separation. These sources are saved under
`reference/`; a replacement socket interface still needs to be designed and
checked against the delivered board and selected mating connectors.

## Carrier circuit / net contract

### J1 — host tray, keyed 1×4

| J1 pin | Net | Meaning |
|---:|---|---|
| 1 | `HOST_3V3` | host's regulated 3.3 V; powers only U1 side 1 |
| 2 | `H_GND` | host return; only U1 pin 4 |
| 3 | `H_TX` | host UART TX |
| 4 | `H_RX` | host UART RX |

No `HOST_5V`, motor power, or base ground appears on J1.

For a Raspberry Pi 5 **40-pin GPIO header**, the required harness is:

| Carrier J1 | Pi physical header pin | Function |
|---:|---:|---|
| 1 | 1 | Pi 3.3 V → `HOST_3V3` |
| 2 | 6 | Pi GND → `H_GND` |
| 3 | 8 | Pi GPIO14 TX → `H_TX` → U1 → Shrike GPIO17 RX |
| 4 | 10 | Pi GPIO15 RX ← `H_RX` ← U1 ← Shrike GPIO16 TX |

These are Pi physical pin numbers; Pi GPIO14/15 are unrelated to Shrike's
reserved GPIO14/15. J1 is not a plug-compatible Pi header. The Pi 5 default
primary/debug UART is UART10 on its separate three-pin debug connector;
do not assume `/dev/serial0` reaches physical pins 8/10. The selected OS must
configure the GPIO14/15 UART and keep firmware/kernel/console output off the
rover protocol. For AxiomOS this requires actual Pi/RP1 UART and pinmux support,
not merely copying a Linux configuration setting. Pin mapping is source-based;
runtime communication has not been tested. [Official UART documentation](https://www.raspberrypi.com/documentation/computers/configuration.html#configure-uarts).

### U1 — power-off-safe UART boundary

Fit **TI ISO7721DR**, narrow SOIC-8, non-`F` default-high version.
It is one forward and one reverse channel, suitable for UART, runs from
2.25–5.5 V on either side, and has a default-high output when the input-side
supply is absent—UART idle rather than a false start bit. This is a real
power-domain boundary, not a claim that a direct UART header is hot-plug safe.
[TI ISO7721 datasheet](https://www.ti.com/lit/ds/symlink/iso7721.pdf).

| U1 pin | Net | Connection |
|---:|---|---|
| 1 | `HOST_3V3` | side-1 VCC |
| 2 | `H_RX` | `OUTA`, base → host |
| 3 | `H_TX` | `INB`, host → base |
| 4 | `H_GND` | side-1 ground |
| 5 | `BASE_GND` | side-2 ground |
| 6 | `RP_UART_RX` | `OUTB` → Shrike J4-17 / GPIO17 |
| 7 | `RP_UART_TX` | `INA` ← Shrike J4-18 / GPIO16 |
| 8 | `BASE_3V3` | side-2 VCC from Shrike J2-2 |

`C1` is 100 nF X7R from U1-1 to U1-4; `C2` is 100 nF X7R from U1-8 to
U1-5, each beside its pins. Do not route copper, a plane, mounting hardware,
or a test clip ground across the isolation barrier. The carrier has no
`H_GND`–`BASE_GND` net tie. The datasheet warns that a strongly driven input
can weakly power a floating input-side VCC; the exact wiring above keeps each
input in its own powered domain and never exports `BASE_3V3` to J1.

### J2 — removable base/interposer harness, keyed 2×8

| Pin | Carrier net | Shrike termination |
|---:|---|---|
| 1 | `BASE_3V3` | J2-2 |
| 2 | `BASE_GND` | J2-8 (or J2-13/J4-19) |
| 3 | `ESTOP_N` | J2-3 GPIO5 and J2-16 F_GPIO0 |
| 4 | `L_IN1` | J2-4 GPIO6 |
| 5 | `L_IN2` | J2-5 GPIO7 |
| 6 | `R_IN3` | J2-6 GPIO8 |
| 7 | `R_IN4` | J2-7 GPIO9 |
| 8 | `US_TRIG` | J2-9 GPIO10 |
| 9 | `US_ECHO_3V` | J2-10 GPIO11 |
| 10 | `RP_UART_TX` | J4-18 GPIO16 |
| 11 | `RP_UART_RX` | J4-17 GPIO17 |
| 12 | `FPGA_ESTOP_N` | J2-16 F_GPIO0; same `ESTOP_N` net |
| 13 | `FPGA_PWM_L` | J2-17 F_GPIO1 |
| 14 | `FPGA_PWM_R` | J2-18 F_GPIO2 |
| 15 | NC | reserved |
| 16 | NC | reserved |

The duplicated e-stop entries are one electrical net, split in the interposer
to both listed pins. The FPGA I/O planner/bitstream must bind F_GPIO0/F_GPIO1/
F_GPIO2 before motors are attached; that is a commissioning gate, not an
assumption about the current RTL.

### HC-SR04, all on the base side

`J3` is keyed 1×4: pin 1 `BASE_5V`, pin 2 `BASE_GND`, pin 3
`SENSOR_TRIG`, pin 4 `US_ECHO_5V`. `US_TRIG` is the pre-resistor RP2040 net;
it is not carried to the sensor connector.

**J3 is not pin-for-pin compatible with the HC-SR04 header.** Its harness
must connect J3-1 → sensor VCC, J3-2 → sensor GND, J3-3 → sensor TRIG,
J3-4 → sensor ECHO. The usual sensor header order is VCC, TRIG, ECHO, GND;
verify the actual unit's markings. A straight four-position cable is wrong.

`J6` is a separate keyed 1×2 low-current sensor-power input: pin 1
`BASE_5V`, pin 2 `BASE_GND`. It supplies only the sensor branch; do not use
it to inject 5 V into Shrike headers or host power.

```text
GPIO10 / US_TRIG -- R1 1.0 kΩ -- SENSOR_TRIG / J3-3 -- HC-SR04 TRIG
HC-SR04 ECHO -- R2 2.2 kΩ --+-- U2 A
                              |
                            R3 3.3 kΩ
                              |
                           BASE_GND

U2 = SN74LVC1G17DBVR: pin 1 NC, pin 2 A=divider, pin 3 GND=BASE_GND,
     pin 4 Y=US_ECHO_3V, pin 5 VCC=BASE_3V3
C3 = 100 nF X7R, U2 VCC-to-GND
```

At 5.0 V echo, the divider node is 3.0 V. U2 is deliberately present: its
input accepts up to 5.5 V and its `Ioff` specification supports live insertion,
partial-power-down, and back-drive protection. Thus an HC-SR04 powered from
`BASE_5V` cannot feed the unpowered Shrike 3.3 V rail through GPIO11.
[TI SN74LVC1G17 product/datasheet](https://www.ti.com/product/SN74LVC1G17).
The HC-SR04 requires 5 V; its exact clone must pass a 3.3 V-trigger bench test.
If it does not, add a 5 V AHCT trigger buffer in revision B rather than defeat
the echo protection. [HC-SR04 electrical sheet](https://cdn.sparkfun.com/datasheets/Sensors/Proximity/HCSR04.pdf).

### FPGA gate, L298N logic, and independently effective e-stop

`S1` is a latching **dual normally-closed** emergency-stop switch. Contacts
are electrically independent.

```text
logic contact: BASE_3V3 -- S1A NC -- ESTOP_N -- 10 kΩ -- BASE_GND
                                  |-- GPIO5 observe
                                  `-- FPGA F_GPIO0

motor contact: MOTOR_BATT+ -- F1 -- S1B NC -- K1 coil+ ; K1 coil- -- MTR_GND
                                    K1 coil has correctly-oriented flyback clamp
K1 NO contact: fused MOTOR_BATT+ -> L298N VS; K1 COM from F1 output
```

`J5` is the keyed 1×2 external logic e-stop loop: pin 1 `BASE_3V3`, pin 2
`ESTOP_N`. It terminates only S1A's NC contact. S1B's motor contact remains a
separate, rated high-current harness; it never passes through the carrier.

Opening S1A, breaking its cable, or disconnecting the harness makes `ESTOP_N`
low. The FPGA uses that physical input directly; firmware's GPIO5 observation
is only additional telemetry. Opening S1B de-energizes K1 and removes motor
power without the FPGA, RP2040, host, or UART participating. A diode clamp is
safe but increases K1 release time; measure the final relay's drop-out time.

`J4` is the L298N low-current control harness. Its order is locked:

| J4 pin | Net | L298N terminal |
|---:|---|---|
| 1 | `BASE_GND` | driver GND |
| 2 | `L_IN1` | IN1 |
| 3 | `L_IN2` | IN2 |
| 4 | `R_IN3` | IN3 |
| 5 | `R_IN4` | IN4 |
| 6 | `FPGA_PWM_L` | ENA |
| 7 | `FPGA_PWM_R` | ENB |

Remove any ENA/ENB jumper that forces an enable high. FPGA F_GPIO1/F_GPIO2
are the only ENA/ENB sources; no RP2040 PWM bypass exists. Carrier R5/R6 are
10 kΩ from each FPGA PWM net to `BASE_GND`. The removable L298N-end harness
also fits R5H/R6H, each 10 kΩ from **ENA/ENB at the driver connector** to
`DRIVER_GND` (J4-1), so a disconnected J4 cannot leave an L298N enable
floating. The existing module must be continuity-tested, have its 3.3 V
logic-high acceptance checked, and have its 5 V-logic jumper/direction checked
before wiring. At a 6 V motor input, do not rely on an undocumented onboard
5 V regulator: use the module's documented external logic-5-V mode if it
needs logic power.

`MOTOR_BATT+`, `MTR_GND`, F1, K1 contacts, L298N `VS`, and motor leads are
not carrier nets. Use separately rated, keyed harnesses and a star/reference
join of `MTR_GND` to `BASE_GND` at the L298N power return. Keep that return
away from the host side of U1.

## Board, layout, and enclosure contract

- Carrier outline: 120.0 mm × 80.0 mm. Four NPTH M3 clearance holes, Ø3.2 mm,
  at `(5,5)`, `(115,5)`, `(115,75)`, `(5,75)` mm from the lower-left board
  origin. Keep copper and components clear of the hole keep-out.
- Fit only low-current connectors, U1/U2, R1–R6, C1–C3, and labels. No relay,
  fuse, motor terminal, or battery connector lands on the carrier.
- Place J1/U1 on one board edge and J2/J3/J4 on the other; keep the U1 barrier
  clear. Use keyed, strain-relieved harnesses and label every connector/pin 1.
- The printed base has four M3 bosses for the carrier, an external guarded
  S1 actuator, separate high-current cable channel, and a removable Shrike
  interposer/harness pocket. The compute tray is mechanically separate; only
  J1 crosses between tray and base.

## Commissioning gates and known limits

1. Confirm the delivered Shrike board header orientation/continuity against
   the pinned schematic before making the interposer. Check J2-16/17/18 and
   J4-17/18 specifically; leave GPIO14/15/18/19 open.
2. With either host or base power absent, measure zero unacceptable voltage on
   the absent domain's UART pins. Confirm isolated UART idles high and parses
   the existing protocol unchanged on 1,000 frames.
3. With `BASE_5V` on and Shrike off, confirm U2 output leakage does not raise
   `BASE_3V3`; then verify the HC-SR04 divider is about 3.0 V at 5.0 V echo.
4. Before motors: FPGA unconfigured/reset, e-stop pressed, UART unplugged,
   and L298N logic-only tests must all leave ENA/ENB low.
5. Record each TT motor's documented or measured stall current. Select F1,
   wire gauge, connector, K1 continuous **DC inductive** contact rating, and
   6 V pack/current limit above the combined start/stall requirement. The
   inexpensive 6 V/10 A relay listed in the BOM is only a price reference and
   is not authorized unless its real DC rating exceeds that result.
6. Verify K1 drop-out, FPGA e-stop-to-PWM-low, motor current, L298N temperature,
   and battery sag with wheels raised first. No unattended run and no current
   limit claim is authorized by this contract.
7. Record the motor pack's full discharge voltage range, including its
   charged maximum and transient behavior. A pack marketed as “6 V nominal” is
   not evidence that its voltage remains within the TT motor and L298N limits.
8. On Pi 5, retain a sustained-load capture of voltage at the USB-C plug and
   current from the host pack/regulator. The 5 V / 5 A supply capability is a
   tray power requirement; it is not carried through J1 or shared with base.

## Cost basis

The present allowance is INR 19,862–38,475 for one prototype **excluding the
compute board and instruments**, including PCBA/print allowances and commercial
externally charged base, motor, and host packs. It exceeds the INR 30,000
upper budget; this document does not claim the budget is met. Exact PCB
assembly, shipping, tax, print volume, pack capacity, and the required K1/F1
rating move the result. See `bom/system-bom.csv` for line items and source URLs.

**Quote gate:** before ordering, selected first-order quotes (including host
power, excluding reserve) must total at most INR 24,000, leaving INR 6,000
(20% of the INR 30,000 cap) as reserve. The current allowance upper is INR
34,475 before its INR 4,000 contingency line, so it fails this gate until
specific sourcing choices reduce it.

Price anchors accessed 2026-09-09: [Mouser India lists ISO7721DR at ₹227.36
quantity 1](https://www.mouser.in/en/ProductDetail/Texas-Instruments/ISO7721DR?qs=0C8XhJW8e4pvzxoLtrI8OQ%3D%3D),
[WHYPCB advertises five 2-layer boards from ₹1,500](https://www.whypcb.com/services/pcb-fabrication),
and [ElectronicsComp lists a 6 V/10 A relay at ₹28 ex GST](https://www.electronicscomp.com/6v-10a-spdt-relay).
