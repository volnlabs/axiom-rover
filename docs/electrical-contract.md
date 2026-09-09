# Axiom rover electrical contract — RevB review

This is the accepted **160 x 100 mm Pi 5 carrier** contract. It records a design
under review, not a fabricated board, qualified harness, motion release, or
firmware implementation.

## Fixed boundaries

- Pi 5 is below the carrier. `J1` is `ESQ-120-24-G-D`, bottom-mounted, with a
  nominal carrier-underside-to-Pi-PCB gap of **16.5 mm**.
- Shrike R0.4 mates through `J2` and `J4`, each `SSW-119-01-G-S` 1 x 19
  socket. Delivered-header orientation and continuity remain physical checks.
- Shrike USB-C is its **only** 5 V input. Pi 5 V pins 2 and 4 and Shrike J2/J4 pin 1 (`VUSB`) are NC.
  `BASE_5V` is a separately supplied sensor rail only.
- The external 6 V motor rail reaches J7 only after an independent, rated stop
  relay and fuse. The PCB does not rate or replace either device.
- U1 isolates `H_GND` and `BASE_GND`; no carrier copper intentionally joins them.

## Pi socket and Shrike connector map

`J1` uses Pi physical-header numbering. All pins not listed are NC.

| J1 / Pi pin | Carrier net | Use |
|---:|---|---|
| 1, 17 | `HOST_3V3` | Pi 3.3 V for U1 host side |
| 6, 9, 14, 20, 25, 30, 34, 39 | `H_GND` | Pi ground for U1 host side |
| 8 | `H_TX` | Pi UART TX |
| 10 | `H_RX` | Pi UART RX |
| 2, 4 | NC | Pi 5 V; never power Shrike/carrier from Pi 5 V |

| J2 pin | Net | Shrike function / destination |
|---:|---|---|
| 1 | NC | — |
| 2 | `BASE_3V3` | Shrike 3.3 V |
| 3 | `ESTOP_RP` | RP GPIO5 observe |
| 4, 5 | `L_IN1`, `L_IN2` | left direction inputs |
| 6, 7 | `R_IN3`, `R_IN4` | right direction inputs |
| 8, 13 | `BASE_GND` | base return |
| 9, 10 | `US_TRIG`, `US_ECHO_3V` | HC-SR04 trigger / protected echo |
| 11, 12, 14, 15 | NC | — |
| 16 | `ESTOP_FPGA` | FPGA stop input |
| 17, 18 | `FPGA_PWM_L`, `FPGA_PWM_R` | FPGA PWM gates |
| 19 | `FAULT_FPGA_N` | FPGA `F_GPIO7` fault observe |

| J4 pin | Net | Shrike function / destination |
|---:|---|---|
| 1 | NC | — |
| 2 | `BASE_3V3` | Shrike 3.3 V |
| 3 | `IMU_INT` | IMU interrupt |
| 4 | `FAULT_RP_N` | RP GPIO28 fault observe |
| 5, 6 | `IMU_SCL`, `IMU_SDA` | I2C clock / data |
| 7, 13, 19 | `BASE_GND` | base return |
| 8, 9, 15, 16 | NC | — |
| 10, 11 | `ENC_R_B`, `ENC_R_A` | right encoder B / A |
| 12, 14 | `ENC_L_B`, `ENC_L_A` | left encoder B / A |
| 17, 18 | `RP_UART_RX`, `RP_UART_TX` | isolated UART RX / TX |

U5 (`SN74LVC125ADR`) gives each controller a separate one-way stop and fault
observation channel. Its four active-low enables are grounded; R16–R19 are
1 kΩ output resistors. J2-19/F_GPIO7 receives `FAULT_FPGA_N`; J4-4/GPIO28
receives `FAULT_RP_N`. Neither receiver can drive the source `DRV_FAULT_N`,
the hardwired `ESTOP_N`/nSLEEP net, or the other controller's observation
channel. Verify buffer propagation and the delivered Shrike pin labels.

## Carrier connectors and peripherals

| Ref | Family / purpose | Pin order, as generated |
|---|---|---|
| J3 | JST XH 1x4, HC-SR04 | `BASE_5V`, `SENSOR_TRIG`, `US_ECHO_5V`, `BASE_GND` |
| J5 | JST XH 1x2, logic NC stop loop | `BASE_3V3`, `ESTOP_N` |
| J6 | JST XH 1x2, sensor 5 V input | `BASE_5V`, `BASE_GND` |
| J7 | JST VH B2P-VH, post-fuse/stop 6 V | `MOTOR_6V`, `BASE_GND` |
| J8 | JST VH B2P-VH, left motor | `MOTOR_L_P`, `MOTOR_L_N` |
| J9 | JST VH B2P-VH, right motor | `MOTOR_R_P`, `MOTOR_R_N` |
| J10 | JST XH 1x4, left encoder | `BASE_GND`, `BASE_3V3`, `ENC_L_A`, `ENC_L_B` |
| J11 | JST XH 1x4, right encoder | `BASE_GND`, `BASE_3V3`, `ENC_R_A`, `ENC_R_B` |
| J12 | JST XH 1x4, alternate host UART | `HOST_3V3`, `H_GND`, `H_TX`, `H_RX` |
| J13 | JST XH 1x5, IMU | `BASE_GND`, `BASE_3V3`, `IMU_SDA`, `IMU_SCL`, `IMU_INT` |

The HC-SR04 uses 5 V. R1 (1 kΩ), R2 (2.2 kΩ), R3 (3.3 kΩ), and U2
`SN74LVC1G17DBVR` drive and protect its 3.3 V interface. R14/R15 are 4.7 kΩ
I2C pull-ups. Actual HC-SR04 header order and trigger threshold need bench
verification.

Encoder connector order is fixed above, but actual motor wire-end order,
polarity, phase, and quadrature CPR are unknown. Establish them by continuity
and a low-energy direction/phase test.

## Motor drive and stop behavior

U3 is `DRV8833PWPR`. R7/R8 are Stackpole `CSRT1206FTR200`, 0.20 Ω, 1 %, 1 W current-sense parts. The
design intent is **1 A nominal per motor channel**, contingent on current,
thermal, supply-sag, and driver-fault measurements.

| Direction source | PWM gate | DRV8833 input |
|---|---|---|
| `L_IN1` | `FPGA_PWM_L` | `DRV_AIN1` |
| `L_IN2` | `FPGA_PWM_L` | `DRV_AIN2` |
| `R_IN3` | `FPGA_PWM_R` | `DRV_BIN1` |
| `R_IN4` | `FPGA_PWM_R` | `DRV_BIN2` |

U4 (`SN74LVC08ADR`) performs these AND gates. PWM low takes both inputs of a
bridge low for a coast stop. `nSLEEP` is the `ESTOP_N` stop level and is
**not** PWM. R4 pulls the stop net low; R5/R6 pull PWM gates low; R10-R13 pull
direction inputs low; R9 pulls open-drain `DRV_FAULT_N` to `BASE_3V3`.

```text
logic: J5-1 BASE_3V3 -> S1A NC -> J5-2 ESTOP_N (R4 pulls to ground)
coil:  fused regulated 6 V -> S1B NC -> K1 rated coil -> BASE_GND
power: fused regulated 6 V -> K1 COM / normally-open contact -> J7-1
return: motor source negative -> J7-2 BASE_GND
K1 coil: correctly polarized rated flyback clamp; measure release time.
```

Select relay, fuse, wire, connector contacts, and source from measured stall
current and rated DC-inductive service. This contract makes no rating, trip,
or release-time claim.

## Selected motors and wheels

Use two ThinkRobotics **MOT3001-6V60RPM** 6 V, 60 RPM encoder motors, 25 mm
diameter. Supplier information states 103:1 gearing and 46 RPM loaded. It does
not establish delivered wire order, quadrature CPR or thermal performance. The seller lists 1.8 A stall current; this is a sourcing datum, not a measured limit of our assembly. Use
Pololu **3690**, an 80 x 10 mm wheel pair with 4 mm D-bore collets; fit and
retention remain mechanical qualification items.

## Release state

Physical tests, fabrication, and motion release are **false / not run**. This
repository does not claim implemented, flashed, or validated Pi, RP2040, or
FPGA motor-control firmware.

## Host transport and electrical limits

Pi pins 8/10 are GPIO14/15 and require the intended RP1 UART pin mux and driver.
Pi 5's primary debug UART is a separate three-pin header; a successful Linux
UART setup does not prove AxiomOS support. Disable boot/console traffic on the
control channel. Use the existing AxiomOS wire protocol; no new protocol or
runtime is implemented here. J12 is an alternative host entry: electrically
remove the Pi from J1 before using it, including Pi 3.3 V. Never connect two
TX outputs or two host 3.3 V sources together.

J13 supplies 3.3 V only. Use a documented 3.3 V-compatible IMU breakout and
check its pull-ups; parallel pull-ups may require omitting R14/R15. Encoder
ports also supply 3.3 V only; verify output type and noise margin before wiring.
HC-SR04 echo passes a 2.2 kΩ / 3.3 kΩ divider (nominal 3.0 V at 5.0 V) and
an SN74LVC1G17 buffer with partial-power isolation. The 1 kΩ trigger resistor
limits current; it does not raise the 3.3 V trigger level.

D1 SMBJ6.0A is a transient clamp, not a regulator, regeneration sink or
reverse-polarity controller. C8 is polarized. Use keyed, polarity-checked
6 V input with a suitably rated external fuse. Test VM overshoot and rail decay
at stop/reverse; TVS pulse ratings alone do not qualify motor regeneration.
U3 uses the PWP exposed-pad package, not the lower-current PW package.
The 0.30 mm driver breakout necks feed 0.8 mm motor trunks and 1.2/0.6 mm
vias; two-layer copper and thermal-via performance remain physical test gates.
This carrier does not claim formal Raspberry Pi HAT+ compliance: ID pins are NC.

Sources: [Stackpole CSRT](https://seielect.com/catalog/SEI-CSRT.pdf),
[TI DRV8833](https://www.ti.com/lit/ds/symlink/drv8833.pdf),
[TI SN74LVC125A](https://www.ti.com/lit/ds/symlink/sn74lvc125a.pdf),
[TI SN74LVC08A](https://www.ti.com/product/SN74LVC08A),
[TI ISO7721](https://www.ti.com/product/ISO7721),
[TI SN74LVC1G17](https://www.ti.com/product/SN74LVC1G17),
[JST VH](https://www.jst-mfg.com/product/pdf/eng/eVH.pdf),
[ThinkRobotics motor](https://thinkrobotics.com/products/25mm-encoder-dc-metal-gearmotors),
[Pololu wheels](https://www.pololu.com/product/3690), and the pinned
[Pi/Samtec reference notes](../reference/raspberry-pi-5/connector-sources.md).
