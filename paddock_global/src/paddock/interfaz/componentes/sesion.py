"""Estado de sesión del usuario en Streamlit (v1: anónimo; v2 añade cuentas)."""

from __future__ import annotations

from uuid import uuid4

import streamlit as st

from paddock.aplicacion.autorizacion import Actor


def actor_actual() -> Actor | None:
    return st.session_state.get("actor")


def id_navegador() -> str:
    """Identificador aleatorio de la sesión del navegador, para el limitador de anónimos."""
    if "id_navegador" not in st.session_state:
        st.session_state.id_navegador = f"anon-{uuid4()}"
    return st.session_state.id_navegador


def puede_emitir() -> bool:
    from paddock.interfaz.componentes import recursos

    c = recursos.contenedor()
    return not c.exigir_sesion_para_emitir or actor_actual() is not None
