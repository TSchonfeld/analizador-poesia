from fastapi.testclient import TestClient

from app import main


def _cliente():
    return TestClient(main.app)


def test_salud():
    assert _cliente().get("/api/salud").json() == {"estado": "ok"}


def test_analizar_sin_interpretacion(poema):
    r = _cliente().post("/api/analizar", json={"texto": poema("garcilaso_soneto_v"), "interpretar": False})
    assert r.status_code == 200
    datos = r.json()
    assert datos["versificacion"]["composicion"]["tipo"] == "soneto"
    assert len(datos["metrica"]["versos"]) == 14
    assert datos["interpretativo"] is None


def test_analizar_sin_api_key_avisa(poema, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    r = _cliente().post("/api/analizar", json={"texto": poema("romance_del_prisionero")})
    assert r.status_code == 200
    datos = r.json()
    assert datos["interpretativo"] is None
    assert "ANTHROPIC_API_KEY" in datos["avisos"][0]


def test_analizar_con_interpretacion_simulada(poema, monkeypatch):
    def falso(versos, metrica):
        return {"recursos": [], "recursos_descartados": [], "temas": {"principal": "x", "subtemas": []},
                "interpretacion": {"texto": "y", "palabras": 1, "recortada": False}, "modelo": "falso"}

    monkeypatch.setattr(main, "analizar_interpretacion", falso)
    r = _cliente().post("/api/analizar", json={"texto": poema("romance_del_prisionero")})
    assert r.json()["interpretativo"]["modelo"] == "falso"


def test_texto_vacio_o_largo():
    c = _cliente()
    assert c.post("/api/analizar", json={"texto": "   "}).status_code == 422
    assert c.post("/api/analizar", json={"texto": "a" * 9000}).status_code == 422


def test_sirve_el_frontend():
    r = _cliente().get("/")
    assert r.status_code == 200
    assert "Analizador de Poesía" in r.text
