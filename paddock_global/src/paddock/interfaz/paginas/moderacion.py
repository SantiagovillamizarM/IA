"""Página «🛡️ Moderación» (moderador y admin): cola priorizada, revisión humana y ocultación.

La etiqueta del modelo nunca cambia: la revisión se guarda aparte. Nada se borra.
"""

from __future__ import annotations

import streamlit as st

from paddock.dominio.enums import SENTIMIENTOS, Rol
from paddock.dominio.errores import ErrorPaddock
from paddock.interfaz.componentes import recursos, sesion
from paddock.interfaz.componentes.tarjetas import chips_aspectos, etiqueta_sentimiento


def render() -> None:
    st.subheader("🛡️ Moderación")
    c = recursos.contenedor()
    actor = sesion.actor_actual()
    if not c.modo_sql or actor is None or actor.rol not in (Rol.MODERADOR.value, Rol.ADMIN.value):
        st.error("⛔ Acceso denegado: esta página es solo para moderadores y administradores.")
        return
    incluir = st.toggle("Incluir opiniones ya revisadas", value=False)
    try:
        cola = c.moderacion.cola(actor, limite=40, incluir_revisadas=incluir)
    except ErrorPaddock as e:
        st.error(str(e))
        return
    st.caption("Orden: denunciadas → ironía → intensidad baja con sentimiento fuerte → mixtas → resto (más antiguas "
               "primero). Revisar guarda la etiqueta humana aparte; la del modelo no cambia.")
    if not cola:
        st.success("No hay opiniones pendientes de revisión. 🎉")
        return
    st.metric("En la cola", len(cola))
    for el in cola:
        op = el.opinion
        titulo = f"{etiqueta_sentimiento(op.sentimiento)} · {op.evento_nombre}" + (" · 🙈 oculta" if not op.visible else "")
        with st.expander(f"{titulo} — {', '.join(el.motivos) or 'sin prioridad'}"):
            st.text(op.opinion_original)
            st.caption(f"Razón del modelo ({op.modelo}, prompt {op.version_prompt}): {op.razon}")
            extras = []
            if op.ironia:
                extras.append("🎭 ironía")
            if op.intensidad:
                extras.append(f"intensidad {op.intensidad}/5")
            if el.denuncias:
                extras.append(f"🚩 {el.denuncias} denuncia(s)")
            if op.revision:
                extras.append(f"revisada: {etiqueta_sentimiento(op.revision.sentimiento)}")
            if extras:
                st.caption(" · ".join(extras))
            if op.aspectos:
                st.markdown(chips_aspectos(op.aspectos), unsafe_allow_html=True)
            with st.form(f"rev_{op.id}"):
                col1, col2 = st.columns([1, 2])
                sent = col1.selectbox("Sentimiento correcto", SENTIMIENTOS, index=SENTIMIENTOS.index(op.sentimiento),
                                      format_func=etiqueta_sentimiento)
                nota = col2.text_input("Nota (opcional)", max_chars=500)
                b1, b2 = st.columns(2)
                confirmar = b1.form_submit_button("✅ Guardar revisión", type="primary")
                ocultar = b2.form_submit_button("🙈 Ocultar" if op.visible else "👁️ Mostrar")
            try:
                if confirmar:
                    c.moderacion.revisar(actor, op.id, sent, nota)
                    recursos.invalidar_datos()
                    st.success("Revisión guardada.")
                    st.rerun()
                if ocultar:
                    c.moderacion.cambiar_visibilidad(actor, op.id, not op.visible)
                    recursos.invalidar_datos()
                    st.rerun()
            except ErrorPaddock as e:
                st.error(str(e))


render()
