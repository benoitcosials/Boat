# Params JSON Schema

The engineering parameters file (`params.json`) is the output of the engineering stage
and the input to the CAD modeling stage. It must pass `validate_params.py` against
the corresponding `spec.json` before proceeding.

## Schema

```json
{
  "units": "string — always 'mm'",
  "gears": [
    {
      "label": "string — matches a gear feature label from spec.json",
      "teeth": "integer ≥ 12 (20° PA) — number of teeth",
      "module": "number — standard module (0.5, 0.8, 1.0, 1.25, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0, 8.0, 10.0)",
      "pitch_diameter": "number — must equal teeth × module",
      "pressure_angle": "number — 20.0° standard",
      "face_width": "number — 3 to 10 × module",
      "bore_diameter": "number — shaft diameter + clearance (0.05 mm)"
    }
  ],
  "shafts": [
    {
      "label": "string — descriptive (e.g., 'input_shaft')",
      "diameter": "number > 0 — shaft outer diameter in mm",
      "length": "number > 0 — total shaft length in mm"
    }
  ],
  "housing": {
    "wall_thickness": "number ≥ material minimum — in mm",
    "clearance_radial": "number ≥ 0 — gap between gear tip and housing",
    "clearance_axial": "number ≥ 0 — gap between gear face and housing"
  },
  "bearings": [
    {
      "label": "string — descriptive or standard designation",
      "inner_diameter": "number > 0",
      "outer_diameter": "number > inner_diameter",
      "width": "number > 0"
    }
  ],
  "fasteners": [
    {
      "label": "string — matches a mounting_hole label from spec",
      "type": "string — socket_head, hex_nut, heat_insert, self_tapping",
      "diameter": "number — nominal screw diameter (M3 → 3.0, M4 → 4.0)",
      "count": "integer ≥ 1"
    }
  ]
}
```

## Field Rules

- **gears[].pitch_diameter**: Must equal `teeth × module` within floating-point tolerance (1e-6).
- **gears[].module**: Prefer standard modules. Non-standard modules generate a warning.
- **gears[].teeth**: Minimum 12 at 20° PA to avoid undercut. 3-4 teeth trigger an error.
- **shafts[].diameter**: Must fit in at least one gear bore or bearing inner diameter
  (shaft Ø < bore Ø or shaft Ø < bearing inner Ø).
- **housing.wall_thickness**: Must be at least the material minimum from `materials.md`.
- **housing.clearance_radial**: Minimum 0.3 mm recommended for FDM.
- **bearings[].inner_diameter**: Must be less than `outer_diameter`.
- **fasteners[].diameter**: Must be a valid metric size (3, 4, 5, 6, 8).

## Minimal Valid Example (simple bracket, no gears)

```json
{
  "units": "mm",
  "gears": [],
  "shafts": [],
  "housing": {
    "wall_thickness": 3.0,
    "clearance_radial": 0.5,
    "clearance_axial": 0.3
  },
  "bearings": [],
  "fasteners": [
    {
      "label": "corner_mounts",
      "type": "socket_head",
      "diameter": 5.0,
      "count": 4
    }
  ]
}
```
