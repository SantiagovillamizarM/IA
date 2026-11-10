"""Tests de contrato: los adaptadores JSON y SQL pasan EXACTAMENTE los mismos casos del puerto."""

from __future__ import annotations

import pytest

from paddock.adaptadores.persistencia.json_repo import RepositorioOpinionesJson
from paddock.adaptadores.persistencia.sql_repo import BaseDatos, SqlRepositorioOpiniones
from paddock.dominio.entidades import FiltrosOpinion, Revision
from tests.conftest import opinion_ejemplo

pytestmark = pytest.mark.integracion


@pytest.fixture(params=["json", "sql"])
def repo(request, tmp_path):
    if request.param == "json":
        return RepositorioOpinionesJson(tmp_path / "opiniones.json")
    bd = BaseDatos(f"sqlite:///{(tmp_path / 'p.db').as_posix()}")
    bd.crear_esquema()
    return SqlRepositorioOpiniones(bd)


def test_guardar_es_idempotente(repo):
    assert repo.guardar(opinion_ejemplo(1)) is True
    assert repo.guardar(opinion_ejemplo(1)) is False
    assert repo.guardar(opinion_ejemplo(2)) is True
    assert repo.contar(FiltrosOpinion()) == 2


def test_obtener_y_roundtrip_completo(repo):
    op = opinion_ejemplo(7, aspectos=[{"aspecto": "trazado", "sentimiento": "positivo"}], ironia=False,
                         intensidad=4, entidades=["Porsche"], usuario_id="u-1", origen="api",
                         opinion_original="Jyväskylä y Nürburgring: São Paulo")
    repo.guardar(op)
    assert repo.obtener(op.id) == op
    assert repo.obtener("no-existe") is None


def test_consultar_filtros_orden_y_paginacion(repo):
    repo.guardar(opinion_ejemplo(1, sentimiento="positivo", fecha_utc="2026-11-01T10:00:00+00:00"))
    repo.guardar(opinion_ejemplo(2, sentimiento="negativo", fecha_utc="2026-11-03T10:00:00+00:00",
                                 aspectos=[{"aspecto": "clima", "sentimiento": "negativo"}]))
    repo.guardar(opinion_ejemplo(3, evento_id="ev-f1-monaco", evento_nombre="GP de Mónaco", disciplina_id="formula",
                                 edicion_anio=2025, fecha_utc="2026-11-02T10:00:00+00:00",
                                 opinion_original="Mucha lluvia en el túnel"))
    todos = repo.consultar(FiltrosOpinion())
    assert [o.id[-1] for o in todos] == ["2", "3", "1"]
    assert len(repo.consultar(FiltrosOpinion(limite=1, desplazamiento=1))) == 1
    assert repo.consultar(FiltrosOpinion(limite=1, desplazamiento=1))[0].id.endswith("3")
    assert [o.id[-1] for o in repo.consultar(FiltrosOpinion(evento_id="ev-f1-monaco"))] == ["3"]
    assert [o.id[-1] for o in repo.consultar(FiltrosOpinion(evento_ids=("ev-f1-monaco", "x")))] == ["3"]
    assert repo.consultar(FiltrosOpinion(evento_ids=())) == []
    assert [o.id[-1] for o in repo.consultar(FiltrosOpinion(disciplina_id="formula"))] == ["3"]
    assert [o.id[-1] for o in repo.consultar(FiltrosOpinion(edicion_anio=2025))] == ["3"]
    assert [o.id[-1] for o in repo.consultar(FiltrosOpinion(sentimiento="negativo"))] == ["2"]
    assert [o.id[-1] for o in repo.consultar(FiltrosOpinion(aspecto="clima"))] == ["2"]
    assert [o.id[-1] for o in repo.consultar(FiltrosOpinion(texto="LLUVIA"))] == ["3"]
    assert [o.id[-1] for o in repo.consultar(FiltrosOpinion(desde_utc="2026-11-02T00:00:00+00:00",
                                                          hasta_utc="2026-11-03T00:00:00+00:00"))] == ["3"]
    assert repo.contar(FiltrosOpinion(sentimiento="positivo")) == 2
    assert repo.contar(FiltrosOpinion(texto="lluvia")) == 1


def test_revision_no_cambia_la_etiqueta_del_modelo(repo):
    op = opinion_ejemplo(1, sentimiento="positivo")
    repo.guardar(op)
    repo.guardar_revision(op.id, Revision("negativo", "mod-1", "2026-11-10T00:00:00+00:00", "ironía"))
    guardada = repo.obtener(op.id)
    assert guardada.sentimiento == "positivo"
    assert guardada.sentimiento_efectivo == "negativo"
    assert repo.contar(FiltrosOpinion(sentimiento="negativo")) == 0
    assert repo.contar(FiltrosOpinion(sentimiento="negativo", usar_revision=True)) == 1
    assert repo.contar(FiltrosOpinion(solo_revisadas=True)) == 1
    assert repo.historial_revisiones(op.id)[-1].sentimiento == "negativo"


def test_ocultar_y_anonimizar(repo):
    repo.guardar(opinion_ejemplo(1, usuario_id="u-9"))
    repo.guardar(opinion_ejemplo(2, usuario_id="u-9"))
    repo.cambiar_visibilidad(opinion_ejemplo(1).id, False)
    assert repo.contar(FiltrosOpinion()) == 1
    assert repo.contar(FiltrosOpinion(incluir_ocultas=True)) == 2
    assert repo.anonimizar_usuario("u-9") == 2
    assert repo.contar(FiltrosOpinion(usuario_id="u-9", incluir_ocultas=True)) == 0


def test_historial_completo_en_sql(tmp_path):
    bd = BaseDatos(f"sqlite:///{(tmp_path / 'h.db').as_posix()}")
    bd.crear_esquema()
    repo = SqlRepositorioOpiniones(bd)
    repo.guardar(opinion_ejemplo(1))
    repo.guardar_revision(opinion_ejemplo(1).id, Revision("mixto", "m1", "2026-11-10T00:00:00+00:00"))
    repo.guardar_revision(opinion_ejemplo(1).id, Revision("negativo", "m2", "2026-11-10T01:00:00+00:00"))
    hist = repo.historial_revisiones(opinion_ejemplo(1).id)
    assert [r.sentimiento for r in hist] == ["mixto", "negativo"]
    assert repo.obtener(opinion_ejemplo(1).id).sentimiento_efectivo == "negativo"  # la última manda
