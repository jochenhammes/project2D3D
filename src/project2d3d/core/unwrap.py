import numpy as np
from scipy.ndimage import map_coordinates


def _build_local_frame(point_a: np.ndarray, point_b: np.ndarray):
    """Return (axis_unit, length, perp1, perp2) for the given axis."""
    axis = point_b - point_a
    length = np.linalg.norm(axis)
    if length == 0:
        raise ValueError("Axis points must be different.")
    axis_unit = axis / length
    arbitrary = np.array([1.0, 0.0, 0.0])
    if abs(np.dot(axis_unit, arbitrary)) > 0.9:
        arbitrary = np.array([0.0, 1.0, 0.0])
    perp1 = np.cross(axis_unit, arbitrary)
    perp1 /= np.linalg.norm(perp1)
    perp2 = np.cross(axis_unit, perp1)
    return axis_unit, length, perp1, perp2


def _sample_surface(volume, pts):
    coords = [pts[..., i].ravel() for i in range(3)]
    sampled = map_coordinates(volume, coords, order=1, mode="constant", cval=0.0)
    return sampled.reshape(pts.shape[:2]).astype(np.float32)


def _project(slices: list, mode: str) -> np.ndarray:
    if mode == "min":
        return np.min(slices, axis=0)
    elif mode == "mean":
        return np.mean(slices, axis=0).astype(np.float32)
    else:
        return np.max(slices, axis=0)


def unwrap_cylinder(
    volume: np.ndarray,
    point_a: np.ndarray,
    point_b: np.ndarray,
    radius: float,
    theta_steps: int = 360,
    z_steps: int | None = None,
    theta_offset_deg: float = 0.0,
    radial_range: float = 1.0,
    radial_samples: int = 3,
    projection: str = "max",
) -> np.ndarray:
    """
    Project a cylindrical surface onto a 2D image.
    Returns shape (z_steps, theta_steps).

    A small radial MIP (±radial_range voxels) makes min/mean projections
    meaningful and improves robustness near the shell boundary.
    """
    axis_unit, length, perp1, perp2 = _build_local_frame(point_a, point_b)
    if z_steps is None:
        z_steps = int(np.round(length))

    offset = np.deg2rad(theta_offset_deg)
    thetas = np.linspace(offset, offset + 2 * np.pi, theta_steps, endpoint=False)
    zs = np.linspace(0, length, z_steps)
    theta_grid, z_grid = np.meshgrid(thetas, zs)
    cos_t, sin_t = np.cos(theta_grid), np.sin(theta_grid)

    dr_offsets = np.linspace(-radial_range, radial_range, radial_samples)
    slices = []
    for dr in dr_offsets:
        r = radius + dr
        pts = (
            point_a
            + z_grid[:, :, np.newaxis] * axis_unit
            + r * cos_t[:, :, np.newaxis] * perp1
            + r * sin_t[:, :, np.newaxis] * perp2
        )
        slices.append(_sample_surface(volume, pts))
    return _project(slices, projection)  # cylinder end


def unwrap_spiral(
    volume: np.ndarray,
    point_a: np.ndarray,
    point_b: np.ndarray,
    r_inner: float,
    r_outer: float,
    n_turns: float,
    theta_steps: int = 1000,
    z_steps: int | None = None,
    theta_offset_deg: float = 0.0,
    radial_range: float = 3.0,
    radial_samples: int = 7,
    projection: str = "max",
) -> np.ndarray:
    """
    Unroll an Archimedean spiral surface (rolled scroll) from a 3D volume.

    r(θ) = r_inner + (r_outer - r_inner) * θ / (2π * n_turns)

    To handle thin shells and slight parameter mismatches, a max-intensity
    projection over ±radial_range voxels around the spiral surface is used.
    Returns shape (z_steps, theta_steps).
    """
    axis_unit, length, perp1, perp2 = _build_local_frame(point_a, point_b)
    if z_steps is None:
        z_steps = int(np.round(length))

    offset = np.deg2rad(theta_offset_deg)
    thetas = np.linspace(offset, offset + 2 * np.pi * n_turns, theta_steps, endpoint=False)
    radii = r_inner + (r_outer - r_inner) * (thetas - offset) / (2 * np.pi * n_turns)

    zs = np.linspace(0, length, z_steps)
    theta_grid, z_grid = np.meshgrid(thetas, zs)
    r_grid, _ = np.meshgrid(radii, zs)

    # Radial direction unit vector at each theta (points outward from axis)
    # outward = cos(θ)*perp1 + sin(θ)*perp2
    cos_t = np.cos(theta_grid)
    sin_t = np.sin(theta_grid)

    dr_offsets = np.linspace(-radial_range, radial_range, radial_samples)
    slices = []
    for dr in dr_offsets:
        r = r_grid + dr
        pts = (
            point_a
            + z_grid[:, :, np.newaxis] * axis_unit
            + r[:, :, np.newaxis] * cos_t[:, :, np.newaxis] * perp1
            + r[:, :, np.newaxis] * sin_t[:, :, np.newaxis] * perp2
        )
        slices.append(_sample_surface(volume, pts))

    return _project(slices, projection)
