"""Página «🗣️ Emitir opinión».

El historial vive en ``st.session_state.historial`` (lista de diccionarios, no ``HumanMessage``)
y se pierde al cerrar la pestaña. La persistencia es ``opiniones.json`` o la base de datos.
El historial **nunca** se pasa al clasificador.
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

import streamlit as st

from paddock.aplicacion.emitir_opinion import SolicitudOpinion
from paddock.interfaz.componentes import recursos, sesion
from paddock.interfaz.componentes.barra_lateral import Seleccion
from paddock.interfaz.componentes.mensajes import mostrar, mostrar_error
from paddock.interfaz.componentes.tarjetas import chip_evento, tarjeta_resultado


def _historial() -> list[dict[str, Any]]:
    if "historial" not in st.session_state:
        st.session_state.historial = []
    return st.session_state.historial


def _pintar_historial(historial: list[dict[str, Any]]) -> None:
    for item in historial:
        if item["rol"] == "usuario":
            with st.chat_message("user"):
                chip_evento(item.get("icono", "🏁"), item["evento_nombre"], item.get("edicion_anio"))
                st.text(item["texto"])  # texto plano: nada se interpreta como HTML
                if item["estado"] == "no_guardada":
                    st.caption("⚠️ no guardada")
        else:
            with st.chat_message("assistant", avatar="🏁"):
                if item["estado"] == "guardada":
                    tarjeta_resultado(item["analisis"], item["modelo"], "✅ Opinión guardada")
                elif item["estado"] == "no_pertinente":
                    st.info(f"No se guardó: el texto no es una opinión sobre {item['evento_nombre']}.")
                    st.caption(f"Motivo del modelo: {item['analisis'].get('razon', '')}")
                else:
                    mostrar(item.get("nivel", "error"), item.get("error", "⚠️ Error."))
                    st.caption("⚠️ No se guardó nada.")


def _procesar(pendiente: dict[str, Any], historial: list[dict[str, Any]]) -> None:
    c = recursos.contenedor()
    aj = c.ajustes
    proveedor = aj.LLM_PROVIDER
    nombre_modelo = aj.GEMINI_MODEL if proveedor == "gemini" else aj.OLLAMA_MODEL
    entrada_usuario = next(h for h in historial if h.get("registro_id") == pendiente["registro_id"]
                           and h["rol"] == "usuario")
    respuesta: dict[str, Any] = {"rol": "asistente", "registro_id": pendiente["registro_id"],
                                 "evento_nombre": pendiente["evento_nombre"], "modelo": aj.modelo_activo,
                                 "evento_id": pendiente["evento_id"], "edicion_anio": pendiente["edicion_anio"],
                                 "texto": "", "analisis": {}}
    with st.chat_message("assistant", avatar="🏁"):
        aviso = f"Analizando con {aj.modelo_activo}…"
        if proveedor == "ollama":
            aviso += " (la primera vez puede tardar ~1 min mientras se carga el modelo)"
        try:
            with st.spinner(aviso):
                res = c.emitir_opinion.ejecutar(
                    SolicitudOpinion(texto=pendiente["texto"], evento_id=pendiente["evento_id"],
                                     registro_id=pendiente["registro_id"], edicion_anio=pendiente["edicion_anio"],
                                     origen="chat"),
                    actor=sesion.actor_actual(), sujeto_limite=sesion.id_navegador(),
                )
            respuesta["analisis"] = res.analisis.model_dump()
            respuesta["modelo"] = res.modelo
            if res.estado == "no_pertinente":
                respuesta["estado"] = entrada_usuario["estado"] = "no_pertinente"
            else:  # «guardada» o «duplicada» (reintento del mismo envío: ya estaba guardada)
                respuesta["estado"] = entrada_usuario["estado"] = "guardada"
                recursos.invalidar_datos()
        except Exception as e:  # noqa: BLE001 - cada tipo tiene su mensaje
            nivel, mensaje = mostrar_error(e, proveedor, nombre_modelo)
            respuesta["estado"] = "error"
            respuesta["nivel"], respuesta["error"] = nivel, mensaje
            entrada_usuario["estado"] = "no_guardada"
    historial.append(respuesta)
    entrada_usuario["analisis"] = respuesta["analisis"]


def render() -> None:
    sel: Seleccion = st.session_state.seleccion
    st.subheader("🗣️ Emitir opinión")
    st.caption(f"Opinas sobre **{sel.evento.nombre}**"
               + (f" · edición {sel.edicion_anio}" if sel.edicion_anio else "")
               + ". Cambia la carrera en la barra lateral.")
    if not sesion.puede_emitir():
        st.info("🔐 Inicia sesión en «Mi cuenta» para emitir opiniones.")
        return

    historial = _historial()
    _pintar_historial(historial)

    texto = st.chat_input("Escribe tu opinión sobre la carrera seleccionada…", max_chars=1000)
    if texto is not None:
        # Se captura una copia del evento y la edición EN ESTE INSTANTE, y un id único por envío.
        pendiente = {
            "texto": texto, "evento_id": sel.evento.id, "evento_nombre": sel.evento.nombre,
            "edicion_anio": sel.edicion_anio, "registro_id": str(uuid4()), "icono": sel.disciplina.icono,
        }
        st.session_state.pendiente = pendiente
        entrada = {"rol": "usuario", "texto": texto, "evento_id": sel.evento.id,
                   "evento_nombre": sel.evento.nombre, "edicion_anio": sel.edicion_anio,
                   "registro_id": pendiente["registro_id"], "estado": "pendiente", "analisis": None,
                   "icono": sel.disciplina.icono}
        historial.append(entrada)
        with st.chat_message("user"):
            chip_evento(sel.disciplina.icono, sel.evento.nombre, sel.edicion_anio)
            st.text(texto)

    pendiente = st.session_state.get("pendiente")
    if pendiente:
        # Si un rerun interrumpe el proceso, se reintenta con el MISMO registro_id: guardar es idempotente.
        _procesar(pendiente, historial)
        st.session_state.pop("pendiente", None)
        st.rerun()


render()
