from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import numpy as np
from PIL import Image, ImageOps, ImageDraw
import trimesh


ReliefMode = Literal["Brightness", "Flat"]
BaseShape = Literal["Rectangle", "Rounded rectangle", "Ellipse", "SVG"]


@dataclass(slots=True)
class MeshSettings:
    width_mm: float = 80.0
    base_thickness_mm: float = 2.0
    design_offset_mm: float = 2.0
    resolution: int = 180
    relief_mode: ReliefMode = "Brightness"
    threshold: float = 0.5
    response: float = 1.0
    smoothing: float = 1.0
    invert: bool = False
    use_baseplate: bool = True
    base_shape: BaseShape = "Rounded rectangle"
    corner_radius: float = 0.10
    svg_path: str = ""
    curve_enabled: bool = False
    curve_profile: Literal["Cylinder", "Flat center + curved sides"] = "Cylinder"
    curve_radius_mm: float = 75.0
    curve_axis: Literal["Horizontal", "Vertical"] = "Horizontal"
    curve_side: Literal["Convex", "Concave"] = "Convex"
    side_radius_mm: float = 15.0
    flat_center_mm: float = 50.0
    side_wrap_degrees: float = 90.0


def _fit_size(image: Image.Image, max_side: int) -> tuple[int, int]:
    w, h = image.size
    scale = max_side / max(w, h)
    return max(3, round(w * scale)), max(3, round(h * scale))


def _gaussian_blur_float(image: np.ndarray, sigma: float) -> np.ndarray:
    """Blur a float height field without reducing it back to 8-bit precision."""
    sigma = float(sigma)
    if sigma <= 0:
        return image
    radius = max(1, int(np.ceil(3.0 * sigma)))
    positions = np.arange(-radius, radius + 1, dtype=np.float32)
    kernel = np.exp(-(positions * positions) / (2.0 * sigma * sigma))
    kernel /= kernel.sum()

    horizontal = np.pad(image, ((0, 0), (radius, radius)), mode="edge")
    horizontal = np.stack(
        [np.convolve(row, kernel, mode="valid") for row in horizontal]
    )
    vertical = np.pad(horizontal, ((radius, radius), (0, 0)), mode="edge")
    return np.stack(
        [np.convolve(column, kernel, mode="valid") for column in vertical.T],
        axis=1,
    ).astype(np.float32, copy=False)


def _resize_grayscale_float(source: Image.Image, size: tuple[int, int]) -> np.ndarray:
    """Resize luminance as floats so interpolation can create sub-8-bit heights."""
    if source.mode in {"I", "F", "I;16", "I;16L", "I;16B"}:
        values = np.asarray(source, dtype=np.float32)
        if source.mode != "F":
            maximum = float(np.iinfo(np.asarray(source).dtype).max)
            values /= maximum
        else:
            finite = values[np.isfinite(values)]
            if finite.size and (finite.min() < 0.0 or finite.max() > 1.0):
                span = float(finite.max() - finite.min())
                values = (values - float(finite.min())) / span if span else np.zeros_like(values)
        grayscale = Image.fromarray(np.clip(values, 0.0, 1.0), mode="F")
    else:
        grayscale = ImageOps.grayscale(source.convert("RGB")).convert("F")
        grayscale = grayscale.point(lambda value: value / 255.0)
    resized = grayscale.resize(size, Image.Resampling.LANCZOS)
    return np.clip(np.asarray(resized, dtype=np.float32), 0.0, 1.0)


def _base_mask(size: tuple[int, int], settings: MeshSettings) -> np.ndarray:
    w, h = size
    if not settings.use_baseplate:
        return np.ones((h, w), dtype=bool)
    if settings.base_shape == "Rectangle":
        return np.ones((h, w), dtype=bool)
    if settings.base_shape == "Ellipse":
        canvas = Image.new("L", size, 0)
        ImageDraw.Draw(canvas).ellipse((0, 0, w - 1, h - 1), fill=255)
        return np.asarray(canvas) > 0
    if settings.base_shape == "Rounded rectangle":
        canvas = Image.new("L", size, 0)
        radius = max(1, round(min(w, h) * settings.corner_radius))
        ImageDraw.Draw(canvas).rounded_rectangle((0, 0, w - 1, h - 1), radius, fill=255)
        return np.asarray(canvas) > 0
    if settings.base_shape == "SVG":
        if not settings.svg_path:
            raise ValueError("Choose an SVG file for the SVG baseplate shape.")
        try:
            import resvg_py
            from io import BytesIO
            svg_string = Path(settings.svg_path).read_text(encoding="utf-8")
            png = resvg_py.svg_to_bytes(
                svg_string=svg_string, width=w, height=h
            )
            svg_image = Image.open(BytesIO(png)).convert("RGBA")
        except Exception as exc:
            raise ValueError(f"Could not rasterize the SVG: {exc}") from exc
        alpha = np.asarray(svg_image.getchannel("A"))
        return alpha > 127
    raise ValueError(f"Unknown base shape: {settings.base_shape}")


def prepare_heightmap(image_path: str | Path, settings: MeshSettings):
    with Image.open(image_path) as opened:
        source = opened.copy()
    size = _fit_size(source, max(24, int(settings.resolution)))
    rgba = source.convert("RGBA").resize(size, Image.Resampling.LANCZOS)
    alpha_image = source.getchannel("A").convert("F") if "A" in source.getbands() else None
    if alpha_image is None:
        alpha = np.ones((size[1], size[0]), dtype=np.float32)
    else:
        alpha = np.asarray(
            alpha_image.resize(size, Image.Resampling.LANCZOS), dtype=np.float32
        ) / 255.0
        alpha = np.clip(alpha, 0.0, 1.0)
    gray = _resize_grayscale_float(source, size)
    if settings.smoothing > 0:
        gray = _gaussian_blur_float(gray, settings.smoothing)
    if settings.invert:
        gray = 1.0 - gray

    # Transparent pixels carry no relief. Opaque black is still valid artwork.
    signal = np.clip(gray * alpha, 0.0, 1.0)
    if settings.relief_mode == "Flat":
        signal = (signal >= settings.threshold).astype(np.float32)
    else:
        signal = np.power(signal, max(0.05, settings.response))

    mask = _base_mask(size, settings)
    if not settings.use_baseplate:
        # No plate: use the artwork itself as the silhouette. This also removes
        # an opaque black background like the one in the sample artwork.
        mask = (alpha > 0.02) & (signal > (0.0 if settings.relief_mode == "Flat" else 0.02))
    if not np.any(mask):
        raise ValueError("The selected image/base shape produced an empty model.")

    base = max(0.2, settings.base_thickness_mm)
    offset = settings.design_offset_mm
    # Preserve a printable floor for engraving.
    offset = max(offset, -(base - 0.15))
    top = base + signal * offset
    top = np.maximum(top, 0.15)
    top[~mask] = 0.0
    return top, mask, rgba


def build_mesh(image_path: str | Path, settings: MeshSettings) -> trimesh.Trimesh:
    top, mask, _ = prepare_heightmap(image_path, settings)
    rows, cols = top.shape
    image = Image.open(image_path)
    aspect = image.height / image.width
    width = float(settings.width_mm)
    height = width * aspect
    xs = np.linspace(-width / 2, width / 2, cols)
    ys = np.linspace(height / 2, -height / 2, rows)

    valid = np.flatnonzero(mask.ravel())
    index = np.full(mask.size, -1, dtype=np.int64)
    index[valid] = np.arange(len(valid))
    rr, cc = np.unravel_index(valid, mask.shape)
    top_vertices = np.column_stack((xs[cc], ys[rr], top[rr, cc]))
    bottom_vertices = np.column_stack((xs[cc], ys[rr], np.zeros(len(valid))))
    vertices = np.vstack((top_vertices, bottom_vertices))
    n = len(valid)

    # Vectorized cell construction keeps million-triangle meshes practical.
    active = mask[:-1, :-1] & mask[:-1, 1:] & mask[1:, 1:] & mask[1:, :-1]
    # Two regions touching at only one corner create a non-manifold vertical edge.
    # Remove the smaller, lower-priority corner cell until every contact has width.
    for _ in range(4):
        nw, ne, sw, se = active[:-1, :-1], active[:-1, 1:], active[1:, :-1], active[1:, 1:]
        drop_se = nw & se & ~ne & ~sw
        drop_sw = ne & sw & ~nw & ~se
        if not drop_se.any() and not drop_sw.any():
            break
        se[drop_se] = False
        sw[drop_sw] = False
    cell_r, cell_c = np.nonzero(active)
    a = index[cell_r * cols + cell_c]
    b = index[cell_r * cols + cell_c + 1]
    d = index[(cell_r + 1) * cols + cell_c + 1]
    e = index[(cell_r + 1) * cols + cell_c]
    faces = [
        np.column_stack((a, e, b)), np.column_stack((b, e, d)),
        np.column_stack((a + n, b + n, e + n)),
        np.column_stack((b + n, d + n, e + n)),
    ]

    # Find the four exposed sides of active cells and add consistently oriented walls.
    above = np.zeros_like(active); above[1:] = active[:-1]
    below = np.zeros_like(active); below[:-1] = active[1:]
    left = np.zeros_like(active); left[:, 1:] = active[:, :-1]
    right = np.zeros_like(active); right[:, :-1] = active[:, 1:]
    boundary_specs = (
        (active & ~above, "top"), (active & ~right, "right"),
        (active & ~below, "bottom"), (active & ~left, "left"),
    )
    for boundary, edge in boundary_specs:
        br, bc = np.nonzero(boundary)
        ia = index[br * cols + bc]
        ib = index[br * cols + bc + 1]
        id_ = index[(br + 1) * cols + bc + 1]
        ie = index[(br + 1) * cols + bc]
        if edge == "top": u, v = ia, ib
        elif edge == "right": u, v = ib, id_
        elif edge == "bottom": u, v = id_, ie
        else: u, v = ie, ia
        faces.extend((np.column_stack((u, v, v + n)),
                      np.column_stack((u, v + n, u + n))))

    mesh = trimesh.Trimesh(vertices=vertices, faces=np.vstack(faces), process=False)
    if settings.curve_enabled:
        if settings.curve_profile == "Flat center + curved sides":
            _bend_flat_center_sides(
                mesh, settings.flat_center_mm, settings.side_radius_mm,
                settings.side_wrap_degrees, settings.curve_axis, settings.curve_side
            )
        else:
            _bend_mesh(mesh, settings.curve_radius_mm, settings.curve_axis,
                       settings.curve_side)
    return mesh


def _bend_mesh(mesh: trimesh.Trimesh, radius_mm: float, axis: str, side: str) -> None:
    """Bend a flat XY mesh around a cylinder while preserving radial thickness."""
    radius = max(1.0, float(radius_mm))
    vertices = mesh.vertices.copy()
    horizontal = axis == "Horizontal"
    along = vertices[:, 0] if horizontal else vertices[:, 1]
    height = vertices[:, 2]
    span = float(np.ptp(along))
    if span / radius >= np.pi * 1.9:
        raise ValueError(
            "The selected radius wraps the model nearly all the way around the "
            "cylinder. Increase the curve radius or reduce the model size."
        )
    if side == "Concave" and float(np.max(height)) >= radius:
        raise ValueError(
            "For a concave bend, the curve radius must be greater than the total "
            "model thickness. Increase the radius."
        )
    theta = along / radius
    sine, cosine = np.sin(theta), np.cos(theta)

    if side == "Convex":
        bent_along = (radius + height) * sine
        bent_z = (radius + height) * cosine - radius
    else:
        # The cylinder center is on the opposite side. Keeping the local normal
        # pointed toward +Z makes the printable relief remain on the front face.
        bent_along = (radius - height) * sine
        bent_z = radius - (radius - height) * cosine

    if horizontal:
        vertices[:, 0] = bent_along
    else:
        vertices[:, 1] = bent_along
    vertices[:, 2] = bent_z
    mesh.vertices = vertices


def _bend_flat_center_sides(
    mesh: trimesh.Trimesh,
    flat_center_mm: float,
    radius_mm: float,
    wrap_degrees: float,
    axis: str,
    side: str,
) -> None:
    """Map artwork by surface distance onto a flat center and tangent side arcs."""
    flat_width = max(1.0, float(flat_center_mm))
    radius = max(1.0, float(radius_mm))
    wrap = np.deg2rad(np.clip(float(wrap_degrees), 0.0, 180.0))
    vertices = mesh.vertices.copy()
    horizontal = axis == "Horizontal"
    along_index, cross_index = (0, 1) if horizontal else (1, 0)
    along = vertices[:, along_index]
    original_span = float(np.ptp(along))
    if original_span <= 0:
        raise ValueError("The model has no width along the selected bend direction.")

    height = vertices[:, 2]
    if side == "Concave" and float(np.max(height)) >= radius:
        raise ValueError(
            "For a concave side curve, the side radius must be greater than the "
            "total model thickness. Increase the side radius."
        )

    # These dimensions define the required distance measured along the finished
    # surface. Scale both image-plane axes equally so the artwork is not stretched.
    total_surface = flat_width + 2.0 * radius * wrap
    scale = total_surface / original_span
    vertices[:, along_index] *= scale
    vertices[:, cross_index] *= scale
    surface = vertices[:, along_index]

    half_flat = flat_width / 2.0
    curved = np.abs(surface) > half_flat
    direction = np.sign(surface[curved])
    distance = np.abs(surface[curved]) - half_flat
    theta = np.minimum(distance / radius, wrap)
    sine, cosine = np.sin(theta), np.cos(theta)
    local_height = height[curved]

    if side == "Convex":
        curved_along = half_flat + (radius + local_height) * sine
        curved_z = (radius + local_height) * cosine - radius
    else:
        curved_along = half_flat + (radius - local_height) * sine
        curved_z = radius - (radius - local_height) * cosine

    vertices[curved, along_index] = direction * curved_along
    vertices[curved, 2] = curved_z
    mesh.vertices = vertices


def export_mesh(mesh: trimesh.Trimesh, path: str | Path) -> None:
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix == ".stl":
        mesh.export(path, file_type="stl")
    elif suffix == ".3mf":
        # Trimesh writes standards-compliant 3MF packages when the exporter is present.
        mesh.export(path, file_type="3mf")
    else:
        raise ValueError("Export filename must end in .stl or .3mf")
