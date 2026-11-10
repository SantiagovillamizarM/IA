"""Página «⚖️ Comparar»: dos carreras (o dos ediciones de la misma) lado a lado."""

from __future__ import annotations

from datetime import datetime

import streamlit as st

from paddock.aplicacion.obtener_estadisticas import calcular
from paddock.dominio.entidades import FiltrosOpinion
from paddock.dominio.enums import SENTIMIENTOS
from paddock.interfaz.componentes import graficos, recursos, sesion
from paddock.interfaz.componentes.tarjetas import aviso_cifras, chips_aspectos, etiqueta_sentimiento


@st.cache_data(ttl=300, show_spinner=False)
def _registros(evento_id: str, edicion: int | None):  # type: ignore[no-untyped-def]
    c = recursos.contenedor()
    return c.repo_opiniones.consultar(FiltrosOpinion(evento_id=evento_id, edicion_anio=edicion))


def _selector(lado: str, defecto: str):  # type: ignore[no-untyped-def]
    cat = recursos.catalogo()
    ids = [e.id for e in cat.eventos]
    ev = st.selectbox(f"Carrera {lado}", ids, index=ids.index(defecto) if defecto in ids else 0, key=f"cmp_ev_{lado}",
                      format_func=lambda i: cat.evento(i).etiqueta)  # type: ignore[union-attr]
    anio = st.number_input(f"Edición {lado}", 0, datetime.now().year, 0, key=f"cmp_an_{lado}",
                           help="0 = todas las ediciones")
    return ev, int(anio) or None


def _columna(evento_id: str, edicion: int | None) -> None:
    cat = recursos.catalogo()
    regs = _registros(evento_id, edicion)
    e = calcular(regs)
    nombre = cat.evento(evento_id).nombre  # type: ignore[union-attr]
    st.markdown(f"### {nombre}" + (f" · {edicion}" if edicion else ""))
    st.metric("Opiniones", e.total, help="Índice de percepción: " + (f"{e.indice:+.2f}" if e.indice is not None else "—"))
    if not regs:
        st.info("Sin opiniones registradas.")
        return
    st.plotly_chart(graficos.barras_distribucion(e.conteo), use_container_width=True, key=f"dist_{evento_id}_{edicion}")
    aspectos = [{"aspecto": a, "sentimiento": s} for a, c in e.aspectos.items() for s, n in c.items() if n]
    if aspectos:
        st.markdown("**Aspectos mencionados**")
        st.markdown(chips_aspectos(aspectos), unsafe_allow_html=True)
    st.markdown("**Ejemplos por categoría**")
    for s in SENTIMIENTOS:
        ej = next((o for o in regs if o.sentimiento == s), None)
        if ej:
            st.caption(etiqueta_sentimiento(s))
            st.text(ej.opinion_original)


def render() -> None:
    st.subheader("⚖️ Comparar carreras")
    if sesion.actor_actual() is None and not recursos.contenedor().consultar_opiniones.permitir_anonimos:
        st.info("🔐 Inicia sesión en «Mi cuenta» para comparar.")
        return
    a, b = st.columns(2)
    with a:
        ev_a, ed_a = _selector("A", "ev-res-lemans")
    with b:
        ev_b, ed_b = _selector("B", "ev-f1-monaco")
    a, b = st.columns(2)
    with a:
        _columna(ev_a, ed_a)
    with b:
        _columna(ev_b, ed_b)
    aviso_cifras()


render()
