"""Página «⚙️ Administración» (solo admin). La autorización se comprueba en los casos de uso.

Ningún borrado físico de opiniones desde la UI.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from paddock.dominio.entidades import Evento
from paddock.dominio.enums import Rol
from paddock.dominio.errores import ErrorPaddock
from paddock.interfaz.componentes import recursos, sesion


def _eventos(actor) -> None:  # type: ignore[no-untyped-def]
    c = recursos.contenedor()
    cat = recursos.catalogo()
    st.dataframe(pd.DataFrame([{"id": e.id, "Carrera": e.nombre, "Campeonato": cat.campeonato(e.campeonato_id).nombre,
                                "País": e.pais, "Activo": "✅" if e.activo else "⛔"} for e in cat.eventos]),
                 hide_index=True, use_container_width=True, height=280)
    col1, col2 = st.columns([3, 1])
    ev_id = col1.selectbox("Evento", [e.id for e in cat.eventos], format_func=lambda i: cat.evento(i).etiqueta)  # type: ignore[union-attr]
    ev = cat.evento(ev_id)
    if col2.button("Desactivar" if ev and ev.activo else "Activar", use_container_width=True):
        try:
            c.gestionar_catalogo.cambiar_activo(actor, ev_id, not ev.activo)  # type: ignore[union-attr]
            st.success("Hecho. Un evento desactivado no aparece en el selector, pero sus opiniones se conservan.")
            st.rerun()
        except ErrorPaddock as e:
            st.error(str(e))
    with st.form("nuevo_evento", clear_on_submit=True):
        st.markdown("**Añadir evento**")
        a, b = st.columns(2)
        ev_nuevo = a.text_input("id (slug)", placeholder="ev-f1-qatar")
        camp = b.selectbox("Campeonato", [x.id for x in cat.campeonatos], format_func=lambda i: cat.campeonato(i).nombre)  # type: ignore[union-attr]
        nombre = a.text_input("Nombre")
        pais = b.text_input("País")
        sede = a.text_input("Sede")
        historico = b.checkbox("Histórico")
        lat = a.number_input("Latitud (aprox.)", -90.0, 90.0, 0.0, format="%.3f")
        lon = b.number_input("Longitud (aprox.)", -180.0, 180.0, 0.0, format="%.3f")
        if st.form_submit_button("Añadir"):
            try:
                c.gestionar_catalogo.anadir_evento(actor, Evento(ev_nuevo.strip(), camp, nombre.strip(), pais.strip(),
                                                                 sede.strip(), lat, lon, historico))
                st.success("Evento añadido.")
            except ErrorPaddock as e:
                st.error(str(e))


def _jerga(actor) -> None:  # type: ignore[no-untyped-def]
    c = recursos.contenedor()
    cat = recursos.catalogo()
    disc = st.selectbox("Disciplina", [d.id for d in cat.disciplinas], key="jerga_disc",
                        format_func=lambda i: cat.disciplina(i).nombre)  # type: ignore[union-attr]
    actuales = c.repo_catalogo.obtener_jerga().get(disc, [])
    texto = st.text_area("Términos (uno por línea). Son descriptivos: por sí solos no son positivos ni negativos.",
                         "\n".join(actuales), height=220, key=f"jerga_{disc}")
    if st.button("Guardar jerga"):
        try:
            c.gestionar_catalogo.editar_jerga(actor, disc, texto.splitlines())
            st.success("Jerga guardada. Se aplica a las próximas clasificaciones.")
        except ErrorPaddock as e:
            st.error(str(e))


def _usuarios(actor) -> None:  # type: ignore[no-untyped-def]
    c = recursos.contenedor()
    usuarios = c.cuentas.listar(actor)
    st.dataframe(pd.DataFrame([{"Correo": u.email, "Nombre": u.nombre_visible, "Rol": u.rol,
                                "Activo": "✅" if u.activo else "⛔", "Último acceso": u.ultimo_acceso_utc or "—",
                                "Bloqueado hasta": u.bloqueado_hasta or "—"} for u in usuarios]),
                 hide_index=True, use_container_width=True)
    if not usuarios:
        return
    ids = [u.id for u in usuarios]
    por_id = {u.id: u for u in usuarios}
    uid = st.selectbox("Usuario", ids, format_func=lambda i: por_id[i].email)
    a, b = st.columns(2)
    rol = a.selectbox("Rol", [r.value for r in Rol], index=[r.value for r in Rol].index(por_id[uid].rol))
    if a.button("Cambiar rol"):
        try:
            c.cuentas.cambiar_rol(actor, uid, rol)
            st.rerun()
        except ErrorPaddock as e:
            st.error(str(e))
    activo = por_id[uid].activo
    if b.button("Bloquear cuenta" if activo else "Reactivar cuenta"):
        try:
            c.cuentas.cambiar_activo(actor, uid, not activo)
            st.rerun()
        except ErrorPaddock as e:
            st.error(str(e))


def _auditoria(actor) -> None:  # type: ignore[no-untyped-def]
    c = recursos.contenedor()
    a, b = st.columns(2)
    accion = a.text_input("Acción", placeholder="login_fallido, cambio_rol, posible_inyeccion_prompt…")
    usuario = b.text_input("Id de usuario")
    filas = c.cuentas.consultar_auditoria(actor, accion=accion.strip() or None, usuario_id=usuario.strip() or None)
    if filas:
        st.dataframe(pd.DataFrame(filas), hide_index=True, use_container_width=True)
    else:
        st.info("Sin registros con esos filtros.")


def render() -> None:
    st.subheader("⚙️ Administración")
    c = recursos.contenedor()
    actor = sesion.actor_actual()
    if not c.modo_sql or actor is None or actor.rol != Rol.ADMIN.value:
        st.error("⛔ Acceso denegado: esta página es solo para administradores.")
        return
    t1, t2, t3, t4 = st.tabs(["Eventos", "Jerga", "Usuarios", "Auditoría"])
    with t1:
        _eventos(actor)
    with t2:
        _jerga(actor)
    with t3:
        _usuarios(actor)
    with t4:
        _auditoria(actor)


render()
