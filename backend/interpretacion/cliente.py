"""Proveedor Anthropic para el análisis interpretativo (secciones C, D y E)."""

from __future__ import annotations

import os

import anthropic
import pydantic

from .esquema import AnalisisInterpretativo
from .prompt import SISTEMA, ErrorInterpretacion, construir_mensaje
from .validacion import validar

MODELO_POR_DEFECTO = "claude-sonnet-5-5"


def crear_cliente() -> anthropic.Anthropic:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise ErrorInterpretacion(
            "Falta configurar la variable de entorno ANTHROPIC_API_KEY; "
            "las secciones de recursos, temas e interpretación no están disponibles."
        )
    return anthropic.Anthropic()


def analizar_con_anthropic(versos: list[str], metrica: dict | None = None,
                           cliente: anthropic.Anthropic | None = None) -> dict:
    """Pide al modelo las secciones C, D y E y las valida contra el poema."""
    cliente = cliente or crear_cliente()
    modelo = os.environ.get("ANTHROPIC_MODEL", MODELO_POR_DEFECTO)
    try:
        respuesta = cliente.beta.messages.parse(
            model=modelo,
            max_tokens=16000,
            system=SISTEMA,
            messages=[{"role": "user", "content": construir_mensaje(versos, metrica)}],
            output_format=AnalisisInterpretativo,
            output_config={"effort": os.environ.get("ANTHROPIC_EFFORT", "medium")},
            # Si el modelo declina la solicitud, la API la reintenta con otro modelo.
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
        )
    except anthropic.AuthenticationError as e:
        raise ErrorInterpretacion("La API key de Anthropic no es válida.") from e
    except anthropic.RateLimitError as e:
        raise ErrorInterpretacion("Se alcanzó el límite de uso de la API. Probá de nuevo en unos minutos.") from e
    except anthropic.APIStatusError as e:
        raise ErrorInterpretacion(f"La API de Anthropic devolvió un error ({e.status_code}).") from e
    except anthropic.APIConnectionError as e:
        raise ErrorInterpretacion("No se pudo conectar con la API de Anthropic.") from e
    except pydantic.ValidationError as e:
        raise ErrorInterpretacion("La respuesta del modelo no respetó el esquema JSON.") from e

    if respuesta.stop_reason == "refusal":
        raise ErrorInterpretacion("El modelo no pudo analizar este texto.")
    if respuesta.stop_reason == "max_tokens":
        raise ErrorInterpretacion("La respuesta del modelo quedó incompleta.")
    analisis = respuesta.parsed_output
    if analisis is None:
        raise ErrorInterpretacion("La respuesta del modelo no respetó el esquema JSON.")

    resultado = validar(analisis, versos)
    resultado["modelo"] = respuesta.model
    return resultado
