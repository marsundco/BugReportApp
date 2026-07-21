"""FastAPI: serwuje formularz "Karta niezgodności" i proxy do GoodDay/Imgur.

Sekrety zostają na serwerze — przeglądarka rozmawia wyłącznie z tym backendem.
"""
from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

import config
from app import goodday, imgur

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
        # Bez Client-ID nie ma sensu pokazywać przycisku zdjęcia.
        "photo_enabled": config.imgur_configured(),
    })


@app.post("/upload")
async def upload(photo: UploadFile = File(...)):
    """Przyjmij zdjęcie, wyślij na Imgur, zwróć link. Client-ID zostaje na serwerze."""
    content = await photo.read()

    if not content:
        return JSONResponse({"ok": False, "error": "Wybrany plik jest pusty."},
                            status_code=400)
    if len(content) > config.MAX_UPLOAD_BYTES:
        return JSONResponse(
            {"ok": False, "error": f"Zdjęcie jest za duże (limit {config.MAX_UPLOAD_MB} MB)."},
            status_code=413,
        )
    if not (photo.content_type or "").startswith("image/"):
        return JSONResponse({"ok": False, "error": "Wybrany plik nie jest zdjęciem."},
                            status_code=400)

    try:
        link = imgur.upload_image(photo.filename, content, photo.content_type)
    except imgur.ImgurError as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=502)
    except Exception:
        logger.exception("Nieoczekiwany błąd wysyłania zdjęcia.")
        return JSONResponse({"ok": False, "error": "Nie udało się wysłać zdjęcia."},
                            status_code=502)

    return {"ok": True, "link": link}


@app.post("/report")
async def report(
    shortDesc: str = Form(...),
    projectName: str = Form(""),
    productId: str = Form(""),
    detailedDesc: str = Form(""),
    reporterName: str = Form(""),
    imageLink: str = Form(""),
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

    links = [link for link in (imageLink or "").split("\n") if link.strip()]

    try:
        result = goodday.submit_report(
            short_desc=shortDesc,
            project_name=projectName,
            product_id=productId,
            detailed_desc=detailedDesc,
            reporter_name=reporterName,
            image_links=links,
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
        "imgur": config.imgur_configured(),
        "status_step": config.status_step_configured(),
    }
