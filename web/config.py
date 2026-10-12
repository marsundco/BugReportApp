"""Konfiguracja aplikacji — ładowana z .env (przez python-dotenv) i zmiennych środowiskowych.

WSZYSTKIE sekrety (token GoodDay) żyją TUTAJ — po stronie serwera.
Nigdy nie trafiają do przeglądarki i nigdy nie są commitowane (patrz .gitignore).
Rotacja klucza = edycja .env + restart usługi. Bez przebudowy klienta.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Katalog projektu (ten plik leży w root aplikacji webowej).
BASE_DIR = Path(__file__).resolve().parent

# Wczytaj .env jeśli istnieje (na produkcji zmienne mogą pochodzić z systemd Environment=).
load_dotenv(BASE_DIR / ".env")

# --- Zachowanie aplikacji ---
PORT = int(os.getenv("PORT", "8001"))

# --- GoodDay ---
GOODDAY_BASE_URL = os.getenv("GOODDAY_BASE_URL", "https://api.goodday.work")
GOODDAY_API_TOKEN = os.getenv("GOODDAY_API_TOKEN", "")
GOODDAY_PROJECT_ID = os.getenv("GOODDAY_PROJECT_ID", "SnVrYd")

# Autor zadania wysyłany przy tworzeniu. W aplikacji androidowej była tu wartość
# "USER1-ID" — to placeholder, którego GoodDay po cichu ignoruje (dlatego 819 z 908
# zgłoszeń nie ma autora). Zachowujemy zgodność zachowania: create działa tak jak
# dotąd, a prawdziwy użytkownik potrzebny jest wyłącznie do zmiany statusu (niżej).
GOODDAY_FROM_USER_ID = os.getenv("GOODDAY_FROM_USER_ID", "USER1-ID")

# Użytkownik-wykonawca zmiany statusu. MUSI być prawdziwym ID z GoodDay:
# placeholder daje 403, brak pola daje 400 (sprawdzone na żywym API).
# Trzymany w .env właśnie po to, żeby zmiana osoby nie wymagała zmiany kodu.
GOODDAY_ACTOR_USER_ID = os.getenv("GOODDAY_ACTOR_USER_ID", "")

# Status nadawany nowym zgłoszeniom. Projekt domyślnie ustawia "Zaplanowane"
# (xuJ1Ih), a chcemy "Nowe" (pcqxl7) — stąd osobny krok po utworzeniu zadania.
GOODDAY_NEW_STATUS_ID = os.getenv("GOODDAY_NEW_STATUS_ID", "pcqxl7")

# ID pól niestandardowych w projekcie (przeniesione 1:1 z aplikacji androidowej).
GOODDAY_FIELD_PROJECT = os.getenv("GOODDAY_FIELD_PROJECT", "l8dmpO")   # Numer projektu
GOODDAY_FIELD_PRODUCT = os.getenv("GOODDAY_FIELD_PRODUCT", "MBYlLP")   # ID produktu / nr rysunku
GOODDAY_FIELD_REPORTER = os.getenv("GOODDAY_FIELD_REPORTER", "5Mk38y")  # Imię i nazwisko

# --- Zdjęcia ---
# Od 2026-10 zdjęcia są natywnymi załącznikami GoodDay (endpoint
# /2.0/attachments/upload-urls). Wcześniej szły na Imgur, bo GoodDay API v2 nie
# miało załączników. Osobny klucz nie jest już potrzebny — wystarcza token GoodDay.

# --- Limity uploadu ---
MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "10"))
MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024

# Timeouty HTTP (sekundy): (connect, read).
HTTP_CONNECT_TIMEOUT_SEC = int(os.getenv("HTTP_CONNECT_TIMEOUT_SEC", "10"))
HTTP_READ_TIMEOUT_SEC = int(os.getenv("HTTP_READ_TIMEOUT_SEC", "60"))


def http_timeout() -> tuple[int, int]:
    return (HTTP_CONNECT_TIMEOUT_SEC, HTTP_READ_TIMEOUT_SEC)


def goodday_configured() -> bool:
    """True gdy ustawiono token — bez niego /report nie ma jak działać."""
    return bool(GOODDAY_API_TOKEN)


def status_step_configured() -> bool:
    """True gdy da się ustawić status (potrzebny prawdziwy użytkownik-wykonawca)."""
    return bool(GOODDAY_ACTOR_USER_ID and GOODDAY_NEW_STATUS_ID)
