from __future__ import annotations

import sys
import uuid
from pathlib import Path

import numpy as np
import pytest
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


@pytest.fixture()
def test_workspace() -> Path:
    path = ROOT / "backend" / "data" / "test_tmp" / uuid.uuid4().hex
    path.mkdir(parents=True, exist_ok=True)
    return path


@pytest.fixture()
def sample_jpeg(test_workspace: Path) -> Path:
    h, w = 240, 360
    y, x = np.mgrid[0:h, 0:w]
    r = (x / w * 255).astype(np.uint8)
    g = (y / h * 255).astype(np.uint8)
    b = np.full((h, w), 120, dtype=np.uint8)
    arr = np.stack([r, g, b], axis=-1)
    path = test_workspace / "sample.jpg"
    Image.fromarray(arr, mode="RGB").save(path, format="JPEG", quality=95)
    return path


@pytest.fixture()
def sample_raw_path(test_workspace: Path) -> Path:
    path = test_workspace / "fake.arw"
    path.write_bytes(b"not a real raw file")
    return path
