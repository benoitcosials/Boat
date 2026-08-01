---
name: cad-onshape-injector
description: "Manages the Onshape CAD workspace via Playwright browser automation: branch-based FeatureScript injection (ai/main), Part Studio mapping from parts/ manifest, merge ai/main→main with user approval, and branch diff analysis for human modifications. Use after cad-featurescript-gen produces the FeatureScript. Triggered by: inject into Onshape, Playwright Onshape, FeatureScript injection, CAD automation, Onshape browser control, merge branch, analyze branch."
---

## Quick Start

1. **Ensure Chromium is installed**: `playwright install chromium`
2. **The `parts/` manifest determines what gets injected** — each `.fs` file maps to one Part Studio.
3. **Injection always targets `ai/main` branch, never `main`**:
   ```bash
   .venv/bin/python3 scripts/inject_featurescript_onshape.py inject \
     --document "https://cad.onshape.com/documents/..." \
     --featurescript parts/hull.fs
   ```
4. **After injection, merge to `main` with user approval**:
   ```bash
   .venv/bin/python3 scripts/inject_featurescript_onshape.py merge \
     --document "https://cad.onshape.com/documents/..." \
     --branch ai/main
   ```
5. **Analyze human modifications on a branch**:
   ```bash
   .venv/bin/python3 scripts/inject_featurescript_onshape.py analyze \
     --document "https://cad.onshape.com/documents/..." \
     --base ai/main --target benoit/modifications
   ```

## Architecture

### Branch Strategy

```
Onshape Document
├── main                    ← humain (ajouts manuels en features natives)
└── ai/main                 ← IA (FeatureScript injecté uniquement)
```

- **IA n'écrit jamais dans `main`** — toujours `ai/main`, puis merge explicite.
- **Humain n'écrit jamais dans `ai/main`** — les modifs manuelles sont dans `main` ou des branches.
- **Merge `ai/main` → `main`** après approbation utilisateur.

### Part Studio Manifest

La présence de fichiers `.fs` dans `parts/` **est** le manifeste :

```
parts/hull.fs     → Part Studio "Hull"     → géré par l'IA
parts/rudder.fs   → Part Studio "Rudder"   → géré par l'IA
(pas de deck.fs)  → Part Studio "Deck"     → ignoré par l'IA
```

L'IA ne touche qu'aux Part Studios qui ont un `.fs` correspondant dans `parts/`.

### Workflow Complet

```
CYCLE NORMAL :
  cad-featurescript-gen → parts/hull.fs
  inject → ai/main (Part Studio "Hull")
  merge → ai/main → main (après approbation)
  L'humain voit la mise à jour dans main

AJOUT MANUEL (humain dans main) :
  Humain ajoute un taquet dans le Part Studio "Hull" sur main

INTÉGRATION (humain → FS) :
  Humain crée branche "benoit/cleats" depuis main
  @cad analyse benoit/cleats
  L'agent lit le diff des features
  L'agent met à jour parts/hull.fs
  L'agent injecte dans ai/main
  L'agent merge ai/main → main
```

## Rules

- **Never `main` directly** — all IA injections go to `ai/main`.
- **Never draw with mouse clicks** — Onshape uses WebGL canvas; Playwright cannot interact with 3D viewport.
- **Always use FeatureScript injection** — navigate to the FeatureScript editor and paste text.
- **Wait for compilation** — FeatureScript compiles asynchronously; wait for the green checkmark.
- **One `.fs` = one Part Studio** — the filename (without extension) matches the Part Studio name.
- **Capture screenshots** — after every injection and merge, for visual confirmation.
- **Merge requires approval** — show the user what changed before merging `ai/main` → `main`.
- **Use persistent browser context** — saves login state between sessions (`.browser-data/`).

## Commands

### `inject` — Inject FeatureScript into a Part Studio on ai/main

```bash
.venv/bin/python3 scripts/inject_featurescript_onshape.py inject \
  --document "https://cad.onshape.com/documents/<id>/w/<wid>" \
  --featurescript parts/hull.fs \
  [--screenshot result.png] \
  [--headless]
```

What it does:
1. Opens the Onshape document
2. Switches to (or creates) branch `ai/main`
3. Finds or creates the Part Studio matching the `.fs` filename
4. Creates or updates the FeatureScript feature with the code
5. Waits for compilation
6. Captures screenshot for verification

### `merge` — Merge ai/main → main

```bash
.venv/bin/python3 scripts/inject_featurescript_onshape.py merge \
  --document "https://cad.onshape.com/documents/<id>/w/<wid>" \
  --branch ai/main \
  [--approve]
```

What it does:
1. Shows a diff summary of what changed in `ai/main` vs `main`
2. Asks for user confirmation (unless `--approve` is set)
3. Performs the merge
4. Captures screenshot of the result

### `analyze` — Analyze feature differences between branches

```bash
.venv/bin/python3 scripts/inject_featurescript_onshape.py analyze \
  --document "https://cad.onshape.com/documents/<id>/w/<wid>" \
  --base ai/main \
  --target benoit/modifications \
  [--part Hull]
```

What it does:
1. Opens both branches
2. Compares the feature tree of specified Part Studios (or all AI-managed ones)
3. Lists added, modified, and removed features
4. Outputs a structured diff report the agent can use to update FeatureScript

### `list-parts` — Show Part Studio mapping

```bash
.venv/bin/python3 scripts/inject_featurescript_onshape.py list-parts
```

What it does:
1. Reads all `.fs` files from `parts/`
2. Shows the mapping: `hull.fs → Part Studio "Hull"`

## Examples

### Example 1: Full cycle for a hull update
```bash
# 1. cad-featurescript-gen produces parts/hull.fs
# 2. Inject into ai/main
.venv/bin/python3 scripts/inject_featurescript_onshape.py inject \
  --document "https://cad.onshape.com/documents/abc123/w/def456" \
  --featurescript parts/hull.fs

# 3. Review the screenshot
# 4. Merge to main (user approves)
.venv/bin/python3 scripts/inject_featurescript_onshape.py merge \
  --document "https://cad.onshape.com/documents/abc123/w/def456" \
  --branch ai/main
```

### Example 2: Analyze human modifications
```bash
# User added a cleat in Part Studio "Hull" on branch benoit/cleats
.venv/bin/python3 scripts/inject_featurescript_onshape.py analyze \
  --document "https://cad.onshape.com/documents/abc123/w/def456" \
  --base ai/main \
  --target benoit/cleats \
  --part Hull
```

## Anti-Patterns

- ❌ Injecting into `main` directly — always use `ai/main`.
- ❌ Trying to click on the 3D viewport canvas — it's a WebGL surface.
- ❌ Assuming FeatureScript compiled — always check the status badge.
- ❌ Merging without user approval — show the diff first.
- ❌ Modifying Part Studios that have no `.fs` in `parts/` — let the human own those.
- ❌ Ignoring error messages in the FeatureScript editor.
