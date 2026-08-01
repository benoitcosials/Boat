---
name: cad-naval-math
description: "Computes naval architecture parameters using JAX on Apple Metal GPU: hull surface modeling (Bézier/NURBS), hydrostatics (displacement, waterplane area, centers), stability (GM, GZ), and structural sandwich analysis. Takes validated spec.json, produces params.json with all geometric and hydrostatic coefficients. Use after cad-requirements validates the spec. Triggered by: naval math, hull design, hydrostatics, Bézier hull, displacement calculation, stability analysis, sandwich structure."
---

## Quick Start

1. **Load spec.json** from `cad-requirements` — contains LOA, beam, draft, displacement target.
2. **Identify the computation type** — hull curves? hydrostatics? structural? all of the above?
3. **Load the appropriate JAX module** from `math/` (see `references/math-modules.md`).
4. **Execute the computation** via the wrapper script:
   ```bash
   .venv/bin/python3 scripts/evaluate_jax_model.py <module> <spec.json> --output params.json
   ```
5. **Validate** with `cad-qa` Gate 2:
   ```bash
   .venv/bin/python3 .opencode/skills/cad-qa/scripts/validate_params.py spec.json params.json
   ```
6. Present key results (displacement, LCB, GM, max speed) to the user for approval.

## Rules

- **Always use JAX vectorized operations** — no Python loops over geometry arrays.
- **JAX runs on Metal GPU** — computations are fast. Do not approximate or skip steps.
- **Strict SI units internally** — meters, kg, radians. Convert to mm only for CAD export.
- **Bézier curves, not polylines** — hull surfaces are smooth. Use cubic Bézier patches.
- **Validate hydrostatic equilibrium** — displacement × g must equal total weight (within 1%).
- **Document every formula** — reference the source (ITTC, ISO 12217, ABS rules).
- **User approves before CAD** — show the computed displacement curve, stability curve, or hull offsets before generating FeatureScript.

## Naval Math Modules

The `math/` directory contains JAX modules for each analysis domain:

| Module | Function | Input | Output |
|--------|----------|-------|--------|
| `hull_surface.py` | Generate 3D hull surface from design parameters | LOA, beam, draft, entry angle, deadrise | Offsets table, Bézier control points |
| `hydrostatics.py` | Displacement, waterplane, centers, coefficients | Hull offsets, waterline | Volume, LCB, LCF, Cb, Cp, Cm, Cwp |
| `stability.py` | Righting arm curve, GM, GZ | Hull offsets, VCG, heel angles | GZ curve, GM, downflooding angle |
| `resistance.py` | Holtrop-Mennen resistance prediction | Hull params, speed range | Rt curve, effective power |
| `structure.py` | Sandwich panel bending, core shear | Panel dims, skin/core material, loads | Deflection, stress, core shear |

## Computation Patterns

### Hull Surface (Bézier Patch)

```python
import jax.numpy as jnp

def hull_surface(loa, beam, draft, entry_angle, deadrise):
    """Generate a 3x3 cubic Bézier patch for the hull surface."""
    # Control grid: 4×4 points in (x, y, z)
    # x: stations (0 = bow, 1 = stern)
    # y: half-beam at each station
    # z: draft at each station
    control_points = jnp.zeros((4, 4, 3))
    # ... fill from design parameters ...
    return control_points
```

### Hydrostatics

```python
def displacement(hull_offsets, waterline):
    """Trapezoidal integration of station areas up to waterline."""
    stations = hull_offsets[:, :, 1]  # y-coordinates (half-beam)
    areas = jnp.trapz(stations, dx=station_spacing, axis=0)
    volume = 2 * jnp.trapz(areas, dx=station_spacing)  # both sides
    displacement_kg = volume * water_density
    return displacement_kg, volume
```

### Stability (GZ curve)

```python
def gz_curve(hull_offsets, vcg, heel_angles):
    """Compute righting arm at each heel angle."""
    def gz_at_angle(angle):
        # Rotate hull, compute new waterline, find displaced volume centroid
        rotated = rotate_hull(hull_offsets, angle)
        cb = center_of_buoyancy(rotated)
        gz = cb[1] * jnp.cos(angle) + cb[2] * jnp.sin(angle) - vcg * jnp.sin(angle)
        return gz
    return jax.vmap(gz_at_angle)(heel_angles)
```

## Examples

### Example 1: Compute displacement for a 4m dinghy
```
Spec: LOA=4.0m, beam=1.5m, draft=0.3m, displacement_target=200kg

JAX computes:
- Volume: 0.212 m³ → displacement: 217 kg
- Cb: 0.39 (light displacement hull)
- LCB: 1.85m from bow (46% LOA — acceptable)

User approves → proceeds to FeatureScript generation.
```

### Example 2: Stability check for sailing dinghy
```
Spec: same hull, VCG=0.4m, crew=2×80kg at 0.5m above deck

JAX computes:
- GM: 0.82m (positive — stable)
- Max GZ: 0.15m at 35° heel
- Downflooding: 62°
- ISO 12217 Category C: PASS

User approves → proceeds.
```

## Anti-Patterns

- ❌ Using Python loops instead of JAX vectorized operations — 100× slower on GPU.
- ❌ Hardcoding water density (1025 salt / 1000 fresh) — read from spec.json.
- ❌ Computing stability without verifying hydrostatic equilibrium first.
- ❌ Generating hull offsets without checking for self-intersection or negative volume.
- ❌ Using SI units in one place and mm in another — convert at the CAD boundary only.
