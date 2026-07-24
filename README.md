# Image Relief Studio

Image Relief Studio is a desktop application for converting grayscale or color
artwork into raised or engraved 3D relief meshes for printing. It provides live
height-map feedback, an interactive 3D inspection window, multiple baseplate
shapes, high-density mesh generation, and STL/3MF export.

The interface is built with
[CustomTkinter](https://github.com/TomSchimansky/CustomTkinter), while Pillow,
NumPy, and Trimesh handle image processing and mesh generation.

## Features

- Continuous brightness-based relief
- Flat, thresholded two-level relief
- Signed design offset: negative engraves and positive raises
- Optional rectangle, rounded rectangle, ellipse, or imported SVG baseplate
- Model width, base thickness, threshold, response, smoothing, and inversion controls
- Mesh resolution from 50 to 1,600 samples on the image's longest side
- Cylindrical bending with radius, direction, and convex/concave controls
- Flat-center surface fitting with tangent curved sides
- Side-curve radius and wrap-angle controls from 0° to 180°
- Pannable and zoomable shaded height-map preview
- Interactive 3D viewer with rotation, pan, zoom, reset, and wireframe modes
- STL and 3MF export

## Screens and output

The shaded preview is intended for fast height-map editing. Select **Generate 3D
mesh**, then **Open 3D Preview**, to inspect the actual mesh used for export.

For responsiveness, the viewer creates a continuous simplified display mesh when
the export mesh exceeds 70,000 triangles. This does not modify or reduce the STL or
3MF export.

## Requirements

- Python 3.11 or newer
- Windows, macOS, or Linux with Tk support
- Enough memory and storage for the selected mesh resolution

The project has been tested on Windows with Python 3.14.

## Installation

### Windows

Open PowerShell in the project directory:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python app.py
```

After installing the dependencies, `start_app.bat` can also launch the application.
It uses whichever `python` command is available on `PATH`.

### macOS or Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python app.py
```

Some Linux distributions require Tk to be installed separately, for example
`python3-tk`.

## Basic workflow

1. Select **Open image** and load a PNG, JPEG, BMP, or TIFF file.
2. Choose **Brightness** or **Flat** relief mode.
3. Set a positive design offset for raised artwork or a negative offset for engraving.
4. Configure the baseplate and model dimensions.
5. Adjust the shaded height-map preview.
6. Select **Generate 3D mesh**.
7. Select **Open 3D Preview** and inspect the model from multiple angles.
8. Export an STL or 3MF file.
9. Verify the final file in a slicer before printing.

See [IMAGE_GENERATION_GUIDE.md](IMAGE_GENERATION_GUIDE.md) for detailed source-image
guidance and reusable prompts for an image-generation agent.

## How image brightness becomes height

In the default, non-inverted configuration:

- Black represents the lowest surface.
- Dark gray produces shallow relief.
- Light gray produces higher relief.
- White produces the maximum selected design offset.

**Brightness** mode preserves continuous grayscale transitions. The Brightness
Response setting changes how quickly middle tones rise.

**Flat** mode compares each pixel with the threshold. Pixels above the threshold
receive the full design offset, while pixels below it remain at the base height.

The **Invert image** option reverses the brightness relationship. Transparent pixels
carry no relief.

Negative offsets are limited automatically so engraving cannot cut through the
bottom of the baseplate.

## Baseplates

Built-in baseplate shapes include:

- Rectangle
- Rounded rectangle
- Ellipse
- SVG silhouette

For an SVG baseplate, use a closed, filled silhouette. The SVG is rasterized and
fitted to the model area. CairoSVG handles SVG conversion.

When **Include baseplate** is disabled, the visible artwork becomes the model
silhouette. Pure-black areas are excluded in the default brightness configuration.
Avoid one-pixel connections and extremely small isolated details.

## Surface fitting

Enable **Fit model to curved surface** to select one of two profiles.

### Cylinder

The entire model bends around one cylindrical radius. Choose the bend direction and
whether the result is convex or concave.

### Flat center + curved sides

The middle remains flat while both sides follow tangent circular arcs. Configure:

- Flat center width
- Side radius
- Side wrap angle from 0° to 180°
- Horizontal or vertical direction
- Convex or concave orientation

For this profile, the configured center and arc dimensions determine the physical
distance along the finished surface. Both image-plane axes are scaled uniformly
before bending, preventing artwork from stretching on the curved ends.

For concave curves, the selected radius must exceed the model's total thickness.

## Mesh resolution and file size

Mesh resolution is the number of samples along the input image's longest side.
Triangle count grows approximately with the square of this value.

Suggested settings:

| Purpose | Resolution |
| --- | ---: |
| Fast experimentation | 300–500 |
| Normal finished model | 600–800 |
| High-quality export | 1,000–1,200 |
| Maximum detail | 1,600 |

A full rectangular model at resolution 1,600 can exceed eight million triangles.
A binary STL of that size may approach 400 MB. Increasing mesh resolution beyond
the useful detail in the source image increases file size without creating new image
detail.

## Watertightness

The generator constructs paired top and bottom surfaces, closes exposed boundaries,
and removes corner-only contacts that would create non-manifold edges. Models below
two million triangles are currently checked for watertightness when generation
finishes.

Very dense models skip the automatic in-app audit to avoid the extra memory and time
cost. Always inspect the exported model with a slicer or dedicated mesh-validation
tool before printing, particularly when using:

- Design-only silhouettes
- Intricate SVG baseplates
- Many disconnected details
- Extreme concave curves
- Multi-million-triangle output

STL does not contain units. Image Relief Studio generates coordinates in millimeters;
select millimeters if importing into software that asks for a unit.

## 3D viewer controls

- Left drag: rotate
- Middle drag: pan
- Right drag or mouse wheel: zoom
- **Reset view**: restore the default camera
- **Wireframe**: display triangle boundaries

## Project structure

```text
.
├── app.py                     # CustomTkinter interface and 3D viewer
├── relief_mesh.py             # Height-map, mesh, bending, and export logic
├── IMAGE_GENERATION_GUIDE.md  # Source artwork instructions
├── requirements.txt           # Python dependencies
└── start_app.bat              # Windows launcher
```

## Troubleshooting

### The application does not start

Activate the virtual environment and reinstall the dependencies:

```powershell
python -m pip install -r requirements.txt
python app.py
```

### SVG import fails

Confirm that the file is a valid SVG with a filled silhouette. CairoSVG depends on
Cairo system libraries; consult the
[CairoSVG installation documentation](https://cairosvg.org/documentation/) if the
runtime cannot locate Cairo.

### The 3D viewer is slow

Close the viewer, lower mesh resolution while tuning the model, regenerate, and open
the viewer again. Use the highest resolutions for final export.

### The model looks stepped or faceted

Increase mesh resolution and confirm the source image itself has sufficient
resolution. Modest image smoothing can reduce pixel-scale roughness but can also
soften small details.

### Export consumes substantial memory or storage

Reduce mesh resolution. Triangle count and output size rise rapidly as resolution
increases; 3MF is generally much smaller than binary STL for dense meshes.

## Development check

Run a syntax check without launching the GUI:

```powershell
python -m py_compile app.py relief_mesh.py
```

Generated STL, 3MF, preview images, Python caches, and virtual environments are
excluded by `.gitignore`.

## License

Image Relief Studio is released under the [MIT License](LICENSE). You may use,
modify, distribute, sublicense, or sell copies of the software as long as the
copyright and license notices are preserved.
