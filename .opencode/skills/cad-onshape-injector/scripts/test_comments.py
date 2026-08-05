#!/usr/bin/env python3
"""Test the CommentsClient write operations (post, reply, resolve).

This script tests the full comment lifecycle:
  1. List existing comments
  2. Create a new document-level comment
  3. Reply to that comment
  4. Resolve the comment

Run from the repo root:
  .venv/bin/python3 .opencode/skills/cad-onshape-injector/scripts/test_comments.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from onshape import CommentsClient, DocumentContext, OnshapeSession  # noqa: E402
from onshape.manifest import load_manifest  # noqa: E402


def main() -> None:
    ctx = DocumentContext.from_url(load_manifest()["onshape"]["document_url"])

    with OnshapeSession(base_url=ctx.base_url) as session:
        comments = CommentsClient(session, ctx)

        # 1. List existing comments
        print("=" * 60)
        print("STEP 1: List existing comments")
        print("=" * 60)
        existing = comments.open()
        print(f"Found {len(existing)} open comment(s)")
        for c in existing:
            print(f"  [{c['id']}] {c['message']!r} by {c['author']}")
        print()

        # 2. Create a new comment anchored to the Hull Part Studio
        print("=" * 60)
        print("STEP 2: Create a new comment anchored to Hull Part Studio")
        print("=" * 60)
        # Use the Hull Part Studio as anchor (from element listing)
        element_id = "91f54d1c620906757545a08d"  # Hull Part Studio
        test_message = "🤖 [AI TEST] Testing comment creation via API"
        created = comments.post(test_message, element_id=element_id)
        comment_id = created.get("id")
        if not comment_id:
            print("❌ ERROR: Failed to create comment")
            return
        print(f"✅ Created comment: {comment_id}")
        print(f"   Message: {created.get('message')!r}")
        print(f"   Anchored to element: {element_id}")
        print()

        # 3. Reply to the comment
        print("=" * 60)
        print("STEP 3: Reply to the comment")
        print("=" * 60)
        reply_message = "🤖 [AI TEST] Testing reply via API"
        reply = comments.reply(comment_id, reply_message)
        print(f"✅ Created reply: {reply.get('id')}")
        print(f"   Message: {reply.get('message')!r}")
        print()

        # 4. Resolve the comment
        print("=" * 60)
        print("STEP 4: Resolve the comment")
        print("=" * 60)
        resolved = comments.resolve(comment_id)
        print(f"✅ Resolved comment: {comment_id}")
        print(f"   State: {resolved.get('state')} (0=open, 1=resolved)")
        print()

        # 5. Verify the comment is now resolved
        print("=" * 60)
        print("STEP 5: Verify comment is resolved")
        print("=" * 60)
        remaining = comments.open()
        print(f"Open comments after resolve: {len(remaining)}")
        if comment_id in [c["id"] for c in remaining]:
            print(f"❌ ERROR: Comment {comment_id} is still open!")
        else:
            print(f"✅ SUCCESS: Comment {comment_id} is no longer in open list")
        print()

        print("=" * 60)
        print("✅ All tests passed!")
        print("=" * 60)


if __name__ == "__main__":
    main()
