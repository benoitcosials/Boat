---
name: cad-qa
description: "Validates CAD pipeline outputs at each stage gate: spec completeness, engineering parameter consistency, STL geometry integrity (manifold/watertight/dimensions), and 3D printability (overhangs/walls/bed adhesion). Run after every pipeline stage to enforce the industrial QA chain. Use for: CAD validation, QA gate, geometry check, printability analysis, spec verification, dimensional tolerance."
---

## Quick Start

Run the appropriate validator after each pipeline stage. All scripts accept a JSON or STL
input and return a standard gate report (exit code 0 = pass, 1 = fail):

```bash
# Gate 1 — after spec is written
.venv/bin/python3 scripts/validate_spec.py spec.json

# Gate 2 — after engineering params are computed
.venv/bin/python3 scripts/validate_params.py spec.json params.json

# Gate 3 — after CAD model is generated
.venv/bin/python3 scripts/validate_geometry.py part.stl spec.json

# Gate 4 — before sending to slicer
.venv/bin/python3 scripts/validate_printability.py part.stl
```

Every script produces a JSON gate report on stdout:

```json
{
  "gate": "spec",
  "passed": false,
  "errors": [
    {"field": "shaft_diameter", "message": "Must be > 0", "severity": "error"}
  ],
  "warnings": [
    {"field": "wall_thickness", "message": "Below 1.2 mm minimum", "severity": "warning"}
  ]
}
```

The orchestrator agent reads the exit code and the gate report to decide: proceed (0),
retry with error context (!0), or ask the user for intervention.

## Rules

- **Run at every gate** — NEVER skip a QA step. A skipped gate means untrusted output.
- **Exit code is the contract** — 0 = pass, 1 = fail. The orchestrator checks `$?` first.
- **Errors block progression** — any `error` severity entry means the stage must be retried.
- **Warnings are advisory** — `warning` severity allows progression but the user is notified.
- **Scripts are deterministic** — same input always produces the same output. No randomness.
- **Scripts are self-documenting** — run with `--help` for parameter details.
- **Missing dependencies produce clear errors** — if `trimesh` is not installed, the
  geometry script prints installation instructions instead of crashing obscurely.
- **All dimensions in millimeters** — the pipeline standard is mm. Scripts validate this.

## Examples

### Example 1: Valid spec passes
```bash
$ .venv/bin/python3 scripts/validate_spec.py spec.json
{"gate": "spec", "passed": true, "errors": [], "warnings": []}
$ echo $?
0
```

### Example 2: Invalid spec blocked
```bash
$ .venv/bin/python3 scripts/validate_spec.py bad_spec.json
{"gate": "spec", "passed": false, "errors": [
  {"field": "shaft_diameter", "message": "Must be a positive number", "severity": "error"},
  {"field": "material", "message": "Missing required field", "severity": "error"}
], "warnings": []}
$ echo $?
1
```

### Example 3: Geometry validation with warnings
```bash
$ .venv/bin/python3 scripts/validate_geometry.py part.stl spec.json
{"gate": "geometry", "passed": true, "errors": [], "warnings": [
  {"field": "wall_thickness", "message": "Minimum wall thickness 0.9 mm — below 1.2 mm recommendation", "severity": "warning"}
]}
$ echo $?
0   # warnings do not block progression
```

## Anti-Patterns

- ❌ Proceeding to the next stage when a gate script returns exit code 1.
- ❌ Modifying a validation script to "pass" a known-bad output — fix the generator, not the validator.
- ❌ Running `validate_geometry.py` on a file that is not STL binary — the script auto-detects and rejects ASCII STL.
- ❌ Ignoring warnings because "it's just a warning" — accumulated warnings often predict print failures.
