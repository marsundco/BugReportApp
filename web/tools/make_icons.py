"""Generuje ikony PWA z monochromatycznego wordmarku WUWER.

Uruchamiaj tylko po zmianie logo/kolorów:
    .venv/Scripts/python tools/make_icons.py

Ikony są w repo (gotowe pliki PNG), więc deploy nie wymaga Pillow.
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image

STATIC = Path(__file__).resolve().parent.parent / "app" / "static"
SRC = STATIC / "logo-white.png"

BG = (11, 18, 32, 255)        # --bg  #0b1220
ACCENT = (255, 217, 102, 255)  # --accent #FFD966


def _wordmark(width: int) -> Image.Image:
    """Wordmark przetintowany na żółto, przeskalowany do zadanej szerokości."""
    logo = Image.open(SRC).convert("RGBA")
    height = max(1, round(logo.height * width / logo.width))
    logo = logo.resize((width, height), Image.LANCZOS)
    # Kształt bierzemy WYŁĄCZNIE z kanału alfa (jak maska CSS w style.css),
    # więc kolor źródłowego PNG nie ma znaczenia.
    tinted = Image.new("RGBA", logo.size, ACCENT)
    tinted.putalpha(logo.getchannel("A"))
    return tinted


def build(size: int, safe: float, out: Path) -> None:
    """safe = jaki ułamek krawędzi zostawić pusty (maskable potrzebuje zapasu)."""
    canvas = Image.new("RGBA", (size, size), BG)
    mark = _wordmark(round(size * safe))
    canvas.alpha_composite(mark, ((size - mark.width) // 2, (size - mark.height) // 2))
    canvas.save(out)
    print(f"  {out.name}  {size}x{size}")


def main() -> None:
    print("Generuję ikony z", SRC.name)
    build(192, 0.74, STATIC / "icon-192.png")
    build(512, 0.74, STATIC / "icon-512.png")
    # Maskable: Android przycina do koła/rounded-square — stąd węższy wordmark.
    build(512, 0.56, STATIC / "icon-maskable-512.png")


if __name__ == "__main__":
    main()
