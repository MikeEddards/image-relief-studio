from pathlib import Path

import numpy as np
import pytest

from relief_mesh import MeshSettings, build_mesh, export_mesh


def _settings(**changes) -> MeshSettings:
    values = {
        "resolution": 48,
        "smoothing": 0,
        "base_shape": "Rectangle",
        "width_mm": 80.0,
    }
    values.update(changes)
    return MeshSettings(**values)


def test_rectangular_calibration_mesh_is_watertight(calibration_image):
    mesh = build_mesh(calibration_image, _settings())

    assert mesh.is_watertight
    assert mesh.is_winding_consistent
    assert mesh.volume > 0
    assert len(mesh.faces) == 9212


@pytest.mark.parametrize("shape", ["Rounded rectangle", "Ellipse"])
def test_shaped_baseplates_produce_watertight_meshes(calibration_image, shape):
    mesh = build_mesh(calibration_image, _settings(base_shape=shape))

    assert mesh.is_watertight
    assert mesh.is_winding_consistent


def test_cylindrical_curve_changes_geometry_without_breaking_mesh(calibration_image):
    flat = build_mesh(calibration_image, _settings())
    curved = build_mesh(
        calibration_image,
        _settings(curve_enabled=True, curve_radius_mm=75.0),
    )

    assert curved.is_watertight
    assert curved.is_winding_consistent
    assert not np.allclose(flat.vertices, curved.vertices)


def test_flat_center_curve_supports_full_180_degree_wrap(calibration_image):
    mesh = build_mesh(
        calibration_image,
        _settings(
            curve_enabled=True,
            curve_profile="Flat center + curved sides",
            flat_center_mm=40.0,
            side_radius_mm=15.0,
            side_wrap_degrees=180.0,
        ),
    )

    assert mesh.is_watertight
    assert mesh.is_winding_consistent
    assert np.isfinite(mesh.vertices).all()


@pytest.mark.parametrize("extension", [".stl", ".3mf"])
def test_supported_export_formats_are_written(calibration_image, tmp_path, extension):
    mesh = build_mesh(calibration_image, _settings(resolution=24))
    output = tmp_path / f"calibration{extension}"

    export_mesh(mesh, output)

    assert output.is_file()
    assert output.stat().st_size > 100


def test_unsupported_export_format_is_rejected(calibration_image, tmp_path):
    mesh = build_mesh(calibration_image, _settings(resolution=24))

    with pytest.raises(ValueError, match=r"\.stl or \.3mf"):
        export_mesh(mesh, tmp_path / "calibration.obj")
