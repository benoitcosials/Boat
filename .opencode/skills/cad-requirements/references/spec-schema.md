# Spec JSON Schema

The specification file (`spec.json`) is the output of the requirements interview
and the input to the engineering stage. It must pass `validate_spec.py` before
proceeding.

## Schema

```json
{
  "part_name": "string — lowercase_snake_case, unique identifier",
  "description": "string — one sentence describing the part's function",
  "material": "string — FDM material name, see materials.md",
  "units": "string — always 'mm' unless the user specifies otherwise",
  "overall_dimensions": {
    "length": "number > 0 — outer X dimension in mm",
    "width": "number > 0 — outer Y dimension in mm",
    "height": "number > 0 — outer Z dimension in mm"
  },
  "features": [
    {
      "type": "string — one of: bore, mounting_hole, pocket, slot, chamfer, fillet, thread, groove, keyway, boss, rib, flange, gear, spline",
      "label": "string — unique, descriptive (e.g., 'input_shaft_bore')",
      "diameter": "number > 0 (for circular features)",
      "depth": "number > 0 (for bores, pockets)",
      "length": "number > 0 (for slots, pockets)",
      "width": "number > 0 (for slots, pockets)",
      "height": "number > 0 (for non-through features)",
      "radius": "number > 0 (for fillets, chamfers)",
      "count": "integer >= 1 (for repeating features like mounting holes)"
    }
  ],
  "tolerances": {
    "general": "number >= 0 — default tolerance for all dimensions",
    "bore": "number >= 0 (optional — tighter tolerance for shaft fits)",
    "length": "number >= 0 (optional)"
  },
  "constraints": {
    "min_wall_thickness": "number > 0 — thinnest allowable wall in mm",
    "max_overhang_angle": "number > 0 — steepest unsupported overhang in degrees"
  }
}
```

## Field Rules

- **part_name**: Lowercase, no spaces. Use underscores. Examples: `motor_mount`, `gear_housing`, `shaft_coupler`.
- **description**: Functional, not poetic. "Houses two spur gears and supports input/output shafts" — not "A beautiful box for gears".
- **material**: Must match a key in `materials.md` (case-insensitive). Unknown materials generate a warning.
- **units**: Always included. Default to `"mm"`. The pipeline rejects anything else.
- **overall_dimensions**: All three must be present and positive. Sanity limit: 5000 mm.
- **features**: Can be empty `[]` if the part has no machined features (rare). Every feature must have a `type` and `label`. Dimensions depend on the feature type.
- **tolerances**: `general` is required. Feature-specific tolerances are optional but strongly recommended.
- **constraints**: `min_wall_thickness` is required. `max_overhang_angle` defaults to 45° if omitted by the user.

## Minimal Valid Example

```json
{
  "part_name": "simple_spacer",
  "description": "Cylindrical spacer for M5 bolt",
  "material": "PLA",
  "units": "mm",
  "overall_dimensions": {
    "length": 20.0,
    "width": 20.0,
    "height": 10.0
  },
  "features": [
    {
      "type": "bore",
      "diameter": 5.2,
      "depth": 10.0,
      "label": "bolt_hole"
    }
  ],
  "tolerances": {
    "general": 0.3
  },
  "constraints": {
    "min_wall_thickness": 1.2
  }
}
```
