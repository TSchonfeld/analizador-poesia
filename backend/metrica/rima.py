"""Rima: terminación desde la última vocal tónica, tipo y esquema."""

from __future__ import annotations

import unicodedata
from collections import Counter
from dataclasses import dataclass

from .silabeo import Palabra, VOCALES_ACENTUADAS, VOCALES_FUERTES, silabear
from .verso import PALABRA_RE


@dataclass
class TerminacionRima:
    texto: str  # terminación tal como se escribe, p. ej. «esto»
    consonante: str  # clave fonológica para la rima consonante
    asonante: str  # vocales que cuentan para la asonancia, p. ej. «e-o»


@dataclass
class Rima:
    tipo: str  # consonante, asonante, libre
    esquema: list[str]  # letra por verso («A», «b», «-»)
    terminaciones: list[TerminacionRima | None]
    confianza: str

    @property
    def esquema_texto(self) -> str:
        return "".join(self.esquema)


def _sin_tilde(c: str) -> str:
    return unicodedata.normalize("NFD", c)[0]


def _vocal_tonica(palabra: Palabra) -> int:
    """Índice (en la palabra) de la vocal tónica de la sílaba acentuada."""
    p = palabra.texto.lower()
    silaba = palabra.silabas[palabra.acento_lexico]
    nucleo = silaba.nucleo
    for i in nucleo:
        if p[i] in VOCALES_ACENTUADAS:
            return i
    fuertes = [i for i in nucleo if p[i] in VOCALES_FUERTES]
    if fuertes:
        return fuertes[0]
    return nucleo[-1] if nucleo else 0


def _fonologizar(t: str) -> str:
    """Clave fonológica aproximada para comparar rimas consonantes."""
    t = t.lower()
    salida = []
    i = 0
    while i < len(t):
        c = t[i]
        sig = t[i + 1] if i + 1 < len(t) else ""
        if c == "h":
            pass
        elif c == "v":
            salida.append("b")
        elif c == "q" and sig == "u":
            salida.append("k")
            i += 1
        elif c == "c":
            salida.append("z" if sig in "eéií" else "k")
        elif c == "g" and sig == "u" and i + 2 < len(t) and t[i + 2] in "eéií":
            salida.append("g")
            i += 1
        elif c == "g" and sig in "eéií":
            salida.append("j")
        elif c == "x":
            salida.append("ks")
        elif c == "y" and not sig:
            salida.append("i")
        elif c == "ü":
            salida.append("u")
        else:
            salida.append(_sin_tilde(c))
        i += 1
    return "".join(salida)


def terminacion(verso: str) -> TerminacionRima | None:
    palabras = PALABRA_RE.findall(verso)
    if not palabras:
        return None
    ultima = silabear(palabras[-1])
    p = ultima.texto.lower()
    inicio = _vocal_tonica(ultima)
    texto = p[inicio:]

    # Asonancia: vocal tónica + vocal final (se omite la penúltima de las
    # esdrújulas); en diptongos átonos cuenta solo la vocal fuerte.
    vocales = [_sin_tilde(p[inicio])]
    postonicas = ultima.silabas[ultima.acento_lexico + 1:]
    if postonicas:
        final = postonicas[-1]
        nucleo = [p[i] for i in final.nucleo]
        fuertes = [c for c in nucleo if c in VOCALES_FUERTES]
        v = _sin_tilde(fuertes[0] if fuertes else (nucleo[-1] if nucleo else ""))
        # Equivalencias en posición final átona: i = e, u = o (Venus, tribu).
        v = {"i": "e", "u": "o", "y": "e"}.get(v, v)
        if v:
            vocales.append(v)
    return TerminacionRima(texto, _fonologizar(texto), "-".join(vocales))


def _letras(claves: list[str | None], arte_mayor: list[bool]) -> list[str]:
    conteo = Counter(c for c in claves if c)
    asignadas: dict[str, str] = {}
    letras = []
    siguiente = 0
    for clave, mayor in zip(claves, arte_mayor):
        if not clave or conteo[clave] < 2:
            letras.append("-")
            continue
        if clave not in asignadas:
            asignadas[clave] = chr(ord("a") + siguiente % 26)
            siguiente += 1
        letra = asignadas[clave]
        letras.append(letra.upper() if mayor else letra)
    return letras


def analizar_rima(versos: list[str], silabas: list[int]) -> Rima:
    terms = [terminacion(v) for v in versos]
    mayor = [s >= 9 for s in silabas]
    n = len(versos)
    cons = [t.consonante if t else None for t in terms]
    ason = [t.asonante if t else None for t in terms]
    cuenta_cons = Counter(c for c in cons if c)
    cuenta_ason = Counter(a for a in ason if a)
    con_consonante = sum(1 for c in cons if c and cuenta_cons[c] >= 2)
    con_asonante = sum(1 for a in ason if a and cuenta_ason[a] >= 2)
    solo_asonante = con_asonante - con_consonante

    if n < 2:
        return Rima("libre", ["-"] * n, terms, "baja")

    # Rima asonante en los pares (romance): la mayoría de los pares comparten
    # asonancia y los impares quedan libres.
    pares = [ason[i] for i in range(1, n, 2) if ason[i]]
    asonancia_pares = Counter(pares).most_common(1)[0] if pares else (None, 0)
    impares = [ason[i] for i in range(0, n, 2)]
    impares_con_esa_asonancia = sum(1 for a in impares if a and a == asonancia_pares[0])
    romance = (
        n >= 6
        and asonancia_pares[1] >= 0.75 * len(pares)
        and impares_con_esa_asonancia <= 0.25 * len(impares)
    )

    if romance:
        clave = asonancia_pares[0]
        esquema = []
        for i, a in enumerate(ason):
            if i % 2 == 1 and a == clave:
                esquema.append("A" if mayor[i] else "a")
            else:
                esquema.append("-")
        confianza = "alta" if asonancia_pares[1] == len(pares) else "media"
        return Rima("asonante", esquema, terms, confianza)

    if con_consonante >= 0.5 * n:
        confianza = "alta" if con_consonante >= 0.8 * n else "media"
        return Rima("consonante", _letras(cons, mayor), terms, confianza)
    if con_asonante >= 0.5 * n:
        return Rima("asonante", _letras(ason, mayor), terms, "media")
    if con_asonante < 0.3 * n:
        return Rima("libre", ["-"] * n, terms, "alta" if con_asonante == 0 else "media")
    # Rimas ocasionales sin esquema claro: se informa la predominante.
    if con_consonante >= solo_asonante:
        return Rima("consonante", _letras(cons, mayor), terms, "baja")
    return Rima("asonante", _letras(ason, mayor), terms, "baja")
