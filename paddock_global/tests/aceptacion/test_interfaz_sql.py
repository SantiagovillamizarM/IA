"""Interfaz en modo SQL (v2) con AppTest: cuentas, roles, dashboard, comparador y administración."""

from __future__ import annotations

from pathlib import Path

import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

from paddock.adaptadores.persistencia.json_repo import cargar_catalogo, cargar_jerga
from paddock.adaptadores.persistencia.sql_repo import BaseDatos, SqlRepositorioCatalogo, SqlRepositorioOpiniones
from paddock.config import DATOS, Ajustes
from paddock.contenedor import crear_contenedor
from tests.conftest import opinion_ejemplo

APP = str(Path(__file__).resolve().parents[2] / "src" / "paddock" / "interfaz" / "app.py")
CLAVE = "Tres-Palabras-Largas-9"


@pytest.fixture
def app_sql(tmp_path, monkeypatch):
    url = f"sqlite:///{(tmp_path / 'ui.db').as_posix()}"
    for k, v in {"PADDOCK_CLASIFICADOR_PRUEBAS": "falso", "STORAGE_BACKEND": "sql", "DATABASE_URL": url,
                 "PERMITIR_ANONIMOS": "true", "REGISTRO_ABIERTO": "true", "VERSION_PROMPT": "2.0"}.items():
        monkeypatch.setenv(k, v)
    bd = BaseDatos(url)
    bd.crear_esquema()
    SqlRepositorioCatalogo(bd).sembrar(cargar_catalogo(DATOS / "catalogo.json"), cargar_jerga(DATOS / "jerga.json"))
    repo = SqlRepositorioOpiniones(bd)
    for i in range(1, 7):
        repo.guardar(opinion_ejemplo(i, sentimiento=["positivo", "negativo", "mixto"][i % 3],
                                     aspectos=[{"aspecto": "ambiente", "sentimiento": "positivo"}],
                                     entidades=["Porsche"]))
    c = crear_contenedor(Ajustes())
    c.cuentas.registrar("admin@ejemplo.com", "Admin", CLAVE, rol="admin", forzar=True)
    c.cuentas.registrar("ana@ejemplo.com", "Ana", CLAVE)
    st.cache_resource.clear()
    st.cache_data.clear()
    at = AppTest.from_file(APP, default_timeout=60)
    at.run()
    assert not at.exception, at.exception
    yield at, repo
    st.cache_resource.clear()


def ir(at, pagina):
    at.switch_page(f"paginas/{pagina}.py")
    at.run()
    assert not at.exception, at.exception
    return at


def login(at, email, clave=CLAVE):
    ir(at, "cuenta")
    at.text_input[0].set_value(email)
    at.text_input[1].set_value(clave)
    at.button[0].click().run()
    assert not at.exception, at.exception
    return at


def test_anonimo_consulta_pero_no_emite(app_sql):
    at, _ = app_sql
    ir(at, "emitir")
    assert any("Inicia sesión" in i.value for i in at.info)
    assert not at.chat_input
    ir(at, "consultar")
    assert at.metric[0].value == "6"


def test_login_emitir_con_aspectos_y_usuario(app_sql):
    at, repo = app_sql
    login(at, "ana@ejemplo.com")
    assert at.session_state.actor.email == "ana@ejemplo.com"
    ir(at, "emitir")
    at.chat_input[0].set_value("La salida al amanecer es pura magia").run()
    assert not at.exception
    from paddock.dominio.entidades import FiltrosOpinion

    mias = repo.consultar(FiltrosOpinion(usuario_id=at.session_state.actor.usuario_id))
    assert len(mias) == 1 and mias[0].aspectos and mias[0].version_prompt == "2.0"


def test_login_fallido_mensaje_generico_y_bloqueo(app_sql):
    at, _ = app_sql
    for _ in range(5):
        login(at, "ana@ejemplo.com", "contraseña-equivocada")
        assert at.error[0].value == "Correo o contraseña incorrectos."
    login(at, "ana@ejemplo.com", CLAVE)
    assert "Demasiados intentos" in at.error[0].value
    assert "actor" not in at.session_state


def test_aficionado_no_ve_admin_y_acceso_denegado(app_sql):
    at, _ = app_sql
    login(at, "ana@ejemplo.com")
    # La página no está registrada en la navegación de un aficionado
    try:
        at.switch_page("paginas/admin.py").run()
    except Exception:  # noqa: BLE001 - Streamlit rechaza la página no registrada
        return
    # Si Streamlit la ejecutara igualmente, la propia página deniega el acceso y no muestra pestañas
    assert any("Acceso denegado" in e.value for e in at.error) or not at.tabs
    assert not at.tabs


def test_pagina_admin_deniega_sin_rol(app_sql, monkeypatch):
    """Defensa en profundidad: aunque se cargara la página, el rol se comprueba dentro."""
    at, _ = app_sql
    login(at, "ana@ejemplo.com")
    import runpy

    import paddock.interfaz.paginas  # noqa: F401
    errores = []
    monkeypatch.setattr(st, "error", lambda m, *a, **k: errores.append(m))
    monkeypatch.setattr(st, "session_state", {"actor": at.session_state.actor})
    from paddock.interfaz.componentes import sesion

    monkeypatch.setattr(sesion, "actor_actual", lambda: at.session_state.actor)
    runpy.run_path(str(Path(APP).parent / "paginas" / "admin.py"))
    assert errores and "Acceso denegado" in errores[0]


def test_admin_ve_administracion_y_auditoria(app_sql):
    at, _ = app_sql
    login(at, "admin@ejemplo.com")
    ir(at, "admin")
    assert not any("Acceso denegado" in e.value for e in at.error)
    assert len(at.tabs) == 4


def test_dashboard_y_comparar(app_sql):
    at, _ = app_sql
    ir(at, "dashboard")
    assert at.metric[0].value == "6"
    ir(at, "comparar")
    assert not at.exception


def test_cerrar_sesion_limpia_estado(app_sql):
    at, _ = app_sql
    login(at, "ana@ejemplo.com")
    ir(at, "cuenta")
    next(b for b in at.button if "Cerrar sesión" in b.label).click().run()
    assert "actor" not in at.session_state
