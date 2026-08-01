"""Naval hydrostatics computations using JAX (Metal GPU accelerated).

Computes volume, displacement, centers of buoyancy/flotation,
and form coefficients from hull offsets.

All computations in SI units (m, m³, kg). Uses trapezoidal integration
vectorized with JAX for GPU speed.
"""

import jax.numpy as jnp
import math

WATER_DENSITY_FRESH = 1000.0  # kg/m³
WATER_DENSITY_SALT = 1025.0  # kg/m³


def station_areas(
    half_breadths: jnp.ndarray, waterlines: jnp.ndarray
) -> jnp.ndarray:
    """Compute cross-sectional area at each station up to each waterline.

    Args:
        half_breadths: (n_stations, n_waterlines) half-beam [m]
        waterlines: (n_waterlines,) vertical positions [m], negative = below waterline

    Returns:
        areas: (n_stations, n_waterlines) cumulative area [m²] at each (station, WL)
    """
    # Integrate vertically: area = 2 × integral of half-breadth dz
    # Trapezoidal rule along waterlines axis
    dz = waterlines[1:] - waterlines[:-1]
    # Average half-breadth between adjacent waterlines
    avg_hb = 0.5 * (half_breadths[:, 1:] + half_breadths[:, :-1])
    # Area contribution per strip: 2 × (avg half-breadth × dz)
    strip_areas = 2.0 * avg_hb * jnp.abs(dz)

    # Cumulative sum from keel (bottom) to each waterline
    areas = jnp.zeros_like(half_breadths)
    areas = areas.at[:, 1:].set(
        jnp.cumsum(strip_areas, axis=1)
    )
    return areas


def displacement_and_volume(
    half_breadths: jnp.ndarray,
    stations: jnp.ndarray,
    waterlines: jnp.ndarray,
    design_waterline_idx: int = -1,
    water_density: float = WATER_DENSITY_FRESH,
) -> dict:
    """Compute displacement volume and mass at a given waterline.

    Args:
        half_breadths: (n_stations, n_waterlines) [m]
        stations: (n_stations,) longitudinal positions [m]
        waterlines: (n_waterlines,) vertical positions [m]
        design_waterline_idx: index of design waterline (default: last = -1)
        water_density: kg/m³

    Returns:
        dict with volume_m3, displacement_kg, displacement_tonnes
    """
    areas = station_areas(half_breadths, waterlines)
    design_areas = areas[:, design_waterline_idx]  # (n_stations,)

    # Simpson's rule integration along stations
    # For odd number of stations, use Simpson's 1/3 rule
    n = len(stations)
    dx = (stations[-1] - stations[0]) / (n - 1)

    # Trapezoidal fallback (works for any n)
    volume = jnp.trapezoid(design_areas, stations)

    displacement_kg = volume * water_density
    displacement_tonnes = displacement_kg / 1000.0

    return {
        "volume_m3": float(volume),
        "displacement_kg": float(displacement_kg),
        "displacement_tonnes": float(displacement_tonnes),
        "station_areas": areas.tolist(),
    }


def center_of_buoyancy(
    half_breadths: jnp.ndarray,
    stations: jnp.ndarray,
    waterlines: jnp.ndarray,
    design_waterline_idx: int = -1,
) -> dict:
    """Compute longitudinal and vertical center of buoyancy (LCB, VCB).

    Returns:
        dict with LCB_m (from station 0), VCB_m (below waterline, negative)
    """
    areas = station_areas(half_breadths, waterlines)
    design_areas = areas[:, design_waterline_idx]

    # Longitudinal center (LCB): weighted average of area × station position
    lcb_moment = jnp.trapezoid(design_areas * stations, stations)
    total_area = jnp.trapezoid(design_areas, stations)
    lcb = lcb_moment / total_area if total_area > 0 else 0.0

    # Vertical center (VCB): weighted average of area centroids vertically
    # For each station, find vertical centroid of immersed area
    n_stations = len(stations)
    n_wl = len(waterlines)
    station_vcb = jnp.zeros(n_stations)

    for i in range(n_stations):
        hb = half_breadths[i, : design_waterline_idx + 1]
        wl = waterlines[: design_waterline_idx + 1]
        # Vertical centroid: ∫ z × half_breadth dz / ∫ half_breadth dz
        # Trapezoidal
        dz = jnp.abs(wl[1:] - wl[:-1])
        avg_hb = 0.5 * (hb[1:] + hb[:-1])
        z_mid = 0.5 * (wl[1:] + wl[:-1])
        area_sum = jnp.sum(avg_hb * dz)
        if area_sum > 0:
            station_vcb = station_vcb.at[i].set(
                jnp.sum(avg_hb * z_mid * dz) / area_sum
            )

    # Average over stations, weighted by station area
    vcb = (
        jnp.trapezoid(station_vcb * design_areas, stations) / total_area
        if total_area > 0
        else 0.0
    )

    return {
        "LCB_m": float(lcb),
        "LCB_pct_loa": float(lcb / (stations[-1] - stations[0]) * 100),
        "VCB_m": float(vcb),
    }


def form_coefficients(
    half_breadths: jnp.ndarray,
    stations: jnp.ndarray,
    waterlines: jnp.ndarray,
    loa: float,
    beam: float,
    draft: float,
    design_waterline_idx: int = -1,
) -> dict:
    """Compute hull form coefficients.

    Returns:
        dict with Cb, Cp, Cm, Cwp
        Cb = block coefficient (fullness)
        Cp = prismatic coefficient (longitudinal fullness)
        Cm = midship section coefficient
        Cwp = waterplane area coefficient
    """
    areas = station_areas(half_breadths, waterlines)
    design_areas = areas[:, design_waterline_idx]  # (n_stations,)

    dx = (stations[-1] - stations[0]) / (len(stations) - 1)
    volume = float(jnp.trapezoid(design_areas, stations))

    # Block coefficient: Cb = ∇ / (L × B × T)
    cb = volume / (loa * beam * draft) if loa * beam * draft > 0 else 0.0

    # Midship area (approximate: station closest to 50% LOA)
    mid_idx = len(stations) // 2
    am = float(design_areas[mid_idx])

    # Prismatic coefficient: Cp = Cb / Cm  (where Cm = Am / (B × T))
    cm = am / (beam * draft) if beam * draft > 0 else 0.0
    cp = cb / cm if cm > 0 else 0.0

    # Waterplane area: area of the section at the waterline
    wl_half_breadths = half_breadths[:, design_waterline_idx]
    awp = float(2.0 * jnp.trapezoid(wl_half_breadths, stations))
    cwp = awp / (loa * beam) if loa * beam > 0 else 0.0

    return {
        "Cb": round(cb, 4),
        "Cp": round(cp, 4),
        "Cm": round(cm, 4),
        "Cwp": round(cwp, 4),
        "volume_m3": round(volume, 4),
        "am_m2": round(am, 4),
        "awp_m2": round(awp, 4),
    }


# Quick self-test
if __name__ == "__main__":
    # Mock a simple rectangular barge for testing
    n_stations, n_wl = 11, 6
    stations = jnp.linspace(0, 10, n_stations)
    waterlines = jnp.linspace(-2, 0, n_wl)
    half_breadths = jnp.ones((n_stations, n_wl)) * 2.5  # 5m beam

    disp = displacement_and_volume(half_breadths, stations, waterlines)
    print(f"Volume: {disp['volume_m3']:.2f} m³")
    print(f"Displacement: {disp['displacement_kg']:.0f} kg")

    cb = form_coefficients(half_breadths, stations, waterlines, 10, 5, 2)
    print(f"Cb: {cb['Cb']} (expected 1.0 for rectangular barge)")
