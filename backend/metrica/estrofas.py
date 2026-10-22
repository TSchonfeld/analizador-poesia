"""Identificación de estrofas y del tipo de composición.

Nomenclatura según Quilis (*Métrica española*) y Navarro Tomás (*Métrica
española*). Cada identificación lleva una justificación breve y un nivel de
confianza.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from .verso import NOMBRES_VERSO

PLURALES = {
    "redondilla": "redondillas", "cuarteto": "cuartetos", "serventesio": "serventesios",
    "cuarteta": "cuartetas", "copla": "coplas", "quintilla": "quintillas",
    "quinteto": "quintetos", "lira": "liras", "terceto": "tercetos",
    "sextilla": "sextillas", "sexteto": "sextetos", "octavilla": "octavillas",
    "octava real": "octavas reales", "décima espinela": "décimas espinelas",
    "décima": "décimas", "pareado": "pareados", "estrofa sáfica": "estrofas sáficas",
    "cuaderna vía": "cuaderna vía", "copla de pie quebrado (manriqueña)": "coplas de pie quebrado",
}


@dataclass
class Estrofa:
    numero: int
    versos: list[int]  # números de verso (1-based)
    tipo: str
    esquema: str  # esquema métrico-rítmico, p. ej. «11A 11B 11B 11A»
    confianza: str


@dataclass
class Composicion:
    tipo: str
    justificacion: str
    confianza: str


def _patron(letras: list[str]) -> str:
    """Renombra las letras de una estrofa en orden de aparición (ABBA, abab...)."""
    mapa: dict[str, str] = {}
    salida = []
    for l in letras:
        if l == "-":
            salida.append("-")
            continue
        base = l.lower()
        if base not in mapa:
            mapa[base] = chr(ord("a") + len(mapa))
        salida.append(mapa[base].upper() if l.isupper() else mapa[base])
    return "".join(salida)


def _menor(longitudes):
    return all(n <= 8 for n in longitudes)


def _mayor(longitudes):
    return all(n >= 9 for n in longitudes)


def clasificar_estrofa(longitudes: list[int], letras: list[str], tipo_rima: str) -> tuple[str, str]:
    """Devuelve (tipo de estrofa, confianza)."""
    n = len(longitudes)
    p = _patron(letras).lower()
    metros = set(longitudes)
    iso = len(metros) == 1
    asonante = tipo_rima == "asonante"
    m = longitudes[0] if iso else None

    if n == 1:
        return "verso suelto", "alta"
    if n == 2:
        if p == "aa":
            return "pareado", "alta"
        return "dístico (sin rima)", "media"
    if n == 3:
        if iso and m == 8 and asonante and p == "a-a":
            return "soleá", "alta"
        if _mayor(longitudes):
            return "terceto", "alta" if p in ("a-a", "aba", "aaa", "---", "abc", "-a-", "ab-", "a--", "--a", "-ab") else "media"
        if _menor(longitudes):
            return "tercerilla" if p == "a-a" else "estrofa de tres versos de arte menor", "media"
        return "terceto", "media"
    if n == 4:
        if metros == {11, 5} and longitudes[3] == 5 and longitudes[:3] == [11, 11, 11]:
            return "estrofa sáfica", "alta"
        if iso and m == 14 and p == "aaaa":
            return "cuaderna vía", "alta"
        if _mayor(longitudes):
            if p == "abba":
                return "cuarteto", "alta"
            if p == "abab":
                return "serventesio", "alta"
            if p == "-a-a":
                return "cuarteta asonantada de arte mayor" if asonante else "cuarteto de rima en los pares", "media"
            if p == "aabb":
                return "cuarteto de rimas pareadas", "media"
            return "cuarteto (rima irregular)", "baja"
        if _menor(longitudes):
            if p == "abba":
                return "redondilla", "alta"
            if p == "abab":
                return "cuarteta", "alta"
            if p == "-a-a":
                return ("copla", "alta") if asonante and m == 8 else ("cuarteta asonantada", "media")
            if p == "aabb":
                return "estrofa de cuatro versos con rimas pareadas", "media"
            return "estrofa de cuatro versos de arte menor", "baja"
        if p == "abab" and metros <= {7, 11}:
            return "serventesio con heptasílabos", "media"
        return "estrofa de cuatro versos", "baja"
    if n == 5:
        if longitudes == [7, 11, 7, 7, 11] and p == "ababb":
            return "lira", "alta"
        if _mayor(longitudes):
            return "quinteto", "alta" if "-" not in p else "media"
        if _menor(longitudes):
            return "quintilla", "alta" if "-" not in p else "media"
        return "estrofa de cinco versos", "baja"
    if n == 6:
        if longitudes == [8, 8, 4, 8, 8, 4] or longitudes == [8, 8, 5, 8, 8, 5]:
            return "copla de pie quebrado (manriqueña)", "alta" if p == "abcabc" else "media"
        if metros <= {7, 11} and len(metros) == 2:
            return "sexteto-lira", "media"
        if _menor(longitudes):
            if 4 in metros or 5 in metros:
                return "sextilla con pie quebrado", "media"
            return "sextilla", "alta" if "-" not in p else "media"
        if _mayor(longitudes):
            return "sexteto", "alta" if "-" not in p else "media"
        return "estrofa de seis versos", "baja"
    if n == 8:
        if iso and m == 11 and p == "abababcc":
            return "octava real", "alta"
        if iso and m == 12:
            return "copla de arte mayor", "media"
        if _menor(longitudes):
            return "octavilla", "alta" if "-" not in p else "media"
        if _mayor(longitudes):
            return "octava", "media"
        return "estrofa de ocho versos", "baja"
    if n == 10:
        if iso and m == 8 and p == "abbaaccddc":
            return "décima espinela", "alta"
        return "décima", "media" if _menor(longitudes) else "baja"
    if n == 14:
        return "soneto (sin división estrófica)", "media"
    return f"estrofa de {n} versos", "baja"


def esquema_metrico(longitudes: list[int], letras: list[str]) -> str:
    return " ".join(f"{n}{l}" for n, l in zip(longitudes, letras))


def clasificar_composicion(longitudes: list[int], letras: list[str], tipo_rima: str,
                           estrofas: list[Estrofa]) -> Composicion:
    n = len(longitudes)
    conteo = Counter(longitudes)
    principal, frec = conteo.most_common(1)[0]
    proporcion = frec / n
    tamanos = [len(e.versos) for e in estrofas]
    tipos = [e.tipo for e in estrofas]
    patron = _patron(letras)

    # Soneto: 14 versos, 4-4-3-3 (o sin división), rima consonante, cuartetos
    # abrazados o cruzados con las mismas rimas.
    if n == 14 and tamanos in ([4, 4, 3, 3], [14], [8, 6]) and tipo_rima == "consonante":
        cuartetos = patron[:8].lower()
        nombre = {11: "soneto", 14: "soneto alejandrino", 8: "sonetillo"}.get(principal, "soneto")
        if principal == 12:
            nombre = "soneto en dodecasílabos"
        if cuartetos in ("abbaabba", "ababcdcd", "ababbaba", "abbacddc", "ababcddc") and proporcion >= 0.85:
            return Composicion(
                nombre,
                f"Catorce versos {('de ' + str(principal) + ' sílabas') if principal != 11 else 'endecasílabos'} "
                f"con rima consonante, organizados en dos cuartetos y dos tercetos "
                f"(esquema {patron[:4]} {patron[4:8]} {patron[8:11]} {patron[11:]}).",
                "alta" if cuartetos == "abbaabba" and proporcion == 1 else "media",
            )

    # Romance: tirada de octosílabos con asonancia en los pares.
    if tipo_rima == "asonante" and n >= 6 and proporcion >= 0.85:
        pares_rimados = sum(1 for i in range(1, n, 2) if letras[i] != "-")
        impares_libres = sum(1 for i in range(0, n, 2) if letras[i] == "-")
        if pares_rimados >= 0.8 * (n // 2) and impares_libres >= 0.8 * ((n + 1) // 2):
            nombre = {8: "romance", 11: "romance heroico", 7: "romance endecha"}.get(
                principal, "romancillo" if principal < 7 else f"romance de versos de {principal} sílabas")
            return Composicion(
                nombre,
                f"Serie de {n} versos de {principal} sílabas, sin número fijo, con rima asonante "
                f"en los versos pares y los impares sueltos (esquema -a-a).",
                "alta" if proporcion == 1 and pares_rimados == n // 2 else "media",
            )

    # Una sola estrofa con nombre propio.
    if len(estrofas) == 1 and estrofas[0].tipo in ("décima espinela", "octava real", "lira", "redondilla", "cuarteto", "serventesio", "copla"):
        return Composicion(estrofas[0].tipo, f"El poema consta de una sola estrofa: {estrofas[0].tipo} ({estrofas[0].esquema}).", estrofas[0].confianza)

    # Silva: heptasílabos y endecasílabos combinados libremente.
    if set(conteo) <= {7, 11} and len(conteo) == 2 and tipo_rima == "consonante" and n >= 8:
        regulares = len(set(tamanos)) == 1 and len(estrofas) > 1 and all("lira" in t for t in tipos)
        if regulares:
            return Composicion("composición en liras", "Serie de liras (7a 11B 7a 7b 11B).", "alta")
        sueltos = letras.count("-")
        return Composicion(
            "silva",
            f"Combinación libre de heptasílabos y endecasílabos con rima consonante"
            f"{' y algunos versos sueltos' if sueltos else ''}, sin estrofa fija.",
            "media",
        )

    # Verso libre: sin metro regular ni rima.
    if proporcion < 0.5 and len(conteo) >= 3:
        if tipo_rima == "libre":
            return Composicion("verso libre", "Versos de medidas variadas, sin metro dominante y sin rima regular.", "alta")
        return Composicion("verso libre con rima ocasional", "Versos de medidas variadas sin metro dominante; aparecen rimas, pero sin un esquema fijo.", "media")

    # Polimetría: dos o más metros que se alternan de manera organizada.
    metros_relevantes = [m for m, c in conteo.items() if c >= max(2, 0.15 * n)]
    if len(metros_relevantes) >= 2 and len(estrofas) >= 3 and len(set(tipos)) >= 2:
        nombres = ", ".join(str(m) for m in sorted(metros_relevantes, reverse=True))
        return Composicion(
            "poema polimétrico",
            f"Combina versos de {nombres} sílabas en estrofas de distinto tipo "
            f"({', '.join(sorted(set(tipos)))}), como en la canción romántica.",
            "media",
        )

    # Verso blanco: metro regular sin rima.
    if tipo_rima == "libre" and proporcion >= 0.8:
        nombre = "verso blanco" if principal >= 9 else "versos sueltos de arte menor"
        return Composicion(nombre, f"Versos de {principal} sílabas, sin rima.", "media")

    # Serie de estrofas iguales.
    if len(estrofas) > 1 and len(set(tipos)) == 1:
        plural = PLURALES.get(tipos[0])
        nombre = f"composición en {plural}" if plural else "composición estrófica regular"
        return Composicion(nombre, f"Serie de {len(estrofas)} estrofas del mismo tipo: {tipos[0]}.",
                           "alta" if plural else "media")

    # Serie isométrica sin forma fija.
    if proporcion >= 0.8 and principal in NOMBRES_VERSO:
        rima_txt = {"libre": "sin rima", "asonante": "con rima asonante", "consonante": "con rima consonante"}[tipo_rima]
        return Composicion(
            f"serie de {NOMBRES_VERSO[principal]}s",
            f"Versos de {principal} sílabas {rima_txt}, sin una estrofa ni una forma fija reconocibles.",
            "media",
        )

    return Composicion(
        "composición estrófica",
        "No coincide con una forma fija de la tradición; se describen sus estrofas por separado.",
        "baja",
    )
