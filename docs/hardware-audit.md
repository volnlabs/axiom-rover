> Historical findings for Rev A at commit 57851dc. Rev B replaces the harness-only PCB with physical Pi/Shrike sockets and onboard motor drive; see [the implementation ledger](revb-plan.md) and current CAD. This document preserves the earlier audit, not the current interface.

# Historical Rev A hardware audit — 9 September 2026

**Revision A does not implement the requested plug-in Shrike carrier. Do not order it as the complete robot PCB.** It is a routed, low-current harness adapter. Fabrication, physical fit and powered-motion release gates remain false. No hardware was connected or tested in this audit.

## Findings and disposition

| Interface | Finding | Disposition |
|---|---|---|
| Shrike mounting | No socket footprint; J2 is a 16-pin IDC harness connector. The suggested interposer has no PCB design. | Replace this interface with two female 1×19 sockets on the fixed carrier. |
| Shrike geometry | Official R0.4 PCB and STEP files exist but were not used in the initial assembly. | Saved under `reference/shrike-r04`; derive the socket and module model from these files. |
| Pi 5 mounting | The 58×49 grid spacing was correct, but its position relative to the 85×56 board envelope was wrong by 10 mm in X. | Corrected the tray holes/bosses to the official drawing datum; regenerated CAD and viewer meshes. This is a CAD correction, not a physical fit test. |
| Pi 5 electrical | Carrier J1 had generic UART names without Pi physical pin numbers. There is no Pi 40-pin socket or top-board design. | Added the explicit four-wire mapping to the electrical contract. Runtime UART routing remains to be demonstrated. |
| HC-SR04 | Carrier J3 order differs from the sensor header; the bracket lacks a measured board-retention interface, and the assembly omits the sensor body. | Added the required harness permutation. Exact sensor fit and trigger acceptance remain unverified. |
| L298N | An unspecified module is represented together with Shrike by one 60×35×15 box. That is not evidence that either module, connectors or heatsink fit. | Use separate models and retention for the actual L298N and Shrike. Check module jumpers and terminal order. |
| Motors, wheels, caster, batteries, switch, relay, fasteners | Exact SKUs, mating features, cable paths and installation access are incomplete or unmeasured. | Do not treat collision-free boxes as a complete enclosure assembly. Select/measure parts and qualify retention and clearances. |
| Runtime and motor power | Shrike firmware explicitly remains safe-low/non-operational; FPGA timing/runtime integration and motor-current qualification are missing. | No claim of a working or safe moving rover. Follow commissioning gates before motion. |

The artifact checker passed on the original design despite the Pi datum error. It checked consistency of the modeled geometry, not correspondence with the real Pi. The corrected generator now checks bores and surrounding spacer material at coordinates independently taken from the vendor drawing.

Verification after correction: the CadQuery generator and artifact checker passed, with zero unexpected intersections among the modeled shapes. Reintroducing the old centred grid in memory failed the drawing-coordinate bore check (15.928 mm³ of obstructing material). The refreshed viewer matched both STEP source hashes and passed its 22 browser checks. These are file/CAD/browser checks; no physical test was run.

## Source-based electrical checks

Rechecked the official R0.4 **PCB pad net names**, not only our own schematic. The contract's used Shrike connections match: J2-2 = 3.3 V; J2-3 = GPIO5; J2-4…7 = GPIO6…9; J2-8 = GND; J2-9/10 = GPIO10/11; J2-16…18 = F_GPIO0…2; J4-17/18 = GPIO17/16. These match the intended UART, sensor, motor-direction and FPGA-enable nets. This does not verify the user's installed board revision, header soldering, FPGA pad binding or running firmware.

Rechecked TI's package-specific tables: ISO7721DR pins 1…8 are VCC1, OUTA, INB, GND1, GND2, OUTB, INA, VCC2; SN74LVC1G17DBVR pins 1…5 are NC, A, GND, Y, VCC. The carrier assignments agree. Neither result proves assembled orientation, power sequencing, isolation performance or sensor-clone compatibility. [ISO7721, figure 5-4/table 5-1](https://www.ti.com/lit/ds/symlink/iso7721.pdf); [SN74LVC1G17, pin table](https://www.ti.com/lit/ds/symlink/sn74lvc1g17.pdf).

## Corrected architecture recommendation

Keep a **physical Shrike socket on the fixed actuator carrier**, with the Pi on its removable upper tray. Use two female 1×19 socket strips, a board-outline/pin-1 marking, and a mechanical guide/retainer that prevents reversed or offset insertion. Select the actual socket/header pair and engagement height before finalizing its footprint. Preserve access to Shrike USB-C, boot/reset and debug connections. Keep the host/base power boundary and independent motor-power stop.

A Shrike socket on a **Pi 5 top add-on board** is also feasible, but it couples the actuator controller mechanically to the computer being swapped. It requires its own 40-pin mating connector, defined stack height, actual cooler/connector clearance and a new thermal/fit review. The official Active Cooler drawing gives 63.5×42.5×13.7 mm reference dimensions. A top board must allow fan intake/exhaust, plug access and installation space; the current enclosure proves none of those. Do not call it HAT/HAT+ compliant without checking the corresponding Raspberry Pi specification.

Before releasing either arrangement: import accurate separate board/component models; select all mating connectors and mounting hardware; check every pad against the vendor and every harness end against its device; rerun ERC/DRC, connectivity and actual-part mechanical checks; perform a paper/template socket fit and unpowered assembly; then follow current-limited electrical, partial-power, stop/watchdog and raised-wheel commissioning. Exact purchased dimensions and physical measurements remain required.

Sources: [pinned Vicharak R0.4 hardware](https://github.com/vicharak-in/shrike/tree/763d0a7dd9ebdfc3f61de148457d5c34f112f61e/hardware/shrike-lite/kicad/v1_r0.4), [Pi 5 mechanical drawing](https://datasheets.raspberrypi.com/rpi5/raspberry-pi-5-mechanical-drawing.pdf), [Active Cooler drawing](https://datasheets.raspberrypi.com/cooling/raspberry-pi-active-cooler-mechanical-drawing.pdf). Raspberry Pi labels its drawings approximate/reference-only and directs readers to physical hardware for complete component representation.
