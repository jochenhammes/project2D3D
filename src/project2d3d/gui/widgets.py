import numpy as np
import napari
import matplotlib
matplotlib.use("QtAgg")
import matplotlib.pyplot as plt
from qtpy.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QDoubleSpinBox, QSpinBox, QGroupBox, QFileDialog,
    QComboBox, QStackedWidget, QSlider, QScrollArea,
)
from qtpy.QtCore import Qt


def _slider_spinbox(
    parent_layout: QVBoxLayout,
    label: str,
    min_val: float,
    max_val: float,
    default: float,
    step: float = 1.0,
    decimals: int = 0,
    on_change=None,
) -> QDoubleSpinBox | QSpinBox:
    """Add a labelled slider+spinbox row to parent_layout. Returns the spinbox."""
    group = QGroupBox(label)
    inner = QVBoxLayout(group)

    # Spinbox
    if decimals > 0:
        spin = QDoubleSpinBox()
        spin.setDecimals(decimals)
    else:
        spin = QSpinBox()
    spin.setRange(min_val, max_val)
    spin.setValue(default)
    spin.setSingleStep(step)

    # Slider (integer ticks, scaled by 1/step)
    scale = 1.0 / step
    slider = QSlider(Qt.Horizontal)
    slider.setRange(int(min_val * scale), int(max_val * scale))
    slider.setValue(int(default * scale))

    # Bidirectional link
    updating = [False]

    def slider_to_spin(v):
        if not updating[0]:
            updating[0] = True
            val = v / scale
            spin.setValue(int(round(val)) if decimals == 0 else round(val, decimals))
            updating[0] = False

    def spin_to_slider(v):
        if not updating[0]:
            updating[0] = True
            slider.setValue(int(v * scale))
            updating[0] = False

    slider.valueChanged.connect(slider_to_spin)
    spin.valueChanged.connect(spin_to_slider)

    if on_change:
        spin.valueChanged.connect(on_change)

    row = QHBoxLayout()
    row.addWidget(slider, stretch=4)
    row.addWidget(spin, stretch=1)
    inner.addLayout(row)
    parent_layout.addWidget(group)
    return spin

from project2d3d.io.nifti import load_nifti, save_nifti
from project2d3d.core.unwrap import unwrap_cylinder, unwrap_spiral
from project2d3d.core.wrap import wrap_to_cylinder
from project2d3d.core.geometry import make_cylinder_mesh, make_spiral_mesh


class CylinderWidget(QWidget):
    def __init__(self, viewer: napari.Viewer):
        super().__init__()
        self.viewer = viewer
        self._volume: np.ndarray | None = None
        self._affine: np.ndarray | None = None
        self._points_layer: napari.layers.Points | None = None
        self._cylinder_layer: napari.layers.Surface | None = None
        self._result_layer: napari.layers.Image | None = None
        self._last_png_path: str | None = None
        self._unwrapped: np.ndarray | None = None

        self._build_ui()

    def _build_ui(self):
        # Scroll area so controls are never hidden when the panel is short
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        inner_widget = QWidget()
        scroll.setWidget(inner_widget)
        outer.addWidget(scroll)
        layout = QVBoxLayout(inner_widget)
        layout.setAlignment(Qt.AlignTop)

        # --- Load ---
        load_group = QGroupBox("NIfTI laden")
        load_layout = QVBoxLayout(load_group)
        btn_load = QPushButton("Datei öffnen...")
        btn_load.clicked.connect(self._load_file)
        load_layout.addWidget(btn_load)
        layout.addWidget(load_group)

        # --- Axis ---
        axis_group = QGroupBox("Zylinderachse")
        axis_layout = QVBoxLayout(axis_group)

        btn_row = QHBoxLayout()
        self._btn_add_points = QPushButton("Achse setzen")
        self._btn_add_points.setToolTip("Zwei Punkte im Viewer platzieren (A → B)")
        self._btn_add_points.clicked.connect(self._activate_point_mode)
        btn_row.addWidget(self._btn_add_points)

        btn_reset = QPushButton("Zurücksetzen")
        btn_reset.setToolTip("Achsenpunkte löschen und neu setzen")
        btn_reset.clicked.connect(self._reset_points)
        btn_row.addWidget(btn_reset)
        axis_layout.addLayout(btn_row)

        self._axis_label = QLabel("Keine Achse definiert")
        self._axis_label.setWordWrap(True)
        axis_layout.addWidget(self._axis_label)
        layout.addWidget(axis_group)

        # --- Mode selector ---
        mode_group = QGroupBox("Modus")
        mode_layout = QVBoxLayout(mode_group)
        self._mode_combo = QComboBox()
        self._mode_combo.addItems(["Zylinder", "Spirale (Papyrus-Rolle)"])
        self._mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        mode_layout.addWidget(self._mode_combo)
        layout.addWidget(mode_group)

        # --- Stacked params ---
        self._param_stack = QStackedWidget()
        self._param_stack.addWidget(self._build_cylinder_params())
        self._param_stack.addWidget(self._build_spiral_params())
        layout.addWidget(self._param_stack)

        # --- Theta resolution (shared) ---
        theta_group = QGroupBox("Winkelauflösung (Schritte)")
        theta_layout = QHBoxLayout(theta_group)
        self._theta_spin = QSpinBox()
        self._theta_spin.setRange(36, 5000)
        self._theta_spin.setValue(360)
        self._theta_spin.setSingleStep(36)
        theta_layout.addWidget(self._theta_spin)
        layout.addWidget(theta_group)

        # --- Actions ---
        btn_unwrap = QPushButton("Abwickeln →")
        btn_unwrap.clicked.connect(self._unwrap)
        layout.addWidget(btn_unwrap)

        btn_export = QPushButton("Ergebnis als NIfTI exportieren")
        btn_export.clicked.connect(self._export_nifti)
        layout.addWidget(btn_export)

        self._status = QLabel("")
        self._status.setWordWrap(True)
        layout.addWidget(self._status)

    def _build_cylinder_params(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        self._radius_spin = _slider_spinbox(
            layout, "Radius (Voxel)",
            min_val=1, max_val=300, default=20, step=1,
            on_change=self._update_overlay,
        )
        self._rotation_spin = _slider_spinbox(
            layout, "Startwinkel / Phasenversatz (°)",
            min_val=0, max_val=360, default=0, step=1,
            on_change=self._update_overlay,
        )
        return w

    def _build_spiral_params(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        self._r_inner_spin = _slider_spinbox(
            layout, "Innenradius (Voxel)",
            min_val=1, max_val=300, default=10, step=1,
            on_change=self._update_overlay,
        )
        self._r_outer_spin = _slider_spinbox(
            layout, "Außenradius (Voxel)",
            min_val=2, max_val=300, default=60, step=1,
            on_change=self._update_overlay,
        )
        self._turns_spin = _slider_spinbox(
            layout, "Anzahl Windungen",
            min_val=0.5, max_val=20, default=3.0, step=0.5, decimals=1,
            on_change=self._update_overlay,
        )
        return w

    # ------------------------------------------------------------------
    # Mode
    # ------------------------------------------------------------------

    def _on_mode_changed(self, index: int):
        self._param_stack.setCurrentIndex(index)
        self._update_overlay()

    def _is_spiral(self) -> bool:
        return self._mode_combo.currentIndex() == 1

    # ------------------------------------------------------------------
    # File I/O
    # ------------------------------------------------------------------

    def _load_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "NIfTI öffnen", "", "NIfTI (*.nii *.nii.gz)"
        )
        if not path:
            return
        self._volume, self._affine = load_nifti(path)
        self.viewer.layers.clear()
        self._points_layer = None
        self._cylinder_layer = None
        self._result_layer = None
        self.viewer.add_image(self._volume, name="Volumen", colormap="gray")
        self._status.setText(f"Geladen: {path}\nShape: {self._volume.shape}")

    # ------------------------------------------------------------------
    # Point / axis handling
    # ------------------------------------------------------------------

    def _activate_point_mode(self):
        if self._volume is None:
            self._status.setText("Zuerst eine NIfTI-Datei laden.")
            return
        if self._points_layer is None or self._points_layer not in self.viewer.layers:
            self._points_layer = self.viewer.add_points(
                name="Zylinderachse",
                ndim=3,
                size=3,
                face_color="yellow",
                symbol="disc",
            )
            self._points_layer.events.data.connect(self._on_points_changed)
        self._points_layer.mode = "add"
        self._btn_add_points.setText("Punkt platzieren …")
        self._status.setText(
            "Punkt A klicken, dann Punkt B.\n"
            "Danach: Punkte sind verschiebbar (einfach ziehen)."
        )

    def _reset_points(self):
        if self._points_layer is not None and self._points_layer in self.viewer.layers:
            self._points_layer.data = np.zeros((0, 3), dtype=float)
            self._points_layer.mode = "add"
        if self._cylinder_layer is not None and self._cylinder_layer in self.viewer.layers:
            self.viewer.layers.remove(self._cylinder_layer)
            self._cylinder_layer = None
        self._axis_label.setText("Keine Achse definiert")
        self._btn_add_points.setText("Achse setzen")
        self._status.setText("Punkte gelöscht — bitte neue Achse setzen.")

    def _on_points_changed(self, event):
        self._update_axis_label()
        self._update_overlay()
        if self._points_layer is None:
            return
        pts = self._points_layer.data
        if len(pts) >= 2:
            # Nach dem zweiten Punkt: Select-Modus, damit Punkte ziehbar sind
            self._points_layer.mode = "select"
            self._btn_add_points.setText("Achse setzen")
            self.viewer.dims.ndisplay = 3

    def _update_axis_label(self):
        if self._points_layer is None:
            return
        pts = self._points_layer.data
        if len(pts) >= 2:
            a, b = pts[-2], pts[-1]
            self._axis_label.setText(
                f"A: {np.round(a, 1)}\n"
                f"B: {np.round(b, 1)}\n"
                f"Länge: {np.linalg.norm(b - a):.1f} Voxel"
            )
        else:
            self._axis_label.setText(f"{len(pts)} Punkt(e) gesetzt — 2 benötigt")

    def _get_axis_points(self) -> tuple[np.ndarray, np.ndarray] | None:
        if self._points_layer is None or len(self._points_layer.data) < 2:
            self._status.setText("Bitte zuerst zwei Achsenpunkte setzen.")
            return None
        pts = self._points_layer.data
        return pts[-2].copy(), pts[-1].copy()

    # ------------------------------------------------------------------
    # Overlay
    # ------------------------------------------------------------------

    def _update_overlay(self):
        result = self._get_axis_points()
        if result is None:
            return
        point_a, point_b = result

        if self._is_spiral():
            verts, faces = make_spiral_mesh(
                point_a, point_b,
                r_inner=self._r_inner_spin.value(),
                r_outer=self._r_outer_spin.value(),
                n_turns=self._turns_spin.value(),
            )
        else:
            verts, faces = make_cylinder_mesh(
                point_a, point_b,
                radius=self._radius_spin.value(),
            )

        values = np.ones(len(verts))
        if self._cylinder_layer is not None and self._cylinder_layer in self.viewer.layers:
            self._cylinder_layer.data = (verts, faces, values)
        else:
            self._cylinder_layer = self.viewer.add_surface(
                (verts, faces, values),
                name="Vorschau",
                colormap="yellow",
                opacity=0.25,
                shading="smooth",
            )

    # ------------------------------------------------------------------
    # Unwrap
    # ------------------------------------------------------------------

    def _unwrap(self):
        if self._volume is None:
            self._status.setText("Keine Datei geladen.")
            return
        result = self._get_axis_points()
        if result is None:
            return
        point_a, point_b = result
        theta_steps = self._theta_spin.value()

        self._status.setText("Berechne Abwicklung…")
        try:
            if self._is_spiral():
                unwrapped = unwrap_spiral(
                    self._volume, point_a, point_b,
                    r_inner=self._r_inner_spin.value(),
                    r_outer=self._r_outer_spin.value(),
                    n_turns=self._turns_spin.value(),
                    theta_steps=theta_steps,
                )
            else:
                unwrapped = unwrap_cylinder(
                    self._volume, point_a, point_b,
                    radius=self._radius_spin.value(),
                    theta_steps=theta_steps,
                    theta_offset_deg=self._rotation_spin.value(),
                )
        except Exception as e:
            self._status.setText(f"Fehler: {e}")
            return

        self._unwrapped = unwrapped

        # PNG speichern
        path, _ = QFileDialog.getSaveFileName(
            self, "Abgewickeltes Bild speichern", "unwrapped.png", "PNG (*.png)"
        )
        if path:
            from PIL import Image
            img_arr = unwrapped - unwrapped.min()
            if img_arr.max() > 0:
                img_arr = (img_arr / img_arr.max() * 255).astype(np.uint8)
            Image.fromarray(img_arr).save(path)
            self._last_png_path = path

        self._show_result_window(unwrapped)
        self._status.setText(
            f"Fertig. Shape: {unwrapped.shape} (z × theta)"
            + (f"\nGespeichert: {path}" if path else "")
        )

    def _show_result_window(self, unwrapped: np.ndarray):
        mode = "Spirale" if self._is_spiral() else "Zylinder"
        title = f"Abgewickeltes Bild ({mode})"
        plt.close(title)
        fig, ax = plt.subplots(num=title, figsize=(12, 5))
        fig.canvas.manager.set_window_title(f"project2D3D — {title}")
        im = ax.imshow(unwrapped, cmap="gray", aspect="auto",
                       origin="upper", interpolation="nearest")
        ax.set_xlabel("Bogenlänge (theta-Schritte)")
        ax.set_ylabel("Achse (z-Schritte)")
        ax.set_title(title)
        fig.colorbar(im, ax=ax, fraction=0.02, pad=0.01)
        fig.tight_layout()
        plt.show(block=False)
        fig.canvas.draw()

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def _export_nifti(self):
        if self._unwrapped is None:
            self._status.setText("Nichts zum Exportieren vorhanden.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Speichern als", "unwrapped.nii.gz", "NIfTI (*.nii.gz *.nii)"
        )
        if not path:
            return
        affine = np.eye(4) if self._affine is None else self._affine
        save_nifti(self._unwrapped, affine, path)
        self._status.setText(f"Gespeichert: {path}")
