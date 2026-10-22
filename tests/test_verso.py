import pytest

from metrica.verso import analizar_verso, arte, nombre_verso, tipo_endecasilabo


def _longitudes(verso):
    return set(analizar_verso(verso).lecturas)


def test_ley_del_acento_final():
    # llana: no cambia; aguda: +1; esdrújula: −1
    assert analizar_verso("cuando los trigos encañan").mejor().silabas == 8
    assert analizar_verso("un velero bergantín").mejor().silabas == 8
    assert analizar_verso("mi única patria la mar").mejor().silabas == 8
    a = analizar_verso("por hábito del alma mismo os quiero")
    assert a.ley_acento_final == "llana"
    e = analizar_verso("tus ojos de color de lágrima")
    assert e.ley_acento_final == "esdrújula" and e.ajuste_final == -1


def test_sinalefa_por_defecto_y_alternativa_de_hiato():
    a = analizar_verso("Escrito está en mi alma vuestro gesto")
    # Con todas las sinalefas da 10; el endecasílabo exige un hiato.
    assert a.mejor().silabas == 10
    once = a.lecturas[11]
    assert [l.tipo for l in once[0].licencias if l.tipo == "hiato"] == ["hiato"]
    # El hiato más natural es tras la vocal tónica: «es-tá ‖ en».
    assert "tá ‖ en" in [l.texto for l in once[0].licencias]


def test_sineresis():
    a = analizar_verso("sea cualquiera")
    assert 4 in a.lecturas
    assert any(l.tipo == "sinéresis" for l in a.lecturas[4][0].licencias)


def test_dieresis_marcada_en_la_grafia():
    a = analizar_verso("con un manso ruïdo")
    lectura = a.mejor()
    assert lectura.silabas == 7
    assert any(l.tipo == "diéresis" for l in lectura.licencias)


def test_y_entre_vocales_no_hace_doble_sinalefa():
    a = analizar_verso("olas de plata y azul")
    assert 8 in a.lecturas
    assert a.lecturas[8][0].coste < 0.5


def test_silabeo_con_guiones_y_ligaduras():
    a = analizar_verso("viento en popa, a toda vela,")
    assert a.mejor().silabeo == "vien-to‿en po-pa‿a to-da ve-la"


@pytest.mark.parametrize(
    "n, nombre, clase",
    [(4, "tetrasílabo", "arte menor"), (8, "octosílabo", "arte menor"),
     (9, "eneasílabo", "arte mayor"), (11, "endecasílabo", "arte mayor"),
     (14, "alejandrino", "arte mayor")],
)
def test_nombres_y_arte(n, nombre, clase):
    assert nombre_verso(n) == nombre
    assert arte(n) == clase


def test_tipo_endecasilabo():
    assert tipo_endecasilabo([2, 6, 10]) == "heroico (2.ª-6.ª)"
    assert tipo_endecasilabo([3, 6, 10]) == "melódico (3.ª-6.ª)"
    assert tipo_endecasilabo([1, 6, 10]) == "enfático (1.ª-6.ª)"
    assert tipo_endecasilabo([4, 8, 10]) == "sáfico (4.ª-8.ª)"
