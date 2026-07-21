"""Klient REST do GoodDay (API v2). Cała komunikacja z tokenem dzieje się tutaj.

Trzy kroki zgłoszenia — dokładnie ten sam wzorzec co w aplikacji androidowej,
plus nowy krok statusu:

1. POST /2.0/tasks                       -> utworzenie zadania
2. PUT  /2.0/task/{id}/custom-fields     -> uzupełnienie 3 pól niestandardowych
3. PUT  /2.0/task/{id}/status            -> ustawienie statusu na "Nowe"

UWAGA do kroku 3: oficjalna dokumentacja GoodDay podaje dla statusu metodę POST.
To nieprawda — POST zwraca 405 Method Not Allowed. Działa wyłącznie PUT
(zweryfikowane na żywym API, 2026-07-20). Nie "poprawiaj" tego na POST.
"""
from __future__ import annotations

import logging

import requests

import config

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


def create_task(title: str, message: str) -> dict:
    """Krok 1: utwórz zadanie. Zwraca surową odpowiedź GoodDay (z `id`, `shortId`)."""
    payload = {
        "projectId": config.GOODDAY_PROJECT_ID,
        "title": title,
        "fromUserId": config.GOODDAY_FROM_USER_ID,
        "message": message,
    }
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
                  image_links: list[str] | None = None) -> dict:
    """Pełne zgłoszenie: utwórz zadanie, ustaw pola, ustaw status.

    Zwraca {"taskId", "shortId", "warnings"}.

    Kroki 2 i 3 są NIEBLOKUJĄCE: jeśli zawiodą, zgłoszenie i tak istnieje w GoodDay
    i zostaje zgłoszone jako sukces (z ostrzeżeniem w logu). Zwrócenie użytkownikowi
    błędu skusiłoby go do ponownego wysłania — a to zduplikowałoby kartę na tablicy.
    """
    links = image_links or []
    message = detailed_desc.strip()
    if links:
        message = (message + "\n" + "\n".join(links)).strip()

    task = create_task(title=short_desc.strip(), message=message)
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

    logger.info("Zgłoszenie utworzone: %s (#%s), ostrzeżenia: %s",
                task_id, short_id, warnings or "brak")
    return {"taskId": task_id, "shortId": short_id, "warnings": warnings}
