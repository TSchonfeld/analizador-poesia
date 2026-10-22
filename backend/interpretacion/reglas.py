"""Detección por reglas de recursos formales, sin modelo de lenguaje.

Sirve cuando no hay API key: solo se reportan recursos que se pueden
reconocer en la superficie del texto (repeticiones, conjunciones, sonidos,
cortes de verso). Los criterios son conservadores para no inventar
recursos; los semánticos (metáfora, antítesis...) quedan fuera de alcance.
"""

from __future__ import annotations

import re
import unicodedata
from collections import Counter

PALABRA_RE = re.compile(r"[a-záéíóúüñ]+", re.IGNORECASE)

# Palabras demasiado frecuentes para que su repetición inicial baste.
GRAMATICALES = {
    "el", "la", "los", "las", "lo", "un", "una", "unos", "unas", "y", "e", "o", "u", "ni",
    "de", "del", "a", "al", "en", "con", "por", "para", "que", "se", "me", "te", "su", "sus",
    "mi", "mis", "tu", "tus", "es",
}
# Palabras átonas tras las que un final de verso sin pausa deja una unidad cortada.
CORTE_ABRUPTO = {
    "el", "la", "los", "las", "un", "una", "unos", "unas", "al", "del",
    "a", "ante", "bajo", "con", "contra", "de", "desde", "en", "entre", "hacia", "hasta",
    "para", "por", "sin", "sobre", "tras", "mi", "mis", "tu", "tus", "su", "sus",
    "nuestro", "nuestra", "nuestros", "nuestras", "y", "e", "ni", "o", "u", "que",
}
CONJUNCIONES_POLISINDETON = ("y", "ni", "o")
PAUSA_FINAL_RE = re.compile(r"[.,;:!?¡¿…—–)\]»\"”]\s*$")

FONEMAS_NOMBRE = {
    "b": "/b/", "k": "/k/", "z": "/θ/ o /s/", "ch": "/ch/", "d": "/d/", "f": "/f/", "g": "/g/",
    "j": "/x/", "l": "/l/", "ll": "/ll/", "m": "/m/", "n": "/n/", "ñ": "/ñ/", "p": "/p/",
    "r": "/r/", "rr": "/rr/", "s": "/s/", "t": "/t/",
}


def _palabras(verso: str) -> list[str]:
    return PALABRA_RE.findall(unicodedata.normalize("NFC", verso))


def _recurso(nombre, categoria, verso, hasta, cita, explicacion, confianza):
    return {
        "nombre": nombre,
        "categoria": categoria,
        "verso": verso,
        "hasta_verso": hasta,
        "cita": cita,
        "explicacion": explicacion,
        "confianza": confianza,
        "verso_corregido": False,
        "origen": "reglas",
    }


def _clave_inicial(verso: str) -> tuple[str, ...] | None:
    p = _palabras(verso)
    if not p:
        return None
    largo = 2 if p[0].lower() in GRAMATICALES else 1
    if len(p) < largo:
        return None
    return tuple(w.lower() for w in p[:largo])


def _anaforas(versos: list[str]) -> list[dict]:
    """Versos que empiezan igual, seguidos o con un verso intermedio.

    Con versos intercalados (como el «cuando» del Romance del prisionero)
    se exigen al menos tres apariciones.
    """
    claves = [_clave_inicial(v) for v in versos]
    recursos = []
    usados: set[int] = set()
    for i, clave in enumerate(claves):
        if clave is None or i in usados:
            continue
        grupo = [i]
        k = i + 1
        while k < len(claves) and k - grupo[-1] <= 2:
            if claves[k] == clave:
                grupo.append(k)
            k += 1
        seguidos = all(b - a == 1 for a, b in zip(grupo, grupo[1:]))
        if len(grupo) < 2 or (not seguidos and len(grupo) < 3):
            continue
        usados.update(grupo)
        primero, ultimo = grupo[0], grupo[-1]
        largo = len(clave)
        repetido = " ".join(_palabras(versos[primero])[:largo])
        partes = []
        for a, g in enumerate(grupo):
            if a and g - grupo[a - 1] > 1:
                partes.append("…")
            partes.append(versos[g].strip().rstrip(",;:."))
        cita = " / ".join(partes)
        numeros = ", ".join(str(g + 1) for g in grupo)
        confianza = "alta" if (len(grupo) >= 3 or largo == 2) else "media"
        recurso = _recurso(
            "anáfora", "sintácticos", primero + 1, ultimo + 1, cita,
            f"Repite «{repetido}» al comienzo de los versos {numeros}: refuerza la idea y marca el ritmo.",
            confianza,
        )
        # Para resaltar solo las palabras repetidas de cada verso.
        recurso["fragmentos"] = [
            {"verso": g + 1, "texto": " ".join(_palabras(versos[g])[:largo])} for g in grupo
        ]
        recursos.append(recurso)
    return recursos


def _epiforas(versos: list[str]) -> list[dict]:
    recursos = []
    i = 0
    n = len(versos)
    while i < n:
        p = _palabras(versos[i])
        if not p:
            i += 1
            continue
        final = p[-1].lower()
        j = i + 1
        while j < n and _palabras(versos[j]) and _palabras(versos[j])[-1].lower() == final:
            j += 1
        if j - i >= 2 and final not in GRAMATICALES:
            cita = " / ".join(v.strip() for v in versos[i:j])
            recursos.append(_recurso(
                "epífora", "sintácticos", i + 1, j, cita,
                f"Repite «{p[-1]}» al final de {j - i} versos seguidos y deja la palabra resonando.",
                "media",
            ))
            i = j
        else:
            i += 1
    return recursos


def _polisindeton(versos: list[str]) -> list[dict]:
    recursos = []
    usados: set[int] = set()
    for i in range(len(versos)):
        if i in usados:
            continue
        for conj in CONJUNCIONES_POLISINDETON:
            for ventana in (1, 2):
                tramo = versos[i:i + ventana]
                if len(tramo) < ventana:
                    continue
                cuenta = sum(1 for v in tramo for w in _palabras(v) if w.lower() == conj)
                umbral = 3
                if cuenta >= umbral:
                    # Si la ventana de dos versos solo suma por el segundo, se deja para él.
                    if ventana == 2 and not any(w.lower() == conj for w in _palabras(tramo[0])):
                        continue
                    recursos.append(_recurso(
                        "polisíndeton", "gramaticales", i + 1, i + ventana,
                        " / ".join(v.strip() for v in tramo),
                        f"Repite la conjunción «{conj}» más de lo necesario ({cuenta} veces): "
                        "acumula los elementos y demora el ritmo.",
                        "media",
                    ))
                    usados.update(range(i, i + ventana))
                    break
            else:
                continue
            break
    return recursos


def _fonemas(verso: str) -> list[str]:
    t = unicodedata.normalize("NFC", verso).lower()
    t = "".join(c for c in unicodedata.normalize("NFD", t) if unicodedata.category(c) != "Mn" or c == "̃")
    t = unicodedata.normalize("NFC", t)
    fonemas = []
    i = 0
    while i < len(t):
        c = t[i]
        sig = t[i + 1] if i + 1 < len(t) else ""
        if c in "ch" and t[i:i + 2] == "ch":
            fonemas.append("ch"); i += 2; continue
        if t[i:i + 2] == "ll":
            fonemas.append("ll"); i += 2; continue
        if t[i:i + 2] == "rr":
            fonemas.append("rr"); i += 2; continue
        if c == "q" and sig == "u":
            fonemas.append("k"); i += 2; continue
        if c == "g" and sig == "u" and i + 2 < len(t) and t[i + 2] in "ei":
            fonemas.append("g"); i += 2; continue
        if c == "c":
            fonemas.append("z" if sig in "ei" else "k")
        elif c == "g":
            fonemas.append("j" if sig in "ei" else "g")
        elif c == "v":
            fonemas.append("b")
        elif c == "r" and (i == 0 or not t[i - 1].isalpha()):
            fonemas.append("rr")
        elif c in "bdfjklmnñprstz":
            fonemas.append(c)
        i += 1
    return fonemas


def _aliteraciones(versos: list[str]) -> list[dict]:
    recursos = []
    for i, v in enumerate(versos):
        fonemas = _fonemas(v)
        if len(fonemas) < 6:
            continue
        fonema, cuenta = Counter(fonemas).most_common(1)[0]
        # /s/, /n/ y /r/ son muy frecuentes en español: se exige más.
        minimo = 6 if fonema in ("s", "n", "r") else 5
        if cuenta >= minimo and cuenta / len(fonemas) >= 0.3:
            recursos.append(_recurso(
                "aliteración", "fónicos", i + 1, i + 1, v.strip().rstrip(",;:."),
                f"Repite el sonido {FONEMAS_NOMBRE.get(fonema, fonema)} ({cuenta} veces en el verso), "
                "que da unidad sonora y musicalidad.",
                "media" if cuenta / len(fonemas) >= 0.35 else "baja",
            ))
    return recursos


def _encabalgamientos(versos: list[str], estrofas: list[int] | None) -> list[dict]:
    recursos = []
    for i in range(len(versos) - 1):
        if estrofas and estrofas[i] != estrofas[i + 1]:
            continue
        if PAUSA_FINAL_RE.search(versos[i]):
            continue
        p = _palabras(versos[i])
        siguiente = _palabras(versos[i + 1])
        if not p or not siguiente:
            continue
        if p[-1].lower() in CORTE_ABRUPTO:
            cita = " ".join(p[-2:]) + " / " + " ".join(siguiente[:2])
            recursos.append(_recurso(
                "encabalgamiento", "sintácticos", i + 1, i + 2, cita,
                f"El verso termina en «{p[-1]}» y la frase sigue en el próximo: la pausa métrica "
                "corta una unidad sintáctica y crea tensión.",
                "media",
            ))
    return recursos


def detectar_recursos(versos: list[str], estrofas: list[int] | None = None) -> list[dict]:
    """Recursos formales detectados por reglas, ordenados por verso."""
    recursos = (
        _aliteraciones(versos)
        + _polisindeton(versos)
        + _anaforas(versos)
        + _epiforas(versos)
        + _encabalgamientos(versos, estrofas)
    )
    return sorted(recursos, key=lambda r: (r["verso"], r["nombre"]))
