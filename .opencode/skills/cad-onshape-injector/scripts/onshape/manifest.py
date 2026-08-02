"""Load and save the project master config (manifest.json)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DEFAULT_PATH = "manifest.json"


def load_manifest(path: str = DEFAULT_PATH) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def save_manifest(data: dict[str, Any], path: str = DEFAULT_PATH) -> None:
    Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
