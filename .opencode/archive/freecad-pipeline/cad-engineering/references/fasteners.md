# Standard Fasteners for 3D-Printed Parts

Fasteners connect 3D-printed parts or attach them to other components. Use these
standard sizes — custom fasteners are almost never needed for FDM parts.

## Metric Socket Head Cap Screws (ISO 4762)

| Size | Thread Ø (mm) | Head Ø (mm) | Head Height (mm) | Clearance Hole Ø | Boss Ø (min) |
|------|-------------|------------|-----------------|-----------------|-------------|
| **M3** | 3.0 | 5.5 | 3.0 | 3.2 | 6.0 |
| **M4** | 4.0 | 7.0 | 4.0 | 4.2 | 8.0 |
| **M5** | 5.0 | 8.5 | 5.0 | 5.2 | 10.0 |
| **M6** | 6.0 | 10.0 | 6.0 | 6.2 | 12.0 |
| **M8** | 8.0 | 13.0 | 8.0 | 8.4 | 16.0 |

## Hex Nuts (ISO 4032)

| Size | Width Across Flats (mm) | Thickness (mm) | Pocket Ø (min) | Pocket Depth |
|------|------------------------|---------------|---------------|-------------|
| **M3** | 5.5 | 2.4 | 6.4 | 2.8 |
| **M4** | 7.0 | 3.2 | 8.1 | 3.6 |
| **M5** | 8.0 | 4.0 | 9.2 | 4.4 |
| **M6** | 10.0 | 5.0 | 11.5 | 5.4 |

## Heat-Set Inserts (for plastic threads)

Much stronger than tapped plastic threads. Press in with soldering iron.

| Size | Insert Ø (mm) | Insert Length (mm) | Hole Ø (mm) | Boss Ø (min) |
|------|-------------|-------------------|-----------|-------------|
| **M3** | 4.0 | 5.0 | 3.8 | 6.0 |
| **M4** | 5.0 | 6.0 | 4.8 | 7.5 |
| **M5** | 6.0 | 7.0 | 5.8 | 9.0 |

## Self-Tapping Screws (direct into plastic)

No insert needed. Use coarse thread (wood screw style).

| Size | Pilot Hole Ø (mm) | Boss Ø (min) | Max Clamp (mm) |
|------|-----------------|-------------|---------------|
| **#4 (2.9 mm)** | 2.0 | 5.0 | 6 |
| **#6 (3.5 mm)** | 2.5 | 6.0 | 10 |
| **#8 (4.2 mm)** | 3.0 | 7.5 | 12 |

## Design Rules for 3D-Printed Fastener Features

1. **Boss diameter** ≥ 2 × fastener diameter (for M5: boss ≥ 10 mm)
2. **Boss height** ≥ 2 × fastener diameter (for M5: height ≥ 10 mm)
3. **Wall thickness around pocket** ≥ 1.5 mm (for nut pockets)
4. **Clearance holes** are always through — do not blind-tap plastic threads (use inserts)
5. **Chamfer** the top of clearance holes (0.5 mm) for easier screw insertion
6. **Countersink angle** = 90° for flat-head screws (ISO 10642)

## Selection Algorithm

1. Determine load → pick screw size (M3 light, M4 medium, M5 structural)
2. Select fastening method:
   - **Nut + bolt** (through-hole, strongest, needs access to both sides)
   - **Heat-set insert** (blind hole, strong, needs soldering iron)
   - **Self-tapping** (blind hole, weakest, no extra hardware)
3. Size the boss: Ø = 2 × screw Ø, height = 2 × screw Ø + insert length
4. Size the hole: clearance = screw Ø + 0.2 mm (for through-holes)
