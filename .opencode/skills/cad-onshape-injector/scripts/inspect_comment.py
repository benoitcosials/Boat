#!/usr/bin/env python3
"""Inspect an existing comment to understand the expected API format.

Run from the repo root:
  .venv/bin/python3 .opencode/skills/cad-onshape-injector/scripts/inspect_comment.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from onshape import (  # noqa: E402
    CommentsClient,
    DocumentContext,
    OnshapeSession,
)
from onshape.manifest import load_manifest  # noqa: E402


def main() -> None:
    manifest = load_manifest()
    onshape = manifest["onshape"]
    ctx = DocumentContext.from_url(onshape["document_url"])

    with OnshapeSession(base_url=ctx.base_url) as session:
        comments = CommentsClient(session, ctx)

        print("=" * 70)
        print("INSPECT: Existing Comment Structure")
        print("=" * 70)

        # Get all comments (raw API response)
        print("\nFetching all comments (raw API response)...")
        raw_comments = session.get(f"/comments?did={ctx.did}")
        
        print(f"\nRaw response keys: {list(raw_comments.keys()) if isinstance(raw_comments, dict) else 'Not a dict'}")
        
        items = raw_comments.get("items", [])
        print(f"\nFound {len(items)} comment(s)")

        if items:
            # Inspect the first comment in detail
            comment = items[0]
            print("\n" + "=" * 70)
            print("FIRST COMMENT STRUCTURE:")
            print("=" * 70)
            print(json.dumps(comment, indent=2, default=str))

            print("\n" + "=" * 70)
            print("KEY FIELDS:")
            print("=" * 70)
            print(f"  id: {comment.get('id')}")
            print(f"  message: {comment.get('message')}")
            print(f"  state: {comment.get('state')} (0=open, 1=resolved)")
            print(f"  elementId: {comment.get('elementId')}")
            print(f"  elementQuery: {comment.get('elementQuery')}")
            print(f"  parentId: {comment.get('parentId')}")
            print(f"  assignedTo: {comment.get('assignedTo')}")
            print(f"  createdAt: {comment.get('createdAt')}")
            print(f"  createdBy: {comment.get('createdBy')}")
            
            # Check if there's an objectId or similar
            print("\n" + "=" * 70)
            print("SEARCHING FOR 'OBJECT' FIELDS:")
            print("=" * 70)
            for key, value in comment.items():
                if 'object' in key.lower() or 'id' in key.lower():
                    print(f"  {key}: {value}")

        print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
