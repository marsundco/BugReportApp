"""Testy klienta GoodDay — bez ruszania prawdziwego API (requests zamockowane).

Pilnują rzeczy, które faktycznie potrafią się zepsuć przy refaktorze:
metody HTTP (status to PUT, nie POST), kolejności kroków i tego, że awaria
kroku 2/3 nie kasuje już utworzonego zgłoszenia.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config  # noqa: E402
from app import goodday  # noqa: E402


class FakeResponse:
    def __init__(self, status_code=200, payload=None, text=""):
        self.status_code = status_code
        self._payload = payload if payload is not None else {}
        self.text = text

    @property
    def ok(self) -> bool:
        return 200 <= self.status_code < 300

    def json(self):
        return self._payload


@pytest.fixture
def calls(monkeypatch):
    """Przechwytuje wywołania requests.post/put i zwraca listę (metoda, url, body)."""
    recorded: list[tuple[str, str, dict]] = []

    def fake_post(url, json=None, headers=None, timeout=None):
        recorded.append(("POST", url, json))
        return FakeResponse(200, {"id": "TASK42", "shortId": "1234"})

    def fake_put(url, json=None, headers=None, timeout=None):
        recorded.append(("PUT", url, json))
        return FakeResponse(200, {})

    monkeypatch.setattr(goodday.requests, "post", fake_post)
    monkeypatch.setattr(goodday.requests, "put", fake_put)
    monkeypatch.setattr(config, "GOODDAY_API_TOKEN", "test-token")
    monkeypatch.setattr(config, "GOODDAY_ACTOR_USER_ID", "SPvGQx")
    return recorded


def _submit(**overrides):
    payload = {
        "short_desc": "Krzywy wspornik",
        "project_name": "P/1898/07",
        "product_id": "6-2001",
        "detailed_desc": "Otwory nie pasują.",
        "reporter_name": "Jan Kowalski",
    }
    payload.update(overrides)
    return goodday.submit_report(**payload)


def test_wysyla_trzy_kroki_we_wlasciwej_kolejnosci(calls):
    result = _submit()

    assert [c[0] for c in calls] == ["POST", "PUT", "PUT"]
    assert calls[0][1].endswith("/2.0/tasks")
    assert calls[1][1].endswith("/2.0/task/TASK42/custom-fields")
    assert calls[2][1].endswith("/2.0/task/TASK42/status")
    assert result == {"taskId": "TASK42", "shortId": "1234", "warnings": []}


def test_status_idzie_metoda_put_a_nie_post(calls):
    """Dokumentacja GoodDay podaje POST — na żywym API zwraca 405. Musi być PUT."""
    _submit()
    method, url, body = calls[2]
    assert method == "PUT"
    assert body == {"userId": "SPvGQx", "statusId": "pcqxl7"}


def test_status_ustawiany_na_nowe(calls):
    _submit()
    assert calls[2][2]["statusId"] == config.GOODDAY_NEW_STATUS_ID == "pcqxl7"


def test_pola_niestandardowe_maja_wlasciwe_id(calls):
    _submit()
    fields = {f["id"]: f["value"] for f in calls[1][2]["customFields"]}
    assert fields == {
        "l8dmpO": "P/1898/07",
        "MBYlLP": "6-2001",
        "5Mk38y": "Jan Kowalski",
    }


def test_link_do_zdjecia_doklejany_do_opisu(calls):
    _submit(image_links=["https://i.imgur.com/a.png"])
    message = calls[0][2]["message"]
    assert message == "Otwory nie pasują.\nhttps://i.imgur.com/a.png"


def test_wiele_zdjec_kazde_w_osobnej_linii(calls):
    _submit(image_links=[
        "https://i.imgur.com/a.png",
        "https://i.imgur.com/b.png",
        "https://i.imgur.com/c.png",
    ])
    assert calls[0][2]["message"] == (
        "Otwory nie pasują.\n"
        "https://i.imgur.com/a.png\n"
        "https://i.imgur.com/b.png\n"
        "https://i.imgur.com/c.png"
    )


def test_same_zdjecia_bez_opisu_nie_daja_wiodacej_pustej_linii(calls):
    _submit(detailed_desc="", image_links=["https://i.imgur.com/a.png"])
    assert calls[0][2]["message"] == "https://i.imgur.com/a.png"


def test_bez_zdjecia_opis_bez_pustej_linii(calls):
    _submit()
    assert calls[0][2]["message"] == "Otwory nie pasują."


def test_blad_tworzenia_zadania_to_wyjatek(calls, monkeypatch):
    monkeypatch.setattr(goodday.requests, "post",
                        lambda *a, **k: FakeResponse(401, text="unauthorized"))
    with pytest.raises(goodday.GoodDayError):
        _submit()


def test_awaria_statusu_nie_kasuje_zgloszenia(calls, monkeypatch):
    """Zadanie już istnieje — użytkownik ma dostać sukces, nie zachętę do retry."""
    monkeypatch.setattr(goodday.requests, "put",
                        lambda url, **k: FakeResponse(403, text="forbidden"))
    result = _submit()
    assert result["taskId"] == "TASK42"
    assert set(result["warnings"]) == {"pola niestandardowe", "status"}


def test_brak_uzytkownika_wykonawcy_daje_ostrzezenie_nie_blad(calls, monkeypatch):
    monkeypatch.setattr(config, "GOODDAY_ACTOR_USER_ID", "")
    result = _submit()
    assert result["taskId"] == "TASK42"
    assert "status" in result["warnings"]
