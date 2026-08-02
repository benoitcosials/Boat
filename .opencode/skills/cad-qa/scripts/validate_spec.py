#!/usr/bin/env python3
"""Validate a CAD specification JSON file (Gate 1: Requirements → Engineering).

Usage:
    python validate_spec.py spec.json

Exit code 0 = valid, 1 = invalid. Prints gate report JSON to stdout.

The spec.json format expected by this validator:

{
  "part_name": "reducer_housing",
  "description": "Gear reducer housing with 4 mounting holes",
  "material": "PLA",
  "units": "mm",
  "overall_dimensions": {
    "length": 120.0,
    "width": 80.0,
    "height": 60.0
  },
  "features": [
    {"type": "bore", "diameter": 10.0, "depth": 25.0, "label": "input_shaft"},
    {"type": "mounting_hole", "diameter": 5.0, "count": 4, "label": "corner_mounts"}
  ],
  "tolerances": {
    "general": 0.2,
    "bore": 0.05
  },
  "constraints": {
    "min_wall_thickness": 1.2,
    "max_overhang_angle": 45
  }
}
"""

import json
import sys
from typing import NoReturn

# Recognized materials with minimum wall thickness (mm) for FDM 3D printing
KNOWN_MATERIALS: dict[str, float] = {
    "pla": 1.2,
    "petg": 1.2,
    "abs": 1.5,
    "asa": 1.5,
    "tpu": 1.5,
    "nylon": 1.5,
    "pc": 1.5,
}

VALID_UNITS = {"mm", "cm", "in", "inch"}

VALID_FEATURE_TYPES = {
    "bore", "mounting_hole", "pocket", "slot", "chamfer",
    "fillet", "thread", "groove", "keyway", "boss",
    "rib", "flange", "gear", "spline",
}

MAX_DIMENSION_MM = 5000.0  # sanity check — no part larger than 5m


def _load_json(path: str):  # returns dict or exits via _fail
    """Load and parse a JSON file, exiting with a gate report on failure."""
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        _fail("spec", f"File not found: {path}")
    except json.JSONDecodeError as e:
        _fail("spec", f"Invalid JSON in {path}: {e}")


def _fail(gate: str, message: str) -> NoReturn:
    """Print a gate report with a single error and exit 1."""
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


def validate_spec(spec_path: str) -> dict:
    """Validate a spec.json file. Returns a gate report dict."""
    errors: list[dict] = []
    warnings: list[dict] = []

    data = _load_json(spec_path)

    # --- required top-level fields ---
    for field in ("part_name", "description", "material", "units"):
        if field not in data or not data[field]:
            errors.append(_error(field, f"Missing required field: {field}"))

    # --- part_name ---
    pn = data.get("part_name", "")
    if pn and (not isinstance(pn, str) or len(pn.strip()) == 0):
        errors.append(_error("part_name", "Must be a non-empty string"))

    # --- material ---
    mat = str(data.get("material", "")).lower().strip()
    if mat and mat not in KNOWN_MATERIALS:
        warnings.append(
            _warning(
                "material",
                f"Unknown material '{mat}'. Known: {', '.join(sorted(KNOWN_MATERIALS))}",
            )
        )

    # --- units ---
    units = str(data.get("units", "")).lower().strip()
    if units and units not in VALID_UNITS:
        errors.append(
            _error("units", f"Invalid unit '{units}'. Valid: {', '.join(sorted(VALID_UNITS))}")
        )

    # --- overall_dimensions ---
    dims = data.get("overall_dimensions")
    if dims is None:
        errors.append(_error("overall_dimensions", "Missing required field"))
    elif not isinstance(dims, dict):
        errors.append(_error("overall_dimensions", "Must be an object"))
    else:
        for dim_key in ("length", "width", "height"):
            val = dims.get(dim_key)
            if val is None:
                errors.append(_error(f"overall_dimensions.{dim_key}", "Missing required dimension"))
            elif not isinstance(val, (int, float)) or val <= 0:
                errors.append(
                    _error(f"overall_dimensions.{dim_key}", "Must be a positive number")
                )
            elif val > MAX_DIMENSION_MM:
                errors.append(
                    _error(
                        f"overall_dimensions.{dim_key}",
                        f"Value {val} exceeds sanity limit of {MAX_DIMENSION_MM}",
                    )
                )

    # --- features ---
    features = data.get("features")
    if features is None:
        errors.append(_error("features", "Missing required field (use empty list if none)"))
    elif not isinstance(features, list):
        errors.append(_error("features", "Must be an array"))
    else:
        for i, feat in enumerate(features):
            if not isinstance(feat, dict):
                errors.append(_error(f"features[{i}]", "Must be an object"))
                continue
            ftype = feat.get("type", "")
            if ftype not in VALID_FEATURE_TYPES:
                errors.append(
                    _error(
                        f"features[{i}].type",
                        f"Unknown feature type '{ftype}'. Valid: {', '.join(sorted(VALID_FEATURE_TYPES))}",
                    )
                )
            if "label" not in feat:
                warnings.append(
                    _warning(f"features[{i}]", "Missing label — recommended for traceability")
                )
            # validate numeric fields if present
            for num_field in ("diameter", "depth", "width", "length", "height", "radius"):
                val = feat.get(num_field)
                if val is not None and (not isinstance(val, (int, float)) or val <= 0):
                    errors.append(
                        _error(
                            f"features[{i}].{num_field}",
                            "Must be a positive number",
                        )
                    )
            count = feat.get("count")
            if count is not None and (not isinstance(count, int) or count < 1):
                errors.append(_error(f"features[{i}].count", "Must be a positive integer"))

    # --- tolerances (optional, warn if missing) ---
    tolerances = data.get("tolerances")
    if tolerances is None:
        warnings.append(_warning("tolerances", "No tolerances specified — assuming ±0.5 mm"))
    elif isinstance(tolerances, dict):
        for tol_key in ("general",):
            val = tolerances.get(tol_key)
            if val is not None and (not isinstance(val, (int, float)) or val < 0):
                errors.append(_error(f"tolerances.{tol_key}", "Must be a non-negative number"))

    # --- constraints ---
    constraints = data.get("constraints")
    if constraints is None:
        warnings.append(_warning("constraints", "No constraints specified"))
    elif isinstance(constraints, dict):
        min_wall = constraints.get("min_wall_thickness")
        if min_wall is not None and (not isinstance(min_wall, (int, float)) or min_wall <= 0):
            errors.append(_error("constraints.min_wall_thickness", "Must be a positive number"))

    passed = len(errors) == 0
    return {
        "gate": "spec",
        "passed": passed,
        "errors": errors,
        "warnings": warnings,
    }


def main() -> None:
    if len(sys.argv) == 2 and sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        sys.exit(0)
    if len(sys.argv) != 2:
        print("Usage: python validate_spec.py <spec.json>", file=sys.stderr)
        sys.exit(2)

    report = validate_spec(sys.argv[1])
    print(json.dumps(report, indent=2))
    sys.exit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()
