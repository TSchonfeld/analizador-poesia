"""Escansión de poemas canónicos de referencia."""

from metrica.poema import escandir


def test_soneto_de_garcilaso(poema):
    e = escandir(poema("garcilaso_soneto_v"))
    assert len(e.versos) == 14
    assert e.metros == [11]
    assert [v.silabas for v in e.versos] == [11] * 14
    assert all(v.arte == "arte mayor" for v in e.versos)
    assert [len(x) for x in e.estrofas] == [4, 4, 3, 3]
    # El primer verso es ambiguo (hiato en «está ‖ en» o en «mi ‖ alma»):
    # se muestran las alternativas y la confianza no es alta.
    v1 = e.versos[0]
    assert v1.confianza == "media"
    assert v1.alternativas
    assert e.versos[0].ritmo == "heroico (2.ª-6.ª)"


def test_romance_tradicional(poema):
    e = escandir(poema("romance_del_prisionero"))
    assert len(e.versos) == 16
    assert e.metros == [8]
    assert all(v.silabas == 8 for v in e.versos)
    # «cuando hace la calor»: aguda (+1) y hiato ante la h aspirada.
    v2 = e.versos[1]
    assert v2.ley_acento_final == "aguda" and v2.ajuste_final == 1
    assert any(l.tipo == "hiato" for l in v2.lectura.licencias)


def test_cancion_del_pirata_polimetria(poema):
    e = escandir(poema("cancion_del_pirata"))
    assert set(e.metros) == {8, 4}
    longitudes = [v.silabas for v in e.versos]
    assert longitudes[:16] == [8] * 16
    # «Navega, velero mío, / sin temor, ...»: octosílabos con pie quebrado.
    assert longitudes[16:22] == [8, 4, 8, 8, 8, 8]
    # «Veinte presas / hemos hecho / ...»: tetrasílabos.
    assert longitudes[22:30] == [4] * 8
    # Estribillo
    assert longitudes[30:34] == [8] * 4
    # «sea cualquiera» exige sinéresis para ser tetrasílabo.
    v42 = e.versos[41]
    assert v42.silabas == 4
    assert any(l.tipo == "sinéresis" for l in v42.lectura.licencias)
    # «a mi valor» solo da tetrasílabo con sinafía con el verso anterior,
    # que el motor no aplica: se informa con confianza baja.
    assert e.versos[47].confianza == "baja"


def test_alejandrinos_de_dario():
    texto = (
        "La princesa está triste... ¿qué tendrá la princesa?\n"
        "Los suspiros se escapan de su boca de fresa,\n"
        "que ha perdido la risa, que ha perdido el color.\n"
        "La princesa está pálida en su silla de oro,\n"
    )
    e = escandir(texto)
    assert all(v.silabas == 14 for v in e.versos)
    assert all(v.hemistiquios == (7, 7) for v in e.versos)
    # Primer hemistiquio esdrújulo: «pá-li-da» cuenta 7 (8 − 1).
    assert e.versos[3].lectura.silabeo.startswith("La prin-ce-sa‿es-tá pá-li-da / ")
