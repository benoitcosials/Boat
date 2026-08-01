#!/usr/bin/env python3
"""Validate an STL mesh for 3D printability (Gate 4: Export → Slicer).

Usage:
    python validate_printability.py part.stl [--nozzle 0.4] [--layer 0.2]

Exit code 0 = printable, 1 = issues found. Prints gate report JSON to stdout.

Checks performed:
1. Overhang angles — faces beyond the critical angle may need supports
2. Bed contact area — sufficient for adhesion
3. Minimum wall thickness vs nozzle diameter
4. Bounding box fits common print volumes (Prusa MK4: 250×210×220, Bambu X1C: 256×256×256)
5. Orientation analysis — recommends optimal print orientation

Requires: trimesh (pip install trimesh)
"""

import json
import sys
from pathlib import Path


def _fail(gate: str, message: str) -> None:
    report = {
        "gate": gate,
        "passed": False,
        "errors": [{"field": "_", "message": message, "severity": "error"}],
        "warnings": [],
    }
    print(json.dumps(report, indent=2))
    sys.exit(1)


def _error(field: str, message: str) -> dict:
    return {"field": field, "message": message, "severity": "error"}


def _warning(field: str, message: str) -> dict:
    return {"field": field, "message": message, "severity": "warning"}


# Common printer build volumes (mm) — [X, Y, Z]
PRINTER_VOLUMES: dict[str, list[float]] = {
    "Prusa MK4": [250, 210, 220],
    "Prusa XL": [360, 360, 360],
    "Bambu X1C": [256, 256, 256],
    "Bambu A1": [256, 256, 256],
    "Ender 3": [220, 220, 250],
    "Voron 2.4": [350, 350, 350],
    "Creality K1": [220, 220, 250],
}

# Critical overhang angle — faces steeper than this may need supports
CRITICAL_OVERHANG_DEG = 45.0  # typical for 0.4 mm nozzle, 0.2 mm layer height


def _validate_printability(stl_path: str, nozzle_dia: float = 0.4, layer_height: float = 0.2) -> dict:
    import numpy as np
    import trimesh

    errors: list[dict] = []
    warnings: list[dict] = []

    try:
        mesh = trimesh.load(stl_path, file_type="stl")
    except Exception as e:
        errors.append(_error("file", f"Failed to load STL: {e}"))
        return {
            "gate": "printability",
            "passed": False,
            "errors": errors,
            "warnings": warnings,
        }

    if mesh is None or len(mesh.faces) == 0:
        errors.append(_error("mesh", "Empty mesh"))
        return {
            "gate": "printability",
            "passed": False,
            "errors": errors,
            "warnings": warnings,
        }

    bbox = mesh.bounds
    mesh_dims = bbox[1] - bbox[0]

    # --- printer volume check ---
    fits_any = False
    volume_warnings = []
    for printer_name, vol in PRINTER_VOLUMES.items():
        if all(mesh_dims[i] <= vol[i] for i in range(3)):
            fits_any = True
            break
        else:
            oversize = [i for i in range(3) if mesh_dims[i] > vol[i]]
            axes = ["X", "Y", "Z"]
            details = ", ".join(f"{axes[i]}: {mesh_dims[i]:.1f} > {vol[i]}" for i in oversize)
            volume_warnings.append(f"Too large for {printer_name} ({details})")

    if not fits_any:
        errors.append(
            _error(
                "dimensions",
                f"Part dimensions {[f'{d:.1f}' for d in mesh_dims]} mm — does not fit any known printer. "
                + "; ".join(volume_warnings),
            )
        )
    else:
        # Find first printer it fits
        suitable = "unknown"
        for printer_name, vol in PRINTER_VOLUMES.items():
            if all(mesh_dims[i] <= vol[i] for i in range(3)):
                suitable = printer_name
                break
        warnings.append(
            _warning("dimensions", f"Fits {suitable}. Dimensions: {[f'{d:.1f}' for d in mesh_dims]} mm")
        )

    # --- overhang analysis ---
    if hasattr(mesh, "face_normals") and len(mesh.face_normals) > 0:
        # Compute angle between face normals and the vertical (Z+)
        z_up = np.array([0.0, 0.0, 1.0])
        normals = mesh.face_normals
        # angle from horizontal plane: 90° - angle from Z
        angles_from_horizontal = np.degrees(
            np.arccos(np.clip(np.abs(np.dot(normals, z_up)), -1.0, 1.0))
        )
        # Faces where the normal points close to horizontal = steep faces
        steep_faces = angles_from_horizontal < (90.0 - CRITICAL_OVERHANG_DEG)
        steep_ratio = float(np.mean(steep_faces))

        if steep_ratio > 0.05:
            steep_pct = steep_ratio * 100
            warnings.append(
                _warning(
                    "overhangs",
                    f"{steep_pct:.1f}% of faces exceed {CRITICAL_OVERHANG_DEG}° overhang — supports may be needed",
                )
            )
        elif steep_ratio > 0.20:
            errors.append(
                _error(
                    "overhangs",
                    f"{steep_ratio*100:.1f}% of faces exceed {CRITICAL_OVERHANG_DEG}° overhang — "
                    "supports required, consider redesign",
                )
            )

    # --- bed contact area ---
    if mesh.is_watertight:
        try:
            # Find the lowest Z plane and compute contact area
            z_min = float(bbox[0, 2])
            # Slice slightly above the lowest point
            slice_plane = z_min + layer_height
            section = mesh.section(plane_origin=[0, 0, slice_plane], plane_normal=[0, 0, 1])
            if section is not None:
                # Approximate area from section polygons
                bed_area = 0.0
                for entity in section.entities:
                    if hasattr(entity, "area"):
                        bed_area += entity.area
                if bed_area < 10.0 and max(mesh_dims) > 50:
                    warnings.append(
                        _warning(
                            "bed_adhesion",
                            f"Small first-layer contact area ({bed_area:.1f} mm²) — "
                            "consider a brim or raft for tall parts",
                        )
                    )
        except Exception:
            pass  # best-effort

    # --- wall thickness vs nozzle ---
    min_wall = nozzle_dia * 2  # minimum 2 perimeters
    # Use bounding box extents as a rough wall thickness proxy
    sorted_extents = sorted(float(d) for d in mesh_dims)
    thinnest_dim = sorted_extents[0] if sorted_extents else 0
    if thinnest_dim < min_wall and thinnest_dim > 0:
        errors.append(
            _error(
                "wall_thickness",
                f"Thinnest dimension {thinnest_dim:.2f} mm is below minimum {min_wall:.2f} mm "
                f"(2 × nozzle Ø {nozzle_dia} mm)",
            )
        )

    # --- orientation recommendation ---
    # For bed adhesion, the largest flat face should face down
    # Simple heuristic: if Z dimension is significantly larger than X and Y,
    # recommend laying the part flat
    if mesh_dims[2] > 1.5 * max(mesh_dims[0], mesh_dims[1]):
        warnings.append(
            _warning(
                "orientation",
                f"Tall part ({mesh_dims[2]:.1f} mm Z vs {mesh_dims[0]:.1f}×{mesh_dims[1]:.1f} XY) — "
                "consider laying flat for better stability",
            )
        )

    passed = len(errors) == 0
    return {
        "gate": "printability",
        "passed": passed,
        "errors": errors,
        "warnings": warnings,
    }


def main() -> None:
    nozzle_dia = 0.4
    layer_height = 0.2

    args = sys.argv[1:]
    i = 0
    stl_path = None

    while i < len(args):
        if args[i] in ("-h", "--help"):
            print(__doc__)
            sys.exit(0)
        elif args[i] == "--nozzle" and i + 1 < len(args):
            nozzle_dia = float(args[i + 1])
            i += 2
        elif args[i] == "--layer" and i + 1 < len(args):
            layer_height = float(args[i + 1])
            i += 2
        elif not args[i].startswith("-"):
            stl_path = args[i]
            i += 1
        else:
            i += 1

    if stl_path is None:
        print("Usage: python validate_printability.py <part.stl> [--nozzle 0.4] [--layer 0.2]", file=sys.stderr)
        sys.exit(2)

    if not Path(stl_path).exists():
        _fail("printability", f"STL file not found: {stl_path}")

    # Check trimesh availability
    try:
        import trimesh  # noqa: F401
    except ImportError:
        _fail(
            "printability",
            "trimesh is required. Install with: pip install trimesh",
        )

    report = _validate_printability(stl_path, nozzle_dia, layer_height)
    print(json.dumps(report, indent=2))
    sys.exit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()
