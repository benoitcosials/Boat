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