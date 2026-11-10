"""Paddock Global — Análisis de sentimientos LangChain (interfaz Streamlit).

Adaptación de streamlit_chatbot2.py del curso: sin selector de personalidad,
modelo ni temperatura; el clasificador usa solo la opinión actual (sin historial),
se usa invoke (no stream) y el resultado es un objeto Pydantic.

Este archivo solo arma la barra lateral y enruta a las secciones de ui/.
"""

from __future__ import annotations

import streamlit as st

import almacenamiento as alm
from analisis import VERSION_PROMPT, verificar_ollama
from config import RUTA_CARRERAS, cargar_config, config_con_modelo
from ui import carga, comparar, consultar, emitir, estadisticas

SECCIONES = {
    "🗣️ Emitir opinión": "emitir",
    "🔎 Consultar opiniones": "consultar",
    "📊 Estadísticas": "estadisticas",
    "📁 Carga masiva": "carga",
    "⚖️ Comparar modelos": "comparar",
}

st.set_page_config(page_title="Paddock Global", page_icon="🏁", layout="wide")
st.title("🏁 Paddock Global — Análisis de sentimientos LangChain")
st.caption("Opiniones sobre carreras de resistencia · modelo local con Ollama")

cfg = cargar_config()


@st.cache_data(ttl=30, show_spinner=False)
def estado_ollama(base_url: str, modelo: str) -> tuple[bool, str]:
    return verificar_ollama(config_con_modelo(cfg, modelo))


try:
    carreras = alm.cargar_carreras(RUTA_CARRERAS)
except alm.CatalogoInvalidoError as e:
    st.error(f"No se pudo cargar el catálogo: {e}")
    st.stop()
carreras_por_id = {c["id"]: c for c in carreras}

if "historial" not in st.session_state:
    st.session_state.historial = []

with st.sidebar:
    st.header("🏎️ Carrera")
    carrera_id = st.selectbox(
        "Selecciona la carrera",
        options=list(carreras_por_id),
        format_func=lambda cid: f"{carreras_por_id[cid]['nombre']} — {carreras_por_id[cid]['pais']}",
        index=0,
    )
    carrera_sel = carreras_por_id[carrera_id]
    st.markdown(f"**País:** {carrera_sel['pais']}  \n**Circuito:** {carrera_sel['circuito']}")

    st.divider()
    seccion = SECCIONES[st.radio("Sección", list(SECCIONES))]

    st.divider()
    st.subheader("Modelo")
    ok, mensaje = estado_ollama(cfg.OLLAMA_BASE_URL, cfg.OLLAMA_MODEL)
    (st.success if ok else st.error)(("🟢 " if ok else "🔴 ") + mensaje)
    st.caption(f"`{cfg.nombre_modelo}` · temperatura {cfg.OLLAMA_TEMPERATURE} · prompt v{VERSION_PROMPT}")
    if seccion == "comparar":
        ok_b, msg_b = estado_ollama(cfg.OLLAMA_BASE_URL, cfg.OLLAMA_MODEL_COMPARACION)
        (st.success if ok_b else st.error)(("🟢 " if ok_b else "🔴 ") + msg_b)

    st.divider()
    if st.button("🗑️ Nueva conversación", width="stretch"):
        st.session_state.historial = []  # solo el chat; opiniones.json no se toca
        st.rerun()

if seccion == "emitir":
    emitir.render(carrera_sel, cfg)
elif seccion == "consultar":
    consultar.render(carreras_por_id)
elif seccion == "estadisticas":
    estadisticas.render()
elif seccion == "carga":
    carga.render(carreras, cfg)
else:
    comparar.render(carrera_sel, cfg)
