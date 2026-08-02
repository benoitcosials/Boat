"""Unwrap the BTFSValue* envelope returned by the FeatureScript eval endpoint.

The `/featurescript` endpoint wraps every result in a typed tree
(BTFSValueMap / BTFSValueArray / BTFSValueNumber / ...); this flattens it back
into native Python maps, lists and scalars.
"""

from __future__ import annotations

from typing import Any


def unwrap(node: Any) -> Any:
    """Convert a FeatureScript eval result into native Python values."""
    if not isinstance(node, dict):
        return node
    bt_type = node.get("btType", "")
    if "ValueMap" in bt_type:
        return {unwrap(e["key"]): unwrap(e["value"]) for e in node.get("value", [])}
    if "ValueArray" in bt_type:
        return [unwrap(v) for v in node.get("value", [])]
    return node.get("value")
