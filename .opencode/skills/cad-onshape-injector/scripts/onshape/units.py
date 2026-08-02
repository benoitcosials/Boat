"""Read the document's working length unit — the Onshape "Workspace unit".

Onshape length-unit names are identical to the FeatureScript length constants
(millimeter, meter, centimeter, inch, foot, yard), so the value returned here
can be emitted directly into FeatureScript as `* <unit>`.
"""

from __future__ import annotations

from .context import DocumentContext
from .session import OnshapeSession

# Onshape length units that map 1:1 to FeatureScript length constants.
VALID_LENGTH_UNITS = {"meter", "centimeter", "millimeter", "inch", "foot", "yard"}

DEFAULT_LENGTH_UNIT = "millimeter"  # Onshape's default for new documents.


def get_length_unit(
    session: OnshapeSession, ctx: DocumentContext, element_id: str | None = None
) -> str:
    """Return the workspace length unit (e.g. "millimeter").

    If `element_id` is given, use that element's unit; otherwise use the first
    element that declares one (all elements share the document default).
    """
    elements = session.get(f"/documents{ctx.dw}/elements")
    with_units = [e for e in elements if e.get("lengthUnits")]
    if element_id:
        for element in with_units:
            if element.get("id") == element_id:
                return element["lengthUnits"]
    if with_units:
        return with_units[0]["lengthUnits"]
    return DEFAULT_LENGTH_UNIT
