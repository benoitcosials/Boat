---
name: cad-requirements
description: "Conducts a structured interview to gather mechanical part specifications for 3D-printable CAD design. Produces a validated spec.json ready for the engineering stage. Use when the user describes a mechanical part to design (gear, housing, bracket, enclosure, shaft, coupling) or starts a CAD pipeline. Triggered by: design a part, 3D print a bracket, create a gear housing, specify dimensions, mechanical requirements."
---

## Quick Start

1. Ask the user **what they want to build** — function, context, constraints.
2. Work through the **6 interview sections** below, filling the spec as you go.
3. After each section, **echo back what you understood** for confirmation.
4. When the interview is complete, write `spec.json` and **run the QA gate**:
   ```bash
   .venv/bin/python3 .opencode/skills/cad-qa/scripts/validate_spec.py spec.json
   ```
5. If validation fails, fix the errors and re-run until it passes.
6. Present the final `spec.json` to the user for **explicit approval** before proceeding.

## Rules

- **Never invent dimensions** — if the user does not specify a value, ask. Do not guess.
- **Always include units** — every dimension in mm unless the user states otherwise.
- **One feature at a time** — enumerate bores, holes, pockets, etc. individually with labels.
- **Material affects everything** — wall thickness, tolerances, print temperature. Get it first.
- **Validate before handing off** — the spec must pass `validate_spec.py` with exit code 0.
- **User has final say** — the spec is a proposal until explicitly approved. Show it, ask for confirmation.
- **Cross-reference the references** — use `references/materials.md` for material properties, `references/features.md` for feature types, `references/spec-schema.md` for the JSON schema.

## Interview Protocol

Conduct these 6 sections in order. After each, summarize and confirm.

### Section 1: Function & Identity
- What does this part do? (load-bearing, aligning, enclosing, transmitting torque…)
- Give it a `part_name` (lowercase_snake_case, e.g., `reducer_housing`)
- Write a one-sentence `description` of its purpose.

### Section 2: Material
- What material will this be printed in?
- Common FDM options: PLA (easy, stiff, brittle), PETG (tough, slightly flexible), ABS (strong, warps), ASA (UV-resistant), TPU (flexible), Nylon (strong, hygroscopic).
- If unsure, recommend PLA for prototypes, PETG for functional parts.
- Record the material name (e.g., `"PLA"`).

### Section 3: Overall Dimensions
- What are the outer bounds? Length × width × height in mm.
- If the user gives one or two dimensions, ask for the missing ones.
- If the part fits around something, work backwards from the contained object.
- For standardised parts (gears, bearings), suggest checking the engineering step rather than guessing.

### Section 4: Features
- Enumerate every geometric feature on the part.
- For each feature, collect: `type`, `label`, and relevant dimensions.
- Valid types (see `references/features.md`): `bore`, `mounting_hole`, `pocket`, `slot`, `chamfer`, `fillet`, `thread`, `groove`, `keyway`, `boss`, `rib`, `flange`, `gear`, `spline`.
- **Bore**: through-hole for a shaft. Needs `diameter` and `depth`.
- **Mounting hole**: for fasteners. Needs `diameter` and `count`.
- **Pocket**: blind cavity. Needs `length`, `width`, `depth`.
- **Slot**: elongated cutout. Needs `length`, `width`, `depth`.
- Ask: "Are there any other features?" until the user says no.

### Section 5: Tolerances
- What precision is needed?
- `general`: default tolerance for non-critical dimensions (typical: 0.2–0.5 mm for FDM).
- Feature-specific tolerances (e.g., `bore: 0.05` for press-fit shafts).
- If the user does not know, suggest `general: 0.3` for FDM.

### Section 6: Constraints
- `min_wall_thickness`: thinnest allowable wall (≥ 1.2 mm for PLA/PETG, ≥ 1.5 mm for ABS).
- `max_overhang_angle`: steepest unsupported angle (45° typical for 0.4 mm nozzle).
- Any other constraints (weight limit, specific infill, must fit in a specific printer volume…).

### After the Interview

Write `spec.json` following the schema in `references/spec-schema.md`. Then validate:

```bash
.venv/bin/python3 .opencode/skills/cad-qa/scripts/validate_spec.py spec.json
```

If the validator fails, read the errors, fix `spec.json`, and re-run until exit code 0.

Then show the validated spec to the user:
```
Here is the validated specification:

- Part: reducer_housing (PLA)
- Dimensions: 120 × 80 × 60 mm
- Features: 2 bores, 4 mounting holes
- Tolerances: general ±0.2 mm, bore ±0.05 mm
- Min wall: 1.2 mm

Does this look correct? I will not proceed to engineering until you approve.
```

## Examples

### Example 1: Simple bracket
**User**: "I need a corner bracket to hold a 20×20 mm aluminum extrusion."

**Interview flow**:
1. Function: corner bracket, right-angle support → `part_name: "corner_bracket"`
2. Material: PLA (indoor use, low load)
3. Dimensions: each leg 40 mm long, 25 mm wide, 5 mm thick
4. Features: 2 mounting_hole (Ø5 mm per leg, 4 total), 1 fillet (r=5 mm inside corner)
5. Tolerances: general ±0.3 mm
6. Constraints: min_wall 1.2 mm, max_overhang 45°

### Example 2: Gear reducer housing
**User**: "I need a housing for two spur gears, 15 and 45 teeth, module 2."

**Interview flow**:
1. Function: enclose gears, hold bearings → `part_name: "reducer_housing"`
2. Material: PETG (functional part, some heat from friction)
3. Dimensions: calculate from gears — length ~130 mm (gear center distance + clearances), width ~80 mm, height ~60 mm
4. Features: 2 bores for shafts (Ø10 and Ø25 mm), 4 mounting_holes (Ø5 mm), 1 pocket for gear cavity
5. Tolerances: bore ±0.05 mm (bearing seats), general ±0.3 mm
6. Constraints: min_wall 2.0 mm (structural), max_overhang 45°

## Anti-Patterns

- ❌ Generating spec.json without running the full interview — missing fields cause downstream failures.
- ❌ Guessing dimensions the user did not provide — ask, don't assume.
- ❌ Handing off an unvalidated spec — always run `validate_spec.py` before proceeding.
- ❌ Skipping the final user approval — the spec is a contract; the user must sign off.
- ❌ Using non-standard feature types — stick to the catalog in `references/features.md`.
- ❌ Forgetting units — every number must have an implied or explicit unit (default: mm).
