"""Persistencia del modo taller (opiniones.json): reglas obligatorias del taller."""

from __future__ import annotations

import json
import os

import pytest

from paddock.adaptadores.persistencia import json_repo
from paddock.adaptadores.persistencia.json_repo import (
    RepositorioOpinionesJson,
    cargar_opiniones,
    consultar_opiniones,
    guardar_opinion,
)
from paddock.dominio.entidades import FiltrosOpinion, Revision
from paddock.dominio.errores import ArchivoOpinionesCorruptoError, ErrorEscrituraOpiniones
from tests.conftest import opinion_ejemplo

pytestmark = pytest.mark.integracion


def test_cargar_inexistente_devuelve_vacio_sin_crear(ruta_opiniones):
    assert not ruta_opiniones.exists()
    assert cargar_opiniones(ruta_opiniones) == {"version": 1, "opiniones": []}
    assert not ruta_opiniones.exists()


def test_json_invalido_lanza_error_y_conserva_bytes(ruta_opiniones):
    ruta_opiniones.write_bytes(b"{roto")
    antes = ruta_opiniones.read_bytes()
    with pytest.raises(ArchivoOpinionesCorruptoError):
        cargar_opiniones(ruta_opiniones)
    with pytest.raises(ArchivoOpinionesCorruptoError):
        guardar_opinion(ruta_opiniones, opinion_ejemplo().a_dict())
    assert ruta_opiniones.read_bytes() == antes


@pytest.mark.parametrize("contenido", [
    [], {"version": 1}, {"opiniones": []}, {"version": "1", "opiniones": []},
    {"version": 1, "opiniones": [{"id": "x"}]},
    {"version": 1, "opiniones": ["texto"]},
])
def test_esquema_inesperado_error_y_archivo_conservado(ruta_opiniones, contenido):
    ruta_opiniones.write_text(json.dumps(contenido), encoding="utf-8")
    antes = ruta_opiniones.read_bytes()
    with pytest.raises(ArchivoOpinionesCorruptoError):
        cargar_opiniones(ruta_opiniones)
    assert ruta_opiniones.read_bytes() == antes


def test_sentimiento_invalido_e_id_repetido(ruta_opiniones):
    reg = opinion_ejemplo().a_dict()
    ruta_opiniones.write_text(json.dumps({"version": 1, "opiniones": [{**reg, "sentimiento": "feliz"}]}),
                              encoding="utf-8")
    with pytest.raises(ArchivoOpinionesCorruptoError):
        cargar_opiniones(ruta_opiniones)
    ruta_opiniones.write_text(json.dumps({"version": 1, "opiniones": [reg, reg]}), encoding="utf-8")
    with pytest.raises(ArchivoOpinionesCorruptoError, match="repetido"):
        cargar_opiniones(ruta_opiniones)


def test_dos_registros_distintos_y_el_mismo_dos_veces(repo_json, ruta_opiniones):
    assert repo_json.guardar(opinion_ejemplo(1)) is True
    assert repo_json.guardar(opinion_ejemplo(2)) is True
    assert len(cargar_opiniones(ruta_opiniones)["opiniones"]) == 2
    assert repo_json.guardar(opinion_ejemplo(2)) is False  # idempotencia
    assert len(cargar_opiniones(ruta_opiniones)["opiniones"]) == 2


def test_mismo_texto_enviado_dos_veces_son_dos_registros(repo_json):
    a = opinion_ejemplo(1)
    b = opinion_ejemplo(2, opinion_original=a.opinion_original)
    assert repo_json.guardar(a) and repo_json.guardar(b)
    assert repo_json.contar(FiltrosOpinion()) == 2


def test_fallo_en_os_replace_conserva_original_y_sin_tmp(repo_json, ruta_opiniones, monkeypatch):
    repo_json.guardar(opinion_ejemplo(1))
    antes = ruta_opiniones.read_bytes()

    def fallar(*_a, **_k):
        raise OSError(28, "No queda espacio en el disco")

    monkeypatch.setattr(json_repo.os, "replace", fallar)
    with pytest.raises(ErrorEscrituraOpiniones):
        repo_json.guardar(opinion_ejemplo(2))
    assert ruta_opiniones.read_bytes() == antes
    assert list(ruta_opiniones.parent.glob("*.tmp")) == []


def test_permission_error_mensaje_comprensible(repo_json, monkeypatch):
    def denegar(*_a, **_k):
        raise PermissionError(13, "Acceso denegado")

    monkeypatch.setattr(json_repo.os, "replace", denegar)
    with pytest.raises(ErrorEscrituraOpiniones, match="solo lectura"):
        repo_json.guardar(opinion_ejemplo(1))
    assert list(repo_json.ruta.parent.glob("*.tmp")) == []


@pytest.mark.skipif(os.name != "nt", reason="attrib +R es de Windows")
def test_archivo_de_solo_lectura_en_windows(repo_json, ruta_opiniones):
    import stat

    repo_json.guardar(opinion_ejemplo(1))
    os.chmod(ruta_opiniones, stat.S_IREAD)
    try:
        with pytest.raises(ErrorEscrituraOpiniones):
            repo_json.guardar(opinion_ejemplo(2))
    finally:
        os.chmod(ruta_opiniones, stat.S_IREAD | stat.S_IWRITE)
    assert len(cargar_opiniones(ruta_opiniones)["opiniones"]) == 1
    assert list(ruta_opiniones.parent.glob("*.tmp")) == []


def test_utf8_sin_escapes(repo_json, ruta_opiniones):
    for i, nombre in enumerate(["Nürburgring", "São Paulo", "Dubái", "Jyväskylä"], start=1):
        repo_json.guardar(opinion_ejemplo(i, opinion_original=f"Qué carrera en {nombre}", evento_nombre=nombre))
    texto = ruta_opiniones.read_text(encoding="utf-8")
    for nombre in ["Nürburgring", "São Paulo", "Dubái", "Jyväskylä"]:
        assert nombre in texto
    assert "\\u" not in texto


def test_consultar_con_y_sin_filtros(repo_json):
    repo_json.guardar(opinion_ejemplo(1))
    repo_json.guardar(opinion_ejemplo(2, sentimiento="negativo"))
    repo_json.guardar(opinion_ejemplo(3, evento_id="ev-f1-monaco", evento_nombre="GP Mónaco", disciplina_id="formula"))
    assert len(repo_json.consultar(FiltrosOpinion())) == 3
    assert len(repo_json.consultar(FiltrosOpinion(evento_id="ev-res-lemans"))) == 2
    assert len(repo_json.consultar(FiltrosOpinion(sentimiento="negativo"))) == 1
    assert len(repo_json.consultar(FiltrosOpinion(disciplina_id="formula"))) == 1
    datos = cargar_opiniones(repo_json.ruta)["opiniones"]
    assert len(consultar_opiniones(datos)) == 3
    assert len(consultar_opiniones(datos, evento_id="ev-res-lemans", sentimiento="positivo")) == 1


def test_compatibilidad_registro_v1_sin_campos_nuevos(ruta_opiniones):
    reg_v1 = {k: v for k, v in opinion_ejemplo().a_dict().items()
              if k in ("id", "fecha_utc", "evento_id", "evento_nombre", "opinion_original", "sentimiento",
                       "razon", "modelo", "version_prompt")}
    ruta_opiniones.write_text(json.dumps({"version": 1, "opiniones": [reg_v1]}), encoding="utf-8")
    ops = RepositorioOpinionesJson(ruta_opiniones).consultar(FiltrosOpinion())
    assert ops[0].aspectos is None and ops[0].visible is True and ops[0].origen == "chat"


def test_revision_visibilidad_y_anonimizar(repo_json):
    repo_json.guardar(opinion_ejemplo(1, usuario_id="u1"))
    oid = opinion_ejemplo(1).id
    repo_json.guardar_revision(oid, Revision("negativo", "mod", "2026-11-10T00:00:00+00:00", "ironía"))
    op = repo_json.obtener(oid)
    assert op.sentimiento == "positivo" and op.sentimiento_efectivo == "negativo"
    assert len(repo_json.historial_revisiones(oid)) == 1
    repo_json.cambiar_visibilidad(oid, False)
    assert repo_json.contar(FiltrosOpinion()) == 0
    assert repo_json.anonimizar_usuario("u1") == 1
    assert repo_json.obtener(oid).usuario_id is None
