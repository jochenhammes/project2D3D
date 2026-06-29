import numpy as np
import nibabel as nib
from pathlib import Path


def load_nifti(path: str | Path) -> tuple[np.ndarray, np.ndarray]:
    """Load a NIfTI file. Returns (voxel_data, affine)."""
    img = nib.load(str(path))
    data = np.asarray(img.dataobj, dtype=np.float32)
    return data, img.affine


def save_nifti(data: np.ndarray, affine: np.ndarray, path: str | Path) -> None:
    """Save a numpy array as NIfTI file."""
    img = nib.Nifti1Image(data.astype(np.float32), affine)
    nib.save(img, str(path))
