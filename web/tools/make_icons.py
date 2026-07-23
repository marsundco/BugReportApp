# -*- coding: utf-8 -*-
"""Generator kafli PNG ze znaku aplikacji — pakiet WUWER.

Skopiuj do projektu obok `tokens.css`. Kształt czyta z `icon-mark.svg`, więc
znak zostaje jednym źródłem prawdy: podmieniasz SVG, uruchamiasz skrypt,
ikona zmienia się wszędzie.

    python make-icons.py static/icon-mark.svg static

Bez zewnętrznych bibliotek: Pillow i cairosvg nie zawsze są zainstalowane na
komputerze, na którym akurat powstaje aplikacja, a kafel jest potrzebny zawsze.
Rasteryzacja polem odległości (piksel bliżej odcinka niż promień kreski =
zamalowany), antyaliasing z tej samej odległości, zapis PNG przez `zlib`.

Znaki bierzemy WYŁĄCZNIE z biblioteki Lucide (reguła systemu, §5). Pliki Lucide
to kilka elementów `<path>` z kreską (`stroke`), we współrzędnych względnych
i z łukami — dlatego parser rozumie pełną gramatykę ścieżki SVG
(M m L l H h V v C c S s Q q T t A a Z z) oraz wiele elementów naraz, a każdy
kształt renderuje jako KRESKĘ (nie wypełnienie). Zaokrąglone końce i złącza
wychodzą same z pola odległości — to ten sam krąg przesuwany wzdłuż odcinka,
co daje `stroke-linecap="round"` Lucide bez dodatkowego kodu.

Grubość kreski bierze się z atrybutu `stroke-width` (Lucide: 2 na siatce 24),
kolory z `tokens.css` (`--bg` i `--accent`) — wpisane niżej, bo PNG powstaje
poza kaskadą CSS.
"""

import math
import os
import re
import struct
import sys
import zlib

# Z tokens.css. Wpisane wprost, bo PNG powstaje poza dokumentem i nie ma
# dostępu do zmiennych CSS.
BG = (0x0b, 0x12, 0x20)      # --bg
FG = (0xFF, 0xD9, 0x66)      # --accent

# (plik, rozmiar, udział znaku w kaflu, zaokrąglony kafel)
#
# Warianty z pełnym kwadratem nie mają własnego zaokrąglenia: system dokłada
# swój kształt, a przezroczyste tło iOS zamienia na czarne.
JOBS = [
    ("icon-192.png",          192, 0.66, True),
    ("icon-512.png",          512, 0.66, True),
    ("icon-maskable-512.png", 512, 0.52, False),   # Android przycina do koła
    ("apple-touch-icon.png",  180, 0.64, False),   # iOS, jedyny format jaki czyta
]

CORNER_FRAC = 0.22           # promień kafla jako część boku (§5)

# Gęstość próbkowania krzywych i łuków. 18 kawałków na krzywą trzyma błąd
# cięciwy poniżej dziesiątej części piksela przy typowej grubości kreski.
CURVE_STEPS = 18


# ====================== CZYTANIE KSZTAŁTU Z SVG ======================

# Token ścieżki: litera polecenia albo liczba (z ułamkiem, znakiem, wykładnikiem).
# Kolejność w alternatywie liczby jest istotna: „.25" musi złapać się przed „2".
_TOK = re.compile(
    r'[MmLlHhVvCcSsQqTtAaZz]|[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][+-]?\d+)?'
)


def parse_mark(path):
    """Zwraca (segmenty, grubość_kreski, viewBox). Wszystkie elementy rysunku
    (każdy `<path>`, a także `<circle>`, `<line>`, `<polyline>`, `<polygon>`,
    gdyby się trafiły) sprowadzone są do listy odcinków — renderer stroke'uje
    je jednakowo, więc kształt jest wierny niezależnie od tego, czym go zapisano."""
    svg = open(path, encoding="utf-8").read()
    svg = re.sub(r"<!--.*?-->", "", svg, flags=re.S)   # komentarze potrafią mieć d=/stroke-width

    vb = [float(v) for v in re.search(r'viewBox="([^"]+)"', svg).group(1).split()]
    m = re.search(r'stroke-width="(\d+(?:\.\d+)?)"', svg)
    stroke_w = float(m.group(1)) if m else 2.0

    segs = []
    for d in re.findall(r'\sd="([^"]+)"', svg):
        segs += path_segments(d)
    for cx, cy, r in re.findall(
            r'<circle[^>]*\bcx="([\d.]+)"[^>]*\bcy="([\d.]+)"[^>]*\br="([\d.]+)"', svg):
        segs += circle_segments(float(cx), float(cy), float(r))
    for pts in re.findall(r'<poly(?:line|gon)[^>]*\bpoints="([^"]+)"', svg):
        segs += polyline_segments(pts)
    for tag in re.findall(r'<rect\b[^>]*>', svg):
        attr = dict(re.findall(r'\b(x|y|width|height|rx|ry)="([\d.]+)"', tag))
        segs += rect_segments(float(attr.get("x", 0)), float(attr.get("y", 0)),
                              float(attr["width"]), float(attr["height"]),
                              float(attr.get("rx", attr.get("ry", 0))),
                              float(attr.get("ry", attr.get("rx", 0))))
    for x1, y1, x2, y2 in re.findall(
            r'<line[^>]*\bx1="([\d.-]+)"[^>]*\by1="([\d.-]+)"[^>]*\bx2="([\d.-]+)"[^>]*\by2="([\d.-]+)"', svg):
        segs.append((float(x1), float(y1), float(x2), float(y2)))
    return segs, stroke_w, vb


def circle_segments(cx, cy, r, steps=64):
    segs, prev = [], None
    for k in range(steps + 1):
        a = 2 * math.pi * k / steps
        p = (cx + r * math.cos(a), cy + r * math.sin(a))
        if prev is not None:
            segs.append((prev[0], prev[1], p[0], p[1]))
        prev = p
    return segs


def polyline_segments(points):
    nums = [float(v) for v in re.findall(r'[-+]?[\d.]+', points)]
    pts = list(zip(nums[0::2], nums[1::2]))
    return [(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1])
            for i in range(len(pts) - 1)]


def rect_segments(x, y, w, h, rx, ry):
    """Prostokąt (z zaokrąglonymi rogami) -> odcinki. Lucide buduje wiele
    znaków z `<rect rx=...>`, więc traktujemy je tak samo jak ścieżki."""
    rx = rx or ry
    ry = ry or rx
    if rx <= 0:
        d = "M%g %gH%gV%gH%gZ" % (x, y, x + w, y + h, x)
    else:
        rx = min(rx, w / 2); ry = min(ry, h / 2)
        d = ("M%g %gH%gA%g %g 0 0 1 %g %gV%gA%g %g 0 0 1 %g %gH%gA%g %g 0 0 1 %g %gV%gA%g %g 0 0 1 %g %gZ"
             % (x + rx, y, x + w - rx, rx, ry, x + w, y + ry,
                y + h - ry, rx, ry, x + w - rx, y + h,
                x + rx, rx, ry, x, y + h - ry,
                y + ry, rx, ry, x + rx, y))
    return path_segments(d)


def path_segments(d):
    """Ścieżka SVG (pełna gramatyka, współrzędne bezwzględne i względne,
    łuki eliptyczne) -> lista odcinków."""
    toks = _TOK.findall(d)
    segs = []
    i = 0
    x = y = 0.0            # bieżący punkt
    sx = sy = 0.0          # początek podścieżki (dla Z)
    cx2 = cy2 = None       # ostatni uchwyt (dla gładkich S/T)
    cmd = last = None

    def is_cmd(t):
        return t[0] in "MmLlHhVvCcSsQqTtAaZz"

    def take(n):
        nonlocal i
        vals = [float(v) for v in toks[i:i + n]]
        i += n
        return vals

    while i < len(toks):
        t = toks[i]
        if is_cmd(t):
            cmd = t
            i += 1
            if cmd in "Zz":
                if (x, y) != (sx, sy):
                    segs.append((x, y, sx, sy))
                x, y = sx, sy
                cmd = None
                continue
        rel = cmd.islower()
        c = cmd.upper()

        if c == "M":
            dx, dy = take(2)
            x, y = (x + dx, y + dy) if rel else (dx, dy)
            sx, sy = x, y
            cmd = "l" if rel else "L"       # kolejne pary po M to linie
        elif c == "L":
            dx, dy = take(2)
            nx, ny = (x + dx, y + dy) if rel else (dx, dy)
            segs.append((x, y, nx, ny)); x, y = nx, ny
        elif c == "H":
            dx = take(1)[0]
            nx = x + dx if rel else dx
            segs.append((x, y, nx, y)); x = nx
        elif c == "V":
            dy = take(1)[0]
            ny = y + dy if rel else dy
            segs.append((x, y, x, ny)); y = ny
        elif c == "C":
            x1, y1, x2, y2, dx, dy = take(6)
            if rel:
                x1 += x; y1 += y; x2 += x; y2 += y; dx += x; dy += y
            segs += cubic(x, y, x1, y1, x2, y2, dx, dy)
            cx2, cy2 = x2, y2; x, y = dx, dy
        elif c == "S":
            x2, y2, dx, dy = take(4)
            if rel:
                x2 += x; y2 += y; dx += x; dy += y
            x1, y1 = (2 * x - cx2, 2 * y - cy2) if last in "CcSs" and cx2 is not None else (x, y)
            segs += cubic(x, y, x1, y1, x2, y2, dx, dy)
            cx2, cy2 = x2, y2; x, y = dx, dy
        elif c == "Q":
            x1, y1, dx, dy = take(4)
            if rel:
                x1 += x; y1 += y; dx += x; dy += y
            segs += quad(x, y, x1, y1, dx, dy)
            cx2, cy2 = x1, y1; x, y = dx, dy
        elif c == "T":
            dx, dy = take(2)
            if rel:
                dx += x; dy += y
            x1, y1 = (2 * x - cx2, 2 * y - cy2) if last in "QqTt" and cx2 is not None else (x, y)
            segs += quad(x, y, x1, y1, dx, dy)
            cx2, cy2 = x1, y1; x, y = dx, dy
        elif c == "A":
            rx, ry, rot, laf, sf, dx, dy = take(7)
            nx, ny = (x + dx, y + dy) if rel else (dx, dy)
            segs += arc(x, y, rx, ry, rot, int(laf), int(sf), nx, ny)
            x, y = nx, ny
        else:
            i += 1                          # nieznany token — pomiń
            continue
        last = cmd

    return segs


def cubic(x0, y0, x1, y1, x2, y2, x3, y3, steps=CURVE_STEPS):
    out, px, py = [], x0, y0
    for s in range(1, steps + 1):
        u = s / steps; v = 1 - u
        bx = v*v*v*x0 + 3*v*v*u*x1 + 3*v*u*u*x2 + u*u*u*x3
        by = v*v*v*y0 + 3*v*v*u*y1 + 3*v*u*u*y2 + u*u*u*y3
        out.append((px, py, bx, by)); px, py = bx, by
    return out


def quad(x0, y0, x1, y1, x2, y2, steps=CURVE_STEPS):
    out, px, py = [], x0, y0
    for s in range(1, steps + 1):
        u = s / steps; v = 1 - u
        bx = v*v*x0 + 2*v*u*x1 + u*u*x2
        by = v*v*y0 + 2*v*u*y1 + u*u*y2
        out.append((px, py, bx, by)); px, py = bx, by
    return out


def arc(x0, y0, rx, ry, rot, large, sweep, x1, y1):
    """Łuk eliptyczny SVG -> odcinki (parametryzacja środkowa, spec F.6.5)."""
    if rx == 0 or ry == 0 or (x0 == x1 and y0 == y1):
        return [(x0, y0, x1, y1)]
    phi = math.radians(rot)
    cosp, sinp = math.cos(phi), math.sin(phi)
    dx2, dy2 = (x0 - x1) / 2.0, (y0 - y1) / 2.0
    x1p = cosp * dx2 + sinp * dy2
    y1p = -sinp * dx2 + cosp * dy2
    rx, ry = abs(rx), abs(ry)
    lam = x1p*x1p / (rx*rx) + y1p*y1p / (ry*ry)
    if lam > 1:
        s = math.sqrt(lam); rx *= s; ry *= s
    sign = -1 if large == sweep else 1
    num = rx*rx*ry*ry - rx*rx*y1p*y1p - ry*ry*x1p*x1p
    den = rx*rx*y1p*y1p + ry*ry*x1p*x1p
    co = sign * math.sqrt(max(0.0, num / den)) if den else 0.0
    cxp, cyp = co * rx * y1p / ry, -co * ry * x1p / rx
    cx = cosp * cxp - sinp * cyp + (x0 + x1) / 2.0
    cy = sinp * cxp + cosp * cyp + (y0 + y1) / 2.0

    def ang(ux, uy, vx, vy):
        d = ux*vx + uy*vy
        ln = math.hypot(ux, uy) * math.hypot(vx, vy)
        a = math.acos(max(-1.0, min(1.0, d / ln))) if ln else 0.0
        return -a if ux*vy - uy*vx < 0 else a

    t1 = ang(1, 0, (x1p - cxp) / rx, (y1p - cyp) / ry)
    dt = ang((x1p - cxp) / rx, (y1p - cyp) / ry, (-x1p - cxp) / rx, (-y1p - cyp) / ry)
    if not sweep and dt > 0:
        dt -= 2 * math.pi
    elif sweep and dt < 0:
        dt += 2 * math.pi
    n = max(2, int(abs(dt) / (math.pi / 16)) + 1)
    out, px, py = [], x0, y0
    for k in range(1, n + 1):
        th = t1 + dt * k / n
        ex = cx + rx * math.cos(th) * cosp - ry * math.sin(th) * sinp
        ey = cy + rx * math.cos(th) * sinp + ry * math.sin(th) * cosp
        out.append((px, py, ex, ey)); px, py = ex, ey
    return out


# ====================== RASTERYZACJA ======================

def clamp01(v):
    return 0.0 if v < 0 else (1.0 if v > 1 else v)


def dist_to_segment(px, py, x0, y0, x1, y1):
    dx, dy = x1 - x0, y1 - y0
    L = dx*dx + dy*dy
    t = 0.0 if L == 0 else max(0.0, min(1.0, ((px - x0)*dx + (py - y0)*dy) / L))
    return math.hypot(px - (x0 + t*dx), py - (y0 + t*dy))


def render(size, segs, stroke_w, vb, mark_frac, rounded):
    vx, vy, vw, vh = vb
    scale = (size * mark_frac) / vw
    ox = (size - vw * scale) / 2.0
    oy = (size - vh * scale) / 2.0
    tx = lambda x, y: ((x - vx) * scale + ox, (y - vy) * scale + oy)

    r = stroke_w / 2.0 * scale
    cov = [0.0] * (size * size)

    def stamp(x_min, x_max, y_min, y_max, fn):
        for py in range(max(0, int(y_min)), min(size, int(y_max) + 1)):
            base = py * size
            for px in range(max(0, int(x_min)), min(size, int(x_max) + 1)):
                a = fn(px + 0.5, py + 0.5)
                if a > cov[base + px]:
                    cov[base + px] = a

    for (x0, y0, x1, y1) in segs:
        ax, ay = tx(x0, y0); bx, by = tx(x1, y1); pad = r + 1
        stamp(min(ax, bx) - pad, max(ax, bx) + pad,
              min(ay, by) - pad, max(ay, by) + pad,
              lambda px, py, ax=ax, ay=ay, bx=bx, by=by:
                  clamp01(r + 0.5 - dist_to_segment(px, py, ax, ay, bx, by)))

    buf = bytearray(size * size * 4)
    corner = size * CORNER_FRAC if rounded else 0.0
    half = size / 2.0

    for py in range(size):
        for px in range(size):
            if rounded:
                dx = abs(px + 0.5 - half) - (half - corner)
                dy = abs(py + 0.5 - half) - (half - corner)
                d = (math.hypot(max(dx, 0.0), max(dy, 0.0))
                     + min(max(dx, dy), 0.0) - corner)
                bg_a = clamp01(0.5 - d)
            else:
                bg_a = 1.0

            a = cov[py * size + px]
            out_a = a + bg_a * (1 - a)
            if out_a <= 0:
                continue
            i = (py * size + px) * 4
            for c in range(3):
                buf[i + c] = int(round((FG[c] * a + BG[c] * bg_a * (1 - a)) / out_a))
            buf[i + 3] = int(round(out_a * 255))

    return buf


# ====================== ZAPIS PNG ======================

def write_png(path, size, rgba):
    raw = bytearray()
    stride = size * 4
    for y in range(size):
        raw.append(0)                        # filtr „none"
        raw.extend(rgba[y * stride:(y + 1) * stride])

    def chunk(tag, data):
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

    png = (b"\x89PNG\r\n\x1a\n"
           + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0))
           + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
           + chunk(b"IEND", b""))

    with open(path, "wb") as f:
        f.write(png)
    return len(png)


def main():
    if len(sys.argv) < 3:
        print(__doc__.strip().splitlines()[0])
        print("Użycie: python make-icons.py <icon-mark.svg> <katalog-wyjściowy>")
        return 1

    src, out_dir = sys.argv[1], sys.argv[2]
    segs, stroke_w, vb = parse_mark(src)
    print("Znak: %d odcinków, kreska %g, viewBox %s" % (len(segs), stroke_w, vb))

    for name, size, frac, rounded in JOBS:
        buf = render(size, segs, stroke_w, vb, frac, rounded)
        n = write_png(os.path.join(out_dir, name), size, buf)
        print("  %-24s %4dx%-4d %6d B" % (name, size, size, n))
    return 0


if __name__ == "__main__":
    sys.exit(main())
