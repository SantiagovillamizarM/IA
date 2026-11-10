"""Paddock Global — Análisis de sentimientos LangChain (interfaz Streamlit).

Adaptación de streamlit_chatbot2.py del curso: sin selector de personalidad,
modelo ni temperatura; el clasificador usa solo la opinión actual (sin historial),
se usa invoke (no stream) y el resultado es un objeto Pydantic.

Este archivo solo arma la barra lateral y enruta a las secciones de ui/.
"""

from __future__ import annotations

import streamlit as st

import almacenamiento as alm
from analisis import VERSION_PROMPT, verificar_modelo
from config import (
    MODELOS_DISPONIBLES, RUTA_CARRERAS, cargar_config, config_con_modelo,
    etiqueta_modelo, hay_clave_google,
)
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
st.caption("Opiniones sobre carreras de resistencia · modelos locales con Ollama o Gemini en la nube")

cfg_base = cargar_config()


@st.cache_data(ttl=30, show_spinner=False)
def estado_modelo(clave: str) -> tuple[bool, str]:
    return verificar_modelo(config_con_modelo(cfg_base, clave))


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

    # ----------------------------------------------------- switch de IAs
    st.divider()
    st.subheader("🤖 Inteligencia artificial")
    claves = [m["clave"] for m in MODELOS_DISPONIBLES]
    if cfg_base.clave not in claves:
        claves.insert(0, cfg_base.clave)
    clave_ia = st.selectbox(
        "Modelo", claves, index=claves.index(cfg_base.clave), format_func=etiqueta_modelo, key="ia_modelo",
        help="Los modelos locales corren en tu PC con Ollama. Gemini corre en la nube de Google: "
             "las opiniones se envían a Google para clasificarlas.",
    )
    if clave_ia.startswith("gemini:") and not hay_clave_google():
        st.error("Falta GOOGLE_API_KEY en el archivo .env para usar Gemini.")

    temperatura = st.slider(
        "🌡️ Temperatura", 0.0, 1.0, float(cfg_base.OLLAMA_TEMPERATURE), 0.1, key="ia_temperatura",
        help="0 = respuestas más estables y repetibles (recomendado para clasificar). "
             "Valores altos = más variación entre una ejecución y otra.",
    )
    if temperatura > 0:
        st.caption("⚠️ Con temperatura mayor que 0, la misma opinión puede recibir etiquetas distintas "
                   "si la envías varias veces. Cada registro guarda el modelo y la temperatura usados.")

    cfg = config_con_modelo(cfg_base, clave_ia, temperatura=temperatura)
    ok, mensaje = estado_modelo(cfg.clave)
    (st.success if ok else st.error)(("🟢 " if ok else "🔴 ") + mensaje)
    st.caption(f"`{cfg.nombre_modelo}` · temperatura {cfg.OLLAMA_TEMPERATURE:.1f} · prompt v{VERSION_PROMPT}"
               + ("" if cfg.es_local else " · ☁️ envía datos a Google"))

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
