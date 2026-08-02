"""Onshape versions = commits: immutable, named snapshots of the workspace.

Onshape has no git; a "commit" is a Version created from the current workspace
state. Each script invocation ends by creating one for traceability, tagged to
show whether the AI or a human authored it (the API acts as the logged-in user,
so authorship is encoded in the version name, e.g. "[AI] ...").
"""

from __future__ import annotations

from typing import Any

from .context import DocumentContext
from .session import OnshapeSession


class VersionsClient:
    def __init__(self, session: OnshapeSession, ctx: DocumentContext):
        self.s = session
        self.ctx = ctx

    def commit(self, name: str, description: str | None = None) -> dict:
        """Create a version (commit) from the current workspace state.

        Returns the created version (contains its `id` and `microversion`).
        """
        body: dict[str, Any] = {
            "documentId": self.ctx.did,
            "workspaceId": self.ctx.wid,
            "name": name,
        }
        if description:
            body["description"] = description
        return self.s.post(f"/documents/d/{self.ctx.did}/versions", body)

    def list(self) -> list[dict]:
        return self.s.get(f"/documents/d/{self.ctx.did}/versions")
