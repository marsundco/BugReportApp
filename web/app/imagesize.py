"""Proporcje zdjęcia (szerokość / wysokość) — sama biblioteka standardowa.

GoodDay rysuje zdjęcie wstawione w treść karty według pola `aspectRatio`.
Telefon zapisuje zdjęcie pionowe jako poziome z flagą obrotu w EXIF
(Orientation 5–8), więc wymiary z nagłówka JPEG trzeba wtedy zamienić —
inaczej pionowe zdjęcie dostałoby proporcje poziome.

Zwraca None, gdy formatu nie rozpoznano; wtedy wołający bierze wartość domyślną.
"""
from __future__ import annotations

import struct


def aspect_ratio(data: bytes) -> float | None:
    size = _png_size(data) or _jpeg_size(data)
    if not size:
        return None
    w, h = size
    return w / h if w > 0 and h > 0 else None


def _png_size(data: bytes) -> tuple[int, int] | None:
    if data[:8] != b"\x89PNG\r\n\x1a\n" or len(data) < 24:
        return None
    return struct.unpack(">II", data[16:24])


def _jpeg_size(data: bytes) -> tuple[int, int] | None:
    if data[:2] != b"\xff\xd8":
        return None
    i, size, orientation = 2, None, 1
    while i + 4 <= len(data):
        if data[i] != 0xFF:
            i += 1
            continue
        marker = data[i + 1]
        if marker in (0xD8, 0x01) or 0xD0 <= marker <= 0xD7:   # bez długości
            i += 2
            continue
        seg_len = struct.unpack(">H", data[i + 2:i + 4])[0]
        seg = data[i + 4:i + 2 + seg_len]
        if marker == 0xE1 and seg[:6] == b"Exif\x00\x00":
            orientation = _exif_orientation(seg[6:]) or 1
        # SOF0..SOF15 poza DHT (C4), JPG (C8), DAC (CC)
        if 0xC0 <= marker <= 0xCF and marker not in (0xC4, 0xC8, 0xCC) and len(seg) >= 5:
            h, w = struct.unpack(">HH", seg[1:5])
            size = (w, h)
            break
        if marker == 0xDA:   # początek danych obrazu — dalej nagłówków nie ma
            break
        i += 2 + seg_len
    if not size:
        return None
    return (size[1], size[0]) if orientation in (5, 6, 7, 8) else size


def _exif_orientation(tiff: bytes) -> int | None:
    if len(tiff) < 8 or tiff[:2] not in (b"II", b"MM"):
        return None
    e = "<" if tiff[:2] == b"II" else ">"
    try:
        ifd = struct.unpack(e + "I", tiff[4:8])[0]
        count = struct.unpack(e + "H", tiff[ifd:ifd + 2])[0]
        for n in range(count):
            off = ifd + 2 + 12 * n
            tag = struct.unpack(e + "H", tiff[off:off + 2])[0]
            if tag == 0x0112:   # Orientation
                return struct.unpack(e + "H", tiff[off + 8:off + 10])[0]
    except struct.error:
        return None
    return None
