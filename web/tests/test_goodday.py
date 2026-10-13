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


class _Calls(list):
    """Lista wywołań (metoda, url, body) + atrybut `attached` do sterowania atrapą."""


@pytest.fixture
def calls(monkeypatch):
    """Przechwytuje wywołania requests.post/put i zwraca listę (metoda, url, body)."""
    recorded = _Calls()
    # Ile załączników GoodDay „przypnie" do zadania — testy mogą to zmienić,
    # żeby zasymulować ciche pominięcie (patrz nagłówek goodday.py).
    recorded_attached = {"count": None}

    def fake_post(url, json=None, headers=None, timeout=None):
        recorded.append(("POST", url, json))
        if url.endswith("/attachments/upload-urls"):
            return FakeResponse(200, [{"fileId": "11111111-2222-3333-4444-555555555555",
                                       "name": json["files"][0]["name"],
                                       "uploadUrl": "https://s3.example/temp/x?sig=1",
                                       "mime": "image/jpeg"}])
        return FakeResponse(200, {"id": "TASK42", "shortId": "1234"})

    def fake_put(url, json=None, headers=None, timeout=None, data=None):
        recorded.append(("PUT", url, json if data is None else {"bytes": len(data),
                                                                 "headers": headers}))
        return FakeResponse(200, {})

    def fake_get(url, headers=None, timeout=None):
        recorded.append(("GET", url, None))
        n = recorded_attached["count"]
        # domyślnie: dołączono wszystko, co wysłano przy tworzeniu zadania
        if n is None:
            create = next(c for c in recorded if c[1].endswith("/2.0/tasks"))
            n = len(create[2].get("attachments", []))
        resp = FakeResponse(200, [{"attachments": [{}] * n}])
        resp.raise_for_status = lambda: None
        return resp

    monkeypatch.setattr(goodday.requests, "post", fake_post)
    monkeypatch.setattr(goodday.requests, "put", fake_put)
    monkeypatch.setattr(goodday.requests, "get", fake_get)
    recorded.attached = recorded_attached
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


ATT_A = {"fileId": "aaaaaaaa-0000-0000-0000-000000000001", "name": "a.jpg",
         "size": 10, "mime": "image/jpeg"}
ATT_B = {"fileId": "bbbbbbbb-0000-0000-0000-000000000002", "name": "b.jpg",
         "size": 20, "mime": "image/jpeg"}


def test_zdjecia_ida_jako_zalaczniki_a_nie_linki_w_opisie(calls):
    _submit(attachments=[ATT_A, ATT_B])
    create = calls[0][2]
    assert create["attachments"] == [ATT_A, ATT_B]
    assert create["message"] == "Otwory nie pasują."   # opis bez doklejonych linków


def test_bez_zdjec_brak_pola_attachments_i_brak_sprawdzania(calls):
    _submit()
    assert "attachments" not in calls[0][2]
    assert not any(c[0] == "GET" for c in calls)


def test_wszystkie_zdjecia_dolaczone_brak_ostrzezenia(calls):
    result = _submit(attachments=[ATT_A, ATT_B])
    assert any(c[0] == "GET" and c[1].endswith("/task/TASK42/messages") for c in calls)
    assert "zdjęcia" not in result["warnings"]


def test_po_cichu_pominiete_zdjecie_daje_ostrzezenie(calls):
    """GoodDay zwraca 200 nawet gdy pominie załącznik — musimy to wykryć sami."""
    calls.attached["count"] = 1
    result = _submit(attachments=[ATT_A, ATT_B])
    assert result["taskId"] == "TASK42"          # karta i tak powstała
    assert "zdjęcia" in result["warnings"]


def test_upload_zalacznika_dwa_kroki_bez_tokenu_do_s3(calls):
    att = goodday.upload_attachment("IMG_1.jpg", b"x" * 7, "image/jpeg")
    assert calls[0][1].endswith("/2.0/attachments/upload-urls")
    assert calls[0][2] == {"files": [{"name": "IMG_1.jpg"}]}
    method, url, body = calls[1]
    assert (method, url) == ("PUT", "https://s3.example/temp/x?sig=1")
    assert body["bytes"] == 7
    # token GoodDay NIE może wyjść do Amazona
    assert "gd-api-token" not in body["headers"]
    assert att == {"fileId": "11111111-2222-3333-4444-555555555555",
                   "name": "IMG_1.jpg", "size": 7, "mime": "image/jpeg"}


def test_nazwa_bez_rozszerzenia_dostaje_je_z_typu(calls):
    """GoodDay ustala MIME po rozszerzeniu, a aparat oddaje czasem plik „blob"."""
    goodday.upload_attachment("blob", b"x", "image/png")
    assert calls[0][2]["files"][0]["name"] == "blob.png"


def test_nazwa_ze_sciezka_jest_oczyszczona(calls):
    goodday.upload_attachment("..\\..\\C:/x/zdj.jpg", b"x", "image/jpeg")
    name = calls[0][2]["files"][0]["name"]
    assert "/" not in name and "\\" not in name


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


def test_zdjecia_wstawione_w_opis_pod_tekstem(calls):
    """messageRTF: najpierw akapity opisu, na końcu akapit ze zdjęciami."""
    _submit(detailed_desc="Linia 1\n\nLinia 3", attachments=[{**ATT_A, "aspectRatio": 0.75}, ATT_B])
    create = calls[0][2]
    assert create["message"] == "Linia 1\n\nLinia 3"        # zwykły tekst zostaje
    paras = create["messageRTF"]["content"]["root"]["children"]
    assert create["messageRTF"]["v"] == "lexical-1"
    assert [p["children"][0]["text"] if p["children"] and p["children"][0]["type"] == "text"
            else None for p in paras[:3]] == ["Linia 1", None, "Linia 3"]
    imgs = paras[-1]["children"]
    assert [i["type"] for i in imgs] == ["attachment", "attachment"]
    assert [i["attachment"]["fileId"] for i in imgs] == [ATT_A["fileId"], ATT_B["fileId"]]
    assert imgs[0]["attachment"]["aspectRatio"] == 0.75
    assert imgs[1]["attachment"]["aspectRatio"] == goodday.DEFAULT_ASPECT   # brak → domyślne


def test_aspect_ratio_nie_trafia_do_listy_attachments(calls):
    _submit(attachments=[{**ATT_A, "aspectRatio": 0.75}])
    assert calls[0][2]["attachments"] == [ATT_A]


def test_same_zdjecia_bez_opisu_to_tylko_akapit_zdjec(calls):
    _submit(detailed_desc="", attachments=[ATT_A])
    paras = calls[0][2]["messageRTF"]["content"]["root"]["children"]
    assert len(paras) == 1 and paras[0]["children"][0]["type"] == "attachment"


def test_bez_zdjec_brak_messageRTF(calls):
    _submit()
    assert "messageRTF" not in calls[0][2]
