"""Silabeo fonológico y acento léxico de palabras españolas.

Las reglas siguen la descripción de Quilis (*Métrica española*) y de Navarro
Tomás (*Métrica española*), y se inspiran en las del proyecto rantanplan
(POSTDATA, UNED; licencia Apache 2.0), reescritas sin depender de spaCy.

El silabeo es fonológico: la «h» no cuenta como sonido, «qu» y «gu» ante e/i
valen por una consonante, y la «y» final de palabra es vocal (rey, muy).
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

VOCALES_FUERTES = set("aeoáéóàèò")
VOCALES_DEBILES = set("iuü")
VOCALES_ACENTUADAS = set("áéíóúàèìòù")
VOCALES = VOCALES_FUERTES | VOCALES_DEBILES | set("íúìùï")
# «ï» y la «ü» que no sigue a «g» marcan diéresis poética (süave, ruïdo).
MARCAS_DIERESIS = set("ï")

# Grupos consonánticos que no se separan: van juntos al comienzo de sílaba.
GRUPOS_INSEPARABLES = {
    "pr", "br", "tr", "dr", "cr", "kr", "gr", "fr",
    "pl", "bl", "cl", "kl", "gl", "fl",
}

LETRA_RE = re.compile(r"[a-záéíóúàèìòùüïñ]", re.IGNORECASE)

# Palabras átonas según Quilis y Navarro Tomás: artículos determinados,
# preposiciones, conjunciones, pronombres clíticos, posesivos antepuestos,
# relativos y tratamientos. Las formas con tilde diacrítica (qué, él, tú, mí,
# sí, más...) son tónicas y no figuran acá.
ATONAS = {
    # artículos y contracciones
    "el", "la", "los", "las", "lo", "al", "del",
    # preposiciones
    "a", "ante", "bajo", "cabe", "con", "contra", "de", "desde", "en",
    "entre", "hacia", "hasta", "para", "por", "sin", "so", "sobre", "tras",
    # conjunciones
    "y", "e", "ni", "o", "u", "que", "pero", "mas", "sino", "aunque", "pues",
    "porque", "si", "como", "cuando", "donde", "conque",
    # pronombres clíticos
    "me", "te", "se", "nos", "os", "le", "les",
    # posesivos antepuestos
    "mi", "mis", "tu", "tus", "su", "sus",
    # relativos
    "cual", "cuales", "quien", "quienes", "cuyo", "cuya", "cuyos", "cuyas",
    "cuanto", "cuanta", "cuantos", "cuantas",
    # otros
    "tan", "aun", "don", "doña", "fray", "san", "sor",
}


@dataclass
class Silaba:
    texto: str
    # Índices (dentro de la palabra) de las vocales del núcleo.
    nucleo: list[int] = field(default_factory=list)
    # Si el núcleo es un diptongo o triptongo que podría deshacerse con
    # diéresis, posición (dentro de `texto`) donde se cortaría.
    corte_dieresis: int | None = None


@dataclass
class Palabra:
    texto: str
    silabas: list[Silaba]
    tonica: int | None  # índice de la sílaba tónica; None si es átona
    acento_lexico: int = 0  # índice de la sílaba con acento léxico (aunque sea átona)
    # Índices de frontera interna (entre la sílaba i y la i+1) que son hiato
    # entre vocales y admiten sinéresis.
    hiatos: list[int] = field(default_factory=list)
    # Fronteras con diéresis forzada por la grafía (ü, ï).
    dieresis_marcadas: list[int] = field(default_factory=list)

    @property
    def num_silabas(self) -> int:
        return len(self.silabas)

    @property
    def textos(self) -> list[str]:
        return [s.texto for s in self.silabas]

    def silabeo(self) -> str:
        return "-".join(self.textos)

    @property
    def empieza_en_vocal(self) -> bool:
        """True si admite sinalefa con la palabra anterior.

        La «h» es muda. Una vocal débil inicial seguida de otra vocal es
        semiconsonante (hielo, huevo) y no hace sinalefa. La «y» seguida de
        vocal es consonante (yo, ya).
        """
        t = self.texto.lower()
        if t == "y":
            return True
        if t.startswith("h"):
            t = t[1:]
        if not t or t[0] not in VOCALES:
            return False
        if t[0] in "iu" and len(t) > 1 and t[1] in VOCALES:
            return False
        return True

    @property
    def termina_en_vocal(self) -> bool:
        """True si admite sinalefa con la palabra siguiente.

        La «y» final (rey, hoy) se resilabea como consonante ante vocal
        (ho-yes), así que no cuenta, salvo la conjunción «y».
        """
        t = self.texto.lower()
        if t == "y":
            return True
        return bool(t) and t[-1] in VOCALES

    @property
    def es_tonica(self) -> bool:
        return self.tonica is not None

    def tipo_acentual(self) -> str:
        """aguda, llana, esdrújula o sobresdrújula (según el acento léxico)."""
        desde_final = self.num_silabas - 1 - self.acento_lexico
        return {0: "aguda", 1: "llana", 2: "esdrújula"}.get(desde_final, "sobresdrújula")


def _es_vocal(c: str) -> bool:
    return c in VOCALES


def _unidades(palabra: str) -> list[tuple[str, int, int]]:
    """Divide la palabra en unidades fonológicas.

    Devuelve tuplas (tipo, inicio, fin) donde tipo es «V» (vocal), «C»
    (consonante) o «H» (h muda, se trata como consonante para el corte).
    """
    p = palabra.lower()
    n = len(p)
    unidades = []
    i = 0
    while i < n:
        c = p[i]
        dos = p[i:i + 2]
        if dos in ("ch", "ll", "rr"):
            unidades.append(("C", i, i + 2))
            i += 2
        elif c == "q" and i + 1 < n and p[i + 1] == "u":
            unidades.append(("C", i, i + 2))
            i += 2
        elif c == "g" and i + 2 < n and p[i + 1] == "u" and p[i + 2] in "eéiíèì":
            unidades.append(("C", i, i + 2))
            i += 2
        elif c == "y":
            # Vocal si está al final o ante consonante; consonante ante vocal.
            siguiente = p[i + 1] if i + 1 < n else ""
            if siguiente and _es_vocal(siguiente):
                unidades.append(("C", i, i + 1))
            elif i == 0 and siguiente:
                unidades.append(("C", i, i + 1))
            else:
                unidades.append(("V", i, i + 1))
            i += 1
        elif c == "h":
            unidades.append(("H", i, i + 1))
            i += 1
        elif _es_vocal(c):
            unidades.append(("V", i, i + 1))
            i += 1
        else:
            unidades.append(("C", i, i + 1))
            i += 1
    return unidades


def _clase_vocal(c: str, previa: str) -> str:
    """«F» fuerte, «D» débil, «M» débil con marca de diéresis."""
    if c in MARCAS_DIERESIS:
        return "M"
    if c == "ü":
        # Tras «g» es la ü de pingüino; en otro lugar es diéresis poética.
        return "D" if previa == "g" else "M"
    if c in VOCALES_FUERTES or c in "íúìù":
        return "F"
    if c == "y":
        return "D"
    return "D"


def _separa(v1: str, c1: str, v2: str, c2: str) -> bool:
    """¿Hay frontera silábica entre dos vocales contiguas?"""
    if c1 == "M" or c2 == "M":
        return True
    if c1 == "F" and c2 == "F":
        return True
    # ii, uu: hiato (chiita, duunviro)
    if c1 == "D" and c2 == "D" and v1.replace("y", "i") == v2.replace("y", "i"):
        return True
    return False


def _corte_onset(consonantes: list[str]) -> int:
    """Cuántas consonantes del grupo intervocálico van con la sílaba siguiente."""
    if not consonantes:
        return 0
    if len(consonantes) >= 2:
        par = consonantes[-2] + consonantes[-1]
        if par in GRUPOS_INSEPARABLES:
            return 2
    return 1


def silabear(palabra: str) -> Palabra:
    """Silabea una palabra (sin signos de puntuación)."""
    if not palabra:
        raise ValueError("palabra vacía")
    p = palabra.lower()
    unidades = _unidades(palabra)

    # 1. Agrupar vocales contiguas en núcleos, separando hiatos.
    nucleos: list[list[int]] = []  # índices de unidades vocálicas
    hiato_tras_nucleo: set[int] = set()  # núcleo k seguido de hiato (sin consonante)
    marca_tras_nucleo: set[int] = set()
    actual: list[int] = []
    for k, (tipo, ini, fin) in enumerate(unidades):
        if tipo == "V":
            if actual:
                prev = unidades[actual[-1]]
                v1 = p[prev[1]]
                v2 = p[ini]
                previa1 = p[prev[1] - 1] if prev[1] > 0 else ""
                c1 = _clase_vocal(v1, previa1)
                c2 = _clase_vocal(v2, p[ini - 1] if ini > 0 else "")
                if _separa(v1, c1, v2, c2):
                    nucleos.append(actual)
                    if c1 == "M" or c2 == "M":
                        marca_tras_nucleo.add(len(nucleos) - 1)
                    else:
                        hiato_tras_nucleo.add(len(nucleos) - 1)
                    actual = [k]
                    continue
                actual.append(k)
            else:
                actual = [k]
        else:
            if actual:
                nucleos.append(actual)
                actual = []
    if actual:
        nucleos.append(actual)

    if not nucleos:
        # Palabra sin vocales (siglas, «y» sola ya contemplada): una sílaba.
        return Palabra(palabra, [Silaba(palabra)], None, 0)

    # Hiatos separados por «h» intervocálica (a-ho-ra) también admiten sinéresis.
    for k in range(len(nucleos) - 1):
        entre = unidades[nucleos[k][-1] + 1:nucleos[k + 1][0]]
        if entre and all(t == "H" for t, _, _ in entre):
            hiato_tras_nucleo.add(k)

    # 2. Repartir las consonantes entre núcleos.
    limites = []  # índice de unidad donde empieza cada sílaba
    limites.append(0)
    for k in range(1, len(nucleos)):
        desde = nucleos[k - 1][-1] + 1
        hasta = nucleos[k][0]
        grupo = unidades[desde:hasta]
        letras = [p[ini:fin] for _, ini, fin in grupo]
        n_onset = _corte_onset(letras)
        # sub-rayar, sub-lunar: el prefijo «sub» no forma grupo con r.
        if p.startswith("sub") and grupo and unidades[desde][1] == 2 and letras[:2] == ["b", "r"]:
            n_onset = 1
        limites.append(hasta - n_onset)

    silabas: list[Silaba] = []
    for k, inicio_u in enumerate(limites):
        fin_u = limites[k + 1] if k + 1 < len(limites) else len(unidades)
        ini_c = unidades[inicio_u][1]
        fin_c = unidades[fin_u - 1][2]
        texto = palabra[ini_c:fin_c]
        nucleo_chars = [unidades[u][1] for u in nucleos[k]]
        corte = None
        if len(nucleo_chars) >= 2:
            pos = _punto_corte_dieresis(p, nucleo_chars)
            # La «y» final (rey, muy, hoy) no se separa por diéresis.
            if p[pos] != "y":
                corte = pos - ini_c
        silabas.append(Silaba(texto, nucleo_chars, corte))

    acento = _silaba_acentuada(p, silabas)
    tonica: int | None = acento
    if len(silabas) == 1 and p in ATONAS:
        tonica = None
    elif p in ATONAS and not any(c in VOCALES_ACENTUADAS for c in p):
        tonica = None

    return Palabra(
        palabra,
        silabas,
        tonica,
        acento,
        hiatos=sorted(hiato_tras_nucleo),
        dieresis_marcadas=sorted(marca_tras_nucleo),
    )


def _punto_corte_dieresis(p: str, nucleo: list[int]) -> int:
    """Posición (en la palabra) donde la diéresis separaría el diptongo.

    Se separa la vocal débil de la fuerte; en triptongos, la primera débil.
    """
    clases = [_clase_vocal(p[i], p[i - 1] if i else "") for i in nucleo]
    for j in range(1, len(nucleo)):
        if clases[j - 1] != clases[j] or clases[j - 1] == "D":
            return nucleo[j]
    return nucleo[1]


def _silaba_acentuada(p: str, silabas: list[Silaba]) -> int:
    n = len(silabas)
    for k, s in enumerate(silabas):
        if any(p[i] in VOCALES_ACENTUADAS for i in s.nucleo):
            # Adverbios en -mente: el acento que rige es el de «men».
            if p.endswith("mente") and n >= 3 and k < n - 2:
                return n - 2
            return k
    if n == 1:
        return 0
    ultima = p[-1]
    if ultima in "aeiouns" or ultima in "ü":
        return n - 2
    return n - 1


def normalizar(texto: str) -> str:
    return unicodedata.normalize("NFC", texto)
