#!/usr/bin/env python3
"""Validate engineering parameter JSON against the specification (Gate 2: Engineering → CAD).

Usage:
    python validate_params.py spec.json params.json

Exit code 0 = valid, 1 = invalid. Prints gate report JSON to stdout.

The params.json format expected by this validator:

{
  "units": "mm",
  "gears": [
    {
      "label": "input_gear",
      "teeth": 15,
      "module": 2.0,
      "pitch_diameter": 30.0,
      "pressure_angle": 20.0,
      "face_width": 10.0,
      "bore_diameter": 10.0
    }
  ],
  "shafts": [
    {"label": "input_shaft", "diameter": 10.0, "length": 50.0}
  ],
  "housing": {
    "wall_thickness": 3.0,
    "clearance_radial": 1.0,
    "clearance_axial": 0.5
  },
  "bearings": [
    {"label": "input_bearing", "inner_diameter": 10.0, "outer_diameter": 26.0, "width": 8.0}
  ],
  "fasteners": [
    {"label": "corner_mounts", "type": "socket_head", "diameter": 5.0, "count": 4}
  ]
}
"""

import json
import sys
import math
from pathlib import Path
from typing import NoReturn


def _load_json(path: str):  # returns dict or exits via _fail
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        _fail("params", f"File not found: {path}")
    except json.JSONDecodeError as e:
        _fail("params", f"Invalid JSON in {path}: {e}")


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


# Minimum wall thickness per material for FDM (mm)
MATERIAL_MIN_WALL: dict[str, float] = {
    "pla": 1.2,
    "petg": 1.2,
    "abs": 1.5,
    "asa": 1.5,
    "tpu": 1.5,
    "nylon": 1.5,
    "pc": 1.5,
}

# Standard gear modules (mm) — ISO 54
STANDARD_MODULES = {0.5, 0.8, 1.0, 1.25, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0, 8.0, 10.0}

# Standard pressure angles (degrees)
STANDARD_PRESSURE_ANGLES = {14.5, 20.0, 25.0}


def validate_params(spec_path: str, params_path: str) -> dict:
    errors: list[dict] = []
    warnings: list[dict] = []

    spec = _load_json(spec_path)
    params = _load_json(params_path)

    # --- top-level units ---
    params_units = str(params.get("units", "")).lower().strip()
    if params_units and params_units != "mm":
        warnings.append(_warning("units", f"Units are '{params_units}' — expected 'mm'"))

    # --- material check ---
    material = str(spec.get("material", "")).lower().strip()
    min_wall_spec = spec.get("constraints", {}).get("min_wall_thickness")
    if material:
        expected_min_wall = MATERIAL_MIN_WALL.get(material)
        if expected_min_wall is None:
            expected_min_wall = 1.5  # conservative default
        if min_wall_spec is not None and min_wall_spec < expected_min_wall:
            warnings.append(
                _warning(
                    "constraints.min_wall_thickness",
                    f"Specified {min_wall_spec} mm is below recommended {expected_min_wall} mm for {material}",
                )
            )

    # --- extract sections for cross-validation ---
    gears = params.get("gears", [])
    bearings = params.get("bearings", [])

    # --- gears validation ---
    if not isinstance(gears, list):
        errors.append(_error("gears", "Must be an array"))
    else:
        for i, gear in enumerate(gears):
            if not isinstance(gear, dict):
                errors.append(_error(f"gears[{i}]", "Must be an object"))
                continue

            prefix = f"gears[{i}]"
            teeth = gear.get("teeth")
            module = gear.get("module")
            pitch_diameter = gear.get("pitch_diameter")
            pressure_angle = gear.get("pressure_angle")
            bore = gear.get("bore_diameter")

            # teeth count
            if teeth is not None:
                if not isinstance(teeth, int) or teeth < 5:
                    errors.append(_error(f"{prefix}.teeth", f"Must be an integer ≥ 5, got {teeth}"))
                if teeth < 12 and pressure_angle == 20.0:
                    warnings.append(
                        _warning(
                            f"{prefix}.teeth",
                            f"{teeth} teeth at 20° may undercut — consider profile shift",
                        )
                    )

            # module
            if module is not None:
                if not isinstance(module, (int, float)) or module <= 0:
                    errors.append(_error(f"{prefix}.module", "Must be a positive number"))
                elif isinstance(module, (int, float)) and module not in STANDARD_MODULES:
                    nearest = min(STANDARD_MODULES, key=lambda m: abs(m - module))  # type: ignore[arg-type]
                    warnings.append(
                        _warning(
                            f"{prefix}.module",
                            f"Module {module} is non-standard. Nearest standard: {nearest}",
                        )
                    )

            # pitch diameter = teeth × module (consistency check)
            if teeth is not None and module is not None and isinstance(teeth, int) and isinstance(module, (int, float)):
                expected_pd = teeth * module
                if pitch_diameter is not None:
                    if not math.isclose(pitch_diameter, expected_pd, rel_tol=1e-6):
                        errors.append(
                            _error(
                                f"{prefix}.pitch_diameter",
                                f"Expected {expected_pd} (teeth × module = {teeth} × {module}), got {pitch_diameter}",
                            )
                        )
                else:
                    warnings.append(
                        _warning(f"{prefix}.pitch_diameter", f"Missing — expected {expected_pd}")
                    )

            # pressure angle
            if pressure_angle is not None:
                if pressure_angle not in STANDARD_PRESSURE_ANGLES:
                    warnings.append(
                        _warning(
                            f"{prefix}.pressure_angle",
                            f"Non-standard pressure angle {pressure_angle}°",
                        )
                    )

            # bore must fit on shaft
            if bore is not None and (not isinstance(bore, (int, float)) or bore <= 0):
                errors.append(_error(f"{prefix}.bore_diameter", "Must be a positive number"))

        # --- gear ratio consistency (if exactly 2 gears) ---
        if len(gears) == 2:
            t0 = gears[0].get("teeth")
            t1 = gears[1].get("teeth")
            if isinstance(t0, int) and isinstance(t1, int) and t0 > 0 and t1 > 0:
                m0 = gears[0].get("module")
                m1 = gears[1].get("module")
                if m0 is not None and m1 is not None and not math.isclose(m0, m1, rel_tol=1e-6):
                    errors.append(
                        _error(
                            "gears[].module",
                            f"Mismatched modules: gear[0]={m0}, gear[1]={m1} — meshing gears need same module",
                        )
                    )

    # --- shafts validation ---
    shafts = params.get("shafts", [])
    if isinstance(shafts, list):
        for i, shaft in enumerate(shafts):
            if not isinstance(shaft, dict):
                errors.append(_error(f"shafts[{i}]", "Must be an object"))
                continue
            prefix = f"shafts[{i}]"
            for key in ("diameter",):
                val = shaft.get(key)
                if val is not None and (not isinstance(val, (int, float)) or val <= 0):
                    errors.append(_error(f"{prefix}.{key}", "Must be a positive number"))
            # check shaft fits in at least one bore or bearing
            sd = shaft.get("diameter")
            if sd is not None and isinstance(sd, (int, float)):
                fits_somewhere = False
                # check gears
                for gear in (gears if isinstance(gears, list) else []):
                    gb = gear.get("bore_diameter") if isinstance(gear, dict) else None
                    if gb is not None and isinstance(gb, (int, float)) and sd < gb:
                        fits_somewhere = True
                        break
                # check bearings
                if not fits_somewhere:
                    for bearing in (bearings if isinstance(bearings, list) else []):
                        inner = bearing.get("inner_diameter") if isinstance(bearing, dict) else None
                        if inner is not None and isinstance(inner, (int, float)) and sd < inner:
                            fits_somewhere = True
                            break
                if not fits_somewhere and (isinstance(gears, list) or isinstance(bearings, list)):
                    warnings.append(
                        _warning(
                            f"shafts[{i}].diameter",
                            f"Shaft Ø {sd} mm fits in no gear bore or bearing — verify intended interface",
                        )
                    )

    # --- housing validation ---
    housing = params.get("housing")
    if isinstance(housing, dict):
        wall = housing.get("wall_thickness")
        if wall is not None:
            if not isinstance(wall, (int, float)) or wall <= 0:
                errors.append(_error("housing.wall_thickness", "Must be a positive number"))
            elif material in MATERIAL_MIN_WALL and wall < MATERIAL_MIN_WALL[material]:
                warnings.append(
                    _warning(
                        "housing.wall_thickness",
                        f"{wall} mm is below recommended {MATERIAL_MIN_WALL[material]} mm for {material}",
                    )
                )

        for clr_key in ("clearance_radial", "clearance_axial"):
            val = housing.get(clr_key)
            if val is not None:
                if not isinstance(val, (int, float)) or val < 0:
                    errors.append(_error(f"housing.{clr_key}", "Must be a non-negative number"))
                elif val < 0.2:
                    warnings.append(
                        _warning(
                            f"housing.{clr_key}",
                            f"{val} mm clearance is very tight — 0.3 mm minimum recommended for FDM",
                        )
                    )

    # --- bearings validation ---
    if isinstance(bearings, list):
        for i, bearing in enumerate(bearings):
            if not isinstance(bearing, dict):
                continue
            prefix = f"bearings[{i}]"
            inner = bearing.get("inner_diameter")
            outer = bearing.get("outer_diameter")
            if inner is not None and outer is not None:
                if inner >= outer:
                    errors.append(
                        _error(
                            f"{prefix}",
                            f"Inner diameter ({inner}) must be less than outer diameter ({outer})",
                        )
                    )
            for key in ("inner_diameter", "outer_diameter", "width"):
                val = bearing.get(key)
                if val is not None and (not isinstance(val, (int, float)) or val <= 0):
                    errors.append(_error(f"{prefix}.{key}", "Must be a positive number"))

    # --- fasteners validation ---
    fasteners = params.get("fasteners", [])
    if isinstance(fasteners, list):
        for i, fastener in enumerate(fasteners):
            if not isinstance(fastener, dict):
                errors.append(_error(f"fasteners[{i}]", "Must be an object"))
                continue
            prefix = f"fasteners[{i}]"
            dia = fastener.get("diameter")
            if dia is not None and (not isinstance(dia, (int, float)) or dia <= 0):
                errors.append(_error(f"{prefix}.diameter", "Must be a positive number"))
            count = fastener.get("count")
            if count is not None and (not isinstance(count, int) or count < 1):
                errors.append(_error(f"{prefix}.count", "Must be a positive integer"))

    passed = len(errors) == 0
    return {
        "gate": "params",
        "passed": passed,
        "errors": errors,
        "warnings": warnings,
    }


def main() -> None:
    if len(sys.argv) == 2 and sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        sys.exit(0)
    if len(sys.argv) != 3:
        print("Usage: python validate_params.py <spec.json> <params.json>", file=sys.stderr)
        sys.exit(2)

    report = validate_params(sys.argv[1], sys.argv[2])
    print(json.dumps(report, indent=2))
    sys.exit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()
