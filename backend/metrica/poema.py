"""Escansión de un poema completo.

Analiza cada verso, detecta el metro (o los metros) dominantes y elige para
cada verso la lectura que mejor encaja, con su nivel de confianza y las
lecturas alternativas cuando el silabeo es ambiguo.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field

from .silabeo import normalizar
from .verso import (
    AnalisisVerso,
    Lectura,
    Licencia,
    analizar_verso,
    arte,
    nombre_verso,
    tipo_endecasilabo,
)

# Penalización por elegir una longitud que no es metro del poema.
PENALIZACION_FUERA_DE_METRO = 1.6
# Margen para considerar que otra lectura es una alternativa razonable.
MARGEN_ALTERNATIVA = 0.6
MAX_ALTERNATIVAS = 3
# Verso compuesto: hemistiquios iguales.
HEMISTIQUIOS = (6, 7, 8)
COSTE_CESURA = 0.2
# Un verso es «reconducible» al metro principal si lo alcanza con este coste.
COSTE_RECONDUCIBLE = 0.7


@dataclass
class VersoEscandido:
    numero: int
    texto: str
    estrofa: int
    lectura: Lectura
    alternativas: list[Lectura]
    ley_acento_final: str
    ajuste_final: int
    confianza: str  # alta, media, baja
    hemistiquios: tuple[int, int] | None = None

    @property
    def silabas(self) -> int:
        return self.lectura.silabas

    @property
    def nombre(self) -> str:
        if self.hemistiquios:
            a, b = self.hemistiquios
            base = nombre_verso(self.silabas)
            return f"{base} ({a}+{b})"
        return nombre_verso(self.silabas)

    @property
    def arte(self) -> str:
        return arte(self.silabas)

    @property
    def ritmo(self) -> str | None:
        if self.silabas == 11 and not self.hemistiquios:
            return tipo_endecasilabo(self.lectura.acentos)
        return None


@dataclass
class Escansion:
    versos: list[VersoEscandido]
    estrofas: list[list[int]]  # índices de versos por estrofa
    metros: list[int]  # longitudes dominantes, de más a menos frecuente
    frecuencias: dict[int, int] = field(default_factory=dict)

    @property
    def isometrico(self) -> bool:
        return len(set(v.silabas for v in self.versos)) == 1


def dividir_estrofas(texto: str) -> list[list[str]]:
    """Separa el poema en estrofas (por líneas en blanco) y versos."""
    texto = normalizar(texto).replace("\r\n", "\n").replace("\r", "\n")
    estrofas: list[list[str]] = []
    actual: list[str] = []
    for linea in texto.split("\n"):
        if linea.strip():
            actual.append(linea.strip())
        elif actual:
            estrofas.append(actual)
            actual = []
    if actual:
        estrofas.append(actual)
    return estrofas


def _lecturas_compuestas(texto: str, simple: AnalisisVerso) -> dict[int, list[Lectura]]:
    """Lecturas como verso compuesto (hemistiquio + hemistiquio).

    Cada hemistiquio se computa por separado, con su propia ley del acento
    final y sin sinalefa a través de la cesura.
    """
    mejor = simple.mejor()
    if mejor is None or mejor.silabas < 12:
        return {}
    cortes = [m.end() for m in re.finditer(r"[a-záéíóúàèìòùüïñ]+", texto, re.IGNORECASE)][:-1]
    resultado: dict[int, list[Lectura]] = {}
    for corte in cortes:
        izq, der = texto[:corte], texto[corte:]
        a, b = analizar_verso(izq), analizar_verso(der)
        if not a.palabras or not b.palabras or not a.palabras[-1].es_tonica:
            continue
        for h in HEMISTIQUIOS:
            la, lb = a.lecturas.get(h), b.lecturas.get(h)
            if not la or not lb:
                continue
            x, y = la[0], lb[0]
            lectura = Lectura(
                silabeo=f"{x.silabeo} / {y.silabeo}",
                silabas=2 * h,
                licencias=x.licencias + y.licencias + [Licencia("cesura", f"{h}+{h}")],
                # El alejandrino y los versos más largos son siempre compuestos.
                coste=round(x.coste + y.coste + (COSTE_CESURA if h < 7 else 0.0), 2),
                acentos=x.acentos + [h + p for p in y.acentos],
            )
            resultado.setdefault(2 * h, []).append(lectura)
    for n in resultado:
        resultado[n].sort(key=lambda l: l.coste)
    return resultado


def _coste_ajustado(lectura: Lectura, metros: set[int]) -> float:
    return lectura.coste + (0 if lectura.silabas in metros else PENALIZACION_FUERA_DE_METRO)


def _todas(analisis: AnalisisVerso, compuestas: dict[int, list[Lectura]]) -> list[Lectura]:
    todas = [l for ls in analisis.lecturas.values() for l in ls]
    todas += [l for ls in compuestas.values() for l in ls]
    return todas


def _metros(elegidas: list[Lectura], entradas) -> set[int]:
    """Longitudes que funcionan como metro del poema.

    Una longitud secundaria solo cuenta como metro si la mayoría de sus versos
    no pueden leerse con el metro principal sin forzar el silabeo; si no, son
    versos ambiguos de un poema isométrico.
    """
    n = len(elegidas)
    conteo = Counter(l.silabas for l in elegidas)
    if n < 4:
        return set(conteo)
    principal = conteo.most_common(1)[0][0]
    umbral = max(2, round(0.15 * n))
    metros = {principal}
    for longitud, c in conteo.items():
        if longitud == principal or c < umbral:
            continue
        reconducibles = 0
        for lectura, (_, _, a, comp) in zip(elegidas, entradas):
            if lectura.silabas != longitud:
                continue
            costes = [l.coste for l in _todas(a, comp) if l.silabas == principal]
            if costes and min(costes) <= COSTE_RECONDUCIBLE:
                reconducibles += 1
        if reconducibles * 2 < c:
            metros.add(longitud)
    return metros


def escandir(texto: str) -> Escansion:
    estrofas_txt = dividir_estrofas(texto)
    entradas = []  # (estrofa, texto, analisis, compuestas)
    for e, estrofa in enumerate(estrofas_txt):
        for linea in estrofa:
            a = analizar_verso(linea)
            if not a.palabras:
                continue
            entradas.append((e, a.texto, a, _lecturas_compuestas(a.texto, a)))

    if not entradas:
        return Escansion([], [], [])

    # Primera aproximación: la lectura más barata de cada verso.
    elegidas = [min(_todas(a, c), key=lambda l: (l.coste, l.silabas)) for _, _, a, c in entradas]
    metros = _metros(elegidas, entradas)
    for _ in range(3):
        conteo = Counter(l.silabas for l in elegidas)
        nuevas = []
        for _, _, a, c in entradas:
            nuevas.append(min(
                _todas(a, c),
                key=lambda l: (_coste_ajustado(l, metros), -conteo.get(l.silabas, 0),
                               " / " not in l.silabeo),
            ))
        nuevos_metros = _metros(nuevas, entradas)
        elegidas = nuevas
        if nuevos_metros == metros:
            break
        metros = nuevos_metros

    conteo = Counter(l.silabas for l in elegidas)
    versos = []
    estrofas: list[list[int]] = []
    for i, ((e, texto_v, a, c), lectura) in enumerate(zip(entradas, elegidas)):
        while len(estrofas) <= e:
            estrofas.append([])
        estrofas[e].append(i)
        ajustada = _coste_ajustado(lectura, metros)
        alternativas = []
        for l in sorted(_todas(a, c), key=lambda l: _coste_ajustado(l, metros)):
            if l is lectura or l.silabeo.replace(" / ", " ") == lectura.silabeo.replace(" / ", " "):
                continue
            if any(l.silabeo.replace(" / ", " ") == x.silabeo.replace(" / ", " ") for x in alternativas):
                continue
            if _coste_ajustado(l, metros) <= ajustada + MARGEN_ALTERNATIVA:
                alternativas.append(l)
        alternativas = alternativas[:MAX_ALTERNATIVAS]
        if lectura.silabas not in metros:
            confianza = "baja"
        elif lectura.coste > 1.0 or any(
            _coste_ajustado(l, metros) <= ajustada + 0.25 for l in alternativas
        ):
            confianza = "media"
        else:
            confianza = "alta"
        hemistiquios = None
        for lic in lectura.licencias:
            if lic.tipo == "cesura":
                x, y = lic.texto.split("+")
                hemistiquios = (int(x), int(y))
        versos.append(VersoEscandido(
            numero=i + 1,
            texto=texto_v,
            estrofa=e,
            lectura=lectura,
            alternativas=alternativas,
            ley_acento_final=a.ley_acento_final,
            ajuste_final=a.ajuste_final,
            confianza=confianza,
            hemistiquios=hemistiquios,
        ))
    estrofas = [e for e in estrofas if e]
    metros_ordenados = [l for l, _ in conteo.most_common() if l in metros]
    return Escansion(versos, estrofas, metros_ordenados, dict(conteo))
