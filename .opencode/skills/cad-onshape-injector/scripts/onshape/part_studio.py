"""PartStudioClient — instantiate defined features and mark parts for the shared vocabulary.

A Part Studio is where geometry actually renders. Instantiate a custom feature
(defined in a Feature Studio) here to produce a solid, then colour / rename the
resulting part so both the human and the AI refer to it the same way.
"""

from __future__ import annotations

import re
from typing import Any

from .constants import BT_FEATURE, BT_PARAM_QUANTITY, PROP_APPEARANCE, PROP_NAME
from .context import DocumentContext
from .session import OnshapeSession

# Dialog expressions ("2300 millimeter") -> code expressions ("2300 * millimeter").
_UNIT_WORDS = "millimeter|centimeter|meter|kilometer|inch|foot|yard|mile|degree|radian"
_DIALOG_UNIT_RE = re.compile(rf"([0-9.eE+\-]) +({_UNIT_WORDS})\b")


def _to_code_expr(expr: str) -> str:
    return _DIALOG_UNIT_RE.sub(r"\1 * \2", expr)


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

    def feature_errors(self, ps_eid: str) -> list[dict]:
        """Features whose regen status is not OK, as {featureId, name, status}."""
        data = self.s.get(f"{self._base()}/e/{ps_eid}/features")
        names = {f.get("featureId"): f.get("name") for f in data.get("features", [])}
        return [
            {"featureId": fid, "name": names.get(fid), "status": state.get("featureStatus")}
            for fid, state in data.get("featureStates", {}).items()
            if state.get("featureStatus") not in (None, "OK")
        ]

    def feature_error_enum(self, ps_eid: str, feature_id: str) -> str | None:
        """Coarse error category for a feature (e.g. "REGEN_ERROR"), via FeatureScript eval."""
        script = (
            "function(context is Context, queries is map)"
            f' {{ return getFeatureError(context, makeId("{feature_id}")); }}'
        )
        resp = self.s.post(
            f"{self._base()}/e/{ps_eid}/featurescript", {"script": script, "queries": {}}
        )
        return (resp.get("result") or {}).get("value")

    def evaluate(self, ps_eid: str, script: str, queries: dict | None = None) -> dict:
        """Run a FeatureScript snippet in this Part Studio's context.

        `script` must be a `function(context is Context, queries is map){...}`
        expression. Returns {result, notices, console}; `notices` carries the
        rich message + line/column for any FeatureScript error the script hits.
        """
        resp = self.s.post(
            f"{self._base()}/e/{ps_eid}/featurescript",
            {"script": script, "queries": queries or {}},
        )
        return {
            "result": resp.get("result"),
            "notices": resp.get("notices", []),
            "console": resp.get("console", ""),
        }

    def feature_notice(
        self,
        ps_eid: str,
        namespace: str,
        feature_type: str,
        parameters: dict[str, str] | None = None,
        fs_eid: str | None = None,
    ) -> dict | None:
        """Rich FeatureScript error for a feature, recovered via eval.

        Re-runs `namespace::feature_type(...)` in an isolated eval (non-persistent)
        so the FeatureScript exception surfaces as a notice with the exact message
        and source location. `featureStates` only reports a coarse ERROR status;
        this recovers the message and the `line:col` inside the Feature Studio.
        Returns {message, location} or None if the feature evaluates cleanly.
        """
        param_src = ", ".join(
            f'"{pid}" : {_to_code_expr(expr)}' for pid, expr in (parameters or {}).items()
        )
        script = (
            "function(context is Context, queries is map)\n"
            "{\n"
            f'    {namespace}::{feature_type}(context, makeId("__probe__"), {{ {param_src} }});\n'
            "    return 1;\n"
            "}"
        )
        result = self.evaluate(ps_eid, script)
        return self._pick_notice(result["notices"], fs_eid)

    @staticmethod
    def _pick_notice(notices: list[dict], fs_eid: str | None) -> dict | None:
        """Prefer the notice located in the Feature Studio source; else first error."""
        fallback = None
        for notice in notices:
            message = notice.get("message")
            if not message:
                continue
            for frame in notice.get("stackTrace", []):
                if fs_eid and frame.get("document") == fs_eid:
                    location = f"line {frame.get('line')}, col {frame.get('column')}"
                    return {"message": message, "location": location}
            if fallback is None and notice.get("level") == "ERROR":
                fallback = {"message": message, "location": None}
        return fallback

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
