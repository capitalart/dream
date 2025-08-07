"""Tests for Pillow configuration used to handle large images."""

from __future__ import annotations

import logging

from PIL import Image

import init.image_config as image_config


def test_large_image_logging(tmp_path, caplog):
    """Image.open is patched and logs when threshold is exceeded."""
    assert Image.MAX_IMAGE_PIXELS is None

    image_file = tmp_path / "tiny.png"
    Image.new("RGB", (10, 10)).save(image_file)

    image_config._LARGE_IMAGE_THRESHOLD = 50
    with caplog.at_level(logging.WARNING):
        Image.open(image_file)
    assert "Large image loaded" in caplog.text
