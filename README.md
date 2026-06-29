# project2D3D

Desktop-Anwendung zur zylindrischen und spiralförmigen Abwicklung von 3D-Voxeldaten (NIfTI-Format), z. B. aus CT-Scannern. Inspiriert vom [Vesuvius Challenge](https://scrollprize.org) Projekt zur virtuellen Entrollung von Herculaneum-Papyri.

## Funktionen

- **Zylinder-Abwicklung** — projiziert eine zylindrische Oberfläche aus einem 3D-Volumen in ein 2D-Bild
- **Spiralen-Abwicklung** — entrollt eine archimedische Spirale (gerollter Papyrus / Schriftrolle) aus einem 3D-Volumen
- **3D-Geometrie-Vorschau** — interaktiver Overlay der definierten Zylinder- oder Spiralform im 3D-Viewer, aktualisiert sich live beim Verschieben von Punkten und Sliders
- **Achsendefinition per Maus** — zwei Punkte im Viewer setzen und jederzeit verschieben (2D und 3D)
- **Phasenversatz** — Startwinkel des Abwickelns frei einstellbar (0–360°), besonders wichtig für Spiralen
- **Projektionsmodi** — Max (MIP), Min (MinIP) oder Mittelwert über einen radialen Bereich; kompensiert dünne Datenschichten und Parameterabweichungen
- **Live-Vorschau** — automatische Neuberechnung der Abwicklung bei Parameteränderungen (Hintergrund-Thread, 500 ms Debounce)
- **PNG-Export** — abgewickeltes Bild direkt als PNG speichern
- **NIfTI-Export** — Ergebnis optional als NIfTI-Datei speichern
- **Synthetische Testdaten** — Generator erzeugt Text auf Zylinder und Spirale zum Testen und Validieren

## Voraussetzungen

- Python 3.10+
- Ubuntu 22.04+ (oder andere Linux-Distribution mit X11/Wayland)

## Installation

```bash
git clone https://github.com/jochenhammes/project2D3D.git
cd project2D3D

python3 -m pip install --user -e .
```

## Starten

```bash
python3 -m project2d3d.main
```

## Bedienung

### 1. NIfTI-Datei laden

Rechtes Panel → **„Datei öffnen…"** → NIfTI-Datei auswählen (`.nii` oder `.nii.gz`).

### 2. Zylinderachse definieren

1. **„Achse setzen"** klicken
2. Im Viewer **Punkt A** und dann **Punkt B** klicken — die Verbindungslinie definiert die Rotationsachse
3. Nach dem zweiten Punkt wechselt der Viewer automatisch in den **3D-Modus**
4. Punkte können danach durch **Ziehen** verschoben werden (in 2D- und 3D-Ansicht)
5. **„Zurücksetzen"** löscht beide Punkte für einen Neustart

### 3. Modus und Parameter

| Modus | Parameter |
|---|---|
| **Zylinder** | Radius (Voxel) |
| **Spirale (Papyrus-Rolle)** | Innenradius, Außenradius, Anzahl Windungen |

Alle Radiusparameter haben **Slider** (schnell) und **Spinboxen** (präzise), die synchron gehalten werden.

### 4. Startwinkel / Phasenversatz

Der Slider (0–360°) dreht den Startpunkt der Abwicklung um die Achse. Im Spiralmodus besonders wichtig, um den Beginn des Dokuments zu finden. Die 3D-Vorschau dreht sich dabei live mit.

### 5. Projektionsmodus

Bestimmt, wie über einen kleinen radialen Bereich (±1 Voxel beim Zylinder, ±3 Voxel bei der Spirale) projiziert wird:

| Modus | Anwendung |
|---|---|
| **Max (MIP)** | Helle Strukturen auf dunklem Hintergrund (Standard) |
| **Min (MinIP)** | Dunkle Strukturen auf hellem Hintergrund (z. B. Tinte auf Papyrus) |
| **Mittelwert** | Glattere Darstellung, reduziert Rauschen |

### 6. Abwickeln

**„Abwickeln →"** berechnet das Ergebnis manuell:
- Ein **Speicherdialog** für das PNG erscheint
- Das abgewickelte Bild öffnet sich in einem **separaten Matplotlib-Fenster**

**„Live"-Checkbox** neben dem Button: Aktiviert die automatische Neuberechnung — jede Parameteränderung löst nach 500 ms einen neuen Berechnungs-Thread aus. Das Matplotlib-Fenster aktualisiert sich automatisch.

Optional: **„Ergebnis als NIfTI exportieren"** für die Weiterverarbeitung.

## Algorithmus

### Zylindrische Abwicklung

Für jeden Punkt `(θ, z)` auf der Zylinderoberfläche:

```
position = achsenmittelpunkt + z·achse + r·cos(θ+φ)·perp1 + r·sin(θ+φ)·perp2
```

`perp1` und `perp2` sind zwei zur Achse orthogonale Einheitsvektoren, `φ` ist der Phasenversatz.  
Der Voxelwert wird trilinear interpoliert (`scipy.ndimage.map_coordinates`).

### Spiralförmige Abwicklung (Papyrus-Rolle)

Der Radius wächst linear mit dem kumulativen Winkel (archimedische Spirale):

```
r(θ) = r_innen + (r_außen - r_innen) · (θ − φ) / (2π · n_windungen)
```

Zur Robustheit wird über mehrere Radii in Radialrichtung projiziert (Max/Min/Mittelwert). Das kompensiert dünne Datenschichten und kleine Parameterabweichungen.

## Testdaten generieren

```bash
python3 scripts/generate_test_data.py
```

Erzeugt in `test_data/`:

| Datei | Beschreibung | Empfohlene Parameter |
|---|---|---|
| `test_cylinder.nii` | Text auf Zylinder | Radius = 45, Achse durch Bildmitte (Z) |
| `test_spiral.nii` | Text auf Spirale | r\_innen = 12, r\_außen = 55, Windungen = 3.5 |
| `text_original.png` | Original-Textbild zum Vergleich | — |

## Projektstruktur

```
project2D3D/
├── src/project2d3d/
│   ├── main.py          # Einstiegspunkt
│   ├── core/
│   │   ├── unwrap.py    # Abwickelungsalgorithmen (Zylinder + Spirale, MIP/MinIP)
│   │   ├── wrap.py      # 2D → 3D Aufwickeln
│   │   └── geometry.py  # Mesh-Generierung für 3D-Vorschau
│   ├── gui/
│   │   └── widgets.py   # Napari-Seitenpanel (Qt, Live-Vorschau, Slider)
│   └── io/
│       └── nifti.py     # NIfTI laden/speichern
├── scripts/
│   └── generate_test_data.py
├── test_data/
│   └── text_original.png
└── pyproject.toml
```

## Abhängigkeiten

| Paket | Zweck |
|---|---|
| `napari` | 3D/2D-Viewer und Plugin-Framework |
| `nibabel` | NIfTI-Dateiformat |
| `numpy` / `scipy` | Koordinatentransformationen, trilineare Interpolation |
| `scikit-image` | Bildverarbeitung |
| `matplotlib` | Ergebnisanzeige im separaten Fenster |
| `Pillow` | PNG-Export |
