"""Base de datos: migraciones de Alembic, catálogo, migración JSON → BD y repositorios auxiliares."""

from __future__ import annotations

import pytest
from alembic import command
from alembic.config import Config
from scripts.migrar_json_a_bd import migrar
from sqlalchemy import inspect

from paddock.adaptadores.persistencia.json_repo import RepositorioOpinionesJson, cargar_catalogo, cargar_jerga
from paddock.adaptadores.persistencia.sql_repo import (
    BaseDatos,
    SqlRepositorioAuditoria,
    SqlRepositorioCatalogo,
    SqlRepositorioLimites,
    SqlRepositorioMetricas,
)
from paddock.config import DATOS, RAIZ
from paddock.dominio.entidades import Evento, MetricaLlamada
from tests.conftest import opinion_ejemplo

pytestmark = pytest.mark.integracion


def url(tmp_path, nombre="p.db"):
    return f"sqlite:///{(tmp_path / nombre).as_posix()}"


def test_alembic_upgrade_crea_todas_las_tablas_y_downgrade(tmp_path):
    cfg = Config(str(RAIZ / "alembic.ini"))
    cfg.attributes["url"] = url(tmp_path)
    command.upgrade(cfg, "head")
    tablas = set(inspect(BaseDatos(url(tmp_path)).engine).get_table_names())
    assert {"disciplinas", "campeonatos", "eventos", "usuarios", "opiniones", "revisiones", "trabajos_lote",
            "resumenes", "auditoria", "limites_uso", "metricas_llm", "tokens_api", "denuncias", "jerga"} <= tablas
    command.downgrade(cfg, "base")
    assert "opiniones" not in set(inspect(BaseDatos(url(tmp_path)).engine).get_table_names())


def test_sembrar_catalogo_idempotente_y_editable(tmp_path):
    bd = BaseDatos(url(tmp_path))
    bd.crear_esquema()
    repo = SqlRepositorioCatalogo(bd)
    cat_json = cargar_catalogo(DATOS / "catalogo.json")
    n1 = repo.sembrar(cat_json, cargar_jerga(DATOS / "jerga.json"))
    assert n1["eventos"] == len(cat_json.eventos)
    assert repo.sembrar(cat_json, {})["eventos"] == 0
    cat = repo.obtener()
    assert [e.id for e in cat.eventos] == [e.id for e in cat_json.eventos]  # mismo orden
    assert cat.evento_por_defecto().id == "ev-f1-monaco"
    repo.guardar_evento(cat.evento("ev-f1-monaco").__class__(**{**cat.evento("ev-f1-monaco").__dict__,
                                                                   "activo": False}))
    assert repo.obtener().evento("ev-f1-monaco").activo is False
    repo.sembrar(cat_json, {})  # sembrar de nuevo no deshace la edición del admin
    assert repo.obtener().evento("ev-f1-monaco").activo is False
    repo.guardar_evento(Evento("ev-nuevo-test", "f1", "GP de Prueba", "Colombia", "Bogotá", 4.6, -74.1))
    assert repo.obtener().evento("ev-nuevo-test").nombre == "GP de Prueba"
    repo.guardar_jerga("rally", ["tramo", " ", "recce"])
    assert repo.obtener_jerga()["rally"] == ["tramo", "recce"]


def test_migrar_json_a_bd_dos_veces_sin_duplicar(tmp_path):
    ruta = tmp_path / "opiniones.json"
    rj = RepositorioOpinionesJson(ruta)
    for i in range(1, 6):
        rj.guardar(opinion_ejemplo(i))
    bd = BaseDatos(url(tmp_path))
    bd.crear_esquema()
    assert migrar(ruta, url(tmp_path)) == (5, 0)
    assert migrar(ruta, url(tmp_path)) == (0, 5)


def test_auditoria_limites_y_metricas(tmp_path):
    bd = BaseDatos(url(tmp_path))
    bd.crear_esquema()
    a = SqlRepositorioAuditoria(bd)
    a.registrar(fecha_utc="2026-11-10T00:00:00+00:00", usuario_id="u", accion="login", detalle={"x": 1}, ip_hash="h")
    a.registrar(fecha_utc="2026-11-10T00:01:00+00:00", usuario_id=None, accion="logout")
    assert [r["accion"] for r in a.consultar()] == ["logout", "login"]
    assert a.consultar(accion="login")[0]["detalle"] == {"x": 1}
    lim = SqlRepositorioLimites(bd)
    for m in range(3):
        lim.registrar("op:u", f"2026-11-10T00:0{m}:00+00:00")
    assert lim.contar_desde("op:u", "2026-11-10T00:01:00+00:00") == 2
    lim.purgar_antes("2026-11-10T00:02:00+00:00")
    assert lim.contar_desde("op:u", "2000-01-01T00:00:00+00:00") == 1
    met = SqlRepositorioMetricas(bd)
    met.registrar(MetricaLlamada("2026-11-10T00:00:00+00:00", "ollama", "qwen2.5:3b", "2.0", 4200, True))
    assert met.listar()[0].latencia_ms == 4200


def test_configurar_streamlit_con_dominio(tmp_path):
    import tomllib

    from scripts.configurar_streamlit import configurar

    ruta = tmp_path / "config.toml"
    ruta.write_text((RAIZ / "despliegue" / ".streamlit" / "config.toml").read_text(encoding="utf-8"), encoding="utf-8")
    assert configurar(ruta, "paddock.midominio.com") is True
    assert configurar(ruta, "paddock.midominio.com") is False  # idempotente
    srv = tomllib.loads(ruta.read_text(encoding="utf-8"))["server"]
    assert srv["allowedHosts"][0] == "paddock.midominio.com"
    assert srv["corsAllowedOrigins"] == ["https://paddock.midominio.com"]
    assert srv["enableCORS"] is True and srv["enableXsrfProtection"] is True
    with pytest.raises(ValueError):
        configurar(ruta, 'mal"dominio')
