"""PartStudioClient — instantiate defined features and mark parts for the shared vocabulary.

A Part Studio is where geometry actually renders. Instantiate a custom feature
(defined in a Feature Studio) here to produce a solid, then colour / rename the
resulting part so both the human and the AI refer to it the same way.
"""

from __future__ import annotations

from typing import Any

from .constants import BT_FEATURE, BT_PARAM_QUANTITY, PROP_APPEARANCE, PROP_NAME
from .context import DocumentContext
from .session import OnshapeSession


class PartStudioClient:
    def __init__(self, session: OnshapeSession, ctx: DocumentContext):
        self.s = session
        self.ctx = ctx

    def _base(self) -> str:
        return f"/partstudios{self.ctx.dw}"

    # ── discovery ────────────────────────────────────────────────────────
    def list(self) -> list[dict]:
        elements = self.s.get(f"/documents{self.ctx.dw}/elements")
        return [e for e in elements if e.get("elementType") == "PARTSTUDIO"]

    def find(self, name: str) -> dict | None:
        return next((e for e in self.list() if e.get("name") == name), None)

    def create(self, name: str) -> str:
        created = self.s.post(self._base(), {"name": name})
        return created["id"]

    def ensure(self, name: str) -> str:
        existing = self.find(name)
        return existing["id"] if existing else self.create(name)

    # ── features ─────────────────────────────────────────────────────────
    def instantiate(
        self,
        ps_eid: str,
        feature_type: str,
        namespace: str,
        name: str,
        parameters: dict[str, str] | None = None,
    ) -> dict:
        """Add a custom feature (from a Feature Studio) to this Part Studio.

        `parameters` maps parameterId -> a dialog-syntax expression (NO `*`,
        as typed in the feature dialog), e.g. {"loa": "2400 millimeter"} or
        {"size": "2.4 meter"}. Only quantity parameters are handled here.
        Returns the API response (contains featureState.featureStatus).
        """
        params = [
            {"btType": BT_PARAM_QUANTITY, "parameterId": pid, "expression": expr}
            for pid, expr in (parameters or {}).items()
        ]
        feature = {
            "btType": BT_FEATURE,
            "featureType": feature_type,
            "namespace": namespace,
            "name": name,
            "parameters": params,
        }
        return self.s.post(f"{self._base()}/e/{ps_eid}/features", {"feature": feature})

    def list_features(self, ps_eid: str) -> list[dict]:
        return self.s.get(f"{self._base()}/e/{ps_eid}/features").get("features", [])

    # ── parts + shared vocabulary (colour / name) ────────────────────────
    def list_parts(self, ps_eid: str) -> list[dict]:
        return self.s.get(f"/parts{self.ctx.dw}/e/{ps_eid}")

    def _set_property(self, ps_eid: str, part_id: str, property_id: str, value: Any) -> Any:
        body = {
            "jsonType": "metadata-part",
            "partId": part_id,
            "properties": [{"propertyId": property_id, "value": value}],
        }
        return self.s.post(f"/metadata{self.ctx.dw}/e/{ps_eid}/p/{part_id}", body)

    def set_appearance(
        self, ps_eid: str, part_id: str, rgb: tuple[int, int, int], opacity: int = 255
    ) -> Any:
        """Colour a part — used to mark the 'active part in the conversation'."""
        red, green, blue = rgb
        value = {"color": {"red": red, "green": green, "blue": blue}, "opacity": opacity}
        return self._set_property(ps_eid, part_id, PROP_APPEARANCE, value)

    def rename_part(self, ps_eid: str, part_id: str, name: str) -> Any:
        """Rename a part — visible to the human in the Parts panel."""
        return self._set_property(ps_eid, part_id, PROP_NAME, name)

    def delete(self, eid: str) -> Any:
        return self.s.delete(f"/elements{self.ctx.dw}/e/{eid}")
