#!/usr/bin/env python3
"""List all features in a Part Studio to understand the feature tree.

Run from the repo root:
  .venv/bin/python3 .opencode/skills/cad-onshape-injector/scripts/list_features.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from onshape import (  # noqa: E402
    DocumentContext,
    OnshapeSession,
    PartStudioClient,
)
from onshape.manifest import load_manifest  # noqa: E402


def main() -> None:
    manifest = load_manifest()
    onshape = manifest["onshape"]
    ctx = DocumentContext.from_url(onshape["document_url"])

    with OnshapeSession(base_url=ctx.base_url) as session:
        parts = PartStudioClient(session, ctx)

        print("=" * 70)
        print("FEATURE TREE")
        print("=" * 70)
        print()

        for part in manifest.get("parts", []):
            name = part["name"]
            ps_eid = part.get("part_studio_eid")

            if not ps_eid:
                print(f"Part: {name}")
                print("  ⚠️  No Part Studio eid in manifest")
                print()
                continue

            print(f"Part: {name} (Part Studio: {ps_eid})")
            print()

            features = parts.list_features(ps_eid)
            if not features:
                print("  No features")
            else:
                print(f"  {len(features)} feature(s):")
                for i, f in enumerate(features, 1):
                    feature_id = f.get("featureId")
                    feature_type = f.get("featureType")
                    feature_name = f.get("name", "?")
                    suppression = f.get("suppressionState", "UNKNOWN")

                    print(f"  {i}. {feature_name}")
                    print(f"     ID: {feature_id}")
                    print(f"     Type: {feature_type}")
                    print(f"     Suppression: {suppression}")
                    print()

            # Check for errors
            errors = parts.feature_errors(ps_eid)
            if errors:
                print(f"  ❌ {len(errors)} error(s):")
                for err in errors:
                    print(f"     - {err.get('name')} ({err.get('featureId')}): {err.get('status')}")
            else:
                print("  ✅ No errors")
            print()

        print("=" * 70)


if __name__ == "__main__":
    main()
