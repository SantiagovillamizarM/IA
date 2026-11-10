"""Página de inicio."""

from __future__ import annotations

import streamlit as st

from paddock.dominio.entidades import FiltrosOpinion
from paddock.dominio.errores import ErrorPaddock
from paddock.interfaz.componentes import recursos
from paddock.interfaz.componentes.tarjetas import aviso_cifras


def render() -> None:
    c = recursos.contenedor()
    cat = recursos.catalogo()
    st.markdown(
        "Elige una carrera en la barra lateral, escribe tu opinión y un modelo de lenguaje la clasificará "
        "como **😀 positiva**, **😞 negativa**, **😐 neutra** o **🤔 mixta**, con una justificación breve. "
        "Tu texto se guarda tal cual lo escribiste."
    )
    try:
        total = c.repo_opiniones.contar(FiltrosOpinion())
    except ErrorPaddock:
        total = None
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Disciplinas", len(cat.disciplinas))
    k2.metric("Campeonatos", len(cat.campeonatos))
    k3.metric("Carreras", sum(1 for e in cat.eventos if e.activo))
    k4.metric("Opiniones registradas", "—" if total is None else total)
    st.markdown("#### ¿Cómo funciona?")
    st.markdown(
        "1. **🗣️ Emitir opinión**: el texto se valida (5 a 1000 caracteres), se clasifica y, si habla de la "
        "carrera elegida, se guarda.\n"
        "2. **🔎 Consultar opiniones**: filtra por disciplina, campeonato, carrera, edición y sentimiento; "
        "descarga los resultados en JSON o CSV. Consultar nunca llama al modelo.\n"
        "3. Un texto que no habla de la carrera **no se guarda**, y un fallo **nunca** se registra como «neutro»."
    )
    aviso_cifras()


render()
