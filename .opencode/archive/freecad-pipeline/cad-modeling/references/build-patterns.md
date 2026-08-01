# FreeCAD Build Patterns

Standard sequences of FreeCAD Part Design operations for common mechanical features.
Follow these patterns when generating the build plan. The build plan always lists
operations in this order:

1. Base body (sketch + pad)
2. Primary subtractive features (pockets, holes — sketched)
3. Additive features (bosses, ribs — sketched + pad)
4. Edge treatments (fillets, chamfers)
5. Patterns (mirror, linear, polar)
6. Export (STEP, STL)

## Pattern 1: Housing / Enclosure

```
1. Sketch base profile on XY plane (rectangle + mounting ears)
   → fully constrain: horizontal, vertical, symmetry, dimensions
2. Pad to overall height (or to a mid-plane for split enclosures)
3. Sketch internal cavity on top face (offset from outer walls by wall_thickness)
4. Pocket to depth = height - min_wall_thickness (leaves bottom wall)
5. Sketch bores on appropriate faces (input/output shaft faces)
6. Pocket bores through_all (or to depth if blind)
7. Sketch mounting holes on base/bottom face
8. Pocket mounting holes through_all
9. Fillet internal corners (stress relief)
10. Chamfer external edges (print bed separation, lead-in)
```

## Pattern 2: Shaft

```
1. Sketch circle on XY plane (shaft Ø)
2. Pad to shaft length
3. If stepped shaft: sketch each step on the end face, pad to step length
4. If keyway: sketch keyway profile on shaft face, pocket to length
5. If spline: sketch spline profile (or use Part Design → Involute Gear if FCGear available)
6. Chamfer ends (1×45° for lead-in)
```

## Pattern 3: Gear (Spur — using FCGear workbench or manual involute)

```
1. If FCGear available (recommended):
   a. Create InvoluteGear object with teeth, module, pressure_angle
   b. Pad to face_width
   c. Sketch bore on gear face, pocket through_all
   d. If hub: sketch hub circle on gear face, pad to hub_height
   e. Fillet tooth roots (r=0.38×module for 20°)

2. If manual (no FCGear):
   a. Create cylinder (tip diameter = module × (teeth + 2))
   b. Use Part Design → SubtractiveHelix or pattern-based tooth cutting
   c. Prefer FCGear — manual gear generation is error-prone
```

## Pattern 4: Bracket / Mount

```
1. Sketch main profile on XY plane (L-shape, T-shape, or flat bar)
2. Pad to thickness
3. Sketch mounting holes on appropriate faces
4. Pocket holes through_all
5. If reinforcing ribs: sketch on perpendicular plane, pad to rib width
6. Fillet internal corners where bracket meets wall
7. Chamfer mounting hole edges
```

## Pattern 5: Flange / Lid

```
1. Sketch flange profile (outer rectangle/circle + bolt hole circle)
2. Pad to flange thickness
3. Sketch bolt holes on flange face (use polar pattern for circular flange)
4. Pocket bolt holes through_all
5. If centering lip: sketch lip offset, pad to lip height
6. Chamfer bolt holes (0.5 mm)
```

## Sketch Constraints Checklist

Every sketch MUST have:
- [ ] All degrees of freedom eliminated (solver shows 0 DOF)
- [ ] Symmetry constraints where applicable (equal + symmetric)
- [ ] Named reference dimensions for critical features
- [ ] Construction geometry for alignment (centerlines, reference circles)
- [ ] No overlapping or self-intersecting geometry

## FreeCAD Python Code Template

For operations that need `execute_code` (complex sketches, patterns):

```python
import FreeCAD as App
import Part
import Sketcher

doc = App.ActiveDocument
body = doc.getObject("Body")

# Example: create a sketch on the XY plane with a centered rectangle
sketch = body.newObject("Sketcher::SketchObject", "base_sketch")
sketch.Support = (doc.getObject("XY_Plane"), [""])
sketch.MapMode = "FlatFace"

# Add geometry
sketch.addGeometry(Part.LineSegment(
    App.Vector(-60, -40, 0), App.Vector(60, -40, 0)), False)
sketch.addGeometry(Part.LineSegment(
    App.Vector(60, -40, 0), App.Vector(60, 40, 0)), False)
sketch.addGeometry(Part.LineSegment(
    App.Vector(60, 40, 0), App.Vector(-60, 40, 0)), False)
sketch.addGeometry(Part.LineSegment(
    App.Vector(-60, 40, 0), App.Vector(-60, -40, 0)), False)

# Add constraints
sketch.addConstraint(Sketcher.Constraint("Horizontal", 0))
sketch.addConstraint(Sketcher.Constraint("Horizontal", 2))
sketch.addConstraint(Sketcher.Constraint("Vertical", 1))
sketch.addConstraint(Sketcher.Constraint("Vertical", 3))
sketch.addConstraint(Sketcher.Constraint("DistanceX", 0, 1, 0, 2, 120.0))
sketch.addConstraint(Sketcher.Constraint("DistanceY", 1, 2, 1, 3, 80.0))
sketch.addConstraint(Sketcher.Constraint("Symmetric", 0, 2, 1, 3, -2))

App.ActiveDocument.recompute()
```

## Error Recovery Patterns

| Error | Likely Cause | Fix |
|-------|-------------|-----|
| "Failed to recompute" | Broken sketch constraint or self-intersection | Delete the last feature, redo the sketch with simpler constraints |
| "Resulting shape is empty" | Pocket/bore direction wrong or sketch on wrong face | Check "Reversed" property, verify sketch plane |
| "Boolean operation failed" | Parts don't intersect or coplanar faces | Add 0.1 mm overlap, avoid exact coplanar faces |
| "BRep_API: command not done" | Fillet radius too large for geometry | Reduce fillet radius, or split into smaller fillets |
| "Access violation" | Topological naming issue (FreeCAD 1.0+ mitigates this) | Re-select the face/edge reference |
