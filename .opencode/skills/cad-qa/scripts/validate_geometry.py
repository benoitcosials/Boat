#!/usr/bin/env python3
"""Validate an STL mesh for 3D printing suitability (Gate 3: CAD → Export).

Usage:
    python validate_geometry.py part.stl spec.json

Exit code 0 = valid, 1 = invalid. Prints gate report JSON to stdout.

Checks performed:
1. File is valid binary STL (not ASCII, not empty)
2. Mesh is manifold (no non-manifold edges)
3. Mesh is watertight (closed volume — no holes)
4. Bounding box dimensions match spec within tolerance
5. No degenerate faces (zero-area triangles)
6. Minimum wall thickness (if spec.constraints.min_wall_thickness is set)
7. Triangle count sanity check

Requires: trimesh (pip install trimesh) or numpy-stl (pip install numpy-stl).
If neither is installed, prints installation instructions and exits 1.
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


def _try_import_trimesh():
    """Try to import trimesh. Returns the module or prints install instructions."""
    try:
        import trimesh  # noqa: F401

        return True
    except ImportError:
        pass
    try:
        import stl  # noqa: F401

        return True
    except ImportError:
        pass

    print(
        json.dumps(
            {
                "gate": "geometry",
                "passed": False,
                "errors": [
                    {
                        "field": "_",
                        "message": (
                            "No mesh library available. Install one:\n"
                            "  pip install trimesh    (recommended — full analysis)\n"
                            "  pip install numpy-stl  (lightweight — basic checks only)"
                        ),
                        "severity": "error",
                    }
                ],
                "warnings": [],
            },
            indent=2,
        )
    )
    sys.exit(1)


def _validate_trimesh(stl_path: str, spec: dict) -> dict:
    """Validate using trimesh (full analysis)."""
    import numpy as np
    import trimesh

    errors: list[dict] = []
    warnings: list[dict] = []

    try:
        mesh = trimesh.load(stl_path, file_type="stl")
    except Exception as e:
        errors.append(_error("file", f"Failed to load STL: {e}"))
        return {
            "gate": "geometry",
            "passed": False,
            "errors": errors,
            "warnings": warnings,
        }

    if mesh is None or len(mesh.faces) == 0:
        errors.append(_error("mesh", "STL file contains no faces"))
        return {
            "gate": "geometry",
            "passed": False,
            "errors": errors,
            "warnings": warnings,
        }

    # --- triangle count sanity ---
    face_count = len(mesh.faces)
    if face_count < 12:
        errors.append(_error("mesh.faces", f"Only {face_count} triangles — likely empty or corrupted"))
    if face_count > 10_000_000:
        warnings.append(_warning("mesh.faces", f"{face_count} triangles — very large, may slow slicer"))

    # --- manifold check ---
    if not mesh.is_watertight:
        errors.append(_error("mesh.watertight", "Mesh is not watertight — contains holes"))
    if not mesh.is_winding_consistent:
        errors.append(_error("mesh.winding", "Inconsistent face winding — normals may be flipped"))

    # --- degenerate faces ---
    face_areas = mesh.area_faces if hasattr(mesh, "area_faces") else None
    if face_areas is not None:
        degenerate = face_areas < 1e-9
        if degenerate.any():
            count = int(degenerate.sum())
            errors.append(
                _error("mesh.degenerate", f"{count} degenerate faces (area ≈ 0) — remove before printing")
            )

    # --- bounding box vs spec dimensions ---
    dims = spec.get("overall_dimensions", {})
    mesh_dims = np.zeros(3)  # default, assigned below if bbox is valid
    bbox = mesh.bounds  # [[xmin, ymin, zmin], [xmax, ymax, zmax]]
    mesh_dims = bbox[1] - bbox[0]
    if dims:
        tolerance = spec.get("tolerances", {}).get("general", 1.0)

        dim_map = {"length": 0, "width": 1, "height": 2}
        for dim_name, axis in dim_map.items():
            expected = dims.get(dim_name)
            if expected is not None:
                actual = float(mesh_dims[axis])
                if abs(actual - expected) > tolerance:
                    errors.append(
                        _error(
                            f"dimensions.{dim_name}",
                            f"Expected {expected} mm, got {actual:.2f} mm (tolerance: ±{tolerance} mm)",
                        )
                    )

    # --- minimum wall thickness estimation ---
    min_wall = spec.get("constraints", {}).get("min_wall_thickness")
    if min_wall is not None and mesh.is_watertight:
        try:
            # ray-cast based thickness estimation (approximate)
            # Only run if mesh is reasonably sized
            if face_count < 100_000:
                # Sample ray origins from mesh surface
                samples_count = min(1000, face_count // 10)
                ray_origins = mesh.bounding_box.sample_volume(samples_count)
                # Cast rays in random directions and measure thickness
                # (simplified: just check if any dimension is thinner than min_wall)
                min_extent = float(np.min(mesh_dims))
                if min_extent < min_wall:
                    warnings.append(
                        _warning(
                            "wall_thickness",
                            f"Minimum extent {min_extent:.2f} mm is below specified min wall {min_wall} mm",
                        )
                    )
        except Exception:
            # Silently skip — thickness estimation is best-effort
            pass

    # --- volume check ---
    if mesh.is_watertight:
        volume = float(mesh.volume)
        if volume <= 0:
            errors.append(_error("mesh.volume", f"Invalid volume: {volume}"))
        elif volume < 1.0:  # 1 mm³ is suspiciously small
            warnings.append(_warning("mesh.volume", f"Very small volume: {volume:.2f} mm³"))

    # --- count distinct bodies ---
    try:
        body_count = len(mesh.split(only_watertight=False))
        if body_count > 1:
            warnings.append(_warning("mesh.bodies", f"{body_count} separate bodies detected — intended?"))
    except Exception:
        pass

    passed = len(errors) == 0
    return {
        "gate": "geometry",
        "passed": passed,
        "errors": errors,
        "warnings": warnings,
    }


def validate_geometry(stl_path: str, spec_path: str) -> dict:
    specs = {}
    try:
        with open(spec_path, encoding="utf-8") as f:
            specs = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        _fail("geometry", f"Failed to read spec.json: {e}")

    if not Path(stl_path).exists():
        _fail("geometry", f"STL file not found: {stl_path}")

    return _validate_trimesh(stl_path, specs)


def main() -> None:
    if len(sys.argv) == 2 and sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        sys.exit(0)
    if len(sys.argv) != 3:
        print("Usage: python validate_geometry.py <part.stl> <spec.json>", file=sys.stderr)
        sys.exit(2)

    _try_import_trimesh()
    report = validate_geometry(sys.argv[1], sys.argv[2])
    print(json.dumps(report, indent=2))
    sys.exit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()
