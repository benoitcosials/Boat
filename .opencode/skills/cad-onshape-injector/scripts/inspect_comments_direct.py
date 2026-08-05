#!/usr/bin/env python3
"""Inspect comments using saved cookies (no browser launch).

This script reads cookies from .browser-data/ and makes direct API calls
to inspect comment structure.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from urllib.parse import unquote
from urllib.request import Request, urlopen
from urllib.error import HTTPError

sys.path.insert(0, str(Path(__file__).resolve().parent))

from onshape.context import DocumentContext  # noqa: E402
from onshape.manifest import load_manifest  # noqa: E402


def load_cookies() -> dict:
    """Load cookies from .browser-data/."""
    # Playwright stores cookies in a SQLite database
    # For simplicity, we'll use a different approach: read from a known location
    # or use the session if available
    
    # Try to read cookies from the persistent session
    session_file = Path(".browser-session.json")
    if session_file.exists():
        data = json.loads(session_file.read_text())
        return {
            "cookies": data.get("cookies", []),
            "xsrf_token": data.get("xsrf_token"),
        }
    
    # Fallback: try to extract from browser data
    # This is more complex and requires reading the SQLite database
    raise RuntimeError("No session file found. Start a session first with start_session.py")


def main() -> None:
    manifest = load_manifest()
    onshape = manifest["onshape"]
    ctx = DocumentContext.from_url(onshape["document_url"])
    
    print("=" * 70)
    print("INSPECT: Comment Structure (via direct API)")
    print("=" * 70)
    
    # Load cookies
    try:
        cookie_data = load_cookies()
    except RuntimeError as e:
        print(f"❌ {e}")
        return
    
    cookies = cookie_data["cookies"]
    xsrf_token = cookie_data["xsrf_token"]
    
    if not xsrf_token:
        print("❌ No XSRF token found in session")
        return
    
    # Build cookie header
    cookie_header = "; ".join(f"{c['name']}={c['value']}" for c in cookies)
    
    # Fetch comments
    url = f"{ctx.base_url}/api/v10/comments?did={ctx.did}"
    headers = {
        "Cookie": cookie_header,
        "X-XSRF-TOKEN": unquote(xsrf_token),
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    
    request = Request(url, headers=headers, method="GET")
    
    try:
        with urlopen(request) as response:
            data = json.loads(response.read().decode())
    except HTTPError as e:
        print(f"❌ API error {e.code}: {e.read().decode()}")
        return
    
    items = data.get("items", [])
    
    print(f"\nFound {len(items)} comment(s)\n")
    
    for i, comment in enumerate(items, 1):
        print(f"{'=' * 70}")
        print(f"COMMENT {i}:")
        print(f"{'=' * 70}")
        print(json.dumps(comment, indent=2, default=str))
        
        print(f"\nKEY FIELDS:")
        print(f"  id: {comment.get('id')}")
        print(f"  message: {comment.get('message')}")
        print(f"  state: {comment.get('state')} (0=open, 1=resolved)")
        print(f"  objectType: {comment.get('objectType')}")
        print(f"  objectId: {comment.get('objectId')}")
        print(f"  elementId: {comment.get('elementId')}")
        print(f"  elementQuery: {comment.get('elementQuery', '')[:100]}...")
        print(f"  workspaceId: {comment.get('workspaceId')}")
        
        # Check for tags/mentions
        if "tags" in comment:
            print(f"  tags: {comment.get('tags')}")
        
        # Check for assignments
        if "assignee" in comment and comment.get("assignee"):
            print(f"  assignee: {comment.get('assignee')}")
        
        print()


if __name__ == "__main__":
    main()
