"""Recursos compartidos por las páginas: contenedor, catálogo y estado del proveedor (con caché)."""

from __future__ import annotations

import os

import streamlit as st

from paddock.config import Ajustes
from paddock.contenedor import Contenedor, crear_contenedor
from paddock.dominio.entidades import Catalogo


@st.cache_resource(show_spinner=False)
def contenedor() -> Contenedor:
    """Un único contenedor (modelo y cadena incluidos) por proceso de Streamlit."""
    aj = Ajustes()
    # Solo para tests de interfaz (AppTest): fuerza el clasificador determinista sin red.
    if os.environ.get("PADDOCK_CLASIFICADOR_PRUEBAS") == "falso":
        from paddock.adaptadores.llm.falso import ClasificadorFalso

        return crear_contenedor(aj, clasificador_forzado=ClasificadorFalso(detallado=aj.VERSION_PROMPT == "2.0"))
    return crear_contenedor(aj)


def catalogo() -> Catalogo:
    return contenedor().repo_catalogo.obtener()


@st.cache_data(ttl=30, show_spinner=False)
def estado_proveedor() -> tuple[bool, str]:
    return contenedor().verificar_proveedor()


def invalidar_datos() -> None:
    """Tras guardar: limpia las cachés de gráficos y consultas."""
    st.cache_data.clear()
