"""Klient REST do GoodDay (API v2). Cała komunikacja z tokenem dzieje się tutaj.

Trzy kroki zgłoszenia — dokładnie ten sam wzorzec co w aplikacji androidowej,
plus nowy krok statusu:

1. POST /2.0/tasks                       -> utworzenie zadania
2. PUT  /2.0/task/{id}/custom-fields     -> uzupełnienie 3 pól niestandardowych
3. PUT  /2.0/task/{id}/status            -> ustawienie statusu na "Nowe"

Zdjęcia (od 2026-10 zamiast Imgura) — natywne załączniki GoodDay, osobno, zanim
powstanie karta:

a. POST /2.0/attachments/upload-urls     -> rezerwacja: fileId + jednorazowy uploadUrl
b. PUT  <uploadUrl> (S3, surowe bajty)    -> wysłanie pliku
c. "attachments": [{fileId, name, size, mime}] w kroku 1

UWAGA do kroku c (sprawdzone na żywym API 2026-10-12, gorzej niż w dokumentacji):
jeden nieprawidłowy fileId (nieudany upload, wygasły link) sprawia, że GoodDay
odrzuca WSZYSTKIE załączniki tej karty — po cichu, z kodem 200. Poprawne fileId
są przy tym zużywane: nie da się ich potem dołączyć nawet komentarzem.

Stąd dwie zasady:
- przeglądarka wysyła wyłącznie zdjęcia z potwierdzonym uploadem, a zdjęcia
  starsze niż 45 min wysyła ponownie (link wygasa po godzinie) — app.js;
- po utworzeniu karty liczymy faktycznie dołączone załączniki
  (count_attachments) i przy braku zwracamy ostrzeżenie „zdjęcia", żeby
  operator dodał je ręcznie, zamiast myśleć, że są.

UWAGA do kroku 3: oficjalna dokumentacja GoodDay podaje dla statusu metodę POST.
To nieprawda — POST zwraca 405 Method Not Allowed. Działa wyłącznie PUT
(zweryfikowane na żywym API, 2026-07-20). Nie "poprawiaj" tego na POST.
"""
from __future__ import annotations

import logging
import mimetypes
import re

import requests

import config
from app import imagesize

logger = logging.getLogger("karty.goodday")


class GoodDayError(RuntimeError):
    """Błąd komunikacji z GoodDay, z komunikatem nadającym się dla użytkownika."""


def _headers() -> dict[str, str]:
    return {
        "gd-api-token": config.GOODDAY_API_TOKEN,
        "Content-Type": "application/json",
    }


def _url(path: str) -> str:
    return f"{config.GOODDAY_BASE_URL.rstrip('/')}{path}"


def _post(path: str, payload: dict) -> requests.Response:
    return requests.post(_url(path), json=payload, headers=_headers(),
                         timeout=config.http_timeout())


def _put(path: str, payload: dict) -> requests.Response:
    return requests.put(_url(path), json=payload, headers=_headers(),
                        timeout=config.http_timeout())


# fileId z GoodDay to UUID. Klient odsyła go nam przy zgłoszeniu, więc
# sprawdzamy format, zanim trafi do API.
FILE_ID_RE = re.compile(r"^[0-9a-fA-F-]{8,64}$")
MAX_ATTACHMENTS = 20   # limit GoodDay na jedno żądanie


def _attachment_name(filename: str | None, content_type: str | None) -> str:
    """Nazwa pliku z rozszerzeniem. GoodDay wyznacza MIME po rozszerzeniu nazwy,
    a aparat w przeglądarce potrafi oddać plik bez niego (np. „blob")."""
    raw = (filename or "").strip()
    name = "".join(c if c.isprintable() and c not in "/\\" else "_" for c in raw)
    name = name[-200:] or "zdjecie"   # GoodDay: nazwa maks. 255 znaków
    if "." not in name:
        ext = mimetypes.guess_extension(content_type or "") or ".jpg"
        name += ".jpg" if ext in (".jpe", ".jfif") else ext
    return name


def upload_attachment(filename: str | None, content: bytes,
                      content_type: str | None) -> dict:
    """Kroki a+b: zarezerwuj miejsce i wyślij plik. Zwraca wpis do `attachments`."""
    name = _attachment_name(filename, content_type)
    resp = _post("/2.0/attachments/upload-urls", {"files": [{"name": name}]})
    if not resp.ok:
        logger.error("Rezerwacja załącznika nieudana: %s %s", resp.status_code, resp.text[:500])
        raise GoodDayError(f"Nie udało się wysłać zdjęcia. Spróbuj ponownie "
                           f"(błąd {resp.status_code}).")
    try:
        slot = resp.json()[0]
        file_id, upload_url, mime = slot["fileId"], slot["uploadUrl"], slot["mime"]
    except (ValueError, LookupError, TypeError):
        logger.error("Nieoczekiwana odpowiedź upload-urls: %s", resp.text[:500])
        raise GoodDayError("Nie udało się wysłać zdjęcia. Spróbuj ponownie.")

    # Podpisany link S3 — BEZ nagłówka gd-api-token: token nie może wyjść do Amazona.
    put = requests.put(upload_url, data=content, headers={"Content-Type": mime},
                       timeout=config.http_timeout())
    if not put.ok:
        logger.error("Upload pliku do S3 nieudany: %s %s", put.status_code, put.text[:300])
        raise GoodDayError(f"Nie udało się wysłać zdjęcia. Spróbuj ponownie "
                           f"(błąd {put.status_code}).")

    logger.info("Załącznik wysłany: %s (%s, %d B)", file_id, name, len(content))
    entry = {"fileId": file_id, "name": name, "size": len(content), "mime": mime}
    ratio = imagesize.aspect_ratio(content)
    if ratio:
        # Tylko do treści sformatowanej (zdjęcie w opisie) — nie do listy attachments.
        entry["aspectRatio"] = round(ratio, 6)
    return entry


def count_attachments(task_id: str) -> int:
    """Ile załączników GoodDay faktycznie przypiął do zadania (patrz UWAGA w nagłówku)."""
    resp = requests.get(_url(f"/2.0/task/{task_id}/messages"), headers=_headers(),
                        timeout=config.http_timeout())
    resp.raise_for_status()
    return sum(len(m.get("attachments") or []) for m in resp.json())


ATTACHMENT_FIELDS = ("fileId", "name", "size", "mime")   # pola listy attachments
DEFAULT_ASPECT = 4 / 3                                    # zdjęcie z aparatu, poziome


def _paragraph(children: list[dict]) -> dict:
    return {"textStyle": "", "direction": None, "indent": 0, "format": "", "version": 1,
            "textFormat": 0, "type": "custom-paragraph", "children": children}


def build_message_rtf(message: str, attachments: list[dict]) -> dict:
    """Treść karty w formacie edytora GoodDay (Lexical): opis, a pod nim zdjęcia.

    Pole `messageRTF` NIE jest w dokumentacji API — format przepisany ze zdjęcia
    wstawionego ręcznie w GoodDay („insert into message"), sprawdzony 2026-10-13:
    zdjęcia wyświetlają się w opisie karty. Same `attachments` dają tylko listę
    plików pod opisem.

    Węzeł zdjęcia z interfejsu ma jeszcze `attachmentId`, którego przed utworzeniem
    karty nie znamy — GoodDay radzi sobie bez niego.
    """
    paragraphs = [
        _paragraph([{"style": "", "format": 0, "text": line, "detail": 0, "version": 1,
                     "mode": "normal", "type": "text"}] if line else [])
        for line in message.split("\n")
    ] if message else []

    images = [{
        "height": "auto", "width": "40%", "version": 1, "type": "attachment",
        "alignment": "left",
        "attachment": {
            "fileId": a["fileId"], "name": a["name"], "fileName": a["name"],
            "mime": a.get("mime") or "image/jpeg", "size": a.get("size") or 0,
            "systemType": 1, "fileType": 1, "storageProvider": 12, "preview": 1,
            "aspectRatio": a.get("aspectRatio") or DEFAULT_ASPECT,
        },
    } for a in attachments]

    return {"content": {"root": {"direction": None, "indent": 0, "format": "",
                                 "version": 1, "type": "root",
                                 "children": paragraphs + [_paragraph(images)]}},
            "v": "lexical-1"}


def create_task(title: str, message: str, attachments: list[dict] | None = None) -> dict:
    """Krok 1: utwórz zadanie. Zwraca surową odpowiedź GoodDay (z `id`, `shortId`).

    Ze zdjęciami: `message` zostaje zwykłym tekstem (podgląd, wyszukiwanie), a
    `messageRTF` wstawia zdjęcia w opis pod tekstem."""
    payload = {
        "projectId": config.GOODDAY_PROJECT_ID,
        "title": title,
        "fromUserId": config.GOODDAY_FROM_USER_ID,
        "message": message,
    }
    if attachments:
        payload["attachments"] = [{k: a[k] for k in ATTACHMENT_FIELDS if k in a}
                                  for a in attachments]
        payload["messageRTF"] = build_message_rtf(message, attachments)
    resp = _post("/2.0/tasks", payload)
    if not resp.ok:
        logger.error("Tworzenie zadania nieudane: %s %s", resp.status_code, resp.text[:500])
        raise GoodDayError(f"Nie udało się wysłać zgłoszenia. Spróbuj ponownie "
                           f"(błąd {resp.status_code}).")

    data = resp.json()
    task_id = (data or {}).get("id")
    if not task_id:
        raise GoodDayError("Zgłoszenie mogło nie zostać zapisane. Sprawdź "
                           "tablicę GoodDay przed ponowną wysyłką.")
    return data


def set_custom_fields(task_id: str, project_name: str, product_id: str,
                      reporter_name: str) -> None:
    """Krok 2: ustaw 3 pola niestandardowe (numer projektu / nr rysunku / zgłaszający)."""
    payload = {
        "customFields": [
            {"id": config.GOODDAY_FIELD_PROJECT, "value": project_name},
            {"id": config.GOODDAY_FIELD_PRODUCT, "value": product_id},
            {"id": config.GOODDAY_FIELD_REPORTER, "value": reporter_name},
        ]
    }
    resp = _put(f"/2.0/task/{task_id}/custom-fields", payload)
    if not resp.ok:
        logger.error("Pola niestandardowe nieudane (%s): %s %s",
                     task_id, resp.status_code, resp.text[:500])
        raise GoodDayError(f"Nie udało się zapisać pól zgłoszenia (HTTP {resp.status_code}).")


def set_status(task_id: str) -> None:
    """Krok 3: ustaw status na "Nowe".

    Wymaga PRAWDZIWEGO użytkownika w `userId` — placeholder daje 403, a brak pola 400.
    """
    if not config.status_step_configured():
        raise GoodDayError("Brak GOODDAY_ACTOR_USER_ID — nie mogę ustawić statusu.")

    payload = {
        "userId": config.GOODDAY_ACTOR_USER_ID,
        "statusId": config.GOODDAY_NEW_STATUS_ID,
    }
    # PUT, nie POST — patrz docstring modułu.
    resp = _put(f"/2.0/task/{task_id}/status", payload)
    if not resp.ok:
        logger.error("Ustawienie statusu nieudane (%s): %s %s",
                     task_id, resp.status_code, resp.text[:500])
        raise GoodDayError(f"Nie udało się ustawić statusu (HTTP {resp.status_code}).")


def submit_report(*, short_desc: str, project_name: str, product_id: str,
                  detailed_desc: str, reporter_name: str,
                  attachments: list[dict] | None = None) -> dict:
    """Pełne zgłoszenie: utwórz zadanie, ustaw pola, ustaw status.

    Zwraca {"taskId", "shortId", "warnings"}.

    Kroki 2 i 3 są NIEBLOKUJĄCE: jeśli zawiodą, zgłoszenie i tak istnieje w GoodDay
    i zostaje zgłoszone jako sukces (z ostrzeżeniem w logu). Zwrócenie użytkownikowi
    błędu skusiłoby go do ponownego wysłania — a to zduplikowałoby kartę na tablicy.
    """
    attachments = (attachments or [])[:MAX_ATTACHMENTS]
    task = create_task(title=short_desc.strip(), message=detailed_desc.strip(),
                       attachments=attachments)
    task_id = task["id"]
    short_id = task.get("shortId")
    warnings: list[str] = []

    try:
        set_custom_fields(task_id, project_name.strip(), product_id.strip(),
                          reporter_name.strip())
    except (GoodDayError, requests.RequestException) as exc:
        logger.warning("Zadanie %s utworzone, ale pola nieuzupełnione: %s", task_id, exc)
        warnings.append("pola niestandardowe")

    try:
        set_status(task_id)
    except (GoodDayError, requests.RequestException) as exc:
        logger.warning("Zadanie %s utworzone, ale status niezmieniony: %s", task_id, exc)
        warnings.append("status")

    if attachments:
        try:
            attached = count_attachments(task_id)
        except (requests.RequestException, ValueError) as exc:
            # Nie wiemy — nie strasz operatora; tylko log.
            logger.warning("Nie udało się policzyć załączników zadania %s: %s", task_id, exc)
        else:
            if attached < len(attachments):
                logger.warning("Zadanie %s: dołączono %d z %d zdjęć.",
                               task_id, attached, len(attachments))
                warnings.append("zdjęcia")

    logger.info("Zgłoszenie utworzone: %s (#%s), ostrzeżenia: %s",
                task_id, short_id, warnings or "brak")
    return {"taskId": task_id, "shortId": short_id, "warnings": warnings}
