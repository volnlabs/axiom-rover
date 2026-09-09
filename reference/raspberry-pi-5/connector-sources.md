# RevB connector source notes

All dimensions are nominal millimetres. Validate the fitted stack with the
actual purchased parts.

## Pi 5 GPIO datum and selected carrier socket

Official Raspberry Pi sources: [mechanical/STEP index](https://www.raspberrypi.com/documentation/computers/raspberry-pi.html#schematics-and-mechanical-drawings), [Pi 5 mechanical drawing](https://pip.raspberrypi.com/documents/RP-008347-DS), and the local unmodified [RP-010083-CA STEP archive](RP-010083-CA-1-rpi-5-3D-STEP-no-graphics.zip).

From the official STEP, with the Pi in top view, USB ports at right, and the
85 x 56 outline's top-left corner as `(0,0)`: pin 1 is `(8.37,4.77)` and pin
2 is `(8.37,2.23)`. Odd pins are `(8.37 + 2.54k,4.77)`; even pins are
`(8.37 + 2.54k,2.23)`, for `k=0..19`. Pin 1 is the square-marked, lower
visible row in the official mechanical drawing. The STEP GPIO post reaches
8.54 above the Pi PCB top.

Selected part: **Samtec ESQ-120-24-G-D**, 2 x 20, elevated THT socket.

* [Product page](https://www.samtec.com/products/esq-120-24-g-d)
* [Series catalogue, F-226](https://suddendocs.samtec.com/catalog_english/esq_th.pdf)
* [Exact part drawing](https://suddendocs.samtec.com/prints/esq-1xx-xx-x-x-xxx-xx-x-xx-mkt.pdf)
* [ESQ THT footprint drawing](https://suddendocs.samtec.com/prints/esq-sdt.pdf)

The `-24` lead style has `B=13.59` (socket body height from PCB mounting
surface to mating face) and `A=9.65` tail. At a carrier underside height of
16.50 above the Pi PCB, the Pi post insertion is `13.59 + 8.54 - 16.50 =
5.63`, within Samtec's 3.68--6.35 insertion-depth range.

Use a 1.02 diameter PTH drill, 2.54 pitch in each direction. For 20 positions
per row, the hole-centre span is `19 x 2.54 = 48.26`; the ESQ moulded body is
`(20 x 2.54) + 0.51 = 51.31` long and 4.95 wide (`.195 REF`). It therefore
overhangs the end-hole centres by 1.525 at each end. The Samtec footprint
drawing gives the drill but no copper-pad outer diameter; select pad OD and
annular ring from the fabricator rules rather than treating 1.02 as a pad OD.

For a socket on the carrier underside, preserve physical pin 1-to-pin 1 XY
coincidence; place/mirror the footprint in CAD rather than mirroring its pin
numbering by hand.

## Shrike sockets

Use **2 x Samtec SSW-119-01-G-S**, each 1 x 19, 2.54 pitch, vertical THT.

* [Product page](https://www.samtec.com/products/ssw-119-01-g-s)
* [Series catalogue](https://suddendocs.samtec.com/catalog_english/ssw_th.pdf)
* [Exact part drawing](https://suddendocs.samtec.com/prints/ssw-1xx-xx-xxx-x-xx-xxx-xx-mkt.pdf)
* [Single-row vertical footprint drawing](https://suddendocs.samtec.com/prints/ssw-svs.pdf)

`-01` has a 2.64 tail. The 8.51 `.335 REF` dimension is the moulded socket
body height above the mounting surface; the tail is dimensioned separately,
so it is not included in 8.51. Samtec specifies 3.68--6.35 mating insertion
depth. Use 1.02 PTH drill on 2.54 centres; the source drawing does not state a
copper-pad OD.

For 19 positions, body length is `(19 x 2.54) + 0.51 = 48.77`; body width is
2.41 (`.095 REF`). The end-hole-centre span is `18 x 2.54 = 45.72`, hence
1.525 body overhang beyond each end-hole centre.
