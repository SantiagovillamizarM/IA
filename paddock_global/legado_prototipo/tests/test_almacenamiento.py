"""Pruebas de almacenamiento (no requieren Ollama)."""

import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import almacenamiento as alm  # noqa: E402
from config import RUTA_CARRERAS  # noqa: E402

CARRERA = {"id": "c002", "nombre": "24 Horas de Nürburgring", "pais": "Alemania", "circuito": "Nordschleife"}


def analisis(sent="positivo", pert=True, razon="El aficionado elogia el trazado."):
    return SimpleNamespace(es_pertinente=pert, sentimiento=sent, razon=razon)


def registro(texto="Qué carrera tan buena", sent="positivo", carrera=CARRERA, rid=None):
    return alm.crear_registro(carrera, texto, analisis(sent), "ollama/prueba", "1.0", registro_id=rid)


# ---------------------------------------------------------------- catálogo

def test_catalogo_real_valido():
    carreras = alm.cargar_carreras(RUTA_CARRERAS)
    assert len(carreras) == 20
    assert len({c["id"] for c in carreras}) == 20
    assert carreras[0]["nombre"] == "24 Horas de Le Mans"


def test_catalogo_id_duplicado(tmp_path):
    ruta = tmp_path / "carreras.json"
    ruta.write_text(json.dumps({"version": 1, "carreras": [
        {"id": "c001", "nombre": "A", "pais": "X", "circuito": "Y"},
        {"id": "c001", "nombre": "B", "pais": "X", "circuito": "Y"},
    ]}), encoding="utf-8")
    with pytest.raises(alm.CatalogoInvalidoError, match="c001"):
        alm.cargar_carreras(ruta)


# --------------------------------------------------------------- opiniones

def test_archivo_inexistente_devuelve_vacio_sin_crear(tmp_path):
    ruta = tmp_path / "opiniones.json"
    assert alm.cargar_opiniones(ruta) == {"version": 1, "opiniones": []}
    assert not ruta.exists()


def test_json_invalido_conserva_archivo(tmp_path):
    ruta = tmp_path / "opiniones.json"
    ruta.write_bytes(b"{roto")
    with pytest.raises(alm.ArchivoOpinionesCorruptoError):
        alm.cargar_opiniones(ruta)
    with pytest.raises(alm.ArchivoOpinionesCorruptoError):
        alm.guardar_opinion(ruta, registro())
    assert ruta.read_bytes() == b"{roto"


@pytest.mark.parametrize("contenido", [
    [],
    {"opiniones": []},
    {"version": 1, "opiniones": {}},
    {"version": 1, "opiniones": [{"id": "x"}]},
])
def test_esquema_inesperado_conserva_archivo(tmp_path, contenido):
    ruta = tmp_path / "opiniones.json"
    original = json.dumps(contenido).encode()
    ruta.write_bytes(original)
    with pytest.raises(alm.ArchivoOpinionesCorruptoError):
        alm.guardar_opinion(ruta, registro())
    assert ruta.read_bytes() == original


def test_dos_registros_distintos(tmp_path):
    ruta = tmp_path / "opiniones.json"
    assert alm.guardar_opinion(ruta, registro("Primera opinión"))
    assert alm.guardar_opinion(ruta, registro("Primera opinión"))  # mismo texto, envío distinto
    assert len(alm.cargar_opiniones(ruta)["opiniones"]) == 2


def test_idempotencia_por_id(tmp_path):
    ruta = tmp_path / "opiniones.json"
    r = registro()
    assert alm.guardar_opinion(ruta, r) is True
    assert alm.guardar_opinion(ruta, r) is False
    assert len(alm.cargar_opiniones(ruta)["opiniones"]) == 1


def test_fallo_escritura_no_corrompe_ni_deja_tmp(tmp_path, monkeypatch):
    ruta = tmp_path / "opiniones.json"
    alm.guardar_opinion(ruta, registro("Opinión inicial"))
    antes = ruta.read_bytes()

    def falla(*_a, **_k):
        raise PermissionError("bloqueado")

    monkeypatch.setattr(alm.os, "replace", falla)
    with pytest.raises(alm.ErrorEscrituraOpiniones):
        alm.guardar_opinion(ruta, registro("Otra opinión"))
    assert ruta.read_bytes() == antes
    assert list(tmp_path.glob("*.tmp")) == []


def test_crear_registro_rechaza_no_pertinente():
    with pytest.raises(ValueError):
        alm.crear_registro(CARRERA, "texto", analisis(None, pert=False), "m")


def test_registro_campos_generados_por_programa():
    r = registro("  Gran carrera nocturna  ")
    assert r["opinion_original"] == "Gran carrera nocturna"
    assert r["carrera_id"] == "c002" and r["carrera_nombre"] == CARRERA["nombre"]
    assert r["fecha_utc"].endswith("+00:00")
    assert len(r["id"]) == 36


def test_utf8_sin_escapes(tmp_path):
    ruta = tmp_path / "opiniones.json"
    for nombre in ("24 Horas de Nürburgring", "6 Horas de São Paulo", "24 Horas de Dubái"):
        c = {**CARRERA, "nombre": nombre}
        alm.guardar_opinion(ruta, registro(f"Opinión sobre {nombre}", carrera=c))
    texto = ruta.read_text(encoding="utf-8")
    assert "Nürburgring" in texto and "São Paulo" in texto and "Dubái" in texto
    assert "\\u" not in texto


# --------------------------------------------------------------- consultas

def test_consultar_y_contar():
    le_mans = {**CARRERA, "id": "c001", "nombre": "24 Horas de Le Mans"}
    regs = [
        registro("a positiva", "positivo"),
        registro("b negativa", "negativo"),
        registro("c positiva", "positivo", carrera=le_mans),
    ]
    assert len(alm.consultar_opiniones(regs)) == 3
    assert len(alm.consultar_opiniones(regs, carrera_id="c002")) == 2
    assert len(alm.consultar_opiniones(regs, sentimiento="positivo")) == 2
    assert len(alm.consultar_opiniones(regs, "c001", "negativo")) == 0
    conteo = alm.contar_por_sentimiento(alm.consultar_opiniones(regs, carrera_id="c002"))
    assert conteo == {"positivo": 1, "negativo": 1, "neutro": 0, "mixto": 0}
