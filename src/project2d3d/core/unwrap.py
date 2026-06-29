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


def unwrap_cylinder(
    volume: np.ndarray,
    point_a: np.ndarray,
    point_b: np.ndarray,
    radius: float,
    theta_steps: int = 360,
    z_steps: int | None = None,
) -> np.ndarray:
    """
    Project a cylindrical surface onto a 2D image.
    Returns shape (z_steps, theta_steps).
    """
    axis_unit, length, perp1, perp2 = _build_local_frame(point_a, point_b)
    if z_steps is None:
        z_steps = int(np.round(length))

    thetas = np.linspace(0, 2 * np.pi, theta_steps, endpoint=False)
    zs = np.linspace(0, length, z_steps)
    theta_grid, z_grid = np.meshgrid(thetas, zs)

    pts = (
        point_a
        + z_grid[:, :, np.newaxis] * axis_unit
        + radius * np.cos(theta_grid)[:, :, np.newaxis] * perp1
        + radius * np.sin(theta_grid)[:, :, np.newaxis] * perp2
    )
    return _sample_surface(volume, pts)


def unwrap_spiral(
    volume: np.ndarray,
    point_a: np.ndarray,
    point_b: np.ndarray,
    r_inner: float,
    r_outer: float,
    n_turns: float,
    theta_steps: int = 1000,
    z_steps: int | None = None,
) -> np.ndarray:
    """
    Unroll an Archimedean spiral surface (rolled scroll) from a 3D volume.

    The radius grows linearly with angle:
        r(θ) = r_inner + (r_outer - r_inner) * θ / (2π * n_turns)

    Returns shape (z_steps, theta_steps).
    Columns represent arc position from the inner to outer edge of the scroll.
    """
    axis_unit, length, perp1, perp2 = _build_local_frame(point_a, point_b)
    if z_steps is None:
        z_steps = int(np.round(length))

    # θ runs from 0 to 2π * n_turns (full spiral from inside to outside)
    thetas = np.linspace(0, 2 * np.pi * n_turns, theta_steps, endpoint=False)
    radii = r_inner + (r_outer - r_inner) * thetas / (2 * np.pi * n_turns)

    zs = np.linspace(0, length, z_steps)
    theta_grid, z_grid = np.meshgrid(thetas, zs)
    r_grid, _ = np.meshgrid(radii, zs)

    pts = (
        point_a
        + z_grid[:, :, np.newaxis] * axis_unit
        + r_grid[:, :, np.newaxis] * np.cos(theta_grid)[:, :, np.newaxis] * perp1
        + r_grid[:, :, np.newaxis] * np.sin(theta_grid)[:, :, np.newaxis] * perp2
    )
    return _sample_surface(volume, pts)
