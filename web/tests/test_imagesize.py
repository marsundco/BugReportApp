"""Proporcje zdjęć do wstawiania w opis karty (app/imagesize.py)."""
from __future__ import annotations

import io
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import imagesize  # noqa: E402

Image = pytest.importorskip("PIL.Image")   # Pillow tylko w środowisku deweloperskim


def _img(fmt, w, h, orientation=None):
    buf = io.BytesIO()
    im = Image.new("RGB", (w, h), (120, 60, 30))
    kw = {}
    if orientation:
        exif = Image.Exif()
        exif[0x0112] = orientation
        kw["exif"] = exif
    im.save(buf, fmt, **kw)
    return buf.getvalue()


def test_png():
    assert imagesize.aspect_ratio(_img("PNG", 800, 600)) == pytest.approx(4 / 3)


def test_jpeg_poziomy():
    assert imagesize.aspect_ratio(_img("JPEG", 800, 600)) == pytest.approx(4 / 3)


def test_jpeg_pionowy():
    assert imagesize.aspect_ratio(_img("JPEG", 600, 800)) == pytest.approx(3 / 4)


@pytest.mark.parametrize("orientation", [6, 8])
def test_jpeg_z_telefonu_obrocony_exifem(orientation):
    """Telefon zapisuje pionowe zdjęcie jako 800x600 + Orientation 6/8."""
    assert imagesize.aspect_ratio(_img("JPEG", 800, 600, orientation)) == pytest.approx(3 / 4)


def test_jpeg_orientacja_normalna():
    assert imagesize.aspect_ratio(_img("JPEG", 800, 600, 1)) == pytest.approx(4 / 3)


@pytest.mark.parametrize("data", [b"", b"nie obraz", b"\xff\xd8\xff", b"\x89PNG\r\n\x1a\n"])
def test_nieznany_lub_uciety_plik(data):
    assert imagesize.aspect_ratio(data) is None
