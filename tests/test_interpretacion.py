"""Tests del módulo interpretativo con un cliente simulado (sin llamar a la API)."""

from types import SimpleNamespace

import pytest

from interpretacion.cliente import analizar_con_anthropic
from interpretacion.gemini import analizar_con_gemini
from interpretacion.prompt import ErrorInterpretacion, construir_mensaje
from interpretacion.proveedor import analizar_interpretacion, proveedor_configurado
from interpretacion.esquema import AnalisisInterpretativo
from interpretacion.validacion import contar_palabras, recortar_palabras, validar

VERSOS = [
    "Escrito está en mi alma vuestro gesto,",
    "y cuanto yo escribir de vos deseo;",
    "vos sola lo escribistes, yo lo leo",
    "tan solo, que aun de vos me guardo en esto.",
]


def _analisis(**cambios):
    datos = {
        "recursos": [
            {"nombre": "metáfora", "categoria": "semánticos", "verso": 1, "hasta_verso": 1,
             "cita": "Escrito está en mi alma vuestro gesto",
             "explicacion": "El alma es un papel donde queda escrito el rostro amado.", "confianza": "alta"},
            {"nombre": "hipérbaton", "categoria": "sintácticos", "verso": 1, "hasta_verso": 1,
             "cita": "y cuanto yo escribir de vos deseo",  # está en el verso 2
             "explicacion": "Altera el orden para destacar el deseo.", "confianza": "media"},
            {"nombre": "aliteración", "categoria": "fónicos", "verso": 3, "hasta_verso": 3,
             "cita": "las olas del mar azul",  # no está en el poema
             "explicacion": "Inventado.", "confianza": "baja"},
        ],
        "temas": {"principal": "El amor como escritura en el alma",
                  "subtemas": ["la amada como modelo", "la fe amorosa", "la lectura", "la entrega", "sobra"]},
        "interpretacion": "Una lectura posible: " + "palabra " * 60,
    }
    datos.update(cambios)
    return AnalisisInterpretativo.model_validate(datos)


def test_validar_descarta_citas_inexistentes_y_corrige_versos():
    r = validar(_analisis(), VERSOS)
    nombres = [x["nombre"] for x in r["recursos"]]
    assert nombres == ["metáfora", "hipérbaton"]
    assert r["recursos"][1]["verso"] == 2 and r["recursos"][1]["verso_corregido"]
    assert r["recursos_descartados"][0]["nombre"] == "aliteración"


def test_validar_limita_subtemas_y_recorta_interpretacion():
    r = validar(_analisis(), VERSOS)
    assert len(r["temas"]["subtemas"]) == 4
    assert r["interpretacion"]["recortada"]
    assert r["interpretacion"]["palabras"] <= 50


def test_cita_en_varios_versos():
    a = _analisis(recursos=[{
        "nombre": "encabalgamiento", "categoria": "sintácticos", "verso": 3, "hasta_verso": 4,
        "cita": "yo lo leo tan solo", "explicacion": "Prolonga la idea.", "confianza": "alta"}])
    r = validar(a, VERSOS)
    assert (r["recursos"][0]["verso"], r["recursos"][0]["hasta_verso"]) == (3, 4)


def test_recortar_palabras():
    texto, recortado = recortar_palabras("uno dos tres", maximo=2)
    assert recortado and texto == "uno dos…"
    assert recortar_palabras("uno dos", maximo=2) == ("uno dos", False)
    assert contar_palabras("uno  dos\ntres") == 3


def test_mensaje_numera_los_versos():
    m = construir_mensaje(VERSOS)
    assert "[1] Escrito está" in m and "[4] tan solo" in m


class _ClienteFalso:
    def __init__(self, respuesta):
        self.llamadas = []
        self.beta = SimpleNamespace(messages=SimpleNamespace(parse=self._parse))
        self._respuesta = respuesta

    def _parse(self, **kwargs):
        self.llamadas.append(kwargs)
        return self._respuesta


def test_analizar_interpretacion_con_cliente_falso():
    respuesta = SimpleNamespace(stop_reason="end_turn", parsed_output=_analisis(), model="claude-sonnet-5-5")
    cliente = _ClienteFalso(respuesta)
    r = analizar_con_anthropic(VERSOS, cliente=cliente)
    assert r["modelo"] == "claude-sonnet-5-5"
    assert len(r["recursos"]) == 2
    llamada = cliente.llamadas[0]
    assert llamada["output_format"] is AnalisisInterpretativo
    assert "No inventes recursos" in llamada["system"]


def test_rechazo_del_modelo():
    respuesta = SimpleNamespace(stop_reason="refusal", parsed_output=None, model="x")
    with pytest.raises(ErrorInterpretacion):
        analizar_con_anthropic(VERSOS, cliente=_ClienteFalso(respuesta))


def test_sin_api_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("IA_PROVEEDOR", raising=False)
    assert proveedor_configurado() is None
    with pytest.raises(ErrorInterpretacion, match="API key"):
        analizar_interpretacion(VERSOS)


def test_eleccion_de_proveedor(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("IA_PROVEEDOR", raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", "clave")
    assert proveedor_configurado() == "gemini"
    monkeypatch.setenv("ANTHROPIC_API_KEY", "clave")
    assert proveedor_configurado() == "anthropic"
    monkeypatch.setenv("IA_PROVEEDOR", "gemini")
    assert proveedor_configurado() == "gemini"
    monkeypatch.setenv("IA_PROVEEDOR", "otro")
    with pytest.raises(ErrorInterpretacion):
        proveedor_configurado()


class _GeminiFalso:
    def __init__(self, respuesta):
        self.llamadas = []
        self.models = SimpleNamespace(generate_content=self._generar)
        self._respuesta = respuesta

    def _generar(self, **kwargs):
        self.llamadas.append(kwargs)
        return self._respuesta


def test_gemini_con_cliente_falso():
    respuesta = SimpleNamespace(parsed=_analisis(), text=None, model_version="gemini-flash")
    cliente = _GeminiFalso(respuesta)
    r = analizar_con_gemini(VERSOS, cliente=cliente)
    assert r["modelo"] == "gemini-flash"
    assert [x["nombre"] for x in r["recursos"]] == ["metáfora", "hipérbaton"]
    config = cliente.llamadas[0]["config"]
    assert config.response_mime_type == "application/json"
    assert config.response_schema is AnalisisInterpretativo
    assert "No inventes recursos" in config.system_instruction


def test_gemini_respuesta_en_texto_json():
    texto = _analisis().model_dump_json()
    respuesta = SimpleNamespace(parsed=None, text=texto, model_version=None)
    r = analizar_con_gemini(VERSOS, cliente=_GeminiFalso(respuesta))
    assert r["temas"]["principal"].startswith("El amor")


def test_gemini_json_invalido():
    respuesta = SimpleNamespace(parsed=None, text="{no es json", model_version=None)
    with pytest.raises(ErrorInterpretacion, match="esquema"):
        analizar_con_gemini(VERSOS, cliente=_GeminiFalso(respuesta))
