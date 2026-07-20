# Karta niezgodności — WebApp (PWA)

Formularz zgłaszania niezgodności dla WUWER. Zastępuje aplikację androidową
(`../app/`), zachowując jej zachowanie wobec GoodDay. Jedna strona, dark theme,
mobile-first, instalowalna jako PWA na tablecie na hali.

**Aplikacja androidowa zostaje w repo** i jest odtwarzalna: `git checkout android-legacy-v1`.

## Stack

Python 3.11 · FastAPI · Jinja2 · vanilla JS + CSS · `requests`. Bez bazy danych,
bez npm, bez kroku build — celowo ten sam zestaw co w Lean Daily Management Board.

## Szybki start

```bash
python -m venv .venv
.venv/Scripts/activate            # Windows; Linux: source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env              # uzupełnij GOODDAY_API_TOKEN i IMGUR_CLIENT_ID
uvicorn app.main:app --reload --port 8001
```

Otwórz <http://localhost:8001>. Testy: `python -m pytest -q`.

## Co zmieniła modernizacja

| | Android | WebApp |
|---|---|---|
| Token GoodDay | zaszyty w kliencie (`MainActivity.kt`) | `.env` na serwerze, nigdy w przeglądarce |
| Rotacja klucza | przebudowa i wymiana APK | edycja `.env` + restart usługi |
| Szerokość pól | sztywne `400dp` (ucinane na telefonie) | płynne, `max-width: 720px` |
| Upload zdjęcia | Imgur prosto z urządzenia | Imgur przez backend (`POST /upload`) |
| Status zgłoszenia | zostawał „Zaplanowane" | ustawiany na „Nowe" |
| Instalacja | APK na każdym urządzeniu | deploy raz, „Dodaj do ekranu głównego" |

## Endpointy

| Endpoint | Opis |
|---|---|
| `GET /` | formularz |
| `POST /upload` | zdjęcie → Imgur, zwraca link (Client-ID zostaje na serwerze) |
| `POST /report` | zadanie w GoodDay + pola niestandardowe + status |
| `GET /healthz` | stan konfiguracji (bez ujawniania sekretów) |

## Integracja z GoodDay

Zgłoszenie to trzy wywołania (`app/goodday.py`):

1. `POST /2.0/tasks` — `{projectId, title, fromUserId, message}`
2. `PUT /2.0/task/{id}/custom-fields` — `l8dmpO` numer projektu, `MBYlLP` nr rysunku, `5Mk38y` zgłaszający
3. `PUT /2.0/task/{id}/status` — `{userId, statusId}` → `pcqxl7` („Nowe")

Ustalenia zweryfikowane na żywym API (2026-07-20), bo dokumentacja myli:

- **Status to `PUT`, nie `POST`.** Dokumentacja GoodDay podaje `POST` — zwraca 405.
- **`userId` przy statusie musi być prawdziwym użytkownikiem.** Placeholder → 403,
  brak pola → 400. Stąd `GOODDAY_ACTOR_USER_ID` w `.env`.
- **`fromUserId="USER1-ID"` to placeholder**, którego GoodDay po cichu ignoruje
  (dlatego 819 z 908 istniejących zgłoszeń nie ma autora). Zostawiony dla
  zgodności — wpisz prawdziwe ID, jeśli chcesz to naprawić.
- **GoodDay v2 nie ma endpointu na załączniki** (`/attachments`, `/attachment`,
  `/files`, `/upload` → 404), więc zdjęcia nadal idą na Imgur.

Statusy w projekcie: `pcqxl7` Nowe · `xuJ1Ih` Zaplanowane (domyślny) ·
`LeHvIP` W realizacij · `EOGb6O` Zakończone.

### Kroki 2 i 3 są nieblokujące

Jeśli zawiodą, użytkownik i tak widzi sukces (a szczegóły lecą do logu). Zadanie
już istnieje w GoodDay — pokazanie błędu skusiłoby do ponownej wysyłki i
zdublowałoby kartę na tablicy.

## Design

Nazwy zmiennych CSS są wspólne z LDM Board (`--bg`, `--bg-elev`, `--text-dim`,
`--border`), więc oba webappy czytają się jak jedna rodzina. Powierzchnie
przesunięte w granat marki, akcentem jest żółty z logo.

| Token | Wartość | |
|---|---|---|
| `--bg` | `#0b1220` | tło (granat/węgiel z `#00366B`) |
| `--bg-elev` | `#131c2e` | karta formularza |
| `--accent` | `#FFD966` | żółty z logo — jedyny mocny akcent |
| `--text` | `#e6edf3` | tekst (wspólny z LDMB) |

Wordmark jest monochromatyczny **z definicji**: kształt bierzemy z kanału alfa
`logo-white.png` maską CSS, a wypełniamy zmienną motywu (ta sama technika co w
LDMB). Zmiana koloru = zmiana jednej zmiennej, bez nowego pliku graficznego.
Ikony PWA generuje `tools/make_icons.py` (uruchamiać tylko po zmianie logo).

## Struktura

```
app/
  main.py         FastAPI: /, /upload, /report, /healthz, manifest, sw.js
  goodday.py      klient GoodDay (3 kroki zgłoszenia)
  imgur.py        upload zdjęć po stronie serwera
  templates/      form.html
  static/         style.css, app.js, sw.js, manifest, logo, ikony
config.py         konfiguracja z .env
tests/            test_goodday.py, test_api.py
tools/            make_icons.py (generator ikon PWA)
deploy/           systemd + instrukcja (HTTPS, rotacja klucza)
```

## Uwagi eksploatacyjne

- **HTTPS jest potrzebne do instalacji PWA**, ale nie do aparatu —
  `<input type="file" capture>` to nie `getUserMedia` i działa po zwykłym HTTP.
  Po LAN bez certyfikatu aplikacja jest w pełni używalna (ze zdjęciami); traci
  się tylko „Dodaj do ekranu głównego". Szczegóły w [deploy/README.md](deploy/README.md).
- **Brak kolejki offline** — świadomie. Urządzenia są online w chwili zgłoszenia,
  a ciche wysyłanie po godzinach dawałoby duplikaty i „znikające" zgłoszenia.
