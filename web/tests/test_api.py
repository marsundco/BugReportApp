"""Testy endpointów HTTP — w tym najważniejszy: sekrety NIE wyciekają do przeglądarki."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config  # noqa: E402
from app import goodday, imgur  # noqa: E402
from app.main import app  # noqa: E402

client = TestClient(app)

# Wartości ATRAPY — prawdziwych sekretów nie wpisujemy nawet w testach, bo testy
# trafiają do repo. Test wycieku działa tak samo: wstrzykujemy je do configu
# i sprawdzamy, że nie wychodzą do przeglądarki.
SECRETS = ("test-goodday-token-DO-NOT-USE", "test-imgur-client-id")


@pytest.fixture(autouse=True)
def _configured(monkeypatch):
    monkeypatch.setattr(config, "GOODDAY_API_TOKEN", SECRETS[0])
    monkeypatch.setattr(config, "IMGUR_CLIENT_ID", SECRETS[1])


def test_strona_glowna_nie_zawiera_zadnego_sekretu():
    """Sedno modernizacji: token żyje na serwerze i nigdy nie trafia do HTML-a."""
    body = client.get("/").text
    for secret in SECRETS:
        assert secret not in body


def test_zadne_statyki_nie_zawieraja_sekretow():
    for path in ("/static/app.js", "/static/style.css", "/static/sw.js"):
        body = client.get(path).text
        for secret in SECRETS:
            assert secret not in body


def test_healthz_pokazuje_stan_ale_nie_wartosci():
    resp = client.get("/healthz")
    assert resp.status_code == 200
    body = resp.text
    assert resp.json()["goodday"] is True
    for secret in SECRETS:
        assert secret not in body


def test_formularz_ma_polskie_etykiety():
    body = client.get("/").text
    for label in ("Karta niezgodności", "Jaka niezgodność wystąpiła?", "Numer projektu",
                  "ID produktu / numer rysunku", "Szczegółowy opis problemu",
                  "Imię i nazwisko", "Dodaj zdjęcie", "Zgłoś kartę"):
        assert label in body


def test_etykiety_nie_zawieraja_starych_bledow():
    """Literówki odziedziczone po aplikacji androidowej — poprawione na życzenie.

    Osobny test, bo to są dokładnie te ciągi, które łatwo wrócą przy kopiowaniu
    starego kodu.
    """
    body = client.get("/").text
    # Całe etykiety, nie fragmenty: „niezgodnośc" jest podciągiem poprawnego
    # „niezgodności", więc sam fragment dawałby fałszywy alarm.
    for stara in ("Jaka niezgodnośc postąpiła?", "Imie i nazwisko", "Zgłoś karte",
                  "Numer Projektu", "ID Produktu / Numer Rysunku",
                  "Napisz opis problemu."):
        assert stara not in body


def test_pole_zdjecia_uzywa_aparatu_tylnego():
    body = client.get("/").text
    assert 'accept="image/*"' in body
    assert 'capture="environment"' in body


def test_pole_zdjecia_pozwala_na_wiele_plikow():
    assert "multiple" in client.get("/").text


def test_naglowek_pokazuje_znak_aplikacji_i_logo_firmy():
    """Ten sam ptaszek co na ikonie — użytkownik ma widzieć, w czym jest."""
    body = client.get("/").text
    assert 'class="app-mark"' in body   # znak aplikacji (maska CSS)
    assert 'class="logo"' in body       # wordmark WUWER
    assert client.get("/static/icon-mark.svg").status_code == 200


def test_znak_stoi_wewnatrz_naglowka():
    """Tylko element liniowy w <h1> siada na linii pisma i równa się z „K".

    Ustawiony obok nagłówka wisiał 2–3 px za wysoko — przy znaku wysokim na
    11 px to widać gołym okiem.
    """
    body = client.get("/").text
    assert '<h1><span class="app-mark"' in body


def test_znak_ma_wysokosc_wersalika():
    """Reguła twarda: znak równa się optycznie z wielką literą nazwy.

    1.2cap, nie 1cap: przy równych 1cap znak MIERZY tyle co wersalik, ale
    wygląda na mniejszy — okrąg dotyka linii wersalika w jednym punkcie.
    """
    css = client.get("/static/style.css").text
    assert "height: 1.2cap;" in css
    assert "height: 0.86em;" in css   # zapas dla przeglądarek bez jednostki cap


def test_znak_na_kaflu_ma_margines():
    """Znak nie może dotykać krawędzi kafla — SVG musi skalować go do środka.

    Regresja: pierwsza wersja icon.svg rysowała znak na całym viewBoksie,
    więc favicon wyglądał zupełnie inaczej niż kafel PNG.
    """
    svg = client.get("/static/icon.svg").text
    assert "scale(0.68)" in svg


def test_favicon_i_kafel_maja_zaokraglone_tlo():
    """Bez kafla znak ginie na jasnym tle zakładki przeglądarki."""
    svg = client.get("/static/icon.svg").text
    assert "<rect" in svg and "rx=" in svg
    assert client.get("/static/icon.svg").status_code == 200


def test_report_wymaga_krotkiego_opisu():
    resp = client.post("/report", data={"shortDesc": "   "})
    assert resp.status_code == 400
    assert resp.json()["ok"] is False


def test_report_zwraca_numer_zgloszenia(monkeypatch):
    monkeypatch.setattr(goodday, "submit_report",
                        lambda **kw: {"taskId": "T1", "shortId": "999", "warnings": []})
    resp = client.post("/report", data={
        "shortDesc": "Krzywy wspornik",
        "projectName": "P/1",
        "productId": "6-2",
        "detailedDesc": "opis",
        "reporterName": "Jan",
    })
    assert resp.status_code == 200
    assert resp.json() == {"ok": True, "taskId": "T1", "shortId": "999", "warnings": []}


def test_report_przekazuje_link_do_zdjecia(monkeypatch):
    captured = {}

    def fake_submit(**kwargs):
        captured.update(kwargs)
        return {"taskId": "T1", "shortId": "9", "warnings": []}

    monkeypatch.setattr(goodday, "submit_report", fake_submit)
    client.post("/report", data={"shortDesc": "x", "imageLink": "https://i.imgur.com/a.png"})
    assert captured["image_links"] == ["https://i.imgur.com/a.png"]


def test_report_przekazuje_wiele_zdjec(monkeypatch):
    """Kilka linków przychodzi jako jedno pole, po jednym w linii."""
    captured = {}

    def fake_submit(**kwargs):
        captured.update(kwargs)
        return {"taskId": "T1", "shortId": "9", "warnings": []}

    monkeypatch.setattr(goodday, "submit_report", fake_submit)
    client.post("/report", data={
        "shortDesc": "x",
        "imageLink": "https://i.imgur.com/a.png\nhttps://i.imgur.com/b.png",
    })
    assert captured["image_links"] == [
        "https://i.imgur.com/a.png",
        "https://i.imgur.com/b.png",
    ]


def test_report_ignoruje_puste_linie_w_linkach(monkeypatch):
    captured = {}

    def fake_submit(**kwargs):
        captured.update(kwargs)
        return {"taskId": "T1", "shortId": "9", "warnings": []}

    monkeypatch.setattr(goodday, "submit_report", fake_submit)
    client.post("/report", data={"shortDesc": "x", "imageLink": "\n\n"})
    assert captured["image_links"] == []


def test_report_blad_goodday_to_502(monkeypatch):
    def boom(**kwargs):
        raise goodday.GoodDayError("GoodDay odrzucił zgłoszenie (HTTP 401).")

    monkeypatch.setattr(goodday, "submit_report", boom)
    resp = client.post("/report", data={"shortDesc": "x"})
    assert resp.status_code == 502
    assert "GoodDay" in resp.json()["error"]


def test_report_bez_tokenu_to_503(monkeypatch):
    monkeypatch.setattr(config, "GOODDAY_API_TOKEN", "")
    resp = client.post("/report", data={"shortDesc": "x"})
    assert resp.status_code == 503


def test_upload_odrzuca_plik_ktory_nie_jest_obrazem():
    resp = client.post("/upload", files={"photo": ("a.txt", b"tekst", "text/plain")})
    assert resp.status_code == 400


def test_upload_odrzuca_za_duzy_plik(monkeypatch):
    monkeypatch.setattr(config, "MAX_UPLOAD_BYTES", 10)
    resp = client.post("/upload", files={"photo": ("a.jpg", b"x" * 50, "image/jpeg")})
    assert resp.status_code == 413


def test_upload_zwraca_link(monkeypatch):
    monkeypatch.setattr(imgur, "upload_image",
                        lambda *a, **k: "https://i.imgur.com/ok.png")
    resp = client.post("/upload", files={"photo": ("a.jpg", b"xxx", "image/jpeg")})
    assert resp.status_code == 200
    assert resp.json() == {"ok": True, "link": "https://i.imgur.com/ok.png"}


def test_manifest_i_sw_serwowane_z_roota():
    """PWA: sw.js spoza roota nie objąłby zakresem całej aplikacji."""
    assert client.get("/manifest.webmanifest").status_code == 200
    assert client.get("/sw.js").status_code == 200
