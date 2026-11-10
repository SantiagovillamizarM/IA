"""Casos de interfaz del taller con ``streamlit.testing.v1.AppTest`` (sin navegador ni LLM real)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

from paddock.adaptadores.persistencia.json_repo import cargar_opiniones

APP = str(Path(__file__).resolve().parents[2] / "src" / "paddock" / "interfaz" / "app.py")


@pytest.fixture
def app(tmp_path, monkeypatch):
    ruta = tmp_path / "opiniones.json"
    monkeypatch.setenv("PADDOCK_CLASIFICADOR_PRUEBAS", "falso")
    monkeypatch.setenv("OPINIONES_JSON", str(ruta))
    monkeypatch.setenv("STORAGE_BACKEND", "json")
    monkeypatch.setenv("VERSION_PROMPT", "1.0")
    st.cache_resource.clear()
    st.cache_data.clear()
    at = AppTest.from_file(APP, default_timeout=60)
    at.run()
    assert not at.exception
    yield at, ruta
    st.cache_resource.clear()


def ir(at: AppTest, pagina: str) -> AppTest:
    at.switch_page(f"paginas/{pagina}.py")
    at.run()
    assert not at.exception, at.exception
    return at


def elegir_evento(at: AppTest, disciplina: str, campeonato: str, evento: str) -> None:
    at.sidebar.selectbox(key="sel_disciplina").select(disciplina).run()
    at.sidebar.selectbox(key="sel_campeonato").select(campeonato).run()
    at.sidebar.selectbox(key="sel_evento").select(evento).run()


def enviar(at: AppTest, texto: str) -> AppTest:
    at.chat_input[0].set_value(texto).run()
    assert not at.exception, at.exception
    return at


def test_portada_titulo_y_selector_por_defecto(app):
    at, _ = app
    assert at.title[0].value == "🏁 Paddock Global"
    assert at.sidebar.selectbox(key="sel_evento").value == "ev-f1-monaco"
    etiquetas = [s.label for s in at.sidebar.selectbox]
    assert etiquetas == ["Disciplina", "Campeonato", "Carrera", "Edición (año)"]
    # Sin selectores de personalidad, modelo ni temperatura
    assert not any(x in " ".join(etiquetas).lower() for x in ("personalidad", "temperatura", "modelo"))


def test_entrada_vacia_y_corta_no_guardan(app):
    at, ruta = app
    ir(at, "emitir")
    enviar(at, "     ")
    enviar(at, "top")
    assert any("al menos 5" in w.value for w in at.warning)
    assert [h["estado"] for h in at.session_state.historial if h["rol"] == "usuario"] == ["no_guardada"] * 2
    assert not ruta.exists()


def test_guardar_confirmacion_y_persistencia_tras_reinicio(app):
    at, ruta = app
    ir(at, "emitir")
    elegir_evento(at, "resistencia", "resistencia_varias", "ev-res-lemans")
    enviar(at, "La salida al amanecer es pura magia")
    datos = cargar_opiniones(ruta)["opiniones"]
    assert len(datos) == 1 and datos[0]["evento_id"] == "ev-res-lemans"
    assert any("Opinión guardada" in m.value for m in at.markdown)
    # «Reinicio»: nueva instancia de la app con la caché vacía
    st.cache_resource.clear()
    at2 = AppTest.from_file(APP, default_timeout=60)
    at2.run()
    ir(at2, "consultar")
    assert at2.metric[0].value == "1"
    assert "pura magia" in at2.dataframe[0].value.to_string()


def test_cambio_de_carrera_y_dos_opiniones(app):
    at, ruta = app
    ir(at, "emitir")
    elegir_evento(at, "resistencia", "resistencia_varias", "ev-res-lemans")
    enviar(at, "La salida al amanecer es pura magia")
    enviar(at, "Otra noche increíble en la Sarthe")
    elegir_evento(at, "formula", "f1", "ev-f1-monaco")
    enviar(at, "Mónaco es precioso de ver")
    datos = cargar_opiniones(ruta)["opiniones"]
    assert [d["evento_id"] for d in datos] == ["ev-res-lemans", "ev-res-lemans", "ev-f1-monaco"]


def test_no_pertinente_no_se_guarda(app):
    at, ruta = app
    ir(at, "emitir")
    enviar(at, "La capital de Francia es París")
    assert any("No se guardó" in i.value for i in at.info)
    assert not ruta.exists()


def test_nueva_conversacion_vacia_chat_y_conserva_archivo(app):
    at, ruta = app
    ir(at, "emitir")
    enviar(at, "La salida al amanecer es pura magia")
    antes = ruta.read_bytes()
    assert at.session_state.historial
    at.sidebar.button[0].click().run()
    assert at.session_state.historial == []
    assert ruta.read_bytes() == antes


def test_archivo_danado_se_muestra_y_se_conserva(app):
    at, ruta = app
    ruta.write_text("{roto", encoding="utf-8")
    ir(at, "consultar")
    assert at.error and "no es un JSON válido" in at.error[0].value
    ir(at, "emitir")
    enviar(at, "La salida al amanecer es pura magia")
    assert ruta.read_text(encoding="utf-8") == "{roto"
    assert at.session_state.historial[0]["estado"] == "no_guardada"


def test_xss_se_muestra_como_texto(app):
    at, ruta = app
    ir(at, "emitir")
    enviar(at, "<script>alert(1)</script> gran carrera, espectacular")
    assert cargar_opiniones(ruta)["opiniones"][0]["opinion_original"].startswith("<script>")
    # El texto del usuario se pinta con st.text (nunca como HTML) y en las tarjetas va escapado
    assert any(t.value.startswith("<script>") for t in at.text)
    assert not any("<script>" in m.value for m in at.markdown)


def test_consulta_filtros_recuentos_y_reejecucion_sin_duplicar(app):
    at, ruta = app
    ir(at, "emitir")
    elegir_evento(at, "resistencia", "resistencia_varias", "ev-res-lemans")
    enviar(at, "La salida al amanecer es pura magia")
    enviar(at, "Fue aburrido y decepcionante")
    ir(at, "consultar")
    assert [m.value for m in at.metric] == ["2", "1", "1", "0", "0"]
    at.selectbox(key="f_sent").select("negativo").run()
    assert [m.value for m in at.metric] == ["1", "0", "1", "0", "0"]
    assert len(at.dataframe[0].value) == 1
    at.selectbox(key="f_sent").select("mixto").run()
    assert any("No hay opiniones" in i.value for i in at.info)
    assert len(cargar_opiniones(ruta)["opiniones"]) == 2  # cambiar filtros no duplica
    json.loads(ruta.read_text(encoding="utf-8"))


@pytest.mark.parametrize(("error", "nivel", "fragmento"), [
    ("ProveedorNoDisponibleError", "error", "ollama serve"),
    ("ModeloNoEncontradoError", "error", "ollama pull qwen2.5:3b"),
    ("CredencialInvalidaError", "error", "GOOGLE_API_KEY"),
    ("CuotaExcedidaError", "error", "429"),
    ("ContenidoBloqueadoError", "error", "filtros de seguridad"),
    ("RespuestaInvalidaError", "error", "inválida"),
    ("EntradaInvalidaError", "warning", "✋"),
    ("ArchivoOpinionesCorruptoError", "error", "🗂️"),
    ("ErrorEscrituraOpiniones", "error", "💾"),
    ("LimiteExcedidoError", "warning", "⏳"),
])
def test_un_mensaje_distinto_por_error(error, nivel, fragmento):
    from paddock.dominio import errores as err
    from paddock.interfaz.componentes.mensajes import describir_error

    n, m = describir_error(getattr(err, error)("detalle"), "ollama", "qwen2.5:3b")
    assert n == nivel and fragmento in m


def test_mensaje_gemini_caido_y_modelo():
    from paddock.dominio import errores as err
    from paddock.interfaz.componentes.mensajes import describir_error

    assert "Gemini no responde" in describir_error(err.ProveedorNoDisponibleError(), "gemini", "g")[1]
    assert "GEMINI_MODEL" in describir_error(err.ModeloNoEncontradoError(), "gemini", "g")[1]
