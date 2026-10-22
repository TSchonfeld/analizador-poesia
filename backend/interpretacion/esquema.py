"""Esquema JSON que el modelo debe respetar para las secciones C, D y E."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Categoria = Literal["fónicos", "semánticos", "léxicos", "gramaticales", "sintácticos"]
Confianza = Literal["alta", "media", "baja"]


class Recurso(BaseModel):
    nombre: str = Field(description="Nombre del recurso en la terminología hispánica, p. ej. «metáfora», «hipérbaton».")
    categoria: Categoria
    verso: int = Field(description="Número del verso donde empieza la cita (1 = primer verso).")
    hasta_verso: int = Field(description="Número del verso donde termina la cita; igual a «verso» si ocupa uno solo.")
    cita: str = Field(description="Fragmento copiado literalmente del poema, sin cambiar ni una letra.")
    explicacion: str = Field(description="Explicación breve (una o dos oraciones) del efecto expresivo del recurso.")
    confianza: Confianza


class Temas(BaseModel):
    principal: str = Field(description="Tema principal, en una frase breve.")
    subtemas: list[str] = Field(description="Entre dos y cuatro subtemas, cada uno en una frase breve.")


class AnalisisInterpretativo(BaseModel):
    recursos: list[Recurso]
    temas: Temas
    interpretacion: str = Field(description="Posibles líneas de lectura e interpretación, en 50 palabras como máximo.")
