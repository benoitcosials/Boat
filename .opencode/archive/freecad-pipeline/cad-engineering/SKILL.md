---
name: cad-engineering
description: "Computes mechanical engineering parameters from a validated spec.json: gear ratios and tooth profiles, shaft diameters, bearing selection, housing wall thickness, and fastener specs. Uses Wolfram MCP for calculations. Produces a validated params.json ready for CAD modeling. Use after cad-requirements validates the spec. Triggered by: compute gear parameters, calculate shaft diameter, engineering calculations, select bearings, Wolfram CAD, dimension a reducer."
---

## Quick Start

1. **Load the validated spec.json** produced by `cad-requirements`.
2. **Identify what needs engineering** — does the spec have gears? shafts? bearings? fasteners?
3. **For each mechanical element, apply the appropriate formula** (see `references/formulas.md`).
4. **Use Wolfram MCP** (`WolframLanguageEvaluator`) for complex calculations — gear geometry,
   shaft deflection, bearing life, stress analysis.
5. **Select standard components** from `references/bearings.md` and `references/fasteners.md`.
6. **Write params.json** following the schema in `references/params-schema.md`.
7. **Run the QA gate**:
   ```bash
   .venv/bin/python3 .opencode/skills/cad-qa/scripts/validate_params.py spec.json params.json
   ```
8. **Fix and re-run** until exit code 0. Present the validated params to the user.

## Rules

- **Wolfram for math, not guesses** — any calculation involving trigonometry, logarithms,
  or iterative solving goes to Wolfram MCP. Do not approximate in your head.
- **Standard parts over custom** — always pick the nearest standard bearing, standard
  module gear, or standard fastener before designing a custom one.
- **Safety factor of 2 minimum** — for load-bearing parts in FDM plastic, double the
  calculated minimum dimension.
- **Clearance is mandatory** — 0.2–0.3 mm between moving parts for FDM. No zero-clearance fits.
- **Validate with spec** — params.json must be consistent with spec.json (material wall
  thickness, feature list, overall dimensions).
- **User approves before CAD** — engineering parameters determine the final geometry.
  Show the user what you computed and why.
- **Use the MCP, don't simulate it** — actually call `WolframLanguageEvaluator` via the
  Wolfram MCP tool. Do not fake the output.

## Engineering Workflow

### Step 1: Gears (if the spec has gear features)

Given: gear ratio target, or input/output speeds, or torque requirements.

**What to compute with Wolfram MCP:**
- Teeth count for input and output gears (must be integers ≥ 12 for 20° pressure angle)
- Module selection (nearest standard: 0.5, 0.8, 1.0, 1.25, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0, 8.0, 10.0)
- Pitch diameter = teeth × module
- Center distance = (pitch_diameter_1 + pitch_diameter_2) / 2
- Face width = 3× to 5× module (for FDM plastic)
- Pressure angle: 20° standard
- Bore diameter: shaft diameter + 0.05 mm clearance

**Wolfram call example:**
```wolfram
(* Find gear pair for ratio 3:1 with minimum 15 teeth *)
FindInstance[{t2/t1 == 3, t1 >= 15, t2 >= 15, t1 \[Element] Integers, t2 \[Element] Integers}, {t1, t2}]
```

### Step 2: Shafts (if the spec has bores)

Given: bore diameters from spec, or torque to transmit.

**What to compute with Wolfram MCP:**
- Shaft diameter from bore (shaft Ø = bore Ø - 0.05 to 0.1 mm clearance)
- If torque is specified: minimum shaft diameter to avoid yield
- Shaft length: at least bearing span + gear width + clearances

**Wolfram call example:**
```wolfram
(* Minimum shaft diameter for given torque in N·mm *)
torque = 500; (* N·mm *)
yieldStrength = 50; (* MPa for PLA *)
d = (16 * torque / (Pi * yieldStrength))^(1/3)
```

### Step 3: Bearings

Given: shaft diameters and expected loads.

**Selection process:**
1. Inner diameter = shaft diameter + 0.05 mm (light press fit for FDM)
2. Pick from standard catalog in `references/bearings.md`
3. For FDM 3D-printed bearings: use 608-2RS (8×22×7 mm) or 6000-2RS (10×26×8 mm) as starting points
4. For bushings (no rolling elements): PTFE or IGUS-style, Ø = shaft Ø + 0.1 mm

### Step 4: Housing

Given: gear center distance, bearing outer diameters, spec constraints.

**What to compute:**
- Wall thickness: max(spec.min_wall_thickness, 2× nozzle diameter, material minimum)
- Radial clearance: 0.5–1.0 mm around gears
- Axial clearance: 0.3–0.5 mm between gear face and housing wall
- Overall housing dimensions from gear envelope + wall thickness + clearances

### Step 5: Fasteners

Given: mounting_hole features in spec.

**Selection:**
- Pick from standard catalog in `references/fasteners.md`
- For M3 screws: hole Ø = 3.2 mm (clearance), boss Ø = 6 mm
- For M4 screws: hole Ø = 4.2 mm (clearance), boss Ø = 8 mm
- For M5 screws: hole Ø = 5.2 mm (clearance), boss Ø = 10 mm

### Step 6: Validate and Present

```bash
.venv/bin/python3 .opencode/skills/cad-qa/scripts/validate_params.py spec.json params.json
```

Present the key engineering decisions:
```
Engineering summary:
- Gear pair: 15T / 45T, module 2.0, center distance 60.0 mm
- Input shaft: Ø 9.95 mm, output shaft: Ø 24.90 mm
- Bearings: 6000-2RS (10×26×8) for input, custom bushing for output
- Housing wall: 3.0 mm PETG
- Fasteners: 4× M5 socket head

Proceed to CAD modeling?
```

## Examples

### Example 1: Simple gear pair
**Spec**: reducer with 3:1 ratio, 10 mm input shaft.

**Wolfram call**: `FindInstance[{t2/t1 == 3, t1 >= 15, ...}]` → t1=15, t2=45
**Module**: target center distance ~60 mm → module = 60/((15+45)/2) = 2.0 → standard ✓
**Shafts**: input Ø = 9.95 mm, output Ø = 24.90 mm (scaled from gear bore)
**Validation**: `validate_params.py` → PASS

### Example 2: Load-bearing bracket
**Spec**: corner bracket, PETG, mounting holes for M5.

**No gears** → skip gear section
**No shafts** → skip shaft section
**No bearings** → skip bearing section
**Fasteners**: M5 → hole Ø = 5.2 mm, boss Ø = 10 mm
**Housing**: wall = max(1.2, 2×0.4, 1.2) = 1.2 → but for structural → 3.0 mm
**Validation**: `validate_params.py` → PASS

## Anti-Patterns

- ❌ Computing gear parameters without Wolfram MCP — use `WolframLanguageEvaluator`, not mental math.
- ❌ Designing a custom bearing when a standard 608 or 6000 exists — always check the catalog first.
- ❌ Zero clearance between shaft and bore — FDM needs at least 0.05 mm clearance.
- ❌ Wall thickness below material minimum — check `references/materials.md` per the spec material.
- ❌ Handing off unvalidated params — always run `validate_params.py` before proceeding.
- ❌ Computing dimensions that contradict the spec — if the spec says 120 mm length, the housing must fit within 120 mm.
