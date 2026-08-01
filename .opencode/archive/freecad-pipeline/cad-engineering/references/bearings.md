# Standard Bearing Catalog for FDM 3D Printing

Prefer these standard bearings over custom ones. They are cheap, widely available,
and dimensionally standardised. For FDM 3D-printed housings, allow 0.05 mm extra
on the housing bore for a press fit.

## Ball Bearings (6000 series — metric, deep groove)

| Designation | Inner Ø (mm) | Outer Ø (mm) | Width (mm) | Dynamic Load (kN) | Common Use |
|------------|-------------|-------------|-----------|-------------------|------------|
| **608-2RS** | 8 | 22 | 7 | 3.3 | Skate wheels, light shafts |
| **6000-2RS** | 10 | 26 | 8 | 4.6 | Small gearboxes, RC cars |
| **6001-2RS** | 12 | 28 | 8 | 5.1 | Small motors |
| **6002-2RS** | 15 | 32 | 9 | 5.6 | General purpose |
| **6003-2RS** | 17 | 35 | 10 | 6.0 | Medium shafts |
| **6004-2RS** | 20 | 42 | 12 | 9.4 | Larger gearboxes |
| **6005-2RS** | 25 | 47 | 12 | 10.1 | Output shafts |
| **6200-2RS** | 10 | 30 | 9 | 5.1 | Wider than 6000 |
| **6201-2RS** | 12 | 32 | 10 | 6.8 | Wider than 6001 |
| **6202-2RS** | 15 | 35 | 11 | 7.6 | Wider than 6002 |

Note: `-2RS` = rubber seals both sides (recommended for FDM — keeps debris out).

## Flanged Bearings (for axial location)

| Designation | Inner Ø | Outer Ø | Flange Ø | Width | Flange Width |
|------------|---------|---------|---------|-------|-------------|
| **F608-2RS** | 8 | 22 | 25 | 7 | 1.5 |
| **F6000-2RS** | 10 | 26 | 28 | 8 | 1.5 |

## Thrust Bearings (for axial loads)

| Designation | Inner Ø | Outer Ø | Width |
|------------|---------|---------|-------|
| **51100** | 10 | 24 | 9 |
| **51101** | 12 | 26 | 9 |
| **51102** | 15 | 28 | 9 |

## FDM-Printed Bushings (no rolling elements)

When the load is light and simplicity matters, print bushings directly:

- **Material**: Nylon or PETG (PLA wears quickly)
- **Clearance**: shaft Ø + 0.1 mm to 0.2 mm
- **Wall thickness**: min 1.5 mm
- **Length**: 1× to 2× shaft diameter
- **Lubrication**: PTFE dry lube or light grease

## Selection Algorithm

1. Find the shaft diameter → inner Ø must be ≥ shaft Ø (for press fit: = shaft Ø)
2. Pick the smallest bearing whose inner Ø matches and outer Ø fits the housing
3. If no standard bearing fits → design a printed bushing or scale the housing
4. For axial loads → add a thrust bearing or thrust washer
