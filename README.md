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
end-to-end. Status by tier:

### Tier 1 — Loop reliability — ✅ done
- **Programmatic FeatureScript error reporting.** `FeatureStudioClient.compiles()`
  catches parse/compile failure (empty featurespecs); `PartStudioClient.feature_errors()`
  + `feature_error_enum()` catch regen errors; `feature_notice()` recovers the rich
  *message* + `line:col` by re-running the feature through the eval endpoint (addressed
  by its namespace). `sync_project` aborts the commit on any error.

### Tier 2 — Close the loop to fabrication — ⏳ next
- **STL export + QA gates 3–4.** Onshape translation API → STL → the existing
  `validate_geometry.py` and `validate_printability.py`. Completes "idea → printable part".

### Tier 3 — Two-way human ↔ AI loop — ✅ mostly done
- **Onshape → LLM feedback ✅.** `PartStudioClient.summary()` returns a *structured*
  summary (part/face/edge/vertex counts, bounding box, volume) after each part.
- **Shared face vocabulary ✅.** The generator colours and numbers each hull face and
  stores a `boatLabel` attribute; `PartStudioClient.vocabulary()` reports each labelled
  face with its clockwise-numbered segments. Numbering is anchored at the transom.
- **Comment command-channel 🚧.** Async, geometry-anchored commands via Onshape comments:
  read-only reader (`CommentsClient` / `list_comments.py`) done; posting anchored pins,
  resolve/reply validated. Full act→commit loop pending. Key finding (see
  `docs/optimiste.md`): two ID layers — transient vs persistent query — so the stable
  handle is our attribute/colour, not the stored comment query.
- **Human-change diff ⏳.** Compare the current tree against `last_ai_version` — not started.

### Tier 4 — Richer generator — 🚧 in progress
- Faithful **Optimist pram**: developable hard-chine hull, 2 raked transoms, rocker;
  `opShell` for wall thickness; expose `beam` / depth / rocker. Class-rule + original
  1948-plan research done — see `docs/optimiste.md` + `docs/optimist-plans-1948/`.
  Next: consolidate offsets → regenerate model.
- **Native metadata / material.** Set `Nom` + `Matériau` (density) via the metadata API
  → live `Masse` / `Barycentre` / `Inertie`, feeding the `math/` hydrostatics.

### Tier 5 — Vision feedback (fit-to-purpose) — ⏳
- Render the part from several angles, then a multimodal LLM names what it sees.
  If "make a bolt" yields images recognized as a bolt, the cycle is on track. A soft,
  semantic sanity check that complements the geometric QA gates.

### Tier 6 — 3D model library as a starting point — ⏳
- When a new part is requested, start from a library entry (e.g. Onshape Standard
  Content for fasteners, or a configurable base part) instead of generating from
  scratch — faster and more reliable for common hardware.