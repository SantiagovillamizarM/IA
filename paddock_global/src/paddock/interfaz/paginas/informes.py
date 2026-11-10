"""Página «📄 Informes»: PDF por carrera (y edición) con fpdf2."""

from __future__ import annotations

from datetime import datetime

import streamlit as st

from paddock.dominio.errores import ErrorPaddock
from paddock.interfaz.componentes import recursos, sesion


def render() -> None:
    st.subheader("📄 Informes PDF")
    c = recursos.contenedor()
    cat = recursos.catalogo()
    ids = [e.id for e in cat.eventos]
    col1, col2 = st.columns([3, 1])
    ev = col1.selectbox("Carrera", ids, format_func=lambda i: cat.evento(i).etiqueta, key="inf_ev")  # type: ignore[union-attr]
    anio = int(col2.number_input("Edición", 0, datetime.now().year, 0, key="inf_anio", help="0 = todas")) or None
    st.caption("Incluye portada, aviso de selección didáctica, indicadores, distribución por sentimiento, aspectos, "
               "resumen de comunidad (si existe) y una muestra de opiniones por categoría.")
    if st.button("Generar PDF", type="primary"):
        try:
            with st.spinner("Generando…"):
                pdf = c.informes.pdf(ev, anio, sesion.actor_actual())
        except ErrorPaddock as e:
            st.error(str(e))
        else:
            nombre = f"paddock_{ev}{'_' + str(anio) if anio else ''}.pdf"
            st.download_button("⬇️ Descargar informe", pdf, file_name=nombre, mime="application/pdf")


render()
