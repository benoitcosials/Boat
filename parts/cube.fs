FeatureScript 2384;
import(path : "onshape/std/geometry.fs", version : "2384.0");

annotation { "Feature Type Name" : "Cube 50x50x50" }
export const cube50 = defineFeature(function(context is Context, id is Id, definition is map)
    precondition
    {
        // Fixed 50mm cube — no parameters needed
    }
    {
        // Sketch on Top plane: 50×50mm centered square
        const sketch = newSketch(context, id + "sketch", {
                "sketchPlane" : qCreatedBy(makeId("Top"), EntityType.FACE)
        });

        skRectangle(sketch, "rect", {
                "firstCorner" : vector(-25, -25) * millimeter,
                "secondCorner" : vector(25, 25) * millimeter
        });

        skSolve(sketch);

        // Extrude 50mm upward
        opExtrude(context, id + "extrude", {
                "entities" : qSketchRegion(id + "sketch"),
                "direction" : evOwnerSketchPlane(context, {
                        "entity" : qSketchRegion(id + "sketch")
                }).normal,
                "endBound" : BoundingType.BLIND,
                "endDepth" : 50 * millimeter
        });
    });
