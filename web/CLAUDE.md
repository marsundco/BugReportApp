# CLAUDE.md — Karta niezgodności (webapp w `web/`)

Ta aplikacja należy do portfela WUWER (**apps.wuwer.pl**). Obowiązuje
**webapp-kit** — system projektowy w
`WUWER/Operations - Dokumente/aiWorkspaces/webapp-kit`.

> **Zanim zmienisz cokolwiek w UI lub we wdrożeniu — przeczytaj
> `webapp-kit/README.md` w całości.** Kopie `tokens.css` i `make-icons.py`
> (tu w `tools/make_icons.py`) mogą się rozjechać z kitem; gdy kit się zmienił,
> skopiuj je na nowo. Nie zmieniaj wartości w `tokens.css`.

- **Wygląd i zachowanie:** reguły §1–10 (tokeny, układ, komponenty, ikony, PWA).
- **Ikony:** wyłącznie z [Lucide](https://lucide.dev) (§5). Znak tej aplikacji:
  `bug`. Nie zmieniaj grubości kreski, nie spłaszczaj do wypełnienia. Po zmianie
  znaku uruchom `python tools/make_icons.py app/static/icon-mark.svg app/static`
  i **podbij wersję cache** w `app/static/sw.js`.
- **Kontrakt portfela (§11):** `GET /healthz` → JSON `{status, version}`;
  nasłuch `127.0.0.1:8001`; logo WUWER w nagłówku linkuje do `https://apps.wuwer.pl`.
- **Wdrożenie i sekrety:** §12 kitu + `DEPLOY-SEKRETY.md`. Ta aplikacja jest
  wdrażana przez **git** (patrz [deploy/README.md](deploy/README.md)); sekrety
  (`GOODDAY_API_TOKEN`, `IMGUR_CLIENT_ID`) w `.env` na serwerze, nigdy w repo.

Kod produkcyjny to `web/` (Python/FastAPI). Katalog `../app/` to martwy
prototyp Kotlin — nie ruszaj.
