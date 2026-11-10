"""Página «👤 Mi cuenta»: inicio de sesión, registro, mis opiniones, exportar y eliminar mi cuenta."""

from __future__ import annotations

import json

import streamlit as st

from paddock.dominio.entidades import FiltrosOpinion
from paddock.dominio.errores import ErrorPaddock
from paddock.interfaz.componentes import recursos, sesion
from paddock.interfaz.componentes.filtros import tabla


def _formulario_login() -> None:
    c = recursos.contenedor()
    with st.form("form_login", clear_on_submit=False):
        email = st.text_input("Correo", autocomplete="email")
        clave = st.text_input("Contraseña", type="password", autocomplete="current-password")
        if st.form_submit_button("Iniciar sesión", type="primary"):
            try:
                actor = c.cuentas.iniciar_sesion(email, clave, sesion.ip_hash())
            except ErrorPaddock as e:
                st.error(str(e))
            else:
                sesion.iniciar_sesion(actor)
                st.rerun()


def _formulario_registro() -> None:
    c = recursos.contenedor()
    if not c.ajustes.REGISTRO_ABIERTO:
        st.info("El registro de nuevas cuentas está cerrado. Pide una cuenta al administrador.")
        return
    with st.form("form_registro", clear_on_submit=False):
        nombre = st.text_input("Nombre visible", max_chars=40, help="Se usa solo dentro de la app.")
        email = st.text_input("Correo", autocomplete="email")
        clave = st.text_input("Contraseña (mínimo 12 caracteres)", type="password", autocomplete="new-password")
        clave2 = st.text_input("Repite la contraseña", type="password", autocomplete="new-password")
        acepto = st.checkbox("He leído la política de privacidad y acepto el tratamiento de mis datos.")
        if st.form_submit_button("Crear cuenta", type="primary"):
            if clave != clave2:
                st.error("Las contraseñas no coinciden.")
            elif not acepto:
                st.error("Debes aceptar la política de privacidad.")
            else:
                try:
                    c.cuentas.registrar(email, nombre, clave, ip_hash=sesion.ip_hash())
                    actor = c.cuentas.iniciar_sesion(email, clave, sesion.ip_hash())
                except ErrorPaddock as e:
                    st.error(str(e))
                else:
                    sesion.iniciar_sesion(actor)
                    st.rerun()


def _mi_cuenta() -> None:
    c = recursos.contenedor()
    actor = sesion.actor_actual()
    assert actor is not None
    st.markdown(f"Hola, **{actor.nombre}** · `{actor.email}` · rol: **{actor.rol}**")
    if st.button("🚪 Cerrar sesión"):
        sesion.cerrar_sesion()
        st.rerun()

    st.markdown("#### Mis opiniones")
    mias = c.repo_opiniones.consultar(FiltrosOpinion(usuario_id=actor.usuario_id))
    if mias:
        st.dataframe(tabla(mias, c.ajustes.ZONA_HORARIA), use_container_width=True, hide_index=True)
    else:
        st.info("Todavía no has emitido opiniones.")

    st.markdown("#### Mis datos")
    if st.button("Preparar exportación (JSON)"):
        st.session_state.exportacion = json.dumps(c.cuentas.exportar_mis_datos(actor), ensure_ascii=False, indent=2)
    if st.session_state.get("exportacion"):
        st.download_button("⬇️ Descargar mis datos", st.session_state.exportacion.encode("utf-8"),
                           file_name="mis_datos_paddock.json", mime="application/json")

    _tokens_api(actor)

    with st.expander("🗑️ Eliminar mi cuenta"):
        st.warning("Se borra tu cuenta. Tus opiniones se conservan de forma anónima (sin vínculo contigo). "
                   "No se puede deshacer.")
        with st.form("form_eliminar"):
            clave = st.text_input("Confirma con tu contraseña", type="password")
            seguro = st.checkbox("Entiendo que no se puede deshacer")
            if st.form_submit_button("Eliminar mi cuenta") and seguro:
                try:
                    n = c.cuentas.eliminar_mi_cuenta(actor, clave)
                except ErrorPaddock as e:
                    st.error(str(e))
                else:
                    sesion.cerrar_sesion(motivo=f"Cuenta eliminada. {n} opiniones quedaron anónimas.")
                    st.rerun()


def _tokens_api(actor) -> None:  # type: ignore[no-untyped-def]
    """v3: tokens personales para la API REST (se muestran una sola vez y se guardan como hash)."""
    c = recursos.contenedor()
    if not hasattr(c, "tokens_api"):
        return
    st.markdown("#### Tokens de API")
    tokens = c.tokens_api.listar(actor)
    for t in tokens:
        col1, col2 = st.columns([4, 1])
        estado = "revocado" if t.revocado else f"último uso: {t.ultimo_uso_utc or 'nunca'}"
        col1.markdown(f"`{t.nombre}` · creado {t.creado_utc[:10]} · {estado}")
        if not t.revocado and col2.button("Revocar", key=f"rev_{t.id}"):
            c.tokens_api.revocar(actor, t.id)
            st.rerun()
    with st.form("form_token", clear_on_submit=True):
        nombre = st.text_input("Nombre del token", max_chars=40, placeholder="p. ej. integración-dashboard")
        if st.form_submit_button("Crear token"):
            try:
                st.session_state.token_nuevo = c.tokens_api.crear(actor, nombre)
            except ErrorPaddock as e:
                st.error(str(e))
    if st.session_state.get("token_nuevo"):
        st.success("Copia este token ahora: no se volverá a mostrar.")
        st.code(st.session_state.pop("token_nuevo"), language=None)


def render() -> None:
    st.subheader("👤 Mi cuenta")
    c = recursos.contenedor()
    if aviso := st.session_state.pop("aviso_sesion", None):
        st.info(aviso)
    if not c.modo_sql:
        st.info("El modo taller (STORAGE_BACKEND=json) no tiene cuentas. Cambia a STORAGE_BACKEND=sql para activarlas.")
        return
    if sesion.actor_actual() is None:
        t1, t2 = st.tabs(["Iniciar sesión", "Crear cuenta"])
        with t1:
            _formulario_login()
        with t2:
            _formulario_registro()
    else:
        _mi_cuenta()


render()
