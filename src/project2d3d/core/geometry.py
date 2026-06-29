import numpy as np


def _local_frame(point_a, point_b):
    axis = point_b - point_a
    length = np.linalg.norm(axis)
    if length == 0:
        return None, 0, None, None
    axis_unit = axis / length
    arb = np.array([1.0, 0.0, 0.0])
    if abs(np.dot(axis_unit, arb)) > 0.9:
        arb = np.array([0.0, 1.0, 0.0])
    perp1 = np.cross(axis_unit, arb)
    perp1 /= np.linalg.norm(perp1)
    perp2 = np.cross(axis_unit, perp1)
    return axis_unit, length, perp1, perp2


def _quad_faces(n_z: int, n_col: int, wrap: bool = False) -> np.ndarray:
    """Triangle faces for a (n_z × n_col) grid. wrap=True closes last column."""
    faces = []
    for iz in range(n_z - 1):
        for ic in range(n_col):
            ic_next = (ic + 1) % n_col if wrap else ic + 1
            if ic_next >= n_col:
                continue
            v00 = iz * n_col + ic
            v01 = iz * n_col + ic_next
            v10 = (iz + 1) * n_col + ic
            v11 = (iz + 1) * n_col + ic_next
            faces.append([v00, v10, v01])
            faces.append([v01, v10, v11])
    return np.array(faces, dtype=np.int32)


def make_cylinder_mesh(
    point_a: np.ndarray,
    point_b: np.ndarray,
    radius: float,
    n_theta: int = 64,
    n_z: int = 32,
) -> tuple[np.ndarray, np.ndarray]:
    """Cylinder surface mesh for napari Surface layer."""
    axis_unit, length, perp1, perp2 = _local_frame(point_a, point_b)
    if axis_unit is None:
        return np.zeros((1, 3), np.float32), np.zeros((1, 3), np.int32)

    thetas = np.linspace(0, 2 * np.pi, n_theta, endpoint=False)
    zs = np.linspace(0, length, n_z)
    theta_grid, z_grid = np.meshgrid(thetas, zs)

    vertices = (
        point_a
        + z_grid[:, :, np.newaxis] * axis_unit
        + radius * np.cos(theta_grid)[:, :, np.newaxis] * perp1
        + radius * np.sin(theta_grid)[:, :, np.newaxis] * perp2
    ).reshape(-1, 3).astype(np.float32)

    return vertices, _quad_faces(n_z, n_theta, wrap=True)


def make_spiral_mesh(
    point_a: np.ndarray,
    point_b: np.ndarray,
    r_inner: float,
    r_outer: float,
    n_turns: float,
    theta_offset_deg: float = 0.0,
    n_theta: int = 256,
    n_z: int = 32,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Archimedean spiral surface mesh for napari Surface layer.

    The spiral goes from r_inner (θ=offset) to r_outer (θ=offset+2π*n_turns).
    """
    axis_unit, length, perp1, perp2 = _local_frame(point_a, point_b)
    if axis_unit is None:
        return np.zeros((1, 3), np.float32), np.zeros((1, 3), np.int32)

    offset = np.deg2rad(theta_offset_deg)
    thetas = np.linspace(offset, offset + 2 * np.pi * n_turns, n_theta, endpoint=False)
    radii = r_inner + (r_outer - r_inner) * (thetas - offset) / (2 * np.pi * n_turns)
    zs = np.linspace(0, length, n_z)

    theta_grid, z_grid = np.meshgrid(thetas, zs)
    r_grid, _ = np.meshgrid(radii, zs)

    vertices = (
        point_a
        + z_grid[:, :, np.newaxis] * axis_unit
        + r_grid[:, :, np.newaxis] * np.cos(theta_grid)[:, :, np.newaxis] * perp1
        + r_grid[:, :, np.newaxis] * np.sin(theta_grid)[:, :, np.newaxis] * perp2
    ).reshape(-1, 3).astype(np.float32)

    return vertices, _quad_faces(n_z, n_theta, wrap=False)
