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

By default, this script launches its own browser session. To use a persistent
session started by start_session.py:
  .venv/Scripts/python .opencode/skills/cad-onshape-injector/scripts/sync_project.py --persistent
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


def _report_feature_errors(
    parts: PartStudioClient, ps_eid: str, name: str, spec: dict, parameters: dict, fs_eid: str
) -> None:
    """Print the coarse status and the rich FeatureScript message for a failed part."""
    for err in parts.feature_errors(ps_eid):
        reason = parts.feature_error_enum(ps_eid, err["featureId"]) or err["status"]
        print(f"  {name}: feature '{err['name']}' errored -> {reason}")
    detail = parts.feature_notice(
        ps_eid, spec["namespace"], spec["featureType"], parameters, fs_eid
    )
    if detail:
        where = f" ({detail['location']})" if detail.get("location") else ""
        print(f"    {detail['message']}{where}")


def _print_summary(summary: dict) -> None:
    """Print a compact, structured description of what was actually built."""
    print(
        f"    {int(summary['parts'])} part(s), {int(summary['faces'])} faces, "
        f"{int(summary['edges'])} edges, {int(summary['vertices'])} vertices"
    )
    print(
        f"    bbox {summary['length_mm']:.0f} x {summary['width_mm']:.0f} x "
        f"{summary['height_mm']:.0f} mm, volume {summary['volume_mm3'] / 1000.0:.0f} cm3"
    )


# Face label initial -> colour name (French), for the shared human/AI vocabulary.
_COLOUR_FR = {"R": "rouge", "J": "jaune", "V": "vert", "B": "bleu", "C": "cyan", "M": "magenta"}


def _print_vocabulary(faces: list[dict]) -> None:
    """Print each labelled face (colour/region) with its clockwise segments."""
    if not faces:
        return
    print("    faces (label = region, couleur -> segments sens horaire):")
    for face in sorted(faces, key=lambda f: f["label"]):
        colour = _COLOUR_FR.get(face["label"][0], "?")
        segments = ", ".join(
            f"s{int(s['seg'])}={s['id']} {int(s['lenMm'])}mm"
            for s in sorted(face["segments"], key=lambda s: s["seg"])
        )
        print(f"      {face['label']} ({face['region']}, {colour}) [{face['faceId']}]: {segments}")


def _sync_part(
    part: dict, unit: str, studios: FeatureStudioClient, parts: PartStudioClient
) -> bool:
    """Sync one part to Onshape. Returns True on success, False on any error."""
    name = part["name"]
    fs_text = _generate_if_needed(part, unit)
    fs_eid = studios.sync(name, fs_text)
    part["feature_studio_eid"] = fs_eid

    if not studios.compiles(fs_eid):
        print(f"  {name}: FeatureScript did NOT compile (see FeatureScript notices)")
        return False

    spec = studios.featurespec(fs_eid)
    ps_eid = parts.ensure(name)
    part["part_studio_eid"] = ps_eid

    already = any(f.get("featureType") == spec["featureType"] for f in parts.list_features(ps_eid))
    if not already:
        parts.instantiate(
            ps_eid, spec["featureType"], spec["namespace"], f"{name} 1", part.get("parameters", {})
        )

    if parts.feature_errors(ps_eid):
        _report_feature_errors(parts, ps_eid, name, spec, part.get("parameters", {}), fs_eid)
        return False

    print(f"  {name}: OK — FS {fs_eid} -> Part Studio {ps_eid}")
    _print_summary(parts.summary(ps_eid))
    _print_vocabulary(parts.vocabulary(ps_eid))
    return True


def main() -> None:
    manifest = load_manifest()
    onshape = manifest["onshape"]
    ctx = DocumentContext.from_url(onshape["document_url"])

    print("🔗 Connecting to Onshape (using saved cookies from .browser-data/)...")
    with OnshapeSession(base_url=ctx.base_url) as session:
        _do_sync(session, ctx, manifest, onshape)


def _do_sync(session, ctx, manifest, onshape):
    """Perform the actual sync operation."""
    unit = get_length_unit(session, ctx)
    onshape["workspace_unit"] = unit
    print(f"Workspace unit: {unit}")

    studios = FeatureStudioClient(session, ctx)
    parts = PartStudioClient(session, ctx)

    failed = [
        part["name"]
        for part in manifest.get("parts", [])
        if not _sync_part(part, unit, studios, parts)
    ]

    if failed:
        save_manifest(manifest)
        raise SystemExit(f"Aborting commit — errors in: {', '.join(failed)}")

    stamp = _dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    version = VersionsClient(session, ctx).commit(
        f"[AI] sync {stamp}", "Automated sync from manifest.json"
    )
    manifest["last_ai_version"] = version["id"]
    save_manifest(manifest)
    print(f"Committed version {version['id']} — {version['name']}")


if __name__ == "__main__":
    main()
