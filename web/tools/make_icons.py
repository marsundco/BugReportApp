"""Generuje ikony PWA z oryginalnego znaku „Karty niezgodności" (żółty ptaszek w kole).

Uruchamiaj tylko po zmianie znaku lub kolorów:
    .venv/Scripts/python tools/make_icons.py

Ikony są w repo (gotowe pliki PNG), więc deploy nie wymaga Pillow.

Dlaczego ptaszek, a nie wordmark WUWER: ikona ma mówić, KTÓRA to aplikacja.
Logo firmy na kaflu przestaje odróżniać cokolwiek, gdy na tablecie wyląduje
druga i trzecia nasza aplikacja. Wordmark zostaje w nagłówku w środku
aplikacji — tam kontekst jest już jednoznaczny.

Znak pochodzi z warstwy adaptive-foreground aplikacji Flutter (IssueReportApp),
czyli to ten sam ptaszek, który operatorzy znają z tabletu. Tło zmienione z
szarego na granat motywu — na ekranie głównym daje wyraźnie większy kontrast,
a przy okazji zgadza się z `background_color` z manifestu.
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image

STATIC = Path(__file__).resolve().parent.parent / "app" / "static"
MARK = STATIC / "icon-mark.png"   # żółty ptaszek na przezroczystości

BG = (11, 18, 32, 255)  # --bg #0b1220


def build(size: int, safe: float, out: Path) -> None:
    """safe = jaka część kafla ma zajmować znak (maskable potrzebuje zapasu)."""
    canvas = Image.new("RGBA", (size, size), BG)

    mark = Image.open(MARK).convert("RGBA")
    # Przytnij przezroczyste marginesy, żeby „safe" odnosiło się do samego
    # znaku, a nie do pustego pola wokół niego.
    bbox = mark.getbbox()
    if bbox:
        mark = mark.crop(bbox)

    target = round(size * safe)
    scale = target / max(mark.width, mark.height)
    mark = mark.resize((max(1, round(mark.width * scale)),
                        max(1, round(mark.height * scale))), Image.LANCZOS)

    canvas.alpha_composite(mark, ((size - mark.width) // 2, (size - mark.height) // 2))
    canvas.save(out)
    print(f"  {out.name}  {size}x{size}")


def main() -> None:
    print("Generuję ikony ze znaku", MARK.name)
    build(192, 0.68, STATIC / "icon-192.png")
    build(512, 0.68, STATIC / "icon-512.png")
    # Maskable: Android przycina kafel do koła/rounded-square — znak musi
    # zmieścić się w bezpiecznym polu ok. 80% średnicy, stąd mniejszy udział.
    build(512, 0.52, STATIC / "icon-maskable-512.png")


if __name__ == "__main__":
    main()
