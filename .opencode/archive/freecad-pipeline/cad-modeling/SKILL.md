---
name: cad-modeling
description: "Generates parametric 3D CAD geometry from validated params.json using FreeCAD MCP. Produces STEP and STL files ready for 3D printing. Uses plan-validate-execute loops with visual feedback. Use after cad-engineering validates the params. Triggered by: generate CAD model, create 3D geometry, model the part, FreeCAD generation, build STEP, export STL, CAD from parameters."
---

## Quick Start

1. **Load the validated params.json** from `cad-engineering`.
2. **Generate a build plan** — a sequence of FreeCAD operations needed to construct the part.
   Write it to `build-plan.json` (see `references/build-patterns.md`).
3. **Execute each step via FreeCAD MCP** — one operation at a time.
4. **Verify after each major step** — use the MCP `get_view` tool for a screenshot.
5. **After the build is complete, run the QA gate**:
   ```bash
   .venv/bin/python3 .opencode/skills/cad-qa/scripts/validate_geometry.py part.stl spec.json
   ```
6. **If validation fails**, fix the geometry and re-run. **Maximum 3 retry loops** before
   asking the user for guidance.
7. **Export final files**: `part.step` (CAD interchange) and `part.stl` (printing).

## Rules

- **Plan before building** — never generate FreeCAD operations on the fly. Write the plan
  first, review it, then execute.
- **One operation per MCP call** — do not batch multiple extrusions or booleans in one
  `execute_code` call. Each MCP call = one logical operation.
- **Verify after each step** — get a screenshot (`get_view`) after every sketch, every
  pad/pocket, and every boolean. Compare visually against the spec.
- **Maximum 3 retries** — if geometry validation fails, analyze the errors, adjust the
  plan, and rebuild. After 3 failed attempts, stop and show the user what went wrong.
- **Always use millimeters** — set FreeCAD units to mm at the start of every session.
- **Prefer Part Design over Part workbench** — use sketches + pads/pockets for parametric
  editability. Use Part booleans only when Part Design cannot express the geometry.
- **Constrain all sketches fully** — unconstrained sketches break when dimensions change.
- **Name everything** — every sketch, body, and feature gets a descriptive label from the spec.
- **Export immediately after validation** — once `validate_geometry.py` passes, export
  STEP and STL before anything else changes.

## Build Workflow

### Phase 1: Analyze the Params

Read `params.json` and identify:
- **Housing geometry** — envelope dimensions, wall thickness, clearances
- **Bores / holes** — diameters, depths, positions (from shaft and bearing params)
- **Gear features** — if present, where gear teeth go (usually external cylinder)
- **Mounting features** — fastener holes, bosses, flanges
- **Edge treatments** — fillets, chamfers from spec

### Phase 2: Generate the Build Plan

Write `build-plan.json` as an ordered list of operations. Each entry has:
```json
{
  "step": 1,
  "operation": "sketch",
  "plane": "XY",
  "description": "Base rectangle 120×80 mm",
  "constraints": ["horizontal 120 mm", "vertical 80 mm", "symmetric about origin"],
  "next": "pad"
}
```

The build plan follows a standard order (see `references/build-patterns.md`):
1. Base body (sketch + pad)
2. Primary features (pockets, bores — sketched + pocketed)
3. Secondary features (holes, threads — sketched + pocketed or hole tool)
4. Edge treatments (fillets, chamfers — always last)
5. Mirror / pattern (if symmetric)

### Phase 3: Execute via FreeCAD MCP

For each step in the plan:

1. **Call the MCP tool** (e.g., `create_object`, `execute_code`, or the appropriate
   FreeCADMCP operation). Pass the exact parameters from the build plan.
2. **Get a screenshot** (`get_view` tool) to verify the result visually.
3. **Check for errors** — if the MCP returns an error, adjust the plan step and retry
   immediately. Do not continue to the next step.
4. **Log** the step as completed in the build plan.

**MCP tools reference (neka-nat/freecad-mcp):**
- `create_document` — start a new FreeCAD document
- `create_object` — add a primitive or feature
- `execute_code` — run arbitrary FreeCAD Python (for complex sketches)
- `get_view` — screenshot the current 3D view
- `get_objects` — list all objects in the document
- `edit_object` — modify an existing object
- `export_stl` / `export_step` — export the final geometry

### Phase 4: Validate and Export

```bash
# Geometry validation
.venv/bin/python3 .opencode/skills/cad-qa/scripts/validate_geometry.py part.stl spec.json

# If pass: export
# FreeCAD MCP: export_stl("part.stl") + export_step("part.step")

# If fail: read errors, fix geometry, retry (max 3 loops)
```

### Phase 5: Present Results

Show the user:
```
CAD model complete: reducer_housing

- File: part.step (1.2 MB) — editable CAD
- File: part.stl (3.4 MB) — printable mesh
- Geometry: manifold ✓, watertight ✓, dimensions within tolerance ✓
- Preview: [screenshot]

Ready for printability check?
```

## Examples

### Example 1: Simple Housing (from params)

**Build plan:**
```
Step 1: create_document("reducer_housing")
Step 2: create_sketch("base") → rectangle 120×80, centered
Step 3: pad("base", height=60)
Step 4: create_sketch("cavity") → rectangle 114×74, centered
Step 5: pocket("cavity", depth=57)  — leaves 3 mm walls
Step 6: create_sketch("input_bore") → circle Ø10, at x=-30
Step 7: pocket("input_bore", through_all)
Step 8: create_sketch("output_bore") → circle Ø25, at x=+30
Step 9: pocket("output_bore", through_all)
Step 10: create_sketch("mounts") → 4× circles Ø5 at corners
Step 11: pocket("mounts", through_all)
Step 12: fillet("corner_reinforcement", radius=3, edges=[4 internal corners])
```

**Execution**: one MCP call per step, screenshot after steps 3, 5, 9, 11.

**Validation**: `validate_geometry.py part.stl spec.json` → PASS.

### Example 2: Gear (from params with gear feature)

**Build plan:**
```
Step 1: create_document("output_gear")
Step 2: create_sketch("gear_blank") → circle Ø92 (tip diameter)
Step 3: pad("gear_blank", height=10)  — face width
Step 4: create_sketch("bore") → circle Ø25, centered
Step 5: pocket("bore", through_all)
Step 6: execute_code → generate involute teeth via FreeCAD Gear workbench
Step 7: fillet("tooth_roots", radius=0.5, edges=[all tooth root edges])
```

**Key**: Step 6 uses the Gear workbench (FCGear) which is available as a FreeCAD addon.
The MCP `execute_code` runs:
```python
import FreeCAD, Part, Sketcher
# Generate involute gear profile with teeth=45, module=2.0, pressure_angle=20
```

## Anti-Patterns

- ❌ Skipping the build plan — writing FreeCAD code directly leads to broken geometry.
- ❌ Multiple operations in one `execute_code` — if it fails, you don't know which step broke.
- ❌ Continuing after an MCP error without fixing — broken geometry propagates.
- ❌ Unconstrained sketches — the part breaks when dimensions change.
- ❌ Fillets before pockets — fillets must always be the LAST operation.
- ❌ More than 3 retry loops — after 3 failures, the approach is wrong; ask the user.
- ❌ Handing off without running `validate_geometry.py` — the orchestrator will reject it anyway.
- ❌ Using Part booleans when Part Design can do it — Part Design is parametric and editable.
