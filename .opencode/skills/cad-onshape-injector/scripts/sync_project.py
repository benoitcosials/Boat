#!/usr/bin/env python3
"""Sync the whole project to Onshape from manifest.json — and commit at the end.

Steps:
  1. Read manifest.json (the master config).
  2. Read the document's workspace length unit and record it in the manifest.
  3. For each part: (re)generate its FeatureScript if it has a "generator",
     otherwise read parts/<name>.fs; sync it into a Feature Studio; ensure a
     Part Studio; instantiate the feature if it is not already present.
  4. Commit an Onshape Version tagged "[AI] ..." and record it as last_ai_version.

Every invocation ends with a commit, so each operation is traceable.

Run from the repo root:
  .venv/Scripts/python .opencode/skills/cad-onshape-injector/scripts/sync_project.py
The first run opens a browser for a one-time manual login (persisted afterwards).
"""

from __future__ import annotations

import datetime as _dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from onshape import (  # noqa: E402
    DocumentContext,
    FeatureStudioClient,
    OnshapeSession,
    PartStudioClient,
    VersionsClient,
    get_length_unit,
)
from onshape.generator import generate_optimist_hull  # noqa: E402
from onshape.manifest import load_manifest, save_manifest  # noqa: E402

# Map a manifest "generator" id to a function(unit, loa_bounds) -> FeatureScript.
GENERATORS = {
    "optimist_hull": generate_optimist_hull,
}


def _generate_if_needed(part: dict, unit: str) -> str:
    """Return the FeatureScript for a part, regenerating it on disk if requested."""
    fs_path = Path(part["fs"])
    generator_id = part.get("generator")
    if generator_id:
        generator = GENERATORS.get(generator_id)
        if generator is None:
            raise SystemExit(f"Unknown generator: {generator_id!r}")
        bounds = tuple(part.get("loa_bounds", (500, 2300, 6000)))
        fs_text = generator(unit=unit, loa_bounds=bounds)
        fs_path.parent.mkdir(parents=True, exist_ok=True)
        fs_path.write_text(fs_text, encoding="utf-8")
        return fs_text
    return fs_path.read_text(encoding="utf-8")


def main() -> None:
    manifest = load_manifest()
    onshape = manifest["onshape"]
    ctx = DocumentContext.from_url(onshape["document_url"])

    with OnshapeSession(base_url=ctx.base_url) as session:
        unit = get_length_unit(session, ctx)
        onshape["workspace_unit"] = unit
        print(f"Workspace unit: {unit}")

        studios = FeatureStudioClient(session, ctx)
        parts = PartStudioClient(session, ctx)

        for part in manifest.get("parts", []):
            name = part["name"]
            fs_text = _generate_if_needed(part, unit)
            fs_eid = studios.sync(name, fs_text)
            spec = studios.featurespec(fs_eid)
            ps_eid = parts.ensure(name)

            already = any(
                f.get("featureType") == spec["featureType"] for f in parts.list_features(ps_eid)
            )
            if not already:
                parts.instantiate(
                    ps_eid,
                    spec["featureType"],
                    spec["namespace"],
                    f"{name} 1",
                    part.get("parameters", {}),
                )
            part["feature_studio_eid"] = fs_eid
            part["part_studio_eid"] = ps_eid
            print(f"  {name}: FS {fs_eid} -> Part Studio {ps_eid}")

        stamp = _dt.datetime.now().strftime("%Y-%m-%d %H:%M")
        version = VersionsClient(session, ctx).commit(
            f"[AI] sync {stamp}", "Automated sync from manifest.json"
        )
        manifest["last_ai_version"] = version["id"]
        save_manifest(manifest)
        print(f"Committed version {version['id']} — {version['name']}")


if __name__ == "__main__":
    main()
