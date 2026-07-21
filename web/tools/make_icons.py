"""Generuje znak aplikacji (SVG) i kafle PWA (PNG) z jednej definicji geometrii.

Uruchamiaj tylko po zmianie znaku lub kolorów:
    .venv/Scripts/python tools/make_icons.py

Wyniki są w repo jako gotowe pliki, więc wdrożenie nie wymaga Pillow.

Dlaczego geometria siedzi tutaj, a nie w SVG: ten sam kształt trafia do maski
CSS w pasku nagłówka (SVG) i do kafli PNG (favicon, ikona PWA). Trzymanie go
w dwóch miejscach gwarantowałoby rozjazd przy pierwszej poprawce.

Kształt odtworzony z oryginalnego znaku aplikacji Flutter (ic_launcher):
parametry dopasowane numerycznie do PNG, pokrycie 97,2 %.
"""
from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw

STATIC = Path(__file__).resolve().parent.parent / "app" / "static"

# --- Kolory (muszą zgadzać się z tokenami motywu) ---
BG = (11, 18, 32, 255)         # token bg      #0b1220
ACCENT = (255, 217, 102, 255)  # token accent  #FFD966

# --- Geometria znaku w układzie 100 x 100 ---
# Pierścień: promień liczony do ŚRODKA obrysu, żeby zewnętrzna krawędź
# wypadła dokładnie na 50.
RING_STROKE = 10.1
RING_R = 50 - RING_STROKE / 2
CHECK_STROKE = 10.3
CHECK = [(21.6, 49.8), (40.2, 68.0), (73.0, 35.0)]   # lewy koniec, wierzchołek, prawy

# Promień zaokrąglenia kafla: ułamek boku, nie stała w px — ten sam kształt
# renderuje się w kilku rozmiarach naraz.
TILE_RADIUS = 0.22

# Jaką część kafla zajmuje znak. JEDNA wartość dla SVG i PNG — wcześniej SVG
# rysował znak na całym viewBoksie (0–100), więc favicon nie miał marginesu
# i wyglądał zupełnie inaczej niż kafel PNG.
MARK_FRAC = 0.68
# Maskable: Android przycina kafel do koła, więc znak musi zmieścić się
# w bezpiecznym polu ok. 80 % boku.
MARK_FRAC_MASKABLE = 0.50


def _svg(body: str, size: int = 100) -> str:
    # width/height obok viewBox: bez rozmiaru naturalnego część narzędzi
    # i generatorów kafli pliku nie wczyta.
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size} {size}" '
        f'width="{size}" height="{size}">\n{body}</svg>\n'
    )


def _mark_paths(color: str, frac: float = 1.0) -> str:
    """Znak w układzie 100 x 100. `frac` < 1 zmniejsza go i centruje (margines)."""
    pts = " ".join(f"{x},{y}" for x, y in CHECK)
    body = (
        f'  <circle cx="50" cy="50" r="{RING_R:g}" fill="none" '
        f'stroke="{color}" stroke-width="{RING_STROKE:g}"/>\n'
        f'  <polyline points="{pts}" fill="none" stroke="{color}" '
        f'stroke-width="{CHECK_STROKE:g}" stroke-linecap="round" '
        f'stroke-linejoin="round"/>\n'
    )
    if frac >= 1.0:
        return body
    off = (100 - 100 * frac) / 2
    return f'  <g transform="translate({off:g} {off:g}) scale({frac:g})">\n  {body}  </g>\n'


def build_svgs() -> None:
    # UWAGA: w komentarzach XML nie wolno użyć dwóch myślników pod rząd —
    # nazwa tokenu wpisana wprost psuje plik i przeglądarka cicho go odrzuca.
    # Dlatego nazwy tokenów są tu pisane słownie.

    # 1) Sam znak, przezroczyste tło — źródło maski CSS w pasku nagłówka.
    #    Kolor bierze się z tokenu przez background-color, więc tutaj jest
    #    dowolny; liczy się wyłącznie kanał alfa.
    (STATIC / "icon-mark.svg").write_text(
        _svg("  <!-- Znak aplikacji: maska CSS. Kolor nadaje token accent. -->\n"
             + _mark_paths("#000")),
        encoding="utf-8",
    )

    # 2) Znak na kafelku — favicon i ikona PWA. Kafel jest konieczny: zakładka
    #    przeglądarki i pulpit renderują ikonę na cudzym, nieprzewidywalnym
    #    tle, a sam znak ginie tam na jasnym motywie.
    r = TILE_RADIUS * 100
    tile = (f'  <!-- Kafel w kolorze tla motywu, znak w kolorze accent. -->\n'
            f'  <rect width="100" height="100" rx="{r:g}" ry="{r:g}" fill="#0b1220"/>\n')
    (STATIC / "icon.svg").write_text(
        _svg(tile + _mark_paths("#FFD966", MARK_FRAC)), encoding="utf-8")

    print("  icon-mark.svg  (maska do paska)")
    print("  icon.svg       (kafel: favicon / PWA)")


def _draw_mark(draw: ImageDraw.ImageDraw, cx: float, cy: float, span: float) -> None:
    """Rysuje znak wyśrodkowany w (cx, cy), o boku `span`."""
    sc = span / 100.0

    def P(x: float, y: float) -> tuple[float, float]:
        return (cx + (x - 50) * sc, cy + (y - 50) * sc)

    r = RING_R * sc
    draw.ellipse([cx - r, cy - r, cx + r, cy + r],
                 outline=ACCENT, width=max(1, round(RING_STROKE * sc)))

    pts = [P(x, y) for x, y in CHECK]
    draw.line(pts, fill=ACCENT, width=max(1, round(CHECK_STROKE * sc)), joint="curve")
    cap = CHECK_STROKE * sc / 2
    for p in (pts[0], pts[-1]):
        draw.ellipse([p[0] - cap, p[1] - cap, p[0] + cap, p[1] + cap], fill=ACCENT)


def build_png(size: int, mark_frac: float, out: Path, rounded: bool) -> None:
    F = 4  # supersampling — krawędzie łuku i skosów bez schodków
    img = Image.new("RGBA", (size * F, size * F), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    if rounded:
        d.rounded_rectangle([0, 0, size * F - 1, size * F - 1],
                            radius=TILE_RADIUS * size * F, fill=BG)
    else:
        # Maskable: Android sam przycina kafel do koła, więc tło na całość.
        d.rectangle([0, 0, size * F, size * F], fill=BG)

    _draw_mark(d, size * F / 2, size * F / 2, size * F * mark_frac)
    img.resize((size, size), Image.LANCZOS).save(out)
    print(f"  {out.name:24} {size}x{size}")


def main() -> None:
    print("Generuję znak i kafle:")
    build_svgs()
    build_png(192, MARK_FRAC, STATIC / "icon-192.png", rounded=True)
    build_png(512, MARK_FRAC, STATIC / "icon-512.png", rounded=True)
    build_png(512, MARK_FRAC_MASKABLE, STATIC / "icon-maskable-512.png", rounded=False)


if __name__ == "__main__":
    main()
