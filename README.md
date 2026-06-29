# project2D3D

Desktop-Anwendung zur zylindrischen und spiralförmigen Abwicklung von 3D-Voxeldaten (NIfTI-Format), z. B. aus CT-Scannern. Inspiriert vom [Vesuvius Challenge](https://scrollprize.org) Projekt zur virtuellen Entrollung von Herculaneum-Papyri.

## Funktionen

- **Zylinder-Abwicklung** — projiziert eine zylindrische Oberfläche aus einem 3D-Volumen in ein 2D-Bild
- **Spiralen-Abwicklung** — entrollt eine archimedische Spirale (gerollter Papyrus / Schriftrolle) aus einem 3D-Volumen
- **Live-Vorschau** — interaktiver 3D-Viewer mit Overlay der definierten Zylinder- oder Spiralgeometrie
- **Achsendefinition per Maus** — zwei Punkte im 3D-Viewer setzen und verschieben
- **Phasenversatz** — Startwinkel des Abwickelns frei einstellbar (wichtig für Spiralen)
- **PNG-Export** — abgewickeltes Bild wird direkt als PNG gespeichert
- **NIfTI-Export** — Ergebnis optional als NIfTI-Datei speichern
- **Synthetische Testdaten** — Generator erzeugt Text auf Zylinder und Spirale zum Testen

## Voraussetzungen

- Python 3.10+
- Ubuntu 22.04+ (oder andere Linux-Distribution mit X11/Wayland)

## Installation

```bash
git clone https://github.com/hammesj/project2D3D.git
cd project2D3D

# Abhängigkeiten installieren
python3 -m pip install --user -e .
```

Beim ersten Start werden alle Abhängigkeiten (napari, nibabel, scipy, etc.) automatisch mit installiert.

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
4. Punkte können danach durch **Ziehen** verschoben werden (2D und 3D)
5. **„Zurücksetzen"** löscht beide Punkte

### 3. Modus wählen

| Modus | Beschreibung | Parameter |
|---|---|---|
| **Zylinder** | Feste Zylinderoberfläche | Radius |
| **Spirale (Papyrus-Rolle)** | Archimedische Spirale | Innenradius, Außenradius, Anzahl Windungen |

Alle Parameter haben Slider für schnelle und Spinboxen für präzise Eingabe.

### 4. Phasenversatz

Der **Startwinkel / Phasenversatz**-Slider (0–360°) dreht den Startpunkt des Abwickelns um die Achse. Besonders wichtig im Spiralmodus, um den Anfang des Dokuments zu finden. Die Vorschau im 3D-Viewer aktualisiert sich live.

### 5. Abwickeln

**„Abwickeln →"** berechnet das Ergebnis:
- Ein **Speicherdialog** für das PNG erscheint
- Das abgewickelte Bild öffnet sich in einem **separaten Matplotlib-Fenster**
- Optional: **„Ergebnis als NIfTI exportieren"** für die Weiterverarbeitung

## Algorithmus

### Zylindrische Abwicklung

Für jeden Punkt `(θ, z)` auf der Zylinderoberfläche:

```
position = achsenmittelpunkt + z·achse + r·cos(θ+φ)·perp1 + r·sin(θ+φ)·perp2
```

Der Voxelwert an dieser Position wird trilinear interpoliert (`scipy.ndimage.map_coordinates`).

### Spiralförmige Abwicklung (Papyrus-Rolle)

Der Radius wächst linear mit dem Winkel (archimedische Spirale):

```
r(θ) = r_innen + (r_außen - r_innen) · θ / (2π · n_windungen)
```

Zur Robustheit wird eine **Max-Intensity-Projektion** über ±3 Voxel in Radialrichtung berechnet. Das kompensiert dünne Datenschichten und kleine Parameterabweichungen.

## Testdaten generieren

```bash
python3 scripts/generate_test_data.py
```

Erzeugt in `test_data/`:

| Datei | Beschreibung | Empfohlene Parameter |
|---|---|---|
| `test_cylinder.nii` | Text auf Zylinder | Radius = 45, Achse durch Bildmitte (Z) |
| `test_spiral.nii` | Text auf Spirale | r\_innen = 12, r\_außen = 55, Windungen = 3.5 |
| `text_original.png` | Original-Textbild | — |

## Projektstruktur

```
project2D3D/
├── src/project2d3d/
│   ├── main.py          # Einstiegspunkt
│   ├── core/
│   │   ├── unwrap.py    # Abwickelungsalgorithmen (Zylinder + Spirale)
│   │   ├── wrap.py      # 2D → 3D Aufwickeln
│   │   └── geometry.py  # Mesh-Generierung für 3D-Vorschau
│   ├── gui/
│   │   └── widgets.py   # Napari-Seitenpanel (Qt)
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
| `numpy` / `scipy` | Koordinatentransformationen, Interpolation |
| `scikit-image` | Bildverarbeitung |
| `matplotlib` | Ergebnisanzeige im separaten Fenster |
| `Pillow` | PNG-Export |
