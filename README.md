# Boat — AI-Assisted Naval & Mechanical CAD Pipeline

## Requirements

- **Python 3.12** (required by jax-metal — Python 3.13/3.14 not supported)
- **Apple Silicon** (M1/M2/M3/M4) for Metal GPU acceleration
- **Homebrew** for system dependencies

## Setup

```bash
# Install Python 3.12 if not present
brew install python@3.12

# Create venv with Python 3.12
/opt/homebrew/bin/python3.12 -m venv .venv

# Activate and install
source .venv/bin/activate
pip install -r requirements.txt

# Install Playwright browser
playwright install chromium

# Allow direnv (auto-activates venv on cd)
direnv allow
```

## Why Python 3.12?

`jax-metal` (Apple's JAX GPU backend for Metal) requires `jax>=0.4.34` and
`jaxlib>=0.4.34`. These versions only ship wheels for Python 3.12 — not 3.13 or
3.14. Since GPU acceleration is mandatory for this project, Python 3.12 is the
pinned version.

## Stack

| Component | Tool | Purpose |
|-----------|------|---------|
| Math/Simulation | JAX + jax-metal | Hydrostatics, hull curves, structural analysis (GPU-accelerated) |
| CAD | Onshape (via Playwright) | 3D modeling — FeatureScript injection, no API limits |
| QA | trimesh (Python) | STL validation — manifold, watertight, printability |
| Browser automation | Playwright + Chromium | Onshape web interface automation |
| Python isolation | venv + direnv | Per-project Python 3.12 environment |

## Roadmap

The Onshape tooling (session-based REST injection, generator, commit) works
end-to-end. Next steps, by priority tier:

### Tier 1 — Loop reliability
- **Programmatic FeatureScript error reporting.** Retrieve the compile/regen
  *message* (file:line + failed precondition), not just `OK/ERROR`, and surface it
  so a failed generation is caught instead of silently committing a red feature.

### Tier 2 — Close the loop to fabrication
- **STL export + QA gates 3–4.** Onshape translation API → STL → the existing
  `validate_geometry.py` and `validate_printability.py`. Completes "idea → printable
  part".

### Tier 3 — Two-way human ↔ AI loop
- **Human-change diff.** Compare the current feature tree against `last_ai_version`,
  detect native features a human added, fold them back into the generator / `.fs`.
- **Onshape → LLM feedback.** Today the flow is one-way (LLM writes FS). Instantiating
  a part generates sub-objects (faces, edges, vertices, bodies, bounding box, mass
  properties). Export a *structured summary* of what was generated back to the LLM so
  the next iteration reasons from the actual result rather than blind.

### Tier 4 — Richer generator
- `opShell` (hollow to a hull thickness), expose `beam` / depth / rocker as
  parameters, add transom and sheer — a real hull, not just a solid loft.

### Tier 5 — Vision feedback (fit-to-purpose)
- Render the part from several angles, then a multimodal LLM names what it sees.
  If "make a bolt" yields images recognized as a bolt, the cycle is on track. A soft,
  semantic sanity check that complements the geometric QA gates.

### Tier 6 — 3D model library as a starting point
- When a new part is requested, start from a library entry (e.g. Onshape Standard
  Content for fasteners, or a configurable base part) instead of generating from
  scratch — faster and more reliable for common hardware.