# FreeCAD MCP Tools Reference

This document describes the MCP tools available when the `neka-nat/freecad-mcp` server
is active. The server communicates with FreeCAD via XML-RPC on port 9875.

## Setup (macOS)

1. Install FreeCAD 1.1+: `brew install --cask freecad`
2. Install the MCP addon: FreeCAD → Tools → Addon Manager → search "FreeCADMCP" → Install
3. Activate the workbench: Workbench selector → "MCP"
4. The server starts automatically on port 9875

## Available Tools

### Document Management
| Tool | Parameters | Description |
|------|-----------|-------------|
| `create_document` | `name: str` | Create a new FreeCAD document |
| `get_document` | — | Get active document info |
| `save_document` | `path: str` | Save document to disk |
| `close_document` | `name: str` | Close a document |

### Object Creation
| Tool | Parameters | Description |
|------|-----------|-------------|
| `create_object` | `type: str, name: str, params: dict` | Create a Part primitive (Box, Cylinder, Sphere, Cone, Torus) or Part Design feature |
| `execute_code` | `code: str` | Execute arbitrary FreeCAD Python code |
| `create_sketch` | `plane: str, name: str` | Create a new sketch on a plane (XY, XZ, YZ, or face name) |
| `edit_object` | `name: str, params: dict` | Modify an existing object's properties |
| `delete_object` | `name: str` | Delete an object |

### Part Design Operations (via execute_code)
| Operation | Code Pattern |
|-----------|-------------|
| `pad` | `body.newObject("PartDesign::Pad", "PadName").Profile = sketch` |
| `pocket` | `body.newObject("PartDesign::Pocket", "PocketName").Profile = sketch` |
| `revolution` | `body.newObject("PartDesign::Revolution", "RevName").Profile = sketch` |
| `fillet` | `body.newObject("PartDesign::Fillet", "FilletName").Base = edge_list` |
| `chamfer` | `body.newObject("PartDesign::Chamfer", "ChamferName").Base = edge_list` |
| `mirrored` | `body.newObject("PartDesign::Mirrored", "MirrorName").Originals = [features]` |
| `linear_pattern` | `body.newObject("PartDesign::LinearPattern", "PatName").Originals = [features]` |
| `polar_pattern` | `body.newObject("PartDesign::PolarPattern", "PatName").Originals = [features]` |

### Boolean Operations (Part Workbench — use sparingly)
| Operation | Code Pattern |
|-----------|-------------|
| `union` | `Part.Fuse(obj1, obj2)` |
| `cut` | `Part.Cut(obj1, obj2)` |
| `intersection` | `Part.Common(obj1, obj2)` |

### View & Inspection
| Tool | Parameters | Description |
|------|-----------|-------------|
| `get_view` | — | Take a screenshot of the current 3D view |
| `get_objects` | — | List all objects in the active document |
| `get_object` | `name: str` | Get details of a specific object |
| `get_parts_list` | — | List all parts/bodies |

### Export
| Tool | Parameters | Description |
|------|-----------|-------------|
| `export_stl` | `path: str, objects: list[str]` | Export selected objects to STL |
| `export_step` | `path: str, objects: list[str]` | Export selected objects to STEP |

### Analysis
| Tool | Parameters | Description |
|------|-----------|-------------|
| `run_fem_analysis` | `params: dict` | Run FEA on the active body |
| `insert_part_from_library` | `part_name: str` | Insert a standard part (fasteners, bearings) |

### Macro & Script
| Tool | Parameters | Description |
|------|-----------|-------------|
| `run_macro` | `path: str` | Execute a .FCMacro file |
| `get_script` | `object_name: str` | Get the Python script that recreates an object |

## MCP Communication Pattern

The MCP server uses XML-RPC. Calls are synchronous — wait for the response before
calling the next tool. Typical call pattern:

```
1. Call tool with parameters
2. Wait for response (JSON or status)
3. If success → proceed to next step
4. If error → read error message, fix the issue, retry the same step
```

## FreeCAD Document Structure

```
Document
├── Body (Part Design)
│   ├── Origin (planes: XY, XZ, YZ, axes)
│   ├── Sketch (2D profile)
│   ├── Pad (extrusion of sketch)
│   ├── Sketch001 (profile for pocket)
│   ├── Pocket (subtractive extrusion)
│   ├── Fillet (edge treatment)
│   └── Chamfer (edge bevel)
├── Part (if using Part workbench)
│   └── ...
└── Assembly (if using Assembly workbench)
    ├── Part001
    └── Part002
```

## Common execute_code Snippets

### Set units to mm
```python
import FreeCAD as App
App.ParamGet("User parameter:BaseApp/Preferences/Units").SetInt("UserSchema", 0)
```

### Create a fully constrained centered rectangle sketch
```python
doc = App.ActiveDocument
body = doc.getObject("Body")
sketch = body.newObject("Sketcher::SketchObject", "my_sketch")
sketch.Support = (doc.getObject("XY_Plane"), [""])
sketch.MapMode = "FlatFace"

import Part, Sketcher
w, h = 120.0, 80.0
sketch.addGeometry(Part.LineSegment(App.Vector(-w/2, -h/2, 0), App.Vector(w/2, -h/2, 0)), False)
sketch.addGeometry(Part.LineSegment(App.Vector(w/2, -h/2, 0), App.Vector(w/2, h/2, 0)), False)
sketch.addGeometry(Part.LineSegment(App.Vector(w/2, h/2, 0), App.Vector(-w/2, h/2, 0)), False)
sketch.addGeometry(Part.LineSegment(App.Vector(-w/2, h/2, 0), App.Vector(-w/2, -h/2, 0)), False)
sketch.addConstraint(Sketcher.Constraint("Horizontal", 0))
sketch.addConstraint(Sketcher.Constraint("Horizontal", 2))
sketch.addConstraint(Sketcher.Constraint("Vertical", 1))
sketch.addConstraint(Sketcher.Constraint("Vertical", 3))
sketch.addConstraint(Sketcher.Constraint("DistanceX", 0, 1, 0, 2, w))
sketch.addConstraint(Sketcher.Constraint("DistanceY", 1, 2, 1, 3, h))
sketch.addConstraint(Sketcher.Constraint("Symmetric", 0, 2, 1, 3, -2))
App.ActiveDocument.recompute()
```

### Pad a sketch
```python
doc = App.ActiveDocument
body = doc.getObject("Body")
pad = body.newObject("PartDesign::Pad", "BasePad")
pad.Profile = doc.getObject("my_sketch")
pad.Length = 60.0
App.ActiveDocument.recompute()
```

### Pocket a sketch (through all)
```python
doc = App.ActiveDocument
body = doc.getObject("Body")
pocket = body.newObject("PartDesign::Pocket", "MyPocket")
pocket.Profile = doc.getObject("hole_sketch")
pocket.Type = 1  # ThroughAll
App.ActiveDocument.recompute()
```
