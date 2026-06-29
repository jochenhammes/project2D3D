import numpy as np
from scipy.ndimage import map_coordinates


def wrap_to_cylinder(
    image_2d: np.ndarray,
    volume_shape: tuple[int, int, int],
    point_a: np.ndarray,
    point_b: np.ndarray,
    radius: float,
    thickness: int = 1,
) -> np.ndarray:
    """
    Paint a 2D image onto a cylindrical surface inside a blank 3D volume.

    image_2d shape: (z_steps, theta_steps)
    Returns a float32 volume of shape volume_shape.
    """
    axis = point_b - point_a
    length = np.linalg.norm(axis)
    axis_unit = axis / length

    arbitrary = np.array([1.0, 0.0, 0.0])
    if abs(np.dot(axis_unit, arbitrary)) > 0.9:
        arbitrary = np.array([0.0, 1.0, 0.0])
    perp1 = np.cross(axis_unit, arbitrary)
    perp1 /= np.linalg.norm(perp1)
    perp2 = np.cross(axis_unit, perp1)

    z_steps, theta_steps = image_2d.shape
    volume = np.zeros(volume_shape, dtype=np.float32)

    thetas = np.linspace(0, 2 * np.pi, theta_steps, endpoint=False)
    zs = np.linspace(0, length, z_steps)

    for dR in range(-thickness // 2, thickness // 2 + 1):
        r = radius + dR
        theta_grid, z_grid = np.meshgrid(thetas, zs)

        pts = (
            point_a[np.newaxis, np.newaxis, :]
            + z_grid[:, :, np.newaxis] * axis_unit[np.newaxis, np.newaxis, :]
            + r * np.cos(theta_grid)[:, :, np.newaxis] * perp1[np.newaxis, np.newaxis, :]
            + r * np.sin(theta_grid)[:, :, np.newaxis] * perp2[np.newaxis, np.newaxis, :]
        )

        xi = np.round(pts[..., 0]).astype(int)
        yi = np.round(pts[..., 1]).astype(int)
        zi = np.round(pts[..., 2]).astype(int)

        mask = (
            (xi >= 0) & (xi < volume_shape[0])
            & (yi >= 0) & (yi < volume_shape[1])
            & (zi >= 0) & (zi < volume_shape[2])
        )
        volume[xi[mask], yi[mask], zi[mask]] = image_2d[
            np.where(mask)[0], np.where(mask)[1]
        ]

    return volume
