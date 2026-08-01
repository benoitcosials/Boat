---
name: cad-featurescript-gen
description: "Generates FeatureScript code from JAX-computed hull parameters for direct injection into Onshape via Playwright. Translates Bézier control points, offsets tables, and structural sandwich parameters into valid FeatureScript that creates parametric 3D geometry. Use after cad-naval-math validates the params. Triggered by: generate FeatureScript, Onshape code, FeatureScript from offsets, hull to Onshape, CAD code generation."
---

## Quick Start

1. **Load params.json** from `cad-naval-math` — contains hull offsets, control points, structural params.
2. **Identify the geometry type** — hull surface? internal structure? sandwich panels? appendages?
3. **Select the FeatureScript template** from `references/featurescript-templates.md`.
4. **Fill the template** with computed values — Bézier grids become `opSpline` calls, offsets become `opLoft` profiles.
5. **Write the FeatureScript** to `parts/<part_name>.fs` — the persistent blueprint of the part.
   All FeatureScript files live in `parts/` and are version-controlled.
6. **Validate syntax** against Onshape's FeatureScript constraints (see Rules below).

## Rules

- **FeatureScript is typed** — every variable must declare its type. Use `ValueWithUnits` for dimensions.
- **All dimensions in meters internally, millimeters in FeatureScript** — convert at the boundary:
  ```featurescript
  const LOA = 4000 * millimeter;  // 4.0 m → 4000 mm
  ```
- **Pre-compute in JAX, not in FeatureScript** — FeatureScript runs in the browser; keep it to geometry construction only.
- **Use standard Onshape features** — `opExtrude`, `opLoft`, `opThicken`, `opBoolean`. No custom FeatureScript magic unless needed.
- **One Part Studio per hull component** — hull surface, deck, bulkheads, appendages are separate parts.
- **Name everything** — every sketch, extrude, and loft gets a descriptive name for the Onshape feature tree.
- **Include error handling** — wrap geometry creation in `try` blocks; log failures for the Playwright injector to detect.

## FeatureScript Templates

See `references/featurescript-templates.md` for complete templates. Summary:

| Template | What it creates | Input |
|----------|----------------|-------|
| `hull_surface.fs` | 3D Bézier hull surface from control grid | `control_points` (4×4×3) |
| `hull_solid.fs` | Solid hull from offsets table (lofted sections) | `stations[]`, `waterlines[]`, `half_breadths[][]` |
| `bulkhead.fs` | Transverse bulkhead at station X | `station_x`, `offsets_at_station` |
| `sandwich_panel.fs` | Sandwich panel (skin + core) | `length`, `width`, `skin_thickness`, `core_thickness` |
| `appendage.fs` | Keel, rudder, skeg from NACA profile | `naca_4digit`, `chord`, `span`, `thickness_ratio` |

## Conversion Patterns

### Bézier Control Grid → FeatureScript `opSpline`

```featurescript
// Input: control_points is a 4×4×3 array from JAX
// Each row is a u-curve, each column is a v-curve
const cp = [
    [vector(0, 0, -150)*mm, vector(0, 50, -100)*mm, vector(0, 200, -50)*mm, vector(0, 400, 0)*mm],
    [vector(1000, 20, -285)*mm, vector(1000, 120, -190)*mm, vector(1000, 380, -95)*mm, vector(1000, 760, 0)*mm],
    [vector(3000, 40, -300)*mm, vector(3000, 150, -200)*mm, vector(3000, 500, -100)*mm, vector(3000, 750, 0)*mm],
    [vector(4000, 30, -270)*mm, vector(4000, 120, -180)*mm, vector(4000, 420, -90)*mm, vector(4000, 640, 0)*mm]
];

opSpline(context, id + "hullSurface", {
    "points": cp,
    "degree": 3  // cubic Bézier
});
```

### Offsets Table → Lofted Hull Solid

```featurescript
// For each station, create a sketch with the hull profile
// Then loft between stations
for (var i = 0; i < size(stations) - 1; i += 1) {
    var skId = id + ("station_" ~ i);
    var sketch = newSketchOnPlane(context, skId, {
        "sketchPlane": plane(vector(stations[i], 0, 0) * millimeter, vector(1, 0, 0), vector(0, 1, 0))
    });
    // Draw profile using half_breadths[i][*] and waterlines[*]
    skSpline(sketch, "profile", {
        "points": profilePoints  // array of vector(x, y) at this station
    });
    skSolve(sketch);
}
opLoft(context, id + "hullSolid", {
    "profiles": stationProfiles,
    "bodyType": ToolBodyType.SOLID
});
```

## Examples

### Example 1: 4m sailing dinghy hull → FeatureScript
```
JAX params:
  LOA=4.0m, beam=1.5m, draft=0.3m
  Control grid: 4×4×3 Bézier patch
  Offsets: 11 stations × 6 waterlines

Generated FeatureScript:
  - opSpline for hull surface (from Bézier control grid)
  - opThicken (2mm inward for hull shell)
  - 3× bulkheads at stations 2, 5, 8
  - opBoolean (union hull + bulkheads + deck)

Output: parts/dinghy_hull.fs (~200 lines of FeatureScript, stored persistently)
```

### Example 2: Sandwich panel → FeatureScript
```
JAX params:
  500×300mm panel, 1mm glass skins, 10mm foam core

FeatureScript:
  opExtrude (core solid: 500×300×10mm)
  opExtrude (bottom skin: 500×300×1mm)
  opExtrude (top skin: 500×300×1mm)
  opBoolean (union all three)
```

## Anti-Patterns

- ❌ Computing geometry in FeatureScript instead of JAX — FeatureScript runs in browser, JAX runs on GPU.
- ❌ Using millimeters in JAX and meters in FeatureScript — always convert explicitly with `* millimeter`.
- ❌ Single monolithic FeatureScript for entire boat — one part per Part Studio for editability.
- ❌ Skipping `skSolve` after creating sketches — unsolved sketches cause loft failures.
- ❌ Hardcoding dimensions in FeatureScript — all dimensions come from params.json via template substitution.
