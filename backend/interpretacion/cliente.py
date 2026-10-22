"""Análisis interpretativo (secciones C, D y E) mediante la API de Anthropic."""

from __future__ import annotations

import os

import anthropic
import pydantic

from .esquema import AnalisisInterpretativo
from .validacion import validar

MODELO_POR_DEFECTO = "claude-sonnet-5-5"

SISTEMA = """Sos un especialista en retórica y métrica española que prepara materiales para docentes de nivel secundario. Analizás poemas en español con la terminología de la tradición hispánica (Quilis, Navarro Tomás, Lausberg en su versión española).

Tu tarea es identificar los recursos poéticos, los temas y las posibles líneas de lectura del poema que te pasan. La métrica y la versificación ya fueron calculadas por un motor determinista; te las paso como contexto para que no las contradigas, pero no tenés que repetirlas.

Recursos, agrupados en cinco categorías:
- fónicos: aliteración, onomatopeya, paronomasia;
- semánticos: metáfora, comparación o símil, personificación o prosopopeya, hipérbole, antítesis, oxímoron, sinestesia, metonimia, sinécdoque, ironía, apóstrofe, etc.;
- léxicos: epítetos, campos semánticos, arcaísmos, neologismos, cultismos;
- gramaticales: enálage, polisíndeton, asíndeton;
- sintácticos: hipérbaton, anáfora, paralelismo, quiasmo, encabalgamiento, elipsis, epífora, retruécano.

Reglas:
1. No inventes recursos. Reportá solo los que tengan evidencia textual clara en el poema. Es preferible omitir un recurso dudoso a forzarlo.
2. La «cita» tiene que ser un fragmento copiado literalmente del poema, letra por letra. Si el recurso abarca varios versos, citá el fragmento completo y marcá «verso» y «hasta_verso».
3. Los números de verso son los que figuran entre corchetes, contando desde 1.
4. La explicación es breve (una o dos oraciones) y dice qué efecto expresivo produce el recurso en este poema, no una definición de manual.
5. Usá «confianza» = «alta» cuando el recurso es evidente, «media» cuando es una lectura razonable pero discutible, y «baja» cuando es posible pero dudoso.
6. El tema principal es una frase breve. Los subtemas son entre dos y cuatro, también frases breves.
7. La interpretación ofrece posibles líneas de lectura en 50 palabras como máximo, en un registro apto para estudiantes de secundaria. Presentala como lectura posible, no como la única.
8. Escribí en español."""


class ErrorInterpretacion(Exception):
    """Error al obtener o validar el análisis interpretativo."""


def _contexto_metrico(metrica: dict | None) -> str:
    if not metrica:
        return ""
    versif = metrica.get("versificacion", {})
    met = metrica.get("metrica", {})
    lineas = ["Datos métricos calculados:"]
    if met.get("metros"):
        lineas.append(f"- Metros: {', '.join(str(m) for m in met['metros'])} sílabas")
    if versif.get("rima"):
        lineas.append(f"- Rima {versif['rima']['tipo']}, esquema {versif['rima']['esquema']}")
    if versif.get("composicion"):
        lineas.append(f"- Composición: {versif['composicion']['tipo']}")
    return "\n".join(lineas)


def construir_mensaje(versos: list[str], metrica: dict | None = None) -> str:
    numerado = "\n".join(f"[{i}] {v}" for i, v in enumerate(versos, start=1))
    partes = ["Poema (cada verso con su número entre corchetes):", "", numerado]
    contexto = _contexto_metrico(metrica)
    if contexto:
        partes += ["", contexto]
    return "\n".join(partes)


def crear_cliente() -> anthropic.Anthropic:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise ErrorInterpretacion(
            "Falta configurar la variable de entorno ANTHROPIC_API_KEY; "
            "las secciones de recursos, temas e interpretación no están disponibles."
        )
    return anthropic.Anthropic()


def analizar_interpretacion(versos: list[str], metrica: dict | None = None,
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
