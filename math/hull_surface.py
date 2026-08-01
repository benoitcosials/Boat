"""Naval hull surface modeling with Bézier/NURBS patches (JAX + Metal GPU).

Generates 3D hull surface from design parameters:
- LOA (length overall) [m]
- Beam (max beam) [m]
- Draft (design draft) [m]
- Entry angle (bow half-angle at waterline) [deg]
- Deadrise (bottom angle at transom) [deg]

Uses a 4×4 cubic Bézier patch for the hull surface. Control points are
derived from the design parameters. Output is an offsets table suitable
for hydrostatics and FeatureScript generation.
"""

import jax.numpy as jnp
import math


def compute_control_points(
    loa: float,
    beam: float,
    draft: float,
    entry_angle_deg: float = 20.0,
    deadrise_deg: float = 5.0,
) -> jnp.ndarray:
    """Compute 4×4×3 control grid for a cubic Bézier hull patch.

    Returns:
        control_points: shape (4, 4, 3) — (u_station, v_height, xyz)
        u: longitudinal (0=bow, 3=transom)
        v: vertical (0=keel, 3=sheer)
    """
    entry_angle = jnp.radians(entry_angle_deg)
    deadrise = jnp.radians(deadrise_deg)

    # Stations along the hull (0 = bow, 1 = transom)
    stations = jnp.array([0.0, 0.25, 0.75, 1.0]) * loa

    # Waterline half-beam at each station (parabolic waterline)
    # Wide amidships, narrow at bow and transom
    wl_beam = beam * jnp.array([0.15, 0.95, 1.0, 0.8])

    # Draft at each station (deep amidships, shallow at bow)
    station_draft = draft * jnp.array([0.5, 0.95, 1.0, 0.9])

    # Keel half-beam (narrow at bow, wider aft, deadrise at transom)
    keel_beam = beam * jnp.array([0.0, 0.3, 0.5, 0.4])

    # Control grid: (station_idx, height_idx, xyz)
    control = jnp.zeros((4, 4, 3))

    for i in range(4):
        # x = longitudinal position
        x = stations[i]
        wl = wl_beam[i]
        kb = keel_beam[i]
        d = station_draft[i]

        # v=0: keel point
        control = control.at[i, 0].set(jnp.array([x, kb, -d]))

        # v=1: lower hull (1/3 up from keel)
        flare = (wl - kb) * 0.33
        control = control.at[i, 1].set(jnp.array([x, kb + flare, -d * 0.67]))

        # v=2: upper hull (2/3 up from keel)
        control = control.at[i, 2].set(jnp.array([x, kb + flare * 2.2, -d * 0.33]))

        # v=3: sheer / deck edge
        # At bow (i=0), entry angle reduces beam
        if i == 0:
            wl_at_sheer = wl * 0.85
        else:
            wl_at_sheer = wl
        control = control.at[i, 3].set(jnp.array([x, wl_at_sheer * 1.02, 0.02 * draft]))

    return control


def evaluate_surface(
    control_points: jnp.ndarray, u_samples: int = 20, v_samples: int = 10
) -> jnp.ndarray:
    """Evaluate Bézier surface at uniform (u, v) grid.

    Args:
        control_points: shape (4, 4, 3) control grid
        u_samples: number of longitudinal stations
        v_samples: number of vertical sections

    Returns:
        surface: shape (u_samples, v_samples, 3) surface points
    """
    u = jnp.linspace(0.0, 1.0, u_samples)
    v = jnp.linspace(0.0, 1.0, v_samples)

    # Pre-compute Bernstein basis
    def bernstein(i, t):
        """Bernstein polynomial B_i^3(t)."""
        if i == 0:
            return (1 - t) ** 3
        elif i == 1:
            return 3 * t * (1 - t) ** 2
        elif i == 2:
            return 3 * t ** 2 * (1 - t)
        else:
            return t ** 3

    # Evaluate at each (u, v)
    surface = jnp.zeros((u_samples, v_samples, 3))
    for ui in range(u_samples):
        for vj in range(v_samples):
            pt = jnp.zeros(3)
            for i in range(4):
                for j in range(4):
                    pt += (
                        bernstein(i, u[ui])
                        * bernstein(j, v[vj])
                        * control_points[i, j]
                    )
            surface = surface.at[ui, vj].set(pt)

    return surface


def generate_offsets(
    loa: float,
    beam: float,
    draft: float,
    entry_angle_deg: float = 20.0,
    deadrise_deg: float = 5.0,
    n_stations: int = 11,
    n_waterlines: int = 6,
) -> dict:
    """Generate full offsets table for a simple sailing dinghy hull.

    Returns:
        dict with:
        - stations: (n_stations,) longitudinal positions [m]
        - waterlines: (n_waterlines,) vertical positions [m]
        - half_breadths: (n_stations, n_waterlines) half-beam at each (station, WL)
        - surface_points: (n_stations, n_waterlines, 3) full 3D points
        - control_points: (4, 4, 3) Bézier control grid
        - parameters: input design parameters
    """
    control = compute_control_points(loa, beam, draft, entry_angle_deg, deadrise_deg)
    surface = evaluate_surface(control, n_stations, n_waterlines)

    # Extract half-breadths and station/waterline positions
    stations = surface[:, 0, 0]  # x-coordinate at keel level (v=0)
    waterlines = surface[0, :, 2]  # z-coordinate at bow (u=0)

    half_breadths = surface[:, :, 1]  # y-coordinate (half-beam)

    return {
        "stations": stations.tolist(),
        "waterlines": waterlines.tolist(),
        "half_breadths": half_breadths.tolist(),
        "surface_points": surface.tolist(),
        "control_points": control.tolist(),
        "parameters": {
            "loa": loa,
            "beam": beam,
            "draft": draft,
            "entry_angle_deg": entry_angle_deg,
            "deadrise_deg": deadrise_deg,
        },
    }


# Quick self-test
if __name__ == "__main__":
    import json

    offsets = generate_offsets(
        loa=4.0, beam=1.5, draft=0.3, entry_angle_deg=20.0, deadrise_deg=5.0
    )
    print(f"Stations: {len(offsets['stations'])}")
    print(f"LOA: {offsets['stations'][-1]:.2f} m")
    print(f"Max half-beam: {max(max(row) for row in offsets['half_breadths']):.3f} m")
    print("Control points (bow, keel):", offsets["control_points"][0][0])
