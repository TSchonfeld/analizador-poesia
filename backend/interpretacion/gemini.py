"""Proveedor Gemini (Google) para el análisis interpretativo (secciones C, D y E).

La API de Gemini tiene una capa gratuita: alcanza con una API key creada en
Google AI Studio, sin tarjeta.
"""

from __future__ import annotations

import os

import pydantic
from google import genai
from google.genai import errors, types

from .esquema import AnalisisInterpretativo
from .prompt import SISTEMA, ErrorInterpretacion, construir_mensaje
from .validacion import validar

# Alias que Google mantiene apuntando al modelo Flash vigente.
MODELO_POR_DEFECTO = "gemini-flash-latest"


def crear_cliente() -> genai.Client:
    if not os.environ.get("GEMINI_API_KEY"):
        raise ErrorInterpretacion(
            "Falta configurar la variable de entorno GEMINI_API_KEY; "
            "las secciones de recursos, temas e interpretación no están disponibles."
        )
    return genai.Client(api_key=os.environ["GEMINI_API_KEY"])


def analizar_con_gemini(versos: list[str], metrica: dict | None = None,
                        cliente: genai.Client | None = None) -> dict:
    """Pide al modelo las secciones C, D y E y las valida contra el poema."""
    cliente = cliente or crear_cliente()
    modelo = os.environ.get("GEMINI_MODEL", MODELO_POR_DEFECTO)
    try:
        respuesta = cliente.models.generate_content(
            model=modelo,
            contents=construir_mensaje(versos, metrica),
            config=types.GenerateContentConfig(
                system_instruction=SISTEMA,
                response_mime_type="application/json",
                response_schema=AnalisisInterpretativo,
            ),
        )
    except errors.ClientError as e:
        if e.code == 429:
            raise ErrorInterpretacion(
                "Se alcanzó el límite de la capa gratuita de Gemini. Probá de nuevo en unos minutos."
            ) from e
        if e.code in (400, 401, 403) and "API key" in str(e):
            raise ErrorInterpretacion("La API key de Gemini no es válida.") from e
        raise ErrorInterpretacion(f"La API de Gemini devolvió un error ({e.code}).") from e
    except errors.ServerError as e:
        raise ErrorInterpretacion(f"La API de Gemini no está disponible ({e.code}). Probá más tarde.") from e
    except pydantic.ValidationError as e:
        raise ErrorInterpretacion("La respuesta del modelo no respetó el esquema JSON.") from e

    analisis = respuesta.parsed
    if not isinstance(analisis, AnalisisInterpretativo):
        try:
            analisis = AnalisisInterpretativo.model_validate_json(respuesta.text or "")
        except pydantic.ValidationError as e:
            raise ErrorInterpretacion("La respuesta del modelo no respetó el esquema JSON.") from e

    resultado = validar(analisis, versos)
    resultado["modelo"] = getattr(respuesta, "model_version", None) or modelo
    return resultado
