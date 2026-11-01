# Driver Section — PCB Designs

KiCad projects for the two boards that make up the LED side of the harness
continuity tester (see the root [README.md](../../README.md) for the full
system). **Both boards have been fabricated, assembled, and verified working
on hardware.**

| Zip | Board | Role |
|---|---|---|
| `matrix_smd_v2_proj.zip` | **LED matrix board** | 8x8 SMD LED display the operator watches during a test |
| `tlc_carrier_proving_v8_with_parallel_RPi_breakout.zip` | **TLC5925 driver/carrier board** | Raspberry Pi hat that shifts data into 4x TLC5925 drivers and sinks the 64 LED channels |

Each zip is a full KiCad 10 project (schematic where applicable, PCB layout,
exported Gerbers/drill files, and a BOM) plus a VS Code `.history` folder
(auto-saved edit snapshots — safe to ignore/delete, not needed to build the
board).

---

## 1. `matrix_smd_v2` — LED Matrix Board

8x8 grid of SMD LEDs (64 total) that forms the visual pattern display
referenced throughout the main app (see `harness_nav/data/patterns.json` and
the LED numbering diagram in the root README).

- **Board size:** 132.1 x 95.3 mm, 2-layer FR4, 1.6 mm
- **PCB-only project** — no schematic capture, laid out directly in Pcbnew
- **LEDs:** D1–D64, footprint `LED_1206_3216Metric` (1206/3216 metric SMD LEDs)
- **Connectors:** two 2x32 IDC headers, 2.54 mm pitch
  - `JA` — row/anode side (A_2x32)
  - `JK` — column/cathode side (K_2x32)
  - Together these carry the row/column drive lines out to the TLC5925
    carrier board's 64-channel output header (J2)
- **Files:** `matrix_smd_v2.kicad_pcb`, `.kicad_pro`, `.kicad_prl`, BOM CSV,
  full Gerber/drill set in `matrix_smd_v2_gerber/` (also pre-zipped as
  `matrix_smd_v2_gerber.zip` for direct upload to a fab)

To re-order boards: send `matrix_smd_v2_gerber.zip` as-is to any 2-layer fab
(JLCPCB, PCBWay, PCB Power / LionCircuits in India, etc.) — no changes needed,
no special stackup.

---

## 2. `tlc_carrier` (rev C, "proving" variant) — TLC5925 Driver/Carrier Board

Raspberry Pi–mounted carrier board: 4x TLC5925 16-channel constant-current
LED sink drivers (64 channels total), driven over SPI-style shift
register signals from the Pi, plus headers for the limit switch and buzzer
used in the two-stage verification workflow.

- **Board size:** ~74.5 x 127 mm, 2-layer FR4, 1.6 mm, 1 oz copper
- **This is the "proving" build** (matches `BOM_tlc_proving.csv` and the
  physical PCB file): straight Pi-ribbon power, **no onboard USB-C input or
  buck-converter power stage**. `README_carrier.md` inside the zip documents
  a separate, more ambitious "full carrier" revision (USB-C power source,
  dual buck converters, screw-terminal power distribution) — that
  functionality is **not** present on the current `tlc_carrier.kicad_pcb` in
  this zip; treat that section of `README_carrier.md` as design notes for a
  future/alternate board, not as a description of what's built here.
- **J14 — parallel RPi breakout:** a second, unshrouded 2x20 header wired
  pin-for-pin with the main ribbon header (J1), so you can probe/jumper any
  Pi GPIO while the ribbon is connected. This is the "parallel RPi breakout"
  the zip is named for. Optional, can be left unpopulated.
- **Key connectors:**
  - `J1` — 2x20 IDC ribbon from the Pi GPIO header
  - `J14` — 2x20 plain header, parallel breakout of J1
  - `J2` — 2x32 header, 64 LED channel outputs → matrix board's `JA`/`JK`
  - `J9` — LCD power (PicoBlade 1.25 mm)
  - `J11`/`J12` — limit switch inputs (3V3 / GND / Signal, series-resistor
    protected)
  - `J13` — buzzer header (Signal/5V/GND)
  - `T1`/`J10` — 5V power in / LED power out screw terminals
- **LED current:** set by `R1–R4` (one R-EXT per TLC5925 bank),
  `I_OUT = (1.21V / R_EXT) x 18`. Proving build uses **2.2k → ~10 mA/channel**
  for yellow LEDs — change per-bank if a different LED color/current is
  needed.
- **Files:** `tlc_carrier.kicad_sch`, `.kicad_pcb`, `.kicad_pro`, `.kicad_prl`,
  two BOMs (`BOM_tlc_carrier.csv` = full/future carrier variant,
  `BOM_tlc_proving.csv` = **this** board), `DFM_NOTES.md` (revision history
  and fab/DRC notes), `README_carrier.md` (detailed bring-up and power notes —
  read the "proving" sections; ignore USB-C/buck-converter sections), full
  Gerber/drill set in `Gerbers/` (also pre-zipped as `Gerbers.zip`).

**Fab spec:** 2-layer FR4, 1.6 mm, 1 oz copper, HASL/ENIG, min track/space
0.25 mm, min via 0.6/0.3 mm — standard capability at JLCPCB/PCBWay/PCB
Power/LionCircuits, no special requests needed.

**Bring-up order:** populate the TLC5925s + decoupling first, verify 5V/3V3
rails before connecting the Pi, then connect the ribbon and run the LED
driver code (`harness_nav/hal/led_matrix/led_matrix.py`) to shift a test
pattern — see `DFM_NOTES.md` for the full checklist and known
schematic/PCB sync notes.

---

## How the two boards connect

```
Raspberry Pi
    │ (GPIO ribbon)
    ▼
tlc_carrier (J1) ──4x TLC5925──▶ J2 (2x32, 64 ch) ──cable──▶ JA/JK (2x32 x2)
    │                                                              │
    ├─ J11/J12 limit switch                                 matrix_smd_v2
    ├─ J13 buzzer                                            (8x8 LED grid)
    └─ J9 LCD power
```
