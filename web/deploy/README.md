# Wdrożenie — Karta niezgodności

Aplikacja należy do portfela **apps.wuwer.pl**. Ogólne zasady wdrożeń (katalogi,
nazwy usług, reverse proxy, certyfikat) opisuje `webapp-kit/README.md`, §11–13.
Tu jest tylko to, co dotyczy tej aplikacji. Sekrety (hasło do serwera, tokeny)
są w poufnym `DEPLOY-SEKRETY.md` obok kitu — nigdy w tym repo.

## Jak to stoi na produkcji

| | |
|---|---|
| Serwer | `192.168.0.19` (Debian), dostęp `ssh root@192.168.0.19` |
| Kod | checkout gita w `/srv/wuwer/karty`, gałąź `claude/app-modernization-strategy-0clbzc` |
| Katalog roboczy | `/srv/wuwer/karty/web` (venv w `web/.venv`) |
| Sekrety | `/srv/wuwer/karty/web/.env` (`chmod 600`) — wzór w `../.env.example` |
| Usługa | `wuwer-karty` (jednostka: [wuwer-karty.service](wuwer-karty.service)) |
| Nasłuch | `0.0.0.0:8001` — reverse proxy portfela łączy się po adresie LAN |
| Adres | **https://karty.apps.wuwer.pl** (certyfikat wildcard portfela) |

HTTPS zapewnia proxy portfela z zaufanym certyfikatem `*.apps.wuwer.pl`, więc
instalacja na tablecie („Dodaj do ekranu głównego") działa bez żadnej
konfiguracji po stronie aplikacji.

## Aktualizacja (zwykły przypadek)

```bash
ssh root@192.168.0.19
cd /srv/wuwer/karty
git status --porcelain            # musi być puste — na serwerze nic nie edytujemy
git pull --ff-only origin claude/app-modernization-strategy-0clbzc
web/.venv/bin/pip install -r web/requirements.txt   # tylko gdy zmienił się requirements.txt
systemctl restart wuwer-karty
curl -s http://127.0.0.1:8001/healthz   # {"status":"ok","goodday":true,...}
```

Statyki mają w adresie `?v=<mtime>`, a service worker pobiera dokument
strategią network-first — tablet dostanie nową wersję po odświeżeniu. Po zmianie
ikon podbij wersję cache w `app/static/sw.js`.

**Wycofanie:** `git log --oneline` → `git checkout <poprzedni-commit>` →
`systemctl restart wuwer-karty`. Powrót na gałąź: `git checkout
claude/app-modernization-strategy-0clbzc`.

## Instalacja od zera

Zwykle wystarcza `deploy_app.sh` z kitu (§13). Ręcznie:

```bash
mkdir -p /srv/wuwer/karty && cd /srv/wuwer/karty
git clone -b claude/app-modernization-strategy-0clbzc https://github.com/marsundco/BugReportApp.git .
cd web
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env && chmod 600 .env && nano .env   # GOODDAY_API_TOKEN
cp deploy/wuwer-karty.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now wuwer-karty
```

## Sekrety i ich rotacja

Jedyny sekret to **`GOODDAY_API_TOKEN`** — obsługuje zgłoszenia i zdjęcia
(załączniki GoodDay). Wcześniej był jeszcze `IMGUR_CLIENT_ID`; od 2026-10 nie
jest potrzebny.

```bash
nano /srv/wuwer/karty/web/.env        # zmień GOODDAY_API_TOKEN
systemctl restart wuwer-karty
```

Tak samo zmienia się `GOODDAY_ACTOR_USER_ID`, gdy osoba wykonująca zmianę
statusu odejdzie z firmy.

## Powrót do wersji z tabletu

Webapp nie usuwa aplikacji mobilnej. Faktyczna wersja z tabletu to aplikacja
**Flutter** — gałąź `android-tablet-flutter`, tag `android-tablet-v1`
(kopia `P-Kupiec/IssueReportApp`, gałąź `builtInCamera`, commit `1eb9433`).

Tag `android-legacy-v1` wskazuje starszy prototyp Kotlin, który najpewniej
się nie kompiluje — nie traktuj go jako wersji zapasowej.
