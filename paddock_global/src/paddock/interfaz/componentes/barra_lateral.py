"""Barra lateral: selector encadenado, ficha del evento, estado del proveedor y «Nueva conversación».

Sin selectores de personalidad, modelo ni temperatura (criterios estables del clasificador).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

import streamlit as st

from paddock.dominio.entidades import Catalogo, Disciplina, Evento
from paddock.interfaz.componentes import recursos

SIN_EDICION = 0


@dataclass(frozen=True)
class Seleccion:
    evento: Evento
    disciplina: Disciplina
    edicion_anio: int | None


def _asegurar(clave: str, opciones: list[str], defecto: str) -> None:
    if st.session_state.get(clave) not in opciones:
        st.session_state[clave] = defecto if defecto in opciones else opciones[0]


def selector_evento(cat: Catalogo) -> Seleccion:
    por_defecto = cat.evento_por_defecto()
    camp_def = cat.campeonato(por_defecto.campeonato_id)
    disc_def = camp_def.disciplina_id if camp_def else cat.disciplinas[0].id

    disciplinas = [d.id for d in cat.disciplinas if any(e.activo for e in cat.eventos_de_disciplina(d.id))]
    _asegurar("sel_disciplina", disciplinas, disc_def)
    disc_id = st.selectbox(
        "Disciplina", disciplinas, key="sel_disciplina",
        format_func=lambda i: f"{cat.disciplina(i).icono} {cat.disciplina(i).nombre}",  # type: ignore[union-attr]
    )
    campeonatos = [c.id for c in cat.campeonatos_de(disc_id) if cat.eventos_de(c.id)]
    _asegurar("sel_campeonato", campeonatos, por_defecto.campeonato_id)
    camp_id = st.selectbox("Campeonato", campeonatos, key="sel_campeonato",
                           format_func=lambda i: cat.campeonato(i).nombre)  # type: ignore[union-attr]
    eventos = [e.id for e in cat.eventos_de(camp_id)]
    _asegurar("sel_evento", eventos, por_defecto.id)
    ev_id = st.selectbox("Carrera", eventos, key="sel_evento",
                         format_func=lambda i: cat.evento(i).etiqueta)  # type: ignore[union-attr]

    anio_actual = datetime.now(UTC).year
    anios = [SIN_EDICION, *range(anio_actual, 1899, -1)]
    edicion = st.selectbox("Edición (año)", anios, key="sel_edicion",
                           format_func=lambda a: "Sin especificar" if a == SIN_EDICION else str(a))
    evento = cat.evento(ev_id)
    assert evento is not None
    return Seleccion(evento=evento, disciplina=cat.disciplina_de_evento(evento),
                     edicion_anio=None if edicion == SIN_EDICION else int(edicion))


def ficha_evento(sel: Seleccion) -> None:
    from paddock.interfaz.componentes.tarjetas import e

    ev = sel.evento
    historica = "<br>🏛️ <i>Prueba histórica: ya no se disputa en su formato clásico.</i>" if ev.historico else ""
    edicion = f" · edición <b>{sel.edicion_anio}</b>" if sel.edicion_anio else ""
    st.markdown(f'<div class="pg-ficha">{e(sel.disciplina.icono)} <b>{e(sel.disciplina.nombre)}</b>{edicion}'
                f"<br>📍 {e(ev.pais)} · {e(ev.sede)}{historica}</div>", unsafe_allow_html=True)


def estado_llm() -> None:
    aj = recursos.contenedor().ajustes
    ok, msg = recursos.estado_proveedor()
    st.markdown('<div class="pg-lateral-tit">Modelo</div>', unsafe_allow_html=True)
    st.markdown(f"{'🟢' if ok else '🔴'} <span class='pg-modelo'>{aj.modelo_activo}</span>", unsafe_allow_html=True)
    if not ok:
        st.caption(msg)
    st.caption(f"Prompt v{aj.VERSION_PROMPT} · temperatura {aj.LLM_TEMPERATURE:g} (solo lectura, desde .env)")


def _usuario() -> None:
    from paddock.interfaz.componentes import sesion

    if not recursos.contenedor().modo_sql:
        return
    actor = sesion.actor_actual()
    if actor is None:
        st.caption("👤 Sin sesión · entra en «Mi cuenta» para opinar")
    else:
        st.caption(f"👤 {actor.nombre} · {actor.rol}")


def render() -> Seleccion:
    with st.sidebar:
        _usuario()
        st.markdown('<div class="pg-lateral-tit">🏁 Carrera</div>', unsafe_allow_html=True)
        sel = selector_evento(recursos.catalogo())
        ficha_evento(sel)
        st.divider()
        estado_llm()
        if st.button("🗑️ Nueva conversación", use_container_width=True,
                     help="Vacía el chat de esta sesión. Las opiniones guardadas no se tocan."):
            st.session_state.historial = []
            st.session_state.pop("pendiente", None)
            st.rerun()
    st.session_state.seleccion = sel
    return sel
