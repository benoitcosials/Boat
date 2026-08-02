"""Parse an Onshape document URL into the identifiers the API needs."""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlsplit

from .constants import DEFAULT_BASE_URL

# .../documents/{did}/w/{wid}[/e/{eid}] — ids are 24 hex chars.
_URL_RE = re.compile(r"/documents/(?P<did>[0-9a-f]{24})/w/(?P<wid>[0-9a-f]{24})")


@dataclass(frozen=True)
class DocumentContext:
    """Identifies a document + workspace to act on."""

    did: str
    wid: str
    base_url: str = DEFAULT_BASE_URL

    @classmethod
    def from_url(cls, url: str) -> DocumentContext:
        """Build a context from a full Onshape document URL."""
        match = _URL_RE.search(url)
        if not match:
            raise ValueError(
                f"Not an Onshape document/workspace URL: {url!r}\n"
                "Expected .../documents/<did>/w/<wid>/..."
            )
        parts = urlsplit(url)
        base_url = f"{parts.scheme}://{parts.netloc}" if parts.netloc else DEFAULT_BASE_URL
        return cls(did=match["did"], wid=match["wid"], base_url=base_url.rstrip("/"))

    @property
    def dw(self) -> str:
        """The `/d/{did}/w/{wid}` path fragment shared by most endpoints."""
        return f"/d/{self.did}/w/{self.wid}"
