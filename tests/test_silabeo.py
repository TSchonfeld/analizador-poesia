import pytest

from metrica.silabeo import silabear


@pytest.mark.parametrize(
    "palabra, esperado",
    [
        ("perro", "pe-rro"),
        ("calle", "ca-lle"),
        ("queso", "que-so"),
        ("guerra", "gue-rra"),
        ("instante", "ins-tan-te"),
        ("abstracto", "abs-trac-to"),
        ("atleta", "at-le-ta"),
        ("subrayar", "sub-ra-yar"),
        ("transporte", "trans-por-te"),
        ("ahora", "a-ho-ra"),
        # diptongos y triptongos
        ("ciudad", "ciu-dad"),
        ("cuidado", "cui-da-do"),
        ("buey", "buey"),
        ("Guadalquivir", "Gua-dal-qui-vir"),
        ("pingüino", "pin-güi-no"),
        ("cigüeña", "ci-güe-ña"),
        ("guion", "guion"),
        ("huir", "huir"),
        ("rey", "rey"),
        # hiatos
        ("país", "pa-ís"),
        ("poeta", "po-e-ta"),
        ("héroe", "hé-ro-e"),
        ("creía", "cre-í-a"),
        ("leíais", "le-í-ais"),
        ("chiita", "chi-i-ta"),
        # diéresis marcada en la grafía
        ("süave", "sü-a-ve"),
        ("ruïdo", "ru-ï-do"),
    ],
)
def test_silabeo(palabra, esperado):
    assert silabear(palabra).silabeo() == esperado


@pytest.mark.parametrize(
    "palabra, tipo",
    [
        ("corazón", "aguda"),
        ("estoy", "aguda"),
        ("virtud", "aguda"),
        ("alma", "llana"),
        ("árbol", "llana"),
        ("lirio", "llana"),
        ("cántaro", "esdrújula"),
        ("héroe", "esdrújula"),
        ("dígaselo", "sobresdrújula"),
        ("rápidamente", "llana"),
    ],
)
def test_tipo_acentual(palabra, tipo):
    assert silabear(palabra).tipo_acentual() == tipo


@pytest.mark.parametrize("palabra", ["el", "la", "de", "que", "mi", "se", "y", "para"])
def test_atonas(palabra):
    assert not silabear(palabra).es_tonica


@pytest.mark.parametrize("palabra", ["qué", "él", "mí", "yo", "sol", "un"])
def test_tonicas(palabra):
    assert silabear(palabra).es_tonica


def test_bordes_para_sinalefa():
    assert silabear("hermosa").empieza_en_vocal  # h muda
    assert not silabear("hielo").empieza_en_vocal  # semiconsonante
    assert not silabear("yo").empieza_en_vocal  # y consonante
    assert not silabear("rey").termina_en_vocal  # re-yes
    assert silabear("y").empieza_en_vocal and silabear("y").termina_en_vocal


def test_sineresis_y_dieresis_posibles():
    assert silabear("poeta").hiatos == [0]
    assert silabear("ahora").hiatos == [0]
    assert silabear("süave").dieresis_marcadas == [0]
    # el diptongo de «ruido» podría deshacerse por diéresis
    assert silabear("ruido").silabas[0].corte_dieresis == 2
    # la «y» final no se separa
    assert silabear("muy").silabas[0].corte_dieresis is None
