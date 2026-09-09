# Compute swaps after AxiomOS v1.0

The July 2026 AxiomOS direction is Linux/CUDA for NVIDIA compute and AxiomOS for bounded control, advancing from two machines to one partitioned machine only after the boundary is demonstrated. This repository implements the common physical base and records that progression; it does not select or implement a hypervisor.

| Stage | Compute arrangement | Boundary to prove | Hardware change |
|---|---|---|---|
| A: first release rover | Raspberry Pi 5 running the qualified AxiomOS host/control build → Shrike | Command expiry, safe start, e-stop, watchdog, recovery | Pi tray on the common mounts |
| B: NVIDIA two-box | Linux/Jetson performs perception/CUDA; Pi/AxiomOS validates bounded intents and retains actuator authority | Linux stalls, crashes and stale/reordered traffic cannot extend actuator authority | Adapter tray/pod and separate host power; base carrier unchanged |
| C: same-SoC research | Linux and AxiomOS on separately owned cores/devices of a supported NVIDIA platform | Memory/DMA/interrupt/timer isolation, resource starvation, reset and boot ownership | Qualified compute pod; base carrier unchanged |

Stage B is the working architecture to qualify before C. A Linux-only direct-to-actuator run is a transport test, not evidence that AxiomOS mediated the command. Stage C depends on the actual NVIDIA SoC, firmware and supported partitioning mechanism; CUDA remains with Linux. Do not infer isolation from successful dual boot or ordinary Linux processes.

All trays share four M3 clearance holes at `(±85, ±65)` mm on a 200 × 160 mm tray. The first Pi mounting grid is 58 × 49 mm. Jetson hardware, cooling, mass distribution and connector envelopes require their own measured adapter; no unspecified Jetson board is declared to fit.

The base controller, sensor, motor driver, gate, e-stop and actuator wiring stay fixed. Swaps are **power-off**, mechanically fastened and strain-relieved. One host owns the isolator at a time: use J1 for Pi or J12 for an alternate host, with the Pi electrically removed before using J12. Use separately qualified host power; J1's 3.3 V feeds only its side of U1, not the other processor or motors.

## Release comparisons

Run the same [commissioning cases](commissioning.md) with the same current limits, battery state, actuator firmware and bitstream, then change only the compute configuration. Record median, tail and maximum observed command-to-gated-output latency; retain complete captures and dropped/error frame counts. Test fault cases as well as nominal motion. A clean Linux/CUDA benchmark does not replace the physical control evidence.

The currently inspected AxiomOS baseline (`4f5aa90`, `firmware/shrike/README.md`) states that its Shrike implementation remains safe-low/non-operational pending a validated bitstream/timing manifest and atomic UART/watchdog/e-stop adapter. This hardware design does not remove that prerequisite or introduce a second wire protocol.

Provenance: the user's post-v1.0 direction and `/home/utkarsh/Work/axiom-lab/roadmap/architecture-north-star.md` (two-box → one-box direction). These are references, not build dependencies; this repository has no AxiomOS submodule, worktree relationship or symlink. The unrelated `Work/linux-multikernel` project is not a design source.
