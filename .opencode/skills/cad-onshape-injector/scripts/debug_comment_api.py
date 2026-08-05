#!/usr/bin/env python3
"""Test different comment body formats to find the correct API signature.

Run from the repo root:
  .venv/bin/python3 .opencode/skills/cad-onshape-injector/scripts/debug_comment_api.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from onshape import (  # noqa: E402
    DocumentContext,
    OnshapeSession,
)
from onshape.manifest import load_manifest  # noqa: E402


def test_body(session, ctx, body, label):
    """Test a specific body format."""
    print(f"\n{label}")
    print(f"  Body: {body}")
    try:
        result = session.post(f"/comments?did={ctx.did}", body)
        print(f"  ✅ SUCCESS: {result.get('id')}")
        return result
    except Exception as e:
        print(f"  ❌ FAILED: {e}")
        return None


def main() -> None:
    manifest = load_manifest()
    onshape = manifest["onshape"]
    ctx = DocumentContext.from_url(onshape["document_url"])

    with OnshapeSession(base_url=ctx.base_url) as session:
        print("=" * 70)
        print("DEBUG: Testing Comment API Body Formats")
        print("=" * 70)

        element_id = "91f54d1c620906757545a08d"  # Hull Part Studio
        message = "🤖 [DEBUG] Test comment"

        # Test 1: elementId (what we tried)
        test_body(
            session,
            ctx,
            {"message": message, "elementId": element_id},
            "Test 1: elementId",
        )

        # Test 2: objectId (maybe that's the field name?)
        test_body(
            session,
            ctx,
            {"message": message, "objectId": element_id},
            "Test 2: objectId",
        )

        # Test 3: element_id (snake_case?)
        test_body(
            session,
            ctx,
            {"message": message, "element_id": element_id},
            "Test 3: element_id (snake_case)",
        )

        # Test 4: Both elementId and objectId
        test_body(
            session,
            ctx,
            {"message": message, "elementId": element_id, "objectId": element_id},
            "Test 4: elementId + objectId",
        )

        # Test 5: No element (document-level)
        test_body(
            session,
            ctx,
            {"message": message},
            "Test 5: No element (document-level)",
        )

        # Test 6: With workspace ID
        test_body(
            session,
            ctx,
            {"message": message, "elementId": element_id, "workspaceId": ctx.wid},
            "Test 6: elementId + workspaceId",
        )

        print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
