"""Pruebas del switch de IAs y de la temperatura (no requieren Ollama ni internet)."""

import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import almacenamiento as alm  # noqa: E402
import analisis  # noqa: E402
from analisis import (  # noqa: E402
    ErrorClasificacion, ModeloNoEncontradoError, OllamaNoDisponibleError, ServicioNoDisponibleError,
    _traducir_excepcion, verificar_modelo,
)
from config import cargar_config, config_con_modelo, etiqueta_modelo, separar_clave  # noqa: E402

CARRERA = {"id": "c001", "nombre": "24 Horas de Le Mans"}


def test_separar_clave():
    assert separar_clave("gemini:gemini-3.5-flash") == ("gemini", "gemini-3.5-flash")
    assert separar_clave("ollama:qwen2.5:3b") == ("ollama", "qwen2.5:3b")
    assert separar_clave("qwen2.5:3b") == ("ollama", "qwen2.5:3b")   # formato antiguo del .env
    assert separar_clave("llama3.2:3b") == ("ollama", "llama3.2:3b")


def test_config_con_modelo_y_temperatura():
    cfg = config_con_modelo(cargar_config(), "gemini:gemini-3.5-flash", temperatura=0.7)
    assert cfg.PROVEEDOR == "gemini" and cfg.OLLAMA_MODEL == "gemini-3.5-flash"
    assert cfg.OLLAMA_TEMPERATURE == 0.7 and not cfg.es_local
    assert cfg.nombre_modelo == "gemini/gemini-3.5-flash"
    local = config_con_modelo(cfg, "ollama:qwen2.5:3b")
    assert local.es_local and local.OLLAMA_TEMPERATURE == 0.7  # conserva la temperatura


def test_etiquetas():
    assert "Gemini" in etiqueta_modelo("gemini:gemini-3.5-flash")
    assert "otro-modelo" in etiqueta_modelo("ollama:otro-modelo")


def test_registro_guarda_temperatura_y_modelo():
    a = SimpleNamespace(es_pertinente=True, sentimiento="positivo", razon="r")
    r = alm.crear_registro(CARRERA, "Gran carrera", a, "gemini/gemini-3.5-flash", "2.1", temperatura=0.3)
    assert r["temperatura"] == 0.3 and r["modelo"] == "gemini/gemini-3.5-flash"


def test_errores_gemini_traducidos():
    cfg = config_con_modelo(cargar_config(), "gemini:gemini-3.5-flash")
    casos = {
        "429 RESOURCE_EXHAUSTED quota": ServicioNoDisponibleError,
        "400 API key not valid. Please pass a valid API key.": ServicioNoDisponibleError,
        "404 NOT_FOUND models/x is not found": ModeloNoEncontradoError,
        "500 INTERNAL": ErrorClasificacion,
        "503 UNAVAILABLE high demand": ErrorClasificacion,
    }
    for texto, clase in casos.items():
        err = _traducir_excepcion(RuntimeError(texto), cfg)
        assert type(err) is clase, texto
    assert "límite" in str(_traducir_excepcion(RuntimeError("429 RESOURCE_EXHAUSTED"), cfg))
    assert "DIARIO" in str(_traducir_excepcion(RuntimeError("429 RESOURCE_EXHAUSTED requests per day"), cfg))
    assert "saturado" in str(_traducir_excepcion(RuntimeError("503 UNAVAILABLE"), cfg))


def test_ollama_caido_es_servicio_no_disponible():
    cfg = config_con_modelo(cargar_config(), "ollama:qwen2.5:3b")
    err = _traducir_excepcion(ConnectionError("rechazada"), cfg)
    assert isinstance(err, OllamaNoDisponibleError) and isinstance(err, ServicioNoDisponibleError)


def test_gemini_sin_clave(monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "")
    cfg = config_con_modelo(cargar_config(), "gemini:gemini-3.5-flash")
    ok, msg = verificar_modelo(cfg)
    assert not ok and "GOOGLE_API_KEY" in msg
    try:
        analisis.crear_modelo(cfg)
    except ServicioNoDisponibleError as e:
        assert "GOOGLE_API_KEY" in str(e)
    else:
        raise AssertionError("debía fallar sin clave")
