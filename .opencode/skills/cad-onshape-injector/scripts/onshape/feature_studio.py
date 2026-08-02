"""FeatureStudioClient — one `parts/<name>.fs` file maps to one Feature Studio.

A Feature Studio only *defines* features; it renders nothing on its own.
Use PartStudioClient.instantiate() to turn a defined feature into geometry.
"""

from __future__ import annotations

from typing import Any

from .context import DocumentContext
from .session import OnshapeSession


class FeatureStudioClient:
    def __init__(self, session: OnshapeSession, ctx: DocumentContext):
        self.s = session
        self.ctx = ctx

    def _base(self) -> str:
        return f"/featurestudios{self.ctx.dw}"

    # ── discovery ────────────────────────────────────────────────────────
    def list(self) -> list[dict]:
        elements = self.s.get(f"/documents{self.ctx.dw}/elements")
        return [e for e in elements if e.get("elementType") == "FEATURESTUDIO"]

    def find(self, name: str) -> dict | None:
        return next((e for e in self.list() if e.get("name") == name), None)

    # ── create / ensure ──────────────────────────────────────────────────
    def create(self, name: str) -> str:
        created = self.s.post(self._base(), {"name": name})
        return created["id"]

    def ensure(self, name: str) -> str:
        """Return the eid of the Feature Studio named `name`, creating it if absent."""
        existing = self.find(name)
        return existing["id"] if existing else self.create(name)

    # ── contents ─────────────────────────────────────────────────────────
    def get_contents(self, eid: str) -> str:
        return self.s.get(f"{self._base()}/e/{eid}")["contents"]

    def set_contents(self, eid: str, fs_text: str) -> Any:
        return self.s.post(f"{self._base()}/e/{eid}", {"contents": fs_text})

    def sync(self, name: str, fs_text: str) -> str:
        """Ensure a Feature Studio named `name` exists and holds `fs_text`.

        Idempotent: this is the single call that injects a `parts/*.fs` file.
        Returns the Feature Studio eid.
        """
        eid = self.ensure(name)
        self.set_contents(eid, fs_text)
        return eid

    # ── feature spec (needed to instantiate into a Part Studio) ───────────
    def featurespec(self, eid: str) -> dict:
        """Return the first feature's {featureType, namespace, parameters}.

        `namespace` has the form `e<eid>::m<microversion>` and auto-resolves to
        the latest microversion for same-document references.
        """
        response = self.s.get(f"{self._base()}/e/{eid}/featurespecs")
        specs = response.get("featureSpecs") or []
        if not specs:
            raise ValueError(f"Feature Studio {eid} defines no features.")
        spec = specs[0]
        return {
            "featureType": spec.get("featureType"),
            "featureTypeName": spec.get("featureTypeName"),
            "namespace": spec.get("namespace"),
            "parameters": [p.get("parameterId") for p in spec.get("parameters", [])],
        }

    def delete(self, eid: str) -> Any:
        return self.s.delete(f"/elements{self.ctx.dw}/e/{eid}")
