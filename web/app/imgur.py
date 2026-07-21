"""Upload zdjęć na Imgur — po stronie SERWERA (Client-ID nie trafia do przeglądarki).

Dlaczego nadal Imgur, skoro celem było uproszczenie? Bo GoodDay API v2 nie ma
endpointu do załączników — sprawdzone na żywym API: /task/{id}/attachments,
/attachment, /files i /upload zwracają 404. Gdyby GoodDay to kiedyś dodał, ten
moduł znika, a `submit_report` dostaje plik zamiast linku.
"""
from __future__ import annotations

import logging

import requests

import config

logger = logging.getLogger("karty.imgur")


class ImgurError(RuntimeError):
    """Błąd uploadu, z komunikatem nadającym się dla użytkownika."""


def upload_image(filename: str, content: bytes, content_type: str) -> str:
    """Wyślij obraz na Imgur i zwróć publiczny link."""
    if not config.imgur_configured():
        raise ImgurError("Wysyłanie zdjęć nie jest skonfigurowane na serwerze.")

    resp = requests.post(
        f"{config.IMGUR_BASE_URL.rstrip('/')}/upload",
        headers={"Authorization": f"Client-ID {config.IMGUR_CLIENT_ID}"},
        files={"image": (filename or "photo.jpg", content, content_type or "image/jpeg")},
        timeout=config.http_timeout(),
    )
    if not resp.ok:
        logger.error("Imgur odrzucił upload: %s %s", resp.status_code, resp.text[:500])
        raise ImgurError(f"Nie udało się wysłać zdjęcia. Spróbuj ponownie "
                         f"(błąd {resp.status_code}).")

    link = ((resp.json() or {}).get("data") or {}).get("link")
    if not link:
        raise ImgurError("Zdjęcie zostało wysłane, ale serwer nie zwrócił "
                         "odnośnika. Spróbuj ponownie.")

    logger.info("Zdjęcie wysłane: %s", link)
    return link
