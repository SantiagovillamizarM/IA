"""Página «🔎 Consultar opiniones». **Jamás** llama al modelo; cambiar filtros no guarda nada."""

from __future__ import annotations

import json

import streamlit as st

from paddock.dominio.enums import SENTIMIENTOS
from paddock.dominio.errores import ErrorPaddock
from paddock.interfaz.componentes import recursos, sesion
from paddock.interfaz.componentes.filtros import csv_con_bom, filtros_ui, tabla
from paddock.interfaz.componentes.tarjetas import aviso_cifras, etiqueta_sentimiento


def render() -> None:
    st.subheader("🔎 Consultar opiniones")
    c = recursos.contenedor()
    filtros = filtros_ui()
    extra = st.columns([1.4, 1.2, 2])
    with extra[0]:
        texto = st.text_input("Buscar en el texto", key="f_texto", placeholder="p. ej. lluvia")
    usar_revision = False
    with extra[1]:
        if c.modo_sql:
            etiqueta = st.radio("Etiqueta", ["Del modelo", "Revisada"], horizontal=True, key="f_etiqueta",
                                help="«Revisada» usa la corrección humana cuando existe.")
            usar_revision = etiqueta == "Revisada"
    filtros = filtros.con(texto=texto or None, usar_revision=usar_revision)

    try:
        res = c.consultar_opiniones.ejecutar(filtros, actor=sesion.actor_actual())
    except ErrorPaddock as e:
        st.error(f"🗂️ {e}")
        st.caption("El archivo no se modificó. Repáralo o restaura una copia y recarga la página.")
        return

    # Recuentos sobre los MISMOS registros filtrados que la tabla
    cols = st.columns(5)
    cols[0].metric("Total", res.total)
    for col, s in zip(cols[1:], SENTIMIENTOS, strict=True):
        col.metric(etiqueta_sentimiento(s), res.por_sentimiento[s])

    if not res.registros:
        st.info("No hay opiniones con esos filtros.")
        return

    st.dataframe(tabla(res.registros, c.ajustes.ZONA_HORARIA, usar_revision), use_container_width=True,
                 hide_index=True)
    datos = {"version": 1, "filtros": {k: v for k, v in filtros.__dict__.items() if v not in (None, False, 0)},
             "opiniones": [o.a_dict() for o in res.registros]}
    d1, d2, _ = st.columns([1, 1, 3])
    d1.download_button("⬇️ Descargar JSON", json.dumps(datos, ensure_ascii=False, indent=2).encode("utf-8"),
                       file_name="opiniones_filtradas.json", mime="application/json")
    d2.download_button("⬇️ Descargar CSV", csv_con_bom(res.registros), file_name="opiniones_filtradas.csv",
                       mime="text/csv")
    _denunciar(res.registros)
    aviso_cifras()


def _denunciar(registros) -> None:  # type: ignore[no-untyped-def]
    """v3: un usuario con sesión puede denunciar una opinión (spam, ofensiva o mal clasificada)."""
    c = recursos.contenedor()
    actor = sesion.actor_actual()
    if not c.modo_sql or actor is None or not registros:
        return
    from paddock.dominio.enums import MotivoDenuncia

    with st.expander("🚩 Denunciar una opinión"):
        por_id = {o.id: o for o in registros}
        oid = st.selectbox("Opinión", list(por_id), format_func=lambda i: por_id[i].opinion_original[:90])
        motivo = st.radio("Motivo", [m.value for m in MotivoDenuncia], horizontal=True,
                          format_func=lambda m: {"spam": "Spam", "ofensiva": "Ofensiva",
                                                 "mal_clasificada": "Mal clasificada"}[m])
        if st.button("Enviar denuncia"):
            try:
                c.moderacion.denunciar(actor, oid, motivo)
                st.success("Gracias. Un moderador la revisará.")
            except ErrorPaddock as e:
                st.error(str(e))


render()
