"""Validaciones posteriores a la respuesta del modelo.

El modelo puede equivocarse aunque responda en el formato pedido. Acá se
descartan los recursos cuya cita no aparece en el poema (no se inventan
recursos), se corrige el número de verso cuando la cita está en otro, y se
recorta la interpretación a 50 palabras.
"""

from __future__ import annotations

import re
import unicodedata

from .esquema import AnalisisInterpretativo

MAX_PALABRAS_INTERPRETACION = 50
MIN_SUBTEMAS, MAX_SUBTEMAS = 2, 4


def _normalizar(texto: str) -> str:
    texto = unicodedata.normalize("NFC", texto).casefold()
    texto = re.sub(r"[^\wáéíóúüñ]+", " ", texto)
    return " ".join(texto.split())


def contar_palabras(texto: str) -> int:
    return len(texto.split())


def recortar_palabras(texto: str, maximo: int = MAX_PALABRAS_INTERPRETACION) -> tuple[str, bool]:
    palabras = texto.split()
    if len(palabras) <= maximo:
        return texto.strip(), False
    recorte = " ".join(palabras[:maximo]).rstrip(",;:—-")
    if not recorte.endswith((".", "!", "?", "…")):
        recorte += "…"
    return recorte, True


def _ubicar(cita: str, versos: list[str], desde: int, hasta: int) -> tuple[int, int] | None:
    """Devuelve (verso, hasta_verso) 1-based donde aparece la cita, o None."""
    objetivo = _normalizar(cita)
    if not objetivo:
        return None
    n = len(versos)
    normalizados = [_normalizar(v) for v in versos]

    def aparece(i: int, j: int) -> bool:
        return objetivo in " ".join(normalizados[i:j + 1])

    i, j = desde - 1, hasta - 1
    if 0 <= i <= j < n and aparece(i, j):
        return desde, hasta
    # Buscar en todo el poema (primero un verso, luego tramos de hasta 4).
    for largo in range(0, 4):
        for k in range(0, n - largo):
            if aparece(k, k + largo):
                return k + 1, k + largo + 1
    return None


def validar(analisis: AnalisisInterpretativo, versos: list[str]) -> dict:
    recursos = []
    descartados = []
    vistos = set()
    for r in analisis.recursos:
        hasta = max(r.verso, r.hasta_verso)
        ubicacion = _ubicar(r.cita, versos, r.verso, hasta)
        if ubicacion is None:
            descartados.append({"nombre": r.nombre, "cita": r.cita, "motivo": "la cita no aparece en el poema"})
            continue
        clave = (r.nombre.casefold(), _normalizar(r.cita))
        if clave in vistos:
            continue
        vistos.add(clave)
        datos = r.model_dump()
        datos["verso"], datos["hasta_verso"] = ubicacion
        datos["verso_corregido"] = ubicacion != (r.verso, hasta)
        recursos.append(datos)

    subtemas = [s.strip() for s in analisis.temas.subtemas if s.strip()][:MAX_SUBTEMAS]
    interpretacion, recortada = recortar_palabras(analisis.interpretacion)

    return {
        "recursos": recursos,
        "recursos_descartados": descartados,
        "temas": {
            "principal": analisis.temas.principal.strip(),
            "subtemas": subtemas,
            "subtemas_insuficientes": len(subtemas) < MIN_SUBTEMAS,
        },
        "interpretacion": {
            "texto": interpretacion,
            "palabras": contar_palabras(interpretacion.rstrip("…")),
            "recortada": recortada,
        },
    }
