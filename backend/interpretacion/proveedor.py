"""Elección del proveedor de IA para las secciones C, D y E.

Se elige con la variable IA_PROVEEDOR («anthropic» o «gemini»). Si no está
definida, se usa el primero que tenga API key: Anthropic y después Gemini.
Sin ninguna key, la app sigue funcionando con la métrica, la versificación
y los recursos formales que se detectan por reglas.
"""

from __future__ import annotations

import os

from .prompt import ErrorInterpretacion

PROVEEDORES = {
    "anthropic": "ANTHROPIC_API_KEY",
    "gemini": "GEMINI_API_KEY",
}


def proveedor_configurado() -> str | None:
    elegido = os.environ.get("IA_PROVEEDOR", "").strip().lower()
    if elegido:
        if elegido not in PROVEEDORES:
            raise ErrorInterpretacion(
                f"IA_PROVEEDOR debe ser «anthropic» o «gemini» (vale «{elegido}»)."
            )
        return elegido if os.environ.get(PROVEEDORES[elegido]) else None
    for nombre, variable in PROVEEDORES.items():
        if os.environ.get(variable):
            return nombre
    return None


def analizar_interpretacion(versos: list[str], metrica: dict | None = None) -> dict:
    proveedor = proveedor_configurado()
    if proveedor == "anthropic":
        from .cliente import analizar_con_anthropic

        return analizar_con_anthropic(versos, metrica)
    if proveedor == "gemini":
        from .gemini import analizar_con_gemini

        return analizar_con_gemini(versos, metrica)
    raise ErrorInterpretacion(
        "No hay una API key configurada (GEMINI_API_KEY o ANTHROPIC_API_KEY): "
        "los temas y la interpretación no están disponibles y los recursos se detectan solo por reglas."
    )
