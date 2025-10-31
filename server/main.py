from pathlib import Path
from typing import Optional

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os


load_dotenv()

RECAPTCHA_SITEKEY: str = os.getenv(
  "RECAPTCHA_SITEKEY",
  "6LeIxAcTAAAAAJcZVRqyHh71UMIEGNQ_MXjiZKhI",
)
RECAPTCHA_SECRET: str = os.getenv(
  "RECAPTCHA_SECRET",
  "6LeIxAcTAAAAAGG-vFI1TnRWxMZNFuojJ4WifJWe",
)
GOOGLE_VERIFY_URL: str = os.getenv(
  "GOOGLE_VERIFY_URL",
  "https://www.google.com/recaptcha/api/siteverify",
)


BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(title="Google reCAPTCHA v2 avec FastAPI")

app.add_middleware(
  CORSMiddleware,
  allow_origins=["*"],
  allow_credentials=True,
  allow_methods=["*"],
  allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@app.get("/")
async def index(request: Request):
  return templates.TemplateResponse(
    "index.html",
    {
      "request": request,
      "site_key": RECAPTCHA_SITEKEY,
    },
  )


@app.get("/index")
async def redirect_index() -> RedirectResponse:
  return RedirectResponse(url="/", status_code=307)


@app.post("/verify")
async def verify_form(
  email: str = Form(...),
  message: str = Form(...),
  g_recaptcha_response: Optional[str] = Form(alias="g-recaptcha-response"),
):
  if not email or not message:
    raise HTTPException(status_code=400, detail="Champs requis manquants")

  if not g_recaptcha_response:
    raise HTTPException(status_code=400, detail="reCAPTCHA manquant")

  try:
    async with httpx.AsyncClient(timeout=10) as client:
      verify_resp = await client.post(
        GOOGLE_VERIFY_URL,
        data={
          "secret": RECAPTCHA_SECRET,
          "response": g_recaptcha_response,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
      )
    data = verify_resp.json()
  except Exception as exc:
    raise HTTPException(status_code=502, detail=f"Erreur de vérification: {exc}")

  if not data.get("success"):
    return JSONResponse(
      status_code=400,
      content={
        "ok": False,
        "error": "Échec reCAPTCHA",
        "details": data.get("error-codes", []),
      },
    )

  return {"ok": True, "message": "Formulaire validé", "email": email}


@app.get("/health")
async def health():
  return {"status": "ok"}


if __name__ == "__main__":
  import uvicorn
  uvicorn.run("server.main:app", host="127.0.0.1", port=8000, reload=True)


