#!/usr/bin/env python3
"""Isolated end-to-end test of the session-based Onshape client.

Reproduces the flow validated live:
  1. sync a .fs file into a Feature Studio  (1 API call)
  2. read its feature spec
  3. instantiate the feature into a same-named Part Studio -> renders a solid
  4. colour + rename the resulting part (shared human/AI vocabulary)
  5. screenshot the Part Studio

Run from the repo root, e.g.:
  .venv/bin/python3 .opencode/skills/cad-onshape-injector/scripts/demo_inject.py \
    "https://cad.onshape.com/documents/<did>/w/<wid>/e/<eid>" \
    parts/hull.fs --param loa="2400 millimeter" --color 232,126,34

First run opens a browser: log in to Onshape yourself; the session persists in
.browser-data/ for subsequent runs.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from onshape import (  # noqa: E402
    DocumentContext,
    FeatureStudioClient,
    OnshapeSession,
    PartStudioClient,
    VersionsClient,
)


def _parse_params(pairs: list[str]) -> dict[str, str]:
    params: dict[str, str] = {}
    for pair in pairs:
        if "=" not in pair:
            raise SystemExit(f"--param must be name=expression, got: {pair!r}")
        key, _, expr = pair.partition("=")
        params[key.strip()] = expr.strip()
    return params


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("document_url", help="Onshape document/workspace URL")
    parser.add_argument("fs_file", help="Path to a FeatureScript .fs file")
    parser.add_argument("--name", help="Element name (default: derived from filename)")
    parser.add_argument(
        "--param", action="append", default=[], help="Feature parameter: name=expression"
    )
    parser.add_argument("--color", help="Part colour as R,G,B (0-255)")
    parser.add_argument("--screenshot", default="tmp/demo_inject.png")
    parser.add_argument("--headless", action="store_true")
    args = parser.parse_args()

    ctx = DocumentContext.from_url(args.document_url)
    name = args.name or Path(args.fs_file).stem.replace("_", " ").title()
    fs_text = Path(args.fs_file).read_text(encoding="utf-8")
    params = _parse_params(args.param)

    Path(args.screenshot).parent.mkdir(parents=True, exist_ok=True)

    with OnshapeSession(base_url=ctx.base_url, headless=args.headless) as session:
        studios = FeatureStudioClient(session, ctx)
        parts = PartStudioClient(session, ctx)

        fs_eid = studios.sync(name, fs_text)
        spec = studios.featurespec(fs_eid)
        print(f"Feature Studio '{name}' synced ({fs_eid}); feature: {spec['featureType']}")

        ps_eid = parts.ensure(name)
        result = parts.instantiate(
            ps_eid, spec["featureType"], spec["namespace"], f"{name} 1", params
        )
        status = result.get("featureState", {}).get("featureStatus")
        print(f"Part Studio '{name}' ({ps_eid}); feature status: {status}")

        rendered = parts.list_parts(ps_eid)
        if rendered and args.color:
            rgb = tuple(int(c) for c in args.color.split(","))
            part_id = rendered[0]["partId"]
            parts.set_appearance(ps_eid, part_id, rgb)  # type: ignore[arg-type]
            parts.rename_part(ps_eid, part_id, name.upper())
            print(f"Part {part_id} coloured {rgb} and renamed '{name.upper()}'")

        doc_url = f"{ctx.base_url}/documents/{ctx.did}/w/{ctx.wid}/e/{ps_eid}"
        session.screenshot(args.screenshot, document_url=doc_url)
        print(f"Screenshot -> {args.screenshot}")
        print("Parts:", [p.get("name") for p in rendered])

        # Every script invocation ends with a commit (an Onshape Version).
        import datetime as _dt

        stamp = _dt.datetime.now().strftime("%Y-%m-%d %H:%M")
        version = VersionsClient(session, ctx).commit(
            f"[AI] {name} {stamp}", "Automated inject from demo_inject.py"
        )
        print(f"Committed version {version['id']} — {version['name']}")


if __name__ == "__main__":
    main()
