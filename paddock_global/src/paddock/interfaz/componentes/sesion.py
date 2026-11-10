"""Sesión del usuario en Streamlit.

- La identidad vive solo en ``st.session_state`` (servidor). Nunca en la URL ni en ``st.query_params``.
- Caduca por inactividad (``SESION_MINUTOS``). Cerrar sesión limpia todo ``st.session_state``.
- En cada ejecución se relee el usuario: un cambio de rol o una baja se aplican al momento.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import uuid4

import streamlit as st

from paddock.aplicacion.autorizacion import Actor
from paddock.dominio.reglas import sesion_expirada


def _contenedor():  # type: ignore[no-untyped-def]
    from paddock.interfaz.componentes import recursos

    return recursos.contenedor()


def ip_hash() -> str | None:
    """Hash con sal de la IP del cliente (nunca en claro). XFF solo si viene del proxy local."""
    from paddock.adaptadores.seguridad.hash import ip_cliente

    c = _contenedor()
    try:
        remota = st.context.ip_address
        xff = st.context.headers.get("X-Forwarded-For")
    except Exception:  # noqa: BLE001 - fuera de un servidor real (tests)
        return None
    remota = remota if isinstance(remota, str) else None
    xff = xff if isinstance(xff, str) else None
    confiables = {p.strip() for p in c.ajustes.PROXY_CONFIABLE.split(",") if p.strip()}
    return c.hash_ip(ip_cliente(remota, xff, confiables))


def actor_actual() -> Actor | None:
    actor: Actor | None = st.session_state.get("actor")
    if actor is None:
        return None
    c = _contenedor()
    ahora = datetime.now(UTC)
    ultima = st.session_state.get("ultima_actividad", ahora)
    if sesion_expirada(ultima, ahora, c.ajustes.SESION_MINUTOS):
        cerrar_sesion(motivo="Tu sesión caducó por inactividad. Vuelve a iniciar sesión.")
        return None
    if c.modo_sql:
        refrescado = c.cuentas.refrescar(actor)
        if refrescado is None:
            cerrar_sesion(motivo="Tu cuenta ya no está activa.")
            return None
        st.session_state.actor = actor = refrescado
    st.session_state.ultima_actividad = ahora
    return actor


def iniciar_sesion(actor: Actor) -> None:
    # Se descarta el estado anónimo previo (evita arrastrar datos de otra sesión).
    historial = st.session_state.get("historial", [])
    st.session_state.clear()
    st.session_state.historial = historial
    st.session_state.actor = actor
    st.session_state.ultima_actividad = datetime.now(UTC)


def cerrar_sesion(motivo: str | None = None) -> None:
    c = _contenedor()
    actor = st.session_state.get("actor")
    if c.modo_sql and actor is not None:
        try:
            c.cuentas.cerrar_sesion(actor, ip_hash())
        except Exception:  # noqa: BLE001 - cerrar sesión nunca debe fallar
            logging.getLogger(__name__).warning("No se pudo auditar el cierre de sesión.")
    st.session_state.clear()
    if motivo:
        st.session_state.aviso_sesion = motivo


def id_navegador() -> str:
    """Identificador aleatorio de la sesión del navegador, para el limitador de anónimos."""
    if "id_navegador" not in st.session_state:
        st.session_state.id_navegador = f"anon-{uuid4()}"
    return st.session_state.id_navegador


def puede_emitir() -> bool:
    return not _contenedor().exigir_sesion_para_emitir or actor_actual() is not None
