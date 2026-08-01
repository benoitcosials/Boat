# Engineering Formulas

All formulas use SI units (mm, N, MPa) unless noted. Call Wolfram MCP for actual
computation — these are the formulas to use, not the results.

## Gear Geometry

### Basic Relationships
```
pitch_diameter = teeth × module
center_distance = (pd1 + pd2) / 2
gear_ratio = teeth_output / teeth_input
```

### Tooth Proportions (ISO 54, 20° pressure angle)
```
addendum = module
dedendum = 1.25 × module
whole_depth = 2.25 × module
clearance = 0.25 × module
tooth_thickness = π × module / 2  (at pitch circle)
```

### Minimum Teeth (to avoid undercut)
```
For 20° pressure angle: min_teeth = 18  (without profile shift)
For 25° pressure angle: min_teeth = 12
For 14.5° pressure angle: min_teeth = 32
With profile shift: min_teeth can be lower (consult Wolfram)
```

### Face Width (FDM plastic gears)
```
face_width = 3 × module  (light load)
face_width = 5 × module  (normal load)
face_width_max = 10 × module  (heavy load, may warp)
```

### Contact Ratio
```
contact_ratio = (√(ra1² - rb1²) + √(ra2² - rb2²) - center_distance × sin(φ)) / (π × module × cos(φ))
Where: ra = tip radius, rb = base radius, φ = pressure angle
```
Call Wolfram for this — it's trigonometric and error-prone to approximate.

## Shaft Sizing

### From Torque (static)
```
τ_max = 16 × T / (π × d³)  — maximum shear stress
d³ = 16 × T / (π × τ_allowable)
d = ∛(16 × T / (π × τ_allowable))

Where:
  T = torque (N·mm)
  d = shaft diameter (mm)
  τ_allowable = yield_strength / safety_factor (MPa)
```

### From Bending (if radial load)
```
σ_max = 32 × M / (π × d³)  — maximum bending stress
d = ∛(32 × M / (π × σ_allowable))

Where:
  M = bending moment (N·mm) = radial_force × distance_to_bearing
```

### Combined Loading (shaft with gear)
```
Use von Mises criterion:
σ_combined = √(σ_bending² + 3 × τ_torsion²)
d = ∛(16 / (π × σ_allowable) × √(4 × M² + 3 × T²))  (simplified)
```

## Housing Dimensions

### Wall Thickness
```
t_wall = max(spec_min_wall, 2 × nozzle_Ø, material_min_wall)
For PLA nozzle 0.4 mm: t_wall ≥ max(1.2, 0.8, 1.2) = 1.2 mm
For structural: t_wall ≥ 3.0 mm
```

### Clearances (FDM)
```
radial_clearance = 0.5 mm  (between stationary parts)
radial_clearance = 1.0 mm  (between moving parts, e.g., gear tip to housing)
axial_clearance = 0.3 mm  (between gear face and housing wall)
shaft_to_bore_clearance = 0.05 mm  (sliding fit for FDM)
bore_to_bearing_clearance = 0.05 mm  (light press fit for FDM)
```

### Housing Envelope
```
housing_length = center_distance + gear_radii_sum + 2 × (radial_clearance + wall_thickness)
housing_width = max(face_width, bearing_width) + 2 × (axial_clearance + wall_thickness)
housing_height = max(gear_tip_radius) + radial_clearance + wall_thickness + base_thickness
```

## Bearing Life (if applicable)
```
L10 = (C / P)^(10/3) × 10⁶  — for ball bearings
Where:
  C = dynamic load rating (N)
  P = equivalent radial load (N)
  L10 = life in revolutions at 90% reliability

For FDM bushings: life is determined by wear, not fatigue. Use PV limit.
PV = pressure × velocity ≤ PV_limit (material dependent)
```

## Safety Factors (FDM plastic)

| Application | Safety Factor |
|-------------|--------------|
| Display / prototype | 1.5 |
| Light functional | 2.0 |
| Normal functional | 3.0 |
| Load-bearing | 4.0 |
| Safety-critical | 5.0+ |

## Material Properties for FDM (approximate)

| Material | Yield Strength (MPa) | Young's Modulus (GPa) | Density (g/cm³) |
|----------|---------------------|----------------------|-----------------|
| PLA | 50 | 3.5 | 1.24 |
| PETG | 45 | 2.0 | 1.27 |
| ABS | 40 | 2.3 | 1.04 |
| Nylon | 50 | 1.7 | 1.14 |
| PC | 60 | 2.4 | 1.20 |

Call Wolfram MCP for precise values: `Entity["Element", "PLA"]` or
`ChemicalData["polylacticacid", "YoungModulus"]` for curated data.
