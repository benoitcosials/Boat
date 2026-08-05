#!/usr/bin/env python3
"""Diagnose FeatureScript errors in all parts from manifest.json.

This script provides detailed error information for each failing part:
  - Feature error type (coarse status)
  - Feature error enum (detailed category)
  - Feature notice (message + line:col location in FeatureScript)

Run from the repo root:
  .venv/bin/python3 .opencode/skills/cad-onshape-injector/scripts/diagnose_errors.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from onshape import (  # noqa: E402
    DocumentContext,
    FeatureStudioClient,
    OnshapeSession,
    PartStudioClient,
)
from onshape.manifest import load_manifest  # noqa: E402


def main() -> None:
    manifest = load_manifest()
    onshape = manifest["onshape"]
    ctx = DocumentContext.from_url(onshape["document_url"])

    with OnshapeSession(base_url=ctx.base_url) as session:
        studios = FeatureStudioClient(session, ctx)
        parts = PartStudioClient(session, ctx)

        print("=" * 70)
        print("DIAGNOSTIC: FeatureScript Errors")
        print("=" * 70)
        print()

        for part in manifest.get("parts", []):
            name = part["name"]
            fs_path = Path(part["fs"])
            fs_eid = part.get("feature_studio_eid")
            ps_eid = part.get("part_studio_eid")

            print(f"Part: {name}")
            print(f"  FeatureScript: {fs_path}")
            print(f"  Feature Studio eid: {fs_eid}")
            print(f"  Part Studio eid: {ps_eid}")
            print()

            # Check if Feature Studio compiles
            if fs_eid:
                compiles = studios.compiles(fs_eid)
                print(f"  Compiles: {'✅ YES' if compiles else '❌ NO'}")
                if not compiles:
                    print("  ⚠️  FeatureScript did NOT compile")
                    print("     Check the Feature Studio in Onshape for syntax errors")
                    print()
                    continue
                print()

            # Check Part Studio for errors
            if ps_eid:
                errors = parts.feature_errors(ps_eid)
                if not errors:
                    print("  ✅ No errors in Part Studio")
                    print()
                    continue

                print(f"  ❌ {len(errors)} error(s) in Part Studio:")
                print()

                for err in errors:
                    feature_id = err.get("featureId")
                    feature_name = err.get("name")
                    status = err.get("status")

                    print(f"  Feature: {feature_name} ({feature_id})")
                    print(f"  Status: {status}")

                    # Get detailed error enum
                    if feature_id:
                        error_enum = parts.feature_error_enum(ps_eid, feature_id)
                        if error_enum:
                            print(f"  Error type: {error_enum}")

                    # Get detailed notice with line:col
                    spec = studios.featurespec(fs_eid) if fs_eid else None
                    if spec:
                        notice = parts.feature_notice(
                            ps_eid,
                            spec["namespace"],
                            spec["featureType"],
                            part.get("parameters", {}),
                            fs_eid,
                        )
                        if notice:
                            message = notice.get("message")
                            location = notice.get("location")
                            print(f"  Message: {message}")
                            if location:
                                print(f"  Location: {location}")
                    print()

        print("=" * 70)
        print("END DIAGNOSTIC")
        print("=" * 70)


if __name__ == "__main__":
    main()
