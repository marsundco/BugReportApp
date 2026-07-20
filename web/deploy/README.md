# Deployment — Karta niezgodności

Ten sam wzorzec co LDM Board: systemd + uvicorn, bez bazy danych i bez kroku build.

## Instalacja

```bash
sudo mkdir -p /opt/karta-niezgodnosci
sudo chown wuwer:wuwer /opt/karta-niezgodnosci
git clone https://github.com/marsundco/bugreportapp.git /opt/karta-niezgodnosci
cd /opt/karta-niezgodnosci/web

python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

cp .env.example .env
chmod 600 .env          # sekrety czyta tylko właściciel usługi
nano .env               # uzupełnij GOODDAY_API_TOKEN i IMGUR_CLIENT_ID
```

```bash
sudo cp deploy/karta-niezgodnosci.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now karta-niezgodnosci
systemctl status karta-niezgodnosci
```

Sprawdzenie: `curl http://localhost:8001/healthz` → `{"status":"ok", ...}`.

## HTTPS — wymagane dla PWA i aparatu

To nie jest opcjonalne. Bez bezpiecznego kontekstu:

- przeglądarka **nie zainstaluje** aplikacji (service worker działa tylko po HTTPS),
- `capture="environment"` **nie otworzy aparatu** na tablecie.

Wyjątkiem jest `http://localhost` (dlatego development działa bez certyfikatu).
Na produkcji postaw reverse proxy (nginx/Caddy) z certyfikatem — przy dostępie
wyłącznie z sieci lokalnej wystarczy certyfikat z wewnętrznego CA
zaimportowany na tablecie.

Przykład dla Caddy (sam ogarnia certyfikat):

```
karty.wuwer.local {
    reverse_proxy 127.0.0.1:8001
}
```

## Rotacja klucza GoodDay

Sedno przejścia z Androida na webapp — bez przebudowy i bez wymiany APK:

```bash
sudo nano /opt/karta-niezgodnosci/web/.env    # zmień GOODDAY_API_TOKEN
sudo systemctl restart karta-niezgodnosci
```

Tak samo zmienia się `GOODDAY_ACTOR_USER_ID`, gdy osoba wykonująca zmianę
statusu odejdzie z firmy.

## Aktualizacja aplikacji

```bash
cd /opt/karta-niezgodnosci
git pull
web/.venv/bin/pip install -r web/requirements.txt   # tylko gdy zmienił się requirements.txt
sudo systemctl restart karta-niezgodnosci
```

Tablet dostanie nową wersję po odświeżeniu — service worker pobiera dokument
strategią network-first, a statyki mają `?v=<mtime>`.

## Instalacja na tablecie

Otwórz adres w Chrome → menu → „Zainstaluj aplikację" / „Dodaj do ekranu
głównego". Aplikacja startuje w trybie `standalone` (bez paska adresu).

## Powrót do wersji androidowej

Webapp nie usuwa aplikacji natywnej — `app/` zostaje nietknięte, a stan sprzed
zmian jest otagowany:

```bash
git checkout android-legacy-v1
```
