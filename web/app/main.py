"""FastAPI: serwuje formularz "Karta niezgodności" i proxy do GoodDay.

Sekrety zostają na serwerze — przeglądarka rozmawia wyłącznie z tym backendem.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

import config
from app import goodday

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("karty")

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


def _asset_version() -> str:
    """Sygnatura cache-busting = najnowszy mtime plików w /static (jak w LDMB).

    Na tablecie w kiosku/PWA stary CSS potrafi zostać w cache — `?v=...` to wymusza.
    """
    try:
        mtimes = [p.stat().st_mtime for p in STATIC_DIR.rglob("*") if p.is_file()]
        return str(int(max(mtimes))) if mtimes else "0"
    except (OSError, ValueError):
        return "0"


app = FastAPI(title="Karta niezgodności")
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(request, "form.html", {
        "request": request,
        "asset_v": _asset_version(),
        # Zdjęcia idą jako załączniki GoodDay — bez tokenu nie ma ich dokąd wysłać.
        "photo_enabled": config.goodday_configured(),
    })


@app.post("/upload")
async def upload(photo: UploadFile = File(...)):
    """Przyjmij zdjęcie i wyślij je do GoodDay jako załącznik (jeszcze bez karty).

    Zwraca wpis do `attachments`, który przeglądarka odeśle przy zgłoszeniu.
    Token GoodDay zostaje na serwerze."""
    content = await photo.read()

    if not content:
        return JSONResponse({"ok": False, "error": "Wybrany plik jest pusty."},
                            status_code=400)
    if len(content) > config.MAX_UPLOAD_BYTES:
        return JSONResponse(
            {"ok": False, "error": f"Zdjęcie jest za duże (limit {config.MAX_UPLOAD_MB} MB)."},
            status_code=413,
        )
    if not config.goodday_configured():
        return JSONResponse({"ok": False, "error": "Wysyłanie zdjęć nie jest skonfigurowane."},
                            status_code=503)
    if not (photo.content_type or "").startswith("image/"):
        return JSONResponse({"ok": False, "error": "Wybrany plik nie jest zdjęciem."},
                            status_code=400)

    try:
        attachment = goodday.upload_attachment(photo.filename, content, photo.content_type)
    except goodday.GoodDayError as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=502)
    except Exception:
        logger.exception("Nieoczekiwany błąd wysyłania zdjęcia.")
        return JSONResponse({"ok": False, "error": "Nie udało się wysłać zdjęcia."},
                            status_code=502)

    return {"ok": True, "file": attachment}


def _parse_attachments(raw: str) -> list[dict] | None:
    """Lista załączników odesłana przez przeglądarkę (JSON). None = zły format.

    Przepuszczamy tylko znane pola i sprawdzamy fileId — wartości przyszły od
    klienta, a trafią do API GoodDay."""
    if not raw.strip():
        return []
    try:
        items = json.loads(raw)
    except ValueError:
        return None
    if not isinstance(items, list) or len(items) > goodday.MAX_ATTACHMENTS:
        return None
    out = []
    for it in items:
        if not isinstance(it, dict):
            return None
        file_id, name = it.get("fileId"), it.get("name")
        if not (isinstance(file_id, str) and goodday.FILE_ID_RE.match(file_id)
                and isinstance(name, str) and 0 < len(name) <= 255):
            return None
        entry = {"fileId": file_id, "name": name}
        if isinstance(it.get("size"), int) and it["size"] >= 0:
            entry["size"] = it["size"]
        if isinstance(it.get("mime"), str) and len(it["mime"]) <= 100:
            entry["mime"] = it["mime"]
        out.append(entry)
    return out


@app.post("/report")
async def report(
    shortDesc: str = Form(...),
    projectName: str = Form(""),
    productId: str = Form(""),
    detailedDesc: str = Form(""),
    reporterName: str = Form(""),
    attachments: str = Form(""),
):
    """Utwórz zgłoszenie w GoodDay (zadanie + pola + status)."""
    if not config.goodday_configured():
        return JSONResponse(
            {"ok": False, "error": "Aplikacja nie jest poprawnie skonfigurowana. "
                                   "Zgłoś to osobie odpowiedzialnej za aplikację."},
            status_code=503,
        )
    if not shortDesc.strip():
        return JSONResponse({"ok": False, "error": "Opis niezgodności jest wymagany."},
                            status_code=400)

    files = _parse_attachments(attachments)
    if files is None:
        return JSONResponse({"ok": False, "error": "Nieprawidłowa lista zdjęć."},
                            status_code=400)

    try:
        result = goodday.submit_report(
            short_desc=shortDesc,
            project_name=projectName,
            product_id=productId,
            detailed_desc=detailedDesc,
            reporter_name=reporterName,
            attachments=files,
        )
    except goodday.GoodDayError as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=502)
    except Exception:
        logger.exception("Nieoczekiwany błąd zgłoszenia.")
        return JSONResponse({"ok": False, "error": "Nie udało się wysłać zgłoszenia."},
                            status_code=502)

    return {"ok": True, **result}


@app.get("/manifest.webmanifest", include_in_schema=False)
async def manifest():
    # Serwowany z roota, żeby zakres PWA obejmował całą aplikację.
    return FileResponse(STATIC_DIR / "manifest.webmanifest",
                        media_type="application/manifest+json")


@app.get("/sw.js", include_in_schema=False)
async def service_worker():
    # Service worker MUSI być serwowany z roota — inaczej nie obejmie zakresem "/".
    return FileResponse(STATIC_DIR / "sw.js", media_type="application/javascript")


@app.get("/healthz")
async def healthz():
    """Stan konfiguracji — bez ujawniania samych sekretów."""
    return {
        "status": "ok" if config.goodday_configured() else "degraded",
        "goodday": config.goodday_configured(),
        "status_step": config.status_step_configured(),
    }
