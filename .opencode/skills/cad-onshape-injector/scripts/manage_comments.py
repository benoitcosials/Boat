#!/usr/bin/env python3
"""Manage Onshape comments as a geometry-anchored command channel.

Subcommands:
  list     — List open comments (default)
  post     — Create a new comment (requires --element-id)
  reply    — Reply to an existing comment
  resolve  — Mark a comment as resolved

Run from the repo root:
  .venv/bin/python3 .opencode/skills/cad-onshape-injector/scripts/manage_comments.py list
  .venv/bin/python3 .opencode/skills/cad-onshape-injector/scripts/manage_comments.py post "Test message" --element-id <eid>
  .venv/bin/python3 .opencode/skills/cad-onshape-injector/scripts/manage_comments.py reply <comment_id> "Reply message"
  .venv/bin/python3 .opencode/skills/cad-onshape-injector/scripts/manage_comments.py resolve <comment_id>

Uses saved cookies from .browser-data/ (start session with start_session.py first).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from onshape import CommentsClient, DocumentContext, OnshapeSession  # noqa: E402
from onshape.manifest import load_manifest  # noqa: E402


def _describe(target: dict) -> str:
    """Format a comment target for display."""
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


def cmd_list(args: argparse.Namespace) -> None:
    """List open comments."""
    ctx = DocumentContext.from_url(load_manifest()["onshape"]["document_url"])
    with OnshapeSession(base_url=ctx.base_url) as session:
        comments = CommentsClient(session, ctx)
        open_comments = comments.open()

    if not open_comments:
        print("No open comments.")
        return

    print(f"{len(open_comments)} open comment(s):\n")
    for comment in open_comments:
        author = comment.get("author") or "?"
        print(f"  [{comment['id']}] ({author}) {comment['message']!r}")
        print(f"      -> {_describe(comment['target'])}")
        print()


def cmd_post(args: argparse.Namespace) -> None:
    """Create a new comment."""
    ctx = DocumentContext.from_url(load_manifest()["onshape"]["document_url"])
    with OnshapeSession(base_url=ctx.base_url) as session:
        comments = CommentsClient(session, ctx)
        created = comments.post(args.message, element_id=args.element_id)

    comment_id = created.get("id")
    print(f"✅ Created comment: {comment_id}")
    print(f"   Message: {created.get('message')!r}")


def cmd_reply(args: argparse.Namespace) -> None:
    """Reply to an existing comment."""
    ctx = DocumentContext.from_url(load_manifest()["onshape"]["document_url"])
    with OnshapeSession(base_url=ctx.base_url) as session:
        comments = CommentsClient(session, ctx)
        reply = comments.reply(args.comment_id, args.message)

    print(f"✅ Created reply: {reply.get('id')}")
    print(f"   Message: {reply.get('message')!r}")


def cmd_resolve(args: argparse.Namespace) -> None:
    """Mark a comment as resolved."""
    ctx = DocumentContext.from_url(load_manifest()["onshape"]["document_url"])
    with OnshapeSession(base_url=ctx.base_url) as session:
        comments = CommentsClient(session, ctx)
        resolved = comments.resolve(args.comment_id)

    print(f"✅ Resolved comment: {args.comment_id}")
    print(f"   State: {resolved.get('state')} (0=open, 1=resolved)")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Manage Onshape comments as a geometry-anchored command channel"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # list
    p_list = sub.add_parser("list", help="List open comments")
    p_list.set_defaults(func=cmd_list)

    # post
    p_post = sub.add_parser("post", help="Create a new comment")
    p_post.add_argument("message", help="Comment message")
    p_post.add_argument("--element-id", required=True, help="Part Studio / Feature Studio eid (required)")
    p_post.set_defaults(func=cmd_post)

    # reply
    p_reply = sub.add_parser("reply", help="Reply to an existing comment")
    p_reply.add_argument("comment_id", help="Comment ID to reply to")
    p_reply.add_argument("message", help="Reply message")
    p_reply.set_defaults(func=cmd_reply)

    # resolve
    p_resolve = sub.add_parser("resolve", help="Mark a comment as resolved")
    p_resolve.add_argument("comment_id", help="Comment ID to resolve")
    p_resolve.set_defaults(func=cmd_resolve)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
