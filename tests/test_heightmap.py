import numpy as np
from PIL import Image

from relief_mesh import MeshSettings, _base_mask, _fit_size, prepare_heightmap


def test_calibration_fixture_is_a_readable_full_range_png(calibration_image):
    with Image.open(calibration_image) as image:
        pixels = np.asarray(image)
        assert image.format == "PNG"
        assert image.mode == "RGB"
        assert image.size == (1254, 1254)
        assert int(pixels.min()) == 0
        assert int(pixels.max()) == 255


def test_fit_size_preserves_aspect_ratio():
    assert _fit_size(Image.new("L", (200, 100)), 50) == (50, 25)
    assert _fit_size(Image.new("L", (100, 200)), 50) == (25, 50)


def test_brightness_mode_maps_black_to_base_and_white_to_peak(linear_gradient):
    settings = MeshSettings(
        resolution=5,
        smoothing=0,
        base_shape="Rectangle",
        base_thickness_mm=2.0,
        design_offset_mm=3.0,
    )
    top, mask, _ = prepare_heightmap(linear_gradient, settings)

    assert mask.all()
    assert top.shape == (14, 24)
    assert float(top[1, 0]) == 2.0
    assert float(top[1, -1]) == 5.0
    assert np.all(np.diff(top[1]) >= 0)


def test_flat_mode_produces_only_two_heights(linear_gradient):
    settings = MeshSettings(
        resolution=5,
        smoothing=0,
        relief_mode="Flat",
        threshold=0.5,
        base_shape="Rectangle",
        base_thickness_mm=2.0,
        design_offset_mm=3.0,
    )
    top, _, _ = prepare_heightmap(linear_gradient, settings)

    assert set(np.unique(top).tolist()) == {2.0, 5.0}
    assert np.all(np.diff(top[1]) >= 0)
    assert np.count_nonzero(top[1] == 2.0) == 12
    assert np.count_nonzero(top[1] == 5.0) == 12


def test_invert_reverses_the_height_response(linear_gradient):
    normal, _, _ = prepare_heightmap(
        linear_gradient,
        MeshSettings(resolution=5, smoothing=0, base_shape="Rectangle"),
    )
    inverted, _, _ = prepare_heightmap(
        linear_gradient,
        MeshSettings(resolution=5, smoothing=0, invert=True, base_shape="Rectangle"),
    )

    np.testing.assert_allclose(normal + inverted, 6.0, atol=0.01)


def test_supported_base_masks_have_expected_geometry():
    rectangle = _base_mask((21, 15), MeshSettings(base_shape="Rectangle"))
    ellipse = _base_mask((21, 15), MeshSettings(base_shape="Ellipse"))
    rounded = _base_mask((21, 15), MeshSettings(base_shape="Rounded rectangle"))

    assert rectangle.all()
    assert ellipse[7, 10] and not ellipse[0, 0]
    assert rounded[7, 10] and not rounded[0, 0]
    assert ellipse.sum() < rounded.sum() < rectangle.sum()


def test_generated_calibration_image_exercises_full_height_range(calibration_image):
    settings = MeshSettings(
        resolution=96,
        smoothing=0,
        base_shape="Rectangle",
        base_thickness_mm=2.0,
        design_offset_mm=2.0,
    )
    top, mask, _ = prepare_heightmap(calibration_image, settings)

    assert top.shape == (96, 96)
    assert mask.all()
    assert float(top.min()) == 2.0
    assert float(top.max()) == 4.0
    assert np.count_nonzero((top > 2.1) & (top < 3.9)) > top.size // 4
