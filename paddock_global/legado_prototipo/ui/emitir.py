"""Sección «Emitir opinión»: chat que clasifica y guarda cada opinión."""

from __future__ import annotations

import uuid

import streamlit as st

import almacenamiento as alm
from analisis import (
    VERSION_PROMPT,
    EntradaInvalidaError,
    ErrorClasificacion,
    ModeloNoEncontradoError,
    RespuestaInvalidaError,
    ServicioNoDisponibleError,
    alerta_revision,
    analizar_opinion,
    validar_texto,
)
from config import RUTA_OPINIONES, ConfigOllama
from ui.comun import EMOJI, NOMBRE_IDIOMA, cadena_de, texto_aspectos


def _mostrar(m: dict) -> None:
    if m["rol"] == "user":
        with st.chat_message("user"):
            st.caption(f"🏁 {m['carrera_nombre']}" + (f" · {m['modelo']}" if m.get("modelo") else ""))
            st.markdown(m["texto"])
            if m.get("estado") == "no_guardada":
                st.caption("⚠️ no guardada")
    else:
        with st.chat_message("assistant"):
            st.markdown(m["texto"])


def _procesar(entrada: dict, carrera: dict, cfg: ConfigOllama) -> dict:
    """Valida, clasifica y guarda. Devuelve el mensaje del asistente."""
    def fallo(texto: str) -> dict:
        entrada["estado"] = "no_guardada"
        return {"rol": "assistant", "texto": texto}

    try:
        texto = validar_texto(entrada["texto"])
    except EntradaInvalidaError as e:
        return fallo(f"✋ **Entrada no válida:** {e}")

    try:
        analisis = analizar_opinion(carrera, texto, cfg=cfg, cadena=cadena_de(cfg))
    except ServicioNoDisponibleError as e:
        return fallo(f"🔴 **{'Ollama' if cfg.es_local else 'Gemini'} no disponible.** {e}")
    except ModeloNoEncontradoError as e:
        return fallo(f"🔴 **Modelo no encontrado.** {e}")
    except RespuestaInvalidaError as e:
        return fallo(f"⚠️ **El modelo devolvió una respuesta no válida** (2 intentos). {e}")
    except ErrorClasificacion as e:
        return fallo(f"⚠️ **No se pudo clasificar.** {e}")

    if not analisis.es_pertinente:
        entrada["estado"] = "no_pertinente"
        return {"rol": "assistant",
                "texto": f"🚫 **No se guardó:** el texto no es una opinión sobre {carrera['nombre']}.\n\n"
                         f"_{analisis.razon}_"}

    lineas = [f"{EMOJI[analisis.sentimiento]} **{analisis.sentimiento.capitalize()}** — {analisis.razon}"]
    detalles = []
    if analisis.aspectos:
        detalles.append(f"**Aspectos:** {texto_aspectos([a.model_dump() for a in analisis.aspectos])}")
    detalles.append(f"**Idioma:** {NOMBRE_IDIOMA.get(analisis.idioma, analisis.idioma)}")
    lineas.append("  \n".join(detalles))
    alerta = alerta_revision(analisis)
    if alerta:
        lineas.append(f"🔎 _Revisión sugerida: {alerta} Puedes corregirla en «Consultar opiniones»._")
    resumen = "\n\n".join(lineas)

    try:
        registro = alm.crear_registro(carrera, texto, analisis, cfg.nombre_modelo, VERSION_PROMPT,
                                      registro_id=entrada["registro_id"],
                                      temperatura=cfg.OLLAMA_TEMPERATURE)
        alm.guardar_opinion(RUTA_OPINIONES, registro)
    except (alm.ArchivoOpinionesCorruptoError, alm.ErrorEscrituraOpiniones) as e:
        return fallo(f"{resumen}\n\n❌ **No se guardó:** {e}")

    entrada["estado"] = "guardada"
    return {"rol": "assistant", "texto": f"{resumen}\n\n✅ Opinión guardada."}


def render(carrera_sel: dict, cfg: ConfigOllama) -> None:
    st.subheader(f"Opinando sobre: {carrera_sel['nombre']}")
    if not st.session_state.historial:
        st.info("Escribe tu opinión sobre la carrera seleccionada, en el idioma que quieras. "
                "La primera clasificación puede tardar ~1 minuto mientras Ollama carga el modelo.")
    for m in st.session_state.historial:
        _mostrar(m)

    texto = st.chat_input("Escribe tu opinión sobre la carrera seleccionada…")
    if texto is None:
        return
    carrera = dict(carrera_sel)  # la selección queda fija en este envío
    entrada = {
        "rol": "user", "texto": texto,
        "carrera_id": carrera["id"], "carrera_nombre": carrera["nombre"],
        "registro_id": str(uuid.uuid4()),  # una vez por envío → idempotencia
        "estado": "pendiente",
        "modelo": f"{cfg.OLLAMA_MODEL} · T={cfg.OLLAMA_TEMPERATURE:.1f}",
    }
    st.session_state.historial.append(entrada)
    _mostrar(entrada)
    with st.chat_message("assistant"):
        espera = " (la primera vez puede tardar ~1 min)" if cfg.es_local else ""
        with st.spinner(f"Analizando con {cfg.OLLAMA_MODEL} · temperatura {cfg.OLLAMA_TEMPERATURE:.1f}…{espera}"):
            respuesta = _procesar(entrada, carrera, cfg)
    st.session_state.historial.append(respuesta)
    st.rerun()
