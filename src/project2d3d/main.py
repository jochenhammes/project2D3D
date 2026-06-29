import sys
import napari
from project2d3d.gui.widgets import CylinderWidget


def main():
    viewer = napari.Viewer(title="project2D3D — Zylindrisches Abwickeln")
    widget = CylinderWidget(viewer)
    viewer.window.add_dock_widget(widget, name="Zylinder-Werkzeuge", area="right")
    napari.run()


if __name__ == "__main__":
    main()
