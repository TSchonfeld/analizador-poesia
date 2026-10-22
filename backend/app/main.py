"""API del Analizador de Poesía."""

from __future__ import annotations

import logging
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from interpretacion.cliente import ErrorInterpretacion, analizar_interpretacion
from metrica.analisis import analizar_metrica

load_dotenv()

logger = logging.getLogger("analizador")

MAX_CARACTERES = 8000
MAX_VERSOS = 200
FRONTEND = Path(__file__).resolve().parents[2] / "frontend"

app = FastAPI(
    title="Analizador de Poesía",
    description="Análisis métrico, de versificación y retórico de poemas en español.",
    version="0.1.0",
)


class Solicitud(BaseModel):
    texto: str = Field(..., description="Poema en español; las estrofas se separan con una línea en blanco.")
    interpretar: bool = Field(True, description="Incluir recursos, temas e interpretación (usa la API de Anthropic).")


@app.get("/api/salud")
def salud():
    return {"estado": "ok"}


@app.post("/api/analizar")
def analizar(solicitud: Solicitud):
    texto = solicitud.texto.strip()
    if not texto:
        raise HTTPException(422, "Pegá un poema para analizar.")
    if len(texto) > MAX_CARACTERES:
        raise HTTPException(422, f"El texto supera el máximo de {MAX_CARACTERES} caracteres.")
    try:
        resultado = analizar_metrica(texto)
    except ValueError as e:
        raise HTTPException(422, str(e)) from e
    versos = [v["texto"] for v in resultado["metrica"]["versos"]]
    if len(versos) > MAX_VERSOS:
        raise HTTPException(422, f"El poema supera el máximo de {MAX_VERSOS} versos.")

    resultado["interpretativo"] = None
    resultado["avisos"] = []
    if solicitud.interpretar:
        try:
            resultado["interpretativo"] = analizar_interpretacion(versos, resultado)
        except ErrorInterpretacion as e:
            logger.warning("Análisis interpretativo no disponible: %s", e)
            resultado["avisos"].append(str(e))
    return resultado


if FRONTEND.is_dir():
    app.mount("/", StaticFiles(directory=FRONTEND, html=True), name="frontend")
