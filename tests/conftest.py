from pathlib import Path

import pytest
from PIL import Image


@pytest.fixture
def calibration_image() -> Path:
    return Path(__file__).parent / "fixtures" / "relief_calibration.png"


@pytest.fixture
def linear_gradient(tmp_path: Path) -> Path:
    image = Image.new("L", (5, 3))
    image.putdata([0, 64, 128, 192, 255] * 3)
    path = tmp_path / "linear-gradient.png"
    image.save(path)
    return path
