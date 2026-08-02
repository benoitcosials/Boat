---
name: cad-onshape-injector
description: "Injects FeatureScript into Onshape via session-authenticated REST calls (browser cookies + X-XSRF-TOKEN, no API keys, off-quota). Manifest-driven: manifest.json maps parts to Feature Studios / Part Studios and holds the workspace unit. Generates FeatureScript, syncs it, instantiates rendered geometry, and commits an Onshape Version at the end of every run. Triggered by: inject into Onshape, FeatureScript injection, sync project, commit version, Onshape automation, generate hull."
---

## Method — why this works

Onshape is a single-page app that talks to its own REST backend. We piggyback on
that: **Playwright only carries an authenticated browser session** (persisted in
`.browser-data/`); every CAD operation is a plain HTTP call to Onshape's API, not
a UI click.

- **Reads** need only the session cookie.
- **Writes** need the cookie **plus** the `X-XSRF-TOKEN` header (value of the
  JS-readable `XSRF-TOKEN` cookie). Without it, writes return `401`.
- These count as **browser-session** calls, so they are **NOT** charged against
  the Free-plan annual API-key quota (2,500/yr). Iterations are effectively
  unlimited. **Do not use API keys** for this reason.

## Layout

```
scripts/
├── onshape/                # the client package
│   ├── session.py          OnshapeSession — Playwright session + cookie + XSRF
│   ├── context.py          DocumentContext.from_url(url) -> did/wid/base_url
│   ├── feature_studio.py   FeatureStudioClient.sync(name, fs_text)   [1 .fs = 1 FS]
│   ├── part_studio.py      instantiate() · set_appearance() · rename_part()
│   ├── versions.py         VersionsClient.commit(name, desc)          [= a commit]
│   ├── units.py            get_length_unit(session, ctx)              [workspace unit]
│   ├── generator.py        generate_optimist_hull(unit, loa_bounds)   [FS emitter]
│   └── manifest.py         load_manifest() / save_manifest()
├── sync_project.py         MAIN entrypoint — manifest sync + commit
└── demo_inject.py          single-.fs test harness + commit
```

## Manifest — the master config

`manifest.json` at the repo root is the single source of truth:

```jsonc
{
  "project": "boat",
  "onshape": { "document_url": "...", "did": "...", "wid": "...", "workspace_unit": "millimeter" },
  "parts": [
    { "name": "Hull", "fs": "parts/hull.fs", "generator": "optimist_hull",
      "loa_bounds": [500, 2300, 6000], "feature": "optimistHull",
      "parameters": { "loa": "2300 millimeter" } }
  ],
  "last_ai_version": "<version id>"
}
```

- **1 part = 1 Feature Studio (code) + 1 Part Studio (rendered geometry)**, same name.
- A part with a `generator` key is regenerated on disk each run; otherwise
  `parts/<name>.fs` is read as-is.
- The document URL is not a CLI argument — it lives here.

## Units

- **Read** the document's workspace length unit (`get_length_unit`) and respect it;
  never hardcode meters.
- Two length syntaxes, do not confuse them:
  - **FeatureScript source** requires the star: `2300 * millimeter`.
  - **Dialog / parameter expressions** take no star: `2300 millimeter`.
- **Preferred**: write generators unit-agnostically — express dimensions as
  fractions of a driving length and multiply by `definition.<len>` (which carries
  units). Then only the bounds line names a unit; the body has no unit tokens.

## Commit — an Onshape Version

Onshape has no git; a **commit is a Version** (an immutable, named snapshot):
`POST /api/v10/documents/d/{did}/versions`.

- **Every script invocation ends with a commit** tagged `[AI] ...`; its id is
  written to `manifest.last_ai_version`.
- Human-authored snapshots use `[HUMAN] ...`. Human changes are detected by
  diffing the current workspace against `last_ai_version`.
- The API acts as the logged-in user, so authorship lives in the version name.

## Geometry & the shared vocabulary

- A Feature Studio only **defines** features — it renders nothing. Instantiate the
  custom feature into a **Part Studio** to produce a solid (`instantiate()`).
- Mark the part being discussed with **colour** (`set_appearance`) and a **name**
  (`rename_part`); both are visible to the human in the Parts panel.
- PNG decals/textures are Render Studio (paid) — unavailable on Free.

## Commands

### `sync_project.py` — full project sync (main entrypoint)

```bash
.venv/Scripts/python .opencode/skills/cad-onshape-injector/scripts/sync_project.py
```

Reads `manifest.json`, records the workspace unit, and for each part: regenerates
its `.fs` (if it has a `generator`), syncs it into a Feature Studio, ensures a
Part Studio, instantiates the feature if absent — then **commits** an `[AI]`
Version and writes `last_ai_version` back to the manifest.

### `demo_inject.py` — single-part test

```bash
.venv/Scripts/python .opencode/skills/cad-onshape-injector/scripts/demo_inject.py \
  "<document_url>" parts/hull.fs --param loa="2400 millimeter" --color 173,216,230
```

Syncs one `.fs`, instantiates it, colours/renames the part, screenshots, and
commits. First run opens a browser for a one-time manual login (then persisted).

## Rules

- **REST via the session, never UI clicks** on the WebGL canvas or the Monaco editor.
- **Never use API keys** — session calls stay off the annual quota.
- **Read + respect `workspace_unit`** — never hardcode `* meter`.
- **FS source uses `n * unit`; dialog/param expressions use `n unit`** (no star).
- **1 `.fs` = 1 Feature Studio = 1 Part Studio** (same name). Only manage parts
  listed in the manifest; Part Studios without a manifest entry are human-owned.
- **End every run with a commit**; record `last_ai_version`.
- **Never edit generated `parts/*.fs` by hand** — change the generator or manifest.
- **The LLM never runs raw git** — the git history of `parts/*.fs` is
  prompt/pipeline-owned.

## Anti-Patterns

- ❌ Using API keys (charged against 2,500/yr) — use the browser session.
- ❌ Clicking the 3D canvas or driving the FeatureScript editor through the UI.
- ❌ Hardcoding `* meter` — read and respect `workspace_unit`.
- ❌ Putting a `*` in dialog/parameter expressions (`2.4 * meter` shows ugly).
- ❌ Hand-editing a generated `parts/*.fs` — it will be overwritten.
- ❌ Forgetting the end-of-run commit.
- ❌ Thinking in Onshape "branches" or git — use Versions.
