# FDM Materials Reference

Material selection affects wall thickness, tolerances, print settings, and part
strength. When the user does not specify a material, recommend based on function.

## Material Table

| Material | Min Wall (mm) | Characteristics | Best For | Avoid For |
|----------|--------------|-----------------|----------|-----------|
| **PLA** | 1.2 | Stiff, brittle, easy to print, low warp, biodegradable | Prototypes, display models, low-stress brackets, enclosures | High-temperature (>50°C), outdoor UV exposure, load-bearing |
| **PETG** | 1.2 | Tough, slightly flexible, good layer adhesion, moderate temp resistance | Functional parts, mechanical components, gear housings, water-tight parts | Very high stiffness requirements, bridging |
| **ABS** | 1.5 | Strong, impact-resistant, higher temp resistance, warps easily | Automotive parts, high-temperature applications, structural components | Open-frame printers without enclosure, large flat parts |
| **ASA** | 1.5 | UV-resistant, weather-resistant, similar to ABS | Outdoor parts, garden fixtures, drone frames | Indoor-only simple parts (overkill) |
| **TPU** | 1.5 | Flexible, rubber-like, excellent layer adhesion | Gaskets, vibration dampeners, flexible couplings, phone cases | Rigid structural parts, precision fits |
| **Nylon** | 1.5 | Very strong, wear-resistant, hygroscopic (absorbs moisture) | Gears, bushings, living hinges, high-wear parts | Beginners (hard to print), humid environments without drying |
| **PC** | 1.5 | Extremely strong, high temp resistance, difficult to print | High-strength structural parts, heat-resistant components | Standard printers (needs 280°C+ nozzle, enclosure) |

## Recommendation Algorithm

1. **Prototype or visual model** → PLA
2. **Functional part, normal conditions** → PETG
3. **High temperature or impact** → ABS
4. **Outdoor use** → ASA
5. **Needs flexibility** → TPU
6. **Gears, wear surfaces** → Nylon
7. **Maximum strength/heat** → PC

## Print Settings Reference (for slicer stage)

| Material | Nozzle (°C) | Bed (°C) | Speed (mm/s) | Retraction (mm) |
|----------|------------|----------|-------------|-----------------|
| PLA | 200–220 | 50–60 | 50–70 | 3–5 |
| PETG | 230–250 | 70–85 | 40–50 | 4–6 |
| ABS | 240–260 | 95–110 | 40–50 | 4–6 |
| ASA | 240–260 | 95–110 | 40–50 | 4–6 |
| TPU | 220–240 | 40–60 | 20–30 | 2–3 |
| Nylon | 250–280 | 70–90 | 30–40 | 3–5 |
| PC | 280–310 | 100–120 | 30–40 | 3–5 |
