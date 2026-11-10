"""Página «📝 ¿Qué opina la comunidad?»: resumen con LangChain usando SOLO las opiniones guardadas."""

from __future__ import annotations

from datetime import datetime

import streamlit as st

from paddock.aplicacion.resumir_comunidad import MINIMO_OPINIONES, NUEVAS_PARA_REGENERAR
from paddock.dominio.entidades import FiltrosOpinion
from paddock.dominio.errores import ErrorPaddock
from paddock.interfaz.componentes import recursos, sesion
from paddock.interfaz.componentes.mensajes import mostrar_error


def render() -> None:
    st.subheader("📝 ¿Qué opina la comunidad?")
    c = recursos.contenedor()
    if not c.modo_sql:
        st.info("Los resúmenes requieren STORAGE_BACKEND=sql.")
        return
    cat = recursos.catalogo()
    ids = [e.id for e in cat.eventos]
    col1, col2 = st.columns([3, 1])
    ev = col1.selectbox("Carrera", ids, format_func=lambda i: cat.evento(i).etiqueta, key="res_ev")  # type: ignore[union-attr]
    anio = int(col2.number_input("Edición", 0, datetime.now().year, 0, key="res_anio", help="0 = todas")) or None
    n = c.repo_opiniones.contar(FiltrosOpinion(evento_id=ev, edicion_anio=anio))
    previo = c.resumir_comunidad.guardado(ev, anio)
    st.caption(f"{n} opiniones registradas. Mínimo para resumir: {MINIMO_OPINIONES}. El resumen se reutiliza hasta que "
               f"haya {NUEVAS_PARA_REGENERAR} opiniones nuevas.")
    actor = sesion.actor_actual()
    b1, b2 = st.columns(2)
    generar = b1.button("Ver o generar resumen", type="primary", disabled=n < MINIMO_OPINIONES)
    regenerar = b2.button("🔄 Regenerar", disabled=previo is None or actor is None,
                          help="Llama de nuevo al modelo (límite: 2 cada 10 minutos).")
    if previo and not (generar or regenerar):
        st.markdown(previo.texto)
        st.caption(f"Generado con {previo.modelo} a partir de {previo.n_opiniones} opiniones · {previo.fecha_utc[:16]}")
    if generar or regenerar:
        aj = c.ajustes
        try:
            with st.spinner(f"Resumiendo con {aj.modelo_activo}…"):
                r = c.resumir_comunidad.ejecutar(ev, anio, actor, regenerar=regenerar)
        except ErrorPaddock as e:
            mostrar_error(e, aj.LLM_PROVIDER, aj.GEMINI_MODEL if aj.LLM_PROVIDER == "gemini" else aj.OLLAMA_MODEL)
        else:
            st.markdown(r.resumen.texto)
            estado = "reutilizado" if r.reutilizado else "nuevo"
            st.caption(f"Resumen {estado} · {r.resumen.modelo} · {r.resumen.n_opiniones} opiniones")
    st.caption("El resumen usa solo las opiniones guardadas en Paddock Global; no incluye nombres de usuarios ni "
               "datos externos.")


render()
