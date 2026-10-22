from metrica.analisis import analizar_metrica
from metrica.rima import terminacion


def _vers(texto):
    return analizar_metrica(texto)["versificacion"]


def test_terminaciones():
    assert terminacion("vuestro gesto").consonante == "esto"
    assert terminacion("de vos deseo").asonante == "e-o"
    # esdrújula: se omite la vocal penúltima
    assert terminacion("tus ojos de color de lágrima").asonante == "a-a"
    # diptongo átono: cuenta la vocal fuerte
    assert terminacion("cuando canta la calandria").asonante == "a-a"
    # aguda: una sola vocal
    assert terminacion("cuando hace la calor").asonante == "o"


def test_soneto(poema):
    v = _vers(poema("garcilaso_soneto_v"))
    assert v["rima"]["tipo"] == "consonante"
    assert v["rima"]["esquema"] == "ABBAABBACDECDE"
    assert [e["tipo"] for e in v["estrofas"]] == ["cuarteto", "cuarteto", "terceto", "terceto"]
    assert v["composicion"]["tipo"] == "soneto"
    assert v["composicion"]["confianza"] == "alta"


def test_soneto_sin_lineas_en_blanco(poema):
    texto = "\n".join(l for l in poema("garcilaso_soneto_v").splitlines() if l.strip())
    v = _vers(texto)
    assert [len(e["versos"]) for e in v["estrofas"]] == [4, 4, 3, 3]
    assert v["composicion"]["tipo"] == "soneto"


def test_romance(poema):
    v = _vers(poema("romance_del_prisionero"))
    assert v["rima"]["tipo"] == "asonante"
    assert v["rima"]["esquema"] == "-a" * 8
    assert v["composicion"]["tipo"] == "romance"
    assert v["estrofas"][0]["tipo"] == "tirada de romance"


def test_pirata_polimetrico(poema):
    v = _vers(poema("cancion_del_pirata"))
    assert v["composicion"]["tipo"] == "poema polimétrico"
    assert v["estrofas"][2]["tipo"] == "sextilla con pie quebrado"
    assert v["estrofas"][2]["esquema"].split()[:2] == ["8a", "4b"] or v["estrofas"][2]["esquema"].startswith("8")


def test_decima_espinela():
    texto = """Cuentan de un sabio que un día
tan pobre y mísero estaba,
que sólo se sustentaba
de unas hierbas que cogía.
¿Habrá otro, entre sí decía,
más pobre y triste que yo?;
y cuando el rostro volvió
halló la respuesta, viendo
que iba otro sabio cogiendo
las hierbas que él arrojó."""
    v = _vers(texto)
    assert v["rima"]["esquema"] == "abbaaccddc"
    assert v["composicion"]["tipo"] == "décima espinela"


def test_redondillas():
    texto = """Hombres necios que acusáis
a la mujer sin razón,
sin ver que sois la ocasión
de lo mismo que culpáis:

si con ansia sin igual
solicitáis su desdén,
¿por qué queréis que obren bien
si las incitáis al mal?"""
    v = _vers(texto)
    assert [e["tipo"] for e in v["estrofas"]] == ["redondilla", "redondilla"]
    assert v["composicion"]["tipo"] == "composición en redondillas"


def test_lira():
    texto = """En una noche oscura,
con ansias, en amores inflamada,
¡oh dichosa ventura!,
salí sin ser notada,
estando ya mi casa sosegada."""
    v = _vers(texto)
    assert v["estrofas"][0]["esquema"] == "7a 11B 7a 7b 11B"
    assert v["composicion"]["tipo"] == "lira"


def test_verso_libre():
    texto = """La ciudad amanece sin nombre
y nadie pregunta
por los pájaros que ayer cruzaban el puerto en bandadas grises,
ni por mí.
Abro la ventana."""
    v = _vers(texto)
    assert v["rima"]["tipo"] == "libre"
    assert v["composicion"]["tipo"] == "verso libre"


def test_b_y_v_riman_en_consonante():
    assert terminacion("suave").consonante == terminacion("sabe").consonante
