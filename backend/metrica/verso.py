"""Cómputo silábico del verso: licencias métricas y ley del acento final.

Cada verso admite varias lecturas según qué licencias se apliquen. El motor
parte de la lectura por defecto (sinalefa en todos los contactos vocálicos
entre palabras, sin sinéresis ni diéresis) y calcula cuánto «cuesta» cada
desvío. Así puede elegir la lectura que encaja con el metro del poema y
mostrar las demás cuando son razonables, en lugar de forzar una sola.

La longitud métrica se obtiene como la posición de la última sílaba tónica
más uno, que es equivalente a aplicar la ley del acento final (+1 aguda,
0 llana, −1 esdrújula).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .silabeo import VOCALES_FUERTES, Palabra, normalizar, silabear

PALABRA_RE = re.compile(r"[a-záéíóúàèìòùüïñ]+", re.IGNORECASE)
PAUSA_FUERTE_RE = re.compile(r"[.;:!?¡¿…—–()\[\]]")
PAUSA_DEBIL_RE = re.compile(r"[,\"«»“”]")

# Costes de cada desvío respecto de la lectura por defecto.
COSTE_HIATO = 1.0
COSTE_HIATO_TRAS_TONICA = 0.3
COSTE_HIATO_ANTE_TONICA = 0.5
COSTE_HIATO_PAUSA_FUERTE = 0.35
COSTE_HIATO_PAUSA_DEBIL = 0.6
COSTE_HIATO_H = 0.7
COSTE_SINERESIS = 0.6
COSTE_SINERESIS_TONICA = 0.8
COSTE_SINERESIS_TILDE = 1.0
COSTE_DIERESIS = 1.2
# «y» entre vocales se apoya en la vocal siguiente como consonante (pla-ta-ya-zul).
COSTE_HIATO_Y_INTERVOCALICA = 0.3

MAX_LECTURAS_POR_LONGITUD = 4

NOMBRES_VERSO = {
    1: "monosílabo",
    2: "bisílabo",
    3: "trisílabo",
    4: "tetrasílabo",
    5: "pentasílabo",
    6: "hexasílabo",
    7: "heptasílabo",
    8: "octosílabo",
    9: "eneasílabo",
    10: "decasílabo",
    11: "endecasílabo",
    12: "dodecasílabo",
    13: "tridecasílabo",
    14: "alejandrino",
    15: "pentadecasílabo",
    16: "hexadecasílabo",
    17: "heptadecasílabo",
    18: "octodecasílabo",
    19: "eneadecasílabo",
}

AJUSTE_FINAL = {"aguda": 1, "llana": 0, "esdrújula": -1, "sobresdrújula": -2}


def nombre_verso(n: int) -> str:
    return NOMBRES_VERSO.get(n, f"verso de {n} sílabas")


def arte(n: int) -> str:
    return "arte menor" if n <= 8 else "arte mayor"


@dataclass
class Licencia:
    tipo: str  # sinalefa, sinéresis, diéresis, hiato
    texto: str  # fragmento afectado, p. ej. «to‿es»


@dataclass
class Lectura:
    silabeo: str
    silabas: int
    licencias: list[Licencia]
    coste: float
    acentos: list[int]  # posiciones (1-based) de las sílabas tónicas

    @property
    def nombre(self) -> str:
        return nombre_verso(self.silabas)


@dataclass
class _Candidato:
    tipo: str  # «sinalefa» (por defecto aplicada), «sineresis», «dieresis»
    posicion: int  # frontera (entre sílaba g y g+1) o sílaba g para diéresis
    coste: float  # coste de apartarse del valor por defecto
    delta: int  # efecto sobre la longitud al apartarse del valor por defecto


@dataclass
class AnalisisVerso:
    texto: str
    palabras: list[Palabra]
    lecturas: dict[int, list[Lectura]] = field(default_factory=dict)
    ley_acento_final: str = ""  # aguda / llana / esdrújula / sobresdrújula
    ajuste_final: int = 0

    def mejor(self) -> Lectura | None:
        todas = [l for ls in self.lecturas.values() for l in ls]
        return min(todas, key=lambda l: (l.coste, l.silabas)) if todas else None

    def coste_para(self, n: int) -> float | None:
        ls = self.lecturas.get(n)
        return ls[0].coste if ls else None


def _tokenizar(verso: str) -> tuple[list[str], list[str]]:
    """Devuelve las palabras y el texto que hay entre cada par de palabras."""
    palabras, separadores = [], []
    ultimo = None
    for m in PALABRA_RE.finditer(verso):
        if ultimo is not None:
            separadores.append(verso[ultimo:m.start()])
        palabras.append(m.group())
        ultimo = m.end()
    return palabras, separadores


def analizar_verso(verso: str) -> AnalisisVerso:
    verso = normalizar(verso).strip()
    textos, separadores = _tokenizar(verso)
    palabras = [silabear(t) for t in textos]
    resultado = AnalisisVerso(verso, palabras)
    if not palabras:
        return resultado

    # Sílabas planas: (índice de palabra, índice de sílaba dentro de la palabra)
    planas: list[tuple[int, int]] = []
    for w, p in enumerate(palabras):
        for s in range(p.num_silabas):
            planas.append((w, s))
    inicio_palabra = []
    acumulado = 0
    for p in palabras:
        inicio_palabra.append(acumulado)
        acumulado += p.num_silabas

    tonicas_globales = set()
    for w, p in enumerate(palabras):
        if p.es_tonica:
            tonicas_globales.add(inicio_palabra[w] + p.tonica)
    ultima = palabras[-1]
    g_ultima_tonica = inicio_palabra[-1] + ultima.acento_lexico
    tonicas_globales.add(g_ultima_tonica)

    resultado.ley_acento_final = ultima.tipo_acentual()
    resultado.ajuste_final = AJUSTE_FINAL[resultado.ley_acento_final]

    candidatos: list[_Candidato] = []
    sinalefas_defecto: set[int] = set()

    # Sinalefas entre palabras (aplicadas por defecto).
    for w in range(len(palabras) - 1):
        a, b = palabras[w], palabras[w + 1]
        if not (a.termina_en_vocal and b.empieza_en_vocal):
            continue
        g = inicio_palabra[w + 1] - 1  # frontera entre la última de a y la primera de b
        coste = COSTE_HIATO
        sep = separadores[w]
        if PAUSA_FUERTE_RE.search(sep):
            coste = min(coste, COSTE_HIATO_PAUSA_FUERTE)
        elif PAUSA_DEBIL_RE.search(sep):
            coste = min(coste, COSTE_HIATO_PAUSA_DEBIL)
        if g in tonicas_globales:
            coste = min(coste, COSTE_HIATO_TRAS_TONICA)
        if g + 1 in tonicas_globales:
            coste = min(coste, COSTE_HIATO_ANTE_TONICA)
        if b.texto.lower().startswith("h"):
            coste = min(coste, COSTE_HIATO_H)
        if a.texto.lower() == "y" and w > 0 and palabras[w - 1].termina_en_vocal:
            coste = min(coste, COSTE_HIATO_Y_INTERVOCALICA)
        sinalefas_defecto.add(g)
        candidatos.append(_Candidato("sinalefa", g, coste, +1))

    # Sinéresis dentro de palabra (no aplicadas por defecto).
    for w, p in enumerate(palabras):
        for frontera in p.hiatos:
            g = inicio_palabra[w] + frontera
            if g + 1 > g_ultima_tonica:
                continue  # tras la última tónica no cambia el cómputo
            texto = p.silabas[frontera].texto + p.silabas[frontera + 1].texto
            if any(c in "íúìù" for c in texto.lower()):
                coste = COSTE_SINERESIS_TILDE
            elif g in tonicas_globales or g + 1 in tonicas_globales:
                coste = COSTE_SINERESIS_TONICA
            else:
                coste = COSTE_SINERESIS
            candidatos.append(_Candidato("sineresis", g, coste, -1))

    # Diéresis posibles (no aplicadas por defecto).
    for w, p in enumerate(palabras):
        for s, silaba in enumerate(p.silabas):
            if silaba.corte_dieresis is None:
                continue
            g = inicio_palabra[w] + s
            if g > g_ultima_tonica:
                continue
            if g == g_ultima_tonica:
                derecha = silaba.texto[silaba.corte_dieresis:].lower()
                izquierda = silaba.texto[:silaba.corte_dieresis].lower()
                vocal_der = next((c for c in derecha if c in "aeiouáéíóúü"), "")
                vocal_izq = next((c for c in reversed(izquierda) if c in "aeiouáéíóúü"), "")
                tonica_a_la_derecha = vocal_der in VOCALES_FUERTES or vocal_der in "íú" or (
                    vocal_izq in "iuü" and vocal_der in "iu"
                )
                if not tonica_a_la_derecha:
                    continue
            candidatos.append(_Candidato("dieresis", g, COSTE_DIERESIS, +1))

    base = g_ultima_tonica + 1 - len(sinalefas_defecto) + 1

    # Programación dinámica sobre el efecto neto en la longitud.
    estados: dict[int, list[tuple[float, frozenset[int]]]] = {0: [(0.0, frozenset())]}
    for i, c in enumerate(candidatos):
        nuevos: dict[int, list[tuple[float, frozenset[int]]]] = {}
        for delta, combos in estados.items():
            for coste, elegidos in combos:
                nuevos.setdefault(delta, []).append((coste, elegidos))
                nuevos.setdefault(delta + c.delta, []).append((coste + c.coste, elegidos | {i}))
        estados = {
            d: sorted(cs, key=lambda x: (x[0], sorted(x[1])))[:MAX_LECTURAS_POR_LONGITUD]
            for d, cs in nuevos.items()
        }

    for delta, combos in estados.items():
        n = base + delta
        if n < 1:
            continue
        lecturas = [
            _construir_lectura(palabras, planas, inicio_palabra, separadores, candidatos,
                               sinalefas_defecto, elegidos, coste, tonicas_globales)
            for coste, elegidos in combos
        ]
        # Comprobación: la longitud reconstruida debe coincidir con la calculada.
        lecturas = [l for l in lecturas if l.silabas == n]
        if lecturas:
            resultado.lecturas[n] = lecturas
    return resultado


def _construir_lectura(palabras, planas, inicio_palabra, separadores, candidatos,
                       sinalefas_defecto, elegidos, coste, tonicas_globales) -> Lectura:
    uniones = set(sinalefas_defecto)
    cortes: set[int] = set()
    hiatos: set[int] = set()
    sineresis: set[int] = set()
    for i in elegidos:
        c = candidatos[i]
        if c.tipo == "sinalefa":
            uniones.discard(c.posicion)
            hiatos.add(c.posicion)
        elif c.tipo == "sineresis":
            uniones.add(c.posicion)
            sineresis.add(c.posicion)
        elif c.tipo == "dieresis":
            cortes.add(c.posicion)

    partes: list[str] = []  # texto con separadores
    licencias: list[Licencia] = []
    acentos: list[int] = []
    posicion_metrica = 0
    ultima_tonica_global = max(tonicas_globales)
    for g, (w, s) in enumerate(planas):
        silaba = palabras[w].silabas[s]
        texto = silaba.texto
        if g == 0:
            posicion_metrica = 1
        else:
            if (g - 1) in uniones:
                sep = "‿" if s == 0 else ""
            else:
                sep = " " if s == 0 else "-"
                posicion_metrica += 1
            partes.append(sep)
        if g in cortes:
            corte = silaba.corte_dieresis
            texto = texto[:corte] + "-" + texto[corte:]
            licencias.append(Licencia("diéresis", texto))
            if g in tonicas_globales:
                # La tónica queda en la parte derecha solo si así se calculó.
                if g == ultima_tonica_global:
                    posicion_metrica += 1
                    acentos.append(posicion_metrica)
                else:
                    acentos.append(posicion_metrica)
                    posicion_metrica += 1
            else:
                posicion_metrica += 1
            partes.append(texto)
            continue
        if g in tonicas_globales:
            acentos.append(posicion_metrica)
        partes.append(texto)

    # Licencias de unión (sinalefa, sinéresis) y de hiato.
    for g in sorted(uniones | hiatos):
        w1, s1 = planas[g]
        w2, s2 = planas[g + 1]
        a = palabras[w1].silabas[s1].texto
        b = palabras[w2].silabas[s2].texto
        if g in hiatos:
            licencias.append(Licencia("hiato", f"{a} | {b}"))
        elif g in sineresis:
            licencias.append(Licencia("sinéresis", a + b))
        else:
            licencias.append(Licencia("sinalefa", f"{a}‿{b}"))
    # Diéresis marcadas en la grafía (süave, ruïdo).
    for w, p in enumerate(palabras):
        for frontera in p.dieresis_marcadas:
            licencias.append(Licencia("diéresis", p.silabas[frontera].texto + "-" + p.silabas[frontera + 1].texto))

    silabeo = "".join(partes)
    silabas = posicion_metrica_final(acentos, ultima_tonica_global, planas, uniones, cortes)
    return Lectura(silabeo, silabas, licencias, round(coste, 2), sorted(set(acentos)))


def posicion_metrica_final(acentos, ultima_tonica_global, planas, uniones, cortes) -> int:
    """Longitud métrica = posición de la última tónica + 1."""
    return (max(acentos) if acentos else 0) + 1


def tipo_endecasilabo(acentos: list[int]) -> str | None:
    """Clasificación rítmica del endecasílabo según Navarro Tomás y Quilis."""
    s = set(acentos)
    if 10 not in s:
        return None
    if 6 in s:
        if 1 in s and 2 not in s and 3 not in s:
            return "enfático (1.ª-6.ª)"
        if 2 in s:
            return "heroico (2.ª-6.ª)"
        if 3 in s:
            return "melódico (3.ª-6.ª)"
    if 4 in s and 8 in s:
        return "sáfico (4.ª-8.ª)"
    if 4 in s and 7 in s:
        return "dactílico o de gaita gallega (4.ª-7.ª)"
    if 6 in s:
        return "con acento en 6.ª"
    return None
