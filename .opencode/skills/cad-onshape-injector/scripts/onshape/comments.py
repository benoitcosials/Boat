"""CommentsClient — geometry-anchored command channel via Onshape comments.

A comment is pinned to one entity; its `elementQuery` carries which. The query
is either readable or a zlib-compressed blob — we decode both to readable tokens
and classify the target (edge with section/segment, loft face, or whole part).

This module supports both reading (list, open, decode) and writing (post, reply,
resolve) of comments, enabling async human↔AI discussion anchored to geometry.
"""

from __future__ import annotations

import base64
import re
import zlib
from collections.abc import Iterator

from .context import DocumentContext
from .session import OnshapeSession

# Generated hull vocabulary the decoder maps onto.
_SECTIONS = ("stern", "mid", "bow")
_SEGMENTS = ("bottom", "starboard", "sheer", "port")

_COMPRESSED_RE = re.compile(r'qCompressed\(1\.0,"(.*)",id\)', re.S)


def _iter_tokens(text: str, name: str) -> Iterator[tuple[int, str]]:
    """Yield (position, value) for each length-prefixed token `<name>S<len>$<value>`."""
    for match in re.finditer(rf"{name}S(\d+)\$", text):
        start = match.end()
        yield match.start(), text[start : start + int(match.group(1))]


def _nearest_before(items: list[tuple[int, str]], position: int) -> str | None:
    """Value of the token whose position is the closest at or before `position`."""
    candidates = [value for pos, value in items if pos <= position]
    return candidates[-1] if candidates else None


def _readable(element_query: str) -> str:
    """Return the query's readable token string, inflating a compressed payload."""
    match = _COMPRESSED_RE.search(element_query)
    payload = match.group(1) if match else element_query
    compressed = re.match(r"&[^$]*\$(.+)$", payload, re.S)
    if not compressed:
        return payload
    try:
        return zlib.decompress(base64.b64decode(compressed.group(1))).decode("utf-8", "replace")
    except (zlib.error, ValueError):
        return payload


def decode_target(element_query: str | None) -> dict:
    """Classify a comment's linked object into a discussion-ready descriptor.

    Returns {kind, entityType, section, segment}: `kind` is "edge" (with
    section/segment for a hull sketch edge), "face" (a loft face), "part" (the
    whole body), or "other". Robust to compressed queries and regeneration.
    """
    if not element_query:
        return {"kind": None, "entityType": None, "section": None, "segment": None}
    text = _readable(element_query)
    if "TOPOLOGY" in text:
        return {"kind": "part", "entityType": "BODY", "section": None, "segment": None}
    if "SWEPT_FACE" in text or "$FACE" in text:
        return {"kind": "face", "entityType": "FACE", "section": None, "segment": None}
    sketch = list(_iter_tokens(text, "sketchEntityId"))
    if sketch:
        position, value = sketch[0]
        sections = [(m.start(), s) for s in _SECTIONS for m in re.finditer(s, text)]
        return {
            "kind": "edge",
            "entityType": "EDGE",
            "section": _nearest_before(sections, position),
            "segment": value if value in _SEGMENTS else None,
        }
    entity = next((v for _, v in _iter_tokens(text, "EntityType")), None)
    return {"kind": "other", "entityType": entity, "section": None, "segment": None}


class CommentsClient:
    def __init__(self, session: OnshapeSession, ctx: DocumentContext):
        self.s = session
        self.ctx = ctx

    def list(self, resolved: bool | None = None) -> list[dict]:
        """List document comments; `resolved=False` returns only open ones."""
        path = f"/comments?did={self.ctx.did}"
        if resolved is not None:
            path += f"&resolved={str(resolved).lower()}"
        response = self.s.get(path)
        return (response or {}).get("items", [])

    def open(self) -> list[dict]:
        """Open (unresolved) comments as a discussion-ready model with the linked object."""
        return [
            {
                "id": comment.get("id"),
                "message": comment.get("message"),
                "author": (comment.get("user") or {}).get("name"),
                "createdAt": comment.get("createdAt"),
                "elementId": comment.get("elementId"),
                "target": decode_target(comment.get("elementQuery")),
            }
            for comment in self.list()
            if comment.get("state") == 0
        ]

    def post(
        self,
        message: str,
        element_id: str,
        element_query: str | None = None,
    ) -> dict:
        """Create a new comment, anchored to a geometry entity.

        `element_id` is the Part Studio / Feature Studio eid (required by Onshape API).
        `element_query` is the Onshape query string identifying the specific entity
        (face, edge, etc.) within the element. If None, the comment is anchored to
        the element as a whole. Returns the created comment as a dict.
        """
        body: dict = {
            "message": message,
            "objectId": self.ctx.did,  # Document ID
            "objectType": 6,  # Comment on element
            "elementId": element_id,
            "workspaceId": self.ctx.wid,  # Workspace ID (required when elementQuery is present)
        }
        if element_query:
            body["elementQuery"] = element_query
        return self.s.post(f"/comments?did={self.ctx.did}", body)

    def resolve(self, comment_id: str) -> dict:
        """Mark a comment as resolved. Returns the updated comment."""
        return self.s.post(f"/comments/{comment_id}/resolve", {"resolved": True})

    def reply(self, comment_id: str, message: str) -> dict:
        """Reply to an existing comment. Returns the created reply.
        
        Replies are implemented as child comments with parentId set to the
        parent comment's ID.
        """
        # Get the parent comment to extract its context
        parent = self.s.get(f"/comments/{comment_id}")
        
        body: dict = {
            "message": message,
            "objectId": parent.get("objectId"),
            "objectType": parent.get("objectType"),
            "elementId": parent.get("elementId"),
            "parentId": comment_id,  # Link to parent comment
        }
        if parent.get("elementQuery"):
            body["elementQuery"] = parent.get("elementQuery")
        
        return self.s.post(f"/comments?did={self.ctx.did}", body)

