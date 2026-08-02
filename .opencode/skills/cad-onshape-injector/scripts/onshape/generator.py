"""Unit-aware FeatureScript generation.

Two length syntaxes exist and must not be confused:
  * FeatureScript SOURCE  -> `2300 * millimeter`  (the star is required)
  * feature dialog fields -> `2300 millimeter`     (no star)

The generated hull expresses every section value as a *fraction of LOA*, so all
lengths derive from `definition.loa` (which carries units). The model is then
unit-agnostic: the only place a unit token appears is the LOA bounds line.
"""

from __future__ import annotations


def _fmt(value: float) -> str:
    """Format a number without a trailing ``.0`` for whole values."""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return repr(value)


def code_length(value: float, unit: str) -> str:
    """A length as written in FeatureScript source, e.g. ``2300 * millimeter``."""
    return f"{_fmt(value)} * {unit}"


def dialog_length(value: float, unit: str) -> str:
    """A length as typed in a feature dialog field, e.g. ``2300 millimeter``."""
    return f"{_fmt(value)} {unit}"


# Optimist pram hull cross-sections as fractions of LOA:
# (name, xFrac, bottomHalfFrac, topHalfFrac, zBottomFrac, zTopFrac)
OPTIMIST_SECTIONS = [
    ("stern", 0.0, 0.108696, 0.239130, 0.008696, 0.152174),
    ("mid", 0.5, 0.119565, 0.245652, 0.0, 0.152174),
    ("bow", 1.0, 0.065217, 0.182609, 0.052174, 0.173913),
]

_HULL_TEMPLATE = """FeatureScript 3029;
import(path : "onshape/std/geometry.fs", version : "3029.0");

// Simplified Optimist pram dinghy hull — GENERATED, do not edit by hand.
//
// Section values are fractions of LOA, so every length derives from
// definition.loa (which carries units) and the model is unit-agnostic.
// Coordinate system: X longitudinal (0 = stern, +X = bow), Y transverse, Z up.

const OPTIMIST_LOA_BOUNDS = { (__UNIT__) : [__LO__, __DEFAULT__, __HI__] } as LengthBoundSpec;

annotation { "Feature Type Name" : "Optimist Hull" }
export const optimistHull = defineFeature(function(context is Context, id is Id, definition is map)
    precondition
    {
        annotation { "Name" : "Length overall (LOA)" }
        isLength(definition.loa, OPTIMIST_LOA_BOUNDS);
    }
    {
        const loa = definition.loa;

        // [name, xFrac, bottomHalfFrac, topHalfFrac, zBottomFrac, zTopFrac]
        const sections = [
__ROWS__
        ];

        var regions = [];
        for (var s in sections)
        {
            const name = s[0];
            const x  = s[1] * loa;
            const bh = s[2] * loa;  // bottom half-width
            const th = s[3] * loa;  // top half-width (flare)
            const zb = s[4] * loa;  // bottom height (rocker)
            const zt = s[5] * loa;  // sheer height

            const sketchId = id + name;
            var sketch = newSketchOnPlane(context, sketchId, {
                    "sketchPlane" : plane(x * vector(1, 0, 0), vector(1, 0, 0), vector(0, 1, 0))
            });

            // bh, zb, ... already carry length units, so these are 2D length vectors.
            skLineSegment(sketch, "bottom", { "start" : vector(-bh, zb), "end" : vector(bh, zb) });
            skLineSegment(sketch, "starboard", { "start" : vector(bh, zb), "end" : vector(th, zt) });
            skLineSegment(sketch, "sheer", { "start" : vector(th, zt), "end" : vector(-th, zt) });
            skLineSegment(sketch, "port", { "start" : vector(-th, zt), "end" : vector(-bh, zb) });
            skSolve(sketch);

            regions = append(regions, qSketchRegion(sketchId));
        }

        opLoft(context, id + "loft", { "profileSubqueries" : regions });
    });
"""


def generate_optimist_hull(
    unit: str = "millimeter", loa_bounds: tuple[float, float, float] = (500, 2300, 6000)
) -> str:
    """Generate the Optimist hull FeatureScript for the given workspace unit.

    `loa_bounds` is (min, default, max) expressed in `unit`.
    """
    lo, default, hi = loa_bounds
    rows = ",\n".join(
        f'            ["{name}", {_fmt(x)}, {_fmt(bh)}, {_fmt(th)}, {_fmt(zb)}, {_fmt(zt)}]'
        for (name, x, bh, th, zb, zt) in OPTIMIST_SECTIONS
    )
    return (
        _HULL_TEMPLATE.replace("__UNIT__", unit)
        .replace("__LO__", _fmt(lo))
        .replace("__DEFAULT__", _fmt(default))
        .replace("__HI__", _fmt(hi))
        .replace("__ROWS__", rows)
    )
