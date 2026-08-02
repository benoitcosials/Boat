FeatureScript 3029;
import(path : "onshape/std/geometry.fs", version : "3029.0");

// Simplified Optimist pram dinghy hull — GENERATED, do not edit by hand.
//
// Section values are fractions of LOA, so every length derives from
// definition.loa (which carries units) and the model is unit-agnostic.
// Coordinate system: X longitudinal (0 = stern, +X = bow), Y transverse, Z up.

const OPTIMIST_LOA_BOUNDS = { (millimeter) : [500, 2300, 6000] } as LengthBoundSpec;

// Shared vocabulary: group faces by region (colour) and number them front->rear.
// A face is referenced as "<letter><n>", e.g. R1 = forward bottom face.
const BOAT_LABEL_ATTR = "boatLabel";
const BOAT_PALETTE = {
        "R" : color(0.85, 0.1, 0.1),   // fond (bottom)
        "J" : color(0.9, 0.8, 0.1),    // pont (deck)
        "V" : color(0.1, 0.6, 0.1),    // babord (port)
        "B" : color(0.1, 0.3, 0.9),    // tribord (starboard)
        "C" : color(0.1, 0.75, 0.8),   // tableau (transom)
        "M" : color(0.8, 0.1, 0.7)     // etrave (bow)
};

function boatRegion(n is Vector)
{
    const ax = abs(n[0]);
    const ay = abs(n[1]);
    const az = abs(n[2]);
    if (az >= ax && az >= ay)
    {
        return n[2] < 0 ? ["fond", "R"] : ["pont", "J"];
    }
    if (ay >= ax)
    {
        return n[1] < 0 ? ["babord", "V"] : ["tribord", "B"];
    }
    return n[0] < 0 ? ["tableau", "C"] : ["etrave", "M"];
}

// Colour every hull face and store a stable "<letter><n>" label as an attribute.
function labelHullFaces(context is Context, faceQuery is Query)
{
    const faces = evaluateQuery(context, faceQuery);
    var info = [];
    for (var i = 0; i < size(faces); i += 1)
    {
        const pl = evFaceTangentPlane(context, { "face" : faces[i], "parameter" : vector(0.5, 0.5) });
        const reg = boatRegion(pl.normal);
        const c = pl.origin / millimeter;
        info = append(info, { "i" : i, "letter" : reg[1], "region" : reg[0], "cx" : c[0], "cy" : c[1], "cz" : c[2] });
    }
    for (var i = 0; i < size(info); i += 1)
    {
        const a = info[i];
        var rank = 1;
        for (var j = 0; j < size(info); j += 1)
        {
            const b = info[j];
            if (j == i || b.letter != a.letter)
            {
                continue;
            }
            // Order front (max X) -> rear; ties broken by Y, Z then index for uniqueness.
            if (b.cx > a.cx
                || (b.cx == a.cx && b.cy > a.cy)
                || (b.cx == a.cx && b.cy == a.cy && b.cz > a.cz)
                || (b.cx == a.cx && b.cy == a.cy && b.cz == a.cz && j < i))
            {
                rank += 1;
            }
        }
        setProperty(context, {
                "entities" : faces[a.i],
                "propertyType" : PropertyType.APPEARANCE,
                "value" : BOAT_PALETTE[a.letter]
        });
        setAttribute(context, {
                "entities" : faces[a.i],
                "name" : BOAT_LABEL_ATTR,
                "attribute" : { "label" : a.letter ~ rank, "region" : a.region }
        });
    }
}

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

        labelHullFaces(context, qCreatedBy(id + "loft", EntityType.FACE));
    });
