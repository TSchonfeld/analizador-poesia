"""API del Analizador de Poesía."""

from __future__ import annotations

import logging
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from interpretacion.prompt import ErrorInterpretacion
from interpretacion.proveedor import analizar_interpretacion, proveedor_configurado
from interpretacion.reglas import detectar_recursos
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
    interpretar: bool = Field(True, description="Usar IA (Gemini o Anthropic) para recursos, temas e interpretación.")


@app.get("/api/salud")
def salud():
    return {"estado": "ok"}


def _proveedor() -> str | None:
    try:
        return proveedor_configurado()
    except ErrorInterpretacion:
        return None


@app.get("/api/config")
def config():
    """Qué puede ofrecer el servidor, para que el frontend lo muestre."""
    proveedor = _proveedor()
    return {"ia_disponible": proveedor is not None, "proveedor": proveedor}


def _solo_reglas(versos: list[str], estrofas: list[int]) -> dict:
    return {
        "origen": "reglas",
        "recursos": detectar_recursos(versos, estrofas),
        "recursos_descartados": [],
        "temas": None,
        "interpretacion": None,
        "modelo": None,
    }


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
    estrofas = [v["estrofa"] for v in resultado["metrica"]["versos"]]
    if len(versos) > MAX_VERSOS:
        raise HTTPException(422, f"El poema supera el máximo de {MAX_VERSOS} versos.")

    resultado["avisos"] = []
    resultado["interpretativo"] = None
    if solicitud.interpretar:
        try:
            resultado["interpretativo"] = {"origen": "ia", **analizar_interpretacion(versos, resultado)}
        except ErrorInterpretacion as e:
            logger.warning("Análisis interpretativo no disponible: %s", e)
            resultado["avisos"].append(str(e))
    if resultado["interpretativo"] is None:
        resultado["interpretativo"] = _solo_reglas(versos, estrofas)
    return resultado


if FRONTEND.is_dir():
    app.mount("/", StaticFiles(directory=FRONTEND, html=True), name="frontend")
