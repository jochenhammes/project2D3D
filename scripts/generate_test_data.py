"""
Generate synthetic NIfTI test volumes with text wrapped onto a cylinder or spiral.

Usage:
    python3 scripts/generate_test_data.py
"""

import numpy as np
import nibabel as nib
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

# --- Output directory ---
OUT_DIR = Path(__file__).parent.parent / "test_data"
OUT_DIR.mkdir(exist_ok=True)

FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"

TEXT_LINES = [
    "Herculaneum  79 AD",
    "project2D3D  Test",
    "ABCDEFGHIJKLMNOP",
    "1234567890!?#*+~",
    "Row 5: lorem ipsu",
    "Row 6: consectetur",
]

# 2D image size: keep small so volumes stay manageable
IMG_W = 360   # columns = arc position (theta)
IMG_H = 120   # rows    = axis position (z)


def render_text(width: int, height: int) -> np.ndarray:
    """Render TEXT_LINES onto a white-on-black grayscale image."""
    img = Image.new("L", (width, height), color=0)
    draw = ImageDraw.Draw(img)
    try:
        font_size = max(12, height // (len(TEXT_LINES) + 1))
        font = ImageFont.truetype(FONT_PATH, font_size)
    except Exception:
        font = ImageFont.load_default()

    line_h = height // (len(TEXT_LINES) + 1)
    for i, line in enumerate(TEXT_LINES):
        draw.text((6, (i + 0.3) * line_h), line, fill=220, font=font)

    return np.array(img, dtype=np.float32) / 255.0


def _voxel_grid(shape):
    Nx, Ny, Nz = shape
    ix = np.arange(Nx, dtype=np.float32)
    iy = np.arange(Ny, dtype=np.float32)
    iz = np.arange(Nz, dtype=np.float32)
    return np.meshgrid(ix, iy, iz, indexing="ij")


def make_cylinder_volume(
    image_2d: np.ndarray,
    radius: float = 45.0,
    volume_shape: tuple = (120, 120, 120),
    thickness: float = 1.5,
) -> np.ndarray:
    """Paint image_2d onto a cylindrical shell inside a 3D volume."""
    H, W = image_2d.shape
    Nx, Ny, Nz = volume_shape
    cx, cy = Nx / 2.0, Ny / 2.0

    IX, IY, IZ = _voxel_grid(volume_shape)
    dx, dy = IX - cx, IY - cy
    r = np.sqrt(dx ** 2 + dy ** 2)

    on_shell = np.abs(r - radius) <= thickness

    # arctan2(-dx, dy) matches the unwrapper's perp1/perp2 basis
    theta = np.arctan2(-dx[on_shell], dy[on_shell])
    theta_norm = theta % (2 * np.pi) / (2 * np.pi)          # 0 … 1
    z_norm = IZ[on_shell] / (Nz - 1)

    col = (theta_norm * (W - 1)).astype(int).clip(0, W - 1)
    row = (z_norm * (H - 1)).astype(int).clip(0, H - 1)

    volume = np.zeros(volume_shape, dtype=np.float32)
    volume[on_shell] = image_2d[row, col]
    return volume


def make_spiral_volume(
    image_2d: np.ndarray,
    r_inner: float = 12.0,
    r_outer: float = 55.0,
    n_turns: float = 3.5,
    volume_shape: tuple = (130, 130, 120),
    thickness: float = 1.5,
) -> np.ndarray:
    """
    Paint image_2d onto an Archimedean spiral shell inside a 3D volume.

    The full image represents the entire unrolled scroll from inner to outer edge.
    Each turn k samples a different horizontal band of the image.
    """
    H, W = image_2d.shape
    Nx, Ny, Nz = volume_shape
    cx, cy = Nx / 2.0, Ny / 2.0

    IX, IY, IZ = _voxel_grid(volume_shape)
    dx = (IX - cx).astype(np.float32)
    dy = (IY - cy).astype(np.float32)
    r = np.sqrt(dx ** 2 + dy ** 2)
    theta_base = np.arctan2(-dx, dy) % (2 * np.pi)  # match unwrapper convention

    volume = np.zeros(volume_shape, dtype=np.float32)

    total_angle = 2 * np.pi * n_turns
    n_turns_int = int(np.ceil(n_turns))

    for k in range(n_turns_int + 1):
        theta_k = theta_base + 2 * np.pi * k          # full cumulative angle
        valid = theta_k <= total_angle
        r_spiral = r_inner + (r_outer - r_inner) * theta_k / total_angle
        on_shell = valid & (np.abs(r - r_spiral) <= thickness)

        arc_norm = theta_k[on_shell] / total_angle     # 0 … 1
        z_norm = IZ[on_shell] / (Nz - 1)

        col = (arc_norm * (W - 1)).astype(int).clip(0, W - 1)
        row = (z_norm * (H - 1)).astype(int).clip(0, H - 1)
        volume[on_shell] = image_2d[row, col]

    return volume


def save_nifti(vol: np.ndarray, path: Path):
    nib.save(nib.Nifti1Image(vol, np.eye(4)), str(path))
    mb = vol.nbytes / 1e6
    print(f"  Gespeichert: {path.name}  shape={vol.shape}  {mb:.1f} MB")


def main():
    print("Rendere Text-Bild …")
    image_2d = render_text(IMG_W, IMG_H)
    Image.fromarray((image_2d * 255).astype(np.uint8)).save(OUT_DIR / "text_original.png")
    print(f"  text_original.png  {IMG_W}×{IMG_H} px")

    print("\nErzeuge Zylinder-Volumen …")
    cyl = make_cylinder_volume(image_2d, radius=45, volume_shape=(120, 120, 120))
    save_nifti(cyl, OUT_DIR / "test_cylinder.nii")

    print("\nErzeuge Spiralen-Volumen …")
    spi = make_spiral_volume(image_2d, r_inner=12, r_outer=55, n_turns=3.5,
                             volume_shape=(130, 130, 120))
    save_nifti(spi, OUT_DIR / "test_spiral.nii")

    print("\nFertig. Dateien liegen in:", OUT_DIR)


if __name__ == "__main__":
    main()
