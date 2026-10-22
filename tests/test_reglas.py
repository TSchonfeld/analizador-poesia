from interpretacion.reglas import detectar_recursos
from metrica.poema import dividir_estrofas


def _recursos(texto):
    estrofas = dividir_estrofas(texto)
    versos = [v for e in estrofas for v in e]
    indices = [k for k, e in enumerate(estrofas) for _ in e]
    return detectar_recursos(versos, indices)


def _nombres(texto):
    return [r["nombre"] for r in _recursos(texto)]


def test_anafora_en_garcilaso(poema):
    r = [x for x in _recursos(poema("garcilaso_soneto_v")) if x["nombre"] == "anáfora"]
    assert len(r) == 1
    assert (r[0]["verso"], r[0]["hasta_verso"]) == (13, 14)
    assert "por vos" in r[0]["explicacion"]


def test_anafora_con_versos_intercalados(poema):
    r = [x for x in _recursos(poema("romance_del_prisionero")) if x["nombre"] == "anáfora"]
    assert r and "2, 3, 5, 7" in r[0]["explicacion"]


def test_polisindeton():
    assert "polisíndeton" in _nombres("y el mar y la tierra y el cielo")
    assert "polisíndeton" not in _nombres("el mar y la tierra")


def test_aliteracion():
    r = _recursos("bajo el ala aleve del leve abanico")
    assert r[0]["nombre"] == "aliteración" and "/l/" in r[0]["explicacion"]
    assert _nombres("la casa estaba vacía") == []


def test_epifora():
    assert "epífora" in _nombres("Te busco en la noche\ny no estás en la noche")


def test_encabalgamiento_abrupto():
    r = [x for x in _recursos("Llegaba con la\nluz de la mañana") if x["nombre"] == "encabalgamiento"]
    assert r and (r[0]["verso"], r[0]["hasta_verso"]) == (1, 2)
    assert _nombres("Llegaba con la luz,\nde la mañana") == []


def test_todos_marcados_como_reglas(poema):
    assert all(r["origen"] == "reglas" for r in _recursos(poema("cancion_del_pirata")))
