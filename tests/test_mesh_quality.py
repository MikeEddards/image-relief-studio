from pathlib import Path

import numpy as np
import pytest
import trimesh
from PIL import Image

from relief_mesh import MeshSettings, build_mesh, export_mesh


def _smooth_surface(path: Path, size: int) -> Path:
    """Write a precisely smooth grayscale surface without generator artifacts."""
    axis = np.linspace(-1.0, 1.0, size, dtype=np.float64)
    x, y = np.meshgrid(axis, axis)
    # A broad dome plus gentle waves exercises curvature in both mesh directions.
    height = (
        0.48
        + 0.25 * np.exp(-2.5 * (x * x + y * y))
        + 0.12 * np.sin(np.pi * x) * np.cos(np.pi * y)
    )
    pixels = np.clip(np.rint(height * 255.0), 0, 255).astype(np.uint8)
    Image.fromarray(pixels, mode="L").save(path)
    return path


def _quality_settings(resolution: int) -> MeshSettings:
    return MeshSettings(
        resolution=resolution,
        smoothing=0,
        base_shape="Rectangle",
        width_mm=80.0,
        base_thickness_mm=2.0,
        design_offset_mm=3.0,
    )


def _assert_mesh_integrity(mesh: trimesh.Trimesh) -> None:
    assert np.isfinite(mesh.vertices).all()
    assert np.isfinite(mesh.face_normals).all()
    assert mesh.is_watertight
    assert mesh.is_winding_consistent
    assert mesh.body_count == 1
    assert mesh.volume > 0
    assert float(mesh.area_faces.min()) > 1e-10
    assert bool(mesh.unique_faces().all())


def test_smooth_input_has_no_triangulation_ridges(tmp_path):
    image_path = _smooth_surface(tmp_path / "smooth-surface.png", 192)
    settings = _quality_settings(192)
    settings.smoothing = 1.0
    mesh = build_mesh(image_path, settings)
    _assert_mesh_integrity(mesh)

    cell_count = 191 * 191
    first_triangles = mesh.face_normals[:cell_count]
    second_triangles = mesh.face_normals[cell_count : 2 * cell_count]
    diagonal_alignment = np.einsum("ij,ij->i", first_triangles, second_triangles)
    diagonal_angles = np.degrees(np.arccos(np.clip(diagonal_alignment, -1.0, 1.0)))

    # Paired triangles cover the same image cell. Float-domain smoothing should
    # remove the visible diagonal ridges caused by 8-bit height steps.
    assert float(np.percentile(diagonal_angles, 99.9)) < 0.35
    assert float(diagonal_angles.max()) < 0.40


@pytest.mark.parametrize("extension", [".stl", ".3mf"])
def test_exported_mesh_reopens_as_one_watertight_body(tmp_path, extension):
    image_path = _smooth_surface(tmp_path / "export-surface.png", 96)
    output = tmp_path / f"quality{extension}"
    export_mesh(build_mesh(image_path, _quality_settings(96)), output)

    # STL stores independent triangles, so normal import processing must merge
    # coincident vertices before topology can be assessed.
    loaded = trimesh.load(output, force="mesh", process=True)

    _assert_mesh_integrity(loaded)


@pytest.mark.local_quality
def test_multi_million_triangle_mesh_on_local_hardware(calibration_image):
    # 724 square samples produce exactly 2,096,700 faces for a rectangular plate.
    resolution = 724
    mesh = build_mesh(calibration_image, _quality_settings(resolution))

    assert len(mesh.faces) == 4 * resolution * resolution - 4
    assert len(mesh.faces) > 2_000_000
    _assert_mesh_integrity(mesh)
