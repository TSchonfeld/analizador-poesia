import pytest
from fastapi.testclient import TestClient

from app import main


def _cliente():
    return TestClient(main.app)


def test_salud():
    assert _cliente().get("/api/salud").json() == {"estado": "ok"}


@pytest.fixture
def sin_keys(monkeypatch):
    for v in ("ANTHROPIC_API_KEY", "GEMINI_API_KEY", "IA_PROVEEDOR"):
        monkeypatch.delenv(v, raising=False)


def test_config_sin_keys(sin_keys):
    assert _cliente().get("/api/config").json() == {"ia_disponible": False, "proveedor": None}


def test_config_con_gemini(sin_keys, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "clave")
    assert _cliente().get("/api/config").json() == {"ia_disponible": True, "proveedor": "gemini"}


def test_analizar_sin_ia_usa_reglas(poema, sin_keys):
    r = _cliente().post("/api/analizar", json={"texto": poema("garcilaso_soneto_v"), "interpretar": False})
    assert r.status_code == 200
    datos = r.json()
    assert datos["versificacion"]["composicion"]["tipo"] == "soneto"
    assert len(datos["metrica"]["versos"]) == 14
    assert datos["avisos"] == []
    interp = datos["interpretativo"]
    assert interp["origen"] == "reglas"
    assert interp["temas"] is None and interp["interpretacion"] is None
    assert any(x["nombre"] == "anáfora" for x in interp["recursos"])


def test_analizar_sin_api_key_avisa(poema, sin_keys):
    r = _cliente().post("/api/analizar", json={"texto": poema("romance_del_prisionero")})
    assert r.status_code == 200
    datos = r.json()
    assert datos["interpretativo"]["origen"] == "reglas"
    assert "API key" in datos["avisos"][0]


def test_analizar_con_interpretacion_simulada(poema, monkeypatch):
    def falso(versos, metrica):
        return {"recursos": [], "recursos_descartados": [], "temas": {"principal": "x", "subtemas": []},
                "interpretacion": {"texto": "y", "palabras": 1, "recortada": False}, "modelo": "falso"}

    monkeypatch.setattr(main, "analizar_interpretacion", falso)
    r = _cliente().post("/api/analizar", json={"texto": poema("romance_del_prisionero")})
    datos = r.json()["interpretativo"]
    assert datos["modelo"] == "falso" and datos["origen"] == "ia"


def test_texto_vacio_o_largo():
    c = _cliente()
    assert c.post("/api/analizar", json={"texto": "   "}).status_code == 422
    assert c.post("/api/analizar", json={"texto": "a" * 9000}).status_code == 422


def test_sirve_el_frontend():
    r = _cliente().get("/")
    assert r.status_code == 200
    assert "Analizador de Poesía" in r.text
