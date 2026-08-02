#!/usr/bin/env python3
"""List open Onshape comments as a geometry-anchored command queue (read-only).

Prints each unresolved comment with its message and decoded target so we can
discuss before making any change. This script never mutates the model.

Run from the repo root:
  .venv/Scripts/python .opencode/skills/cad-onshape-injector/scripts/list_comments.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from onshape import CommentsClient, DocumentContext, OnshapeSession  # noqa: E402
from onshape.manifest import load_manifest  # noqa: E402


def _describe(target: dict) -> str:
    kind = target.get("kind")
    if kind == "edge":
        section, segment = target.get("section"), target.get("segment")
        return f"edge — section '{section}', segment '{segment}'"
    if kind == "face":
        return "face (loft) — name it via its colour/label (e.g. J1 = pont)"
    if kind == "part":
        return "the whole part (body)"
    if target.get("entityType"):
        return f"{target['entityType']} (unclassified)"
    return "document/element (no geometry)"


def main() -> None:
    ctx = DocumentContext.from_url(load_manifest()["onshape"]["document_url"])
    with OnshapeSession(base_url=ctx.base_url) as session:
        comments = CommentsClient(session, ctx).open()

    if not comments:
        print("No open comments.")
        return

    print(f"{len(comments)} open comment(s):")
    for comment in comments:
        author = comment.get("author") or "?"
        print(f"  [{comment['id']}] ({author}) {comment['message']!r}")
        print(f"      -> {_describe(comment['target'])}")


if __name__ == "__main__":
    main()
