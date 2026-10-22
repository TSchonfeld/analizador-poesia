"""Punto de entrada del motor determinista: secciones A (métrica) y B (versificación)."""

from __future__ import annotations

from dataclasses import asdict

from .estrofas import Estrofa, clasificar_composicion, clasificar_estrofa, esquema_metrico
from .poema import escandir
from .rima import analizar_rima


def _lectura_dict(lectura):
    return {
        "silabeo": lectura.silabeo,
        "silabas": lectura.silabas,
        "licencias": [asdict(l) for l in lectura.licencias],
        "acentos": lectura.acentos,
    }


def analizar_metrica(texto: str) -> dict:
    """Analiza un poema y devuelve un diccionario serializable a JSON."""
    esc = escandir(texto)
    if not esc.versos:
        raise ValueError("El texto no contiene versos.")
    textos = [v.texto for v in esc.versos]
    silabas = [v.silabas for v in esc.versos]
    rima = analizar_rima(textos, silabas)

    grupos = [list(g) for g in esc.estrofas]
    # Un soneto pegado sin líneas en blanco se divide en 4-4-3-3.
    if len(grupos) == 1 and len(textos) == 14:
        provisoria = clasificar_composicion(
            silabas, rima.esquema, rima.tipo, [Estrofa(1, list(range(1, 15)), "", "", "")])
        if provisoria.tipo.startswith("soneto") or provisoria.tipo == "sonetillo":
            grupos = [list(range(0, 4)), list(range(4, 8)), list(range(8, 11)), list(range(11, 14))]

    estrofas = []
    for k, grupo in enumerate(grupos):
        longs = [silabas[i] for i in grupo]
        letras = [rima.esquema[i] for i in grupo]
        tipo, confianza = clasificar_estrofa(longs, letras, rima.tipo)
        estrofas.append(Estrofa(k + 1, [i + 1 for i in grupo], tipo, esquema_metrico(longs, letras), confianza))

    composicion = clasificar_composicion(silabas, rima.esquema, rima.tipo, estrofas)
    if len(estrofas) == 1 and composicion.tipo.startswith("romance"):
        estrofas[0].tipo = "tirada de romance"
        estrofas[0].confianza = composicion.confianza

    versos = []
    for v, letra, term in zip(esc.versos, rima.esquema, rima.terminaciones):
        versos.append({
            "numero": v.numero,
            "texto": v.texto,
            "estrofa": next(e.numero for e in estrofas if v.numero in e.versos),
            **_lectura_dict(v.lectura),
            "ley_acento_final": v.ley_acento_final,
            "ajuste_final": v.ajuste_final,
            "nombre": v.nombre,
            "arte": v.arte,
            "ritmo": v.ritmo,
            "hemistiquios": list(v.hemistiquios) if v.hemistiquios else None,
            "rima": letra,
            "terminacion": (term.asonante if rima.tipo == "asonante" else "-" + term.texto) if term else None,
            "confianza": v.confianza,
            "alternativas": [_lectura_dict(a) for a in v.alternativas],
        })

    return {
        "metrica": {
            "versos": versos,
            "metros": esc.metros,
            "frecuencias": {str(k): c for k, c in sorted(esc.frecuencias.items())},
            "isometrico": esc.isometrico,
        },
        "versificacion": {
            "rima": {
                "tipo": rima.tipo,
                "esquema": rima.esquema_texto,
                "confianza": rima.confianza,
            },
            "estrofas": [asdict(e) for e in estrofas],
            "composicion": asdict(composicion),
        },
    }
