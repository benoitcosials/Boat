FeatureScript 3029;
import(path : "onshape/std/geometry.fs", version : "3029.0");

// Simplified Optimist pram dinghy hull — GENERATED, do not edit by hand.
//
// Section values are fractions of LOA, so every length derives from
// definition.loa (which carries units) and the model is unit-agnostic.
// Coordinate system: X longitudinal (0 = stern, +X = bow), Y transverse, Z up.

const OPTIMIST_LOA_BOUNDS = { (millimeter) : [500, 2300, 6000] } as LengthBoundSpec;

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
            ["stern", 0, 0.108696, 0.23913, 0.008696, 0.152174],
            ["mid", 0.5, 0.119565, 0.245652, 0, 0.152174],
            ["bow", 1, 0.065217, 0.182609, 0.052174, 0.173913]
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
