"""Filtros, tabla y exportación compartidos por Consultar, Dashboard y Comparar. Nunca llaman al modelo."""

from __future__ import annotations

import io
import json
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

from paddock.dominio.entidades import FiltrosOpinion, Opinion
from paddock.dominio.enums import SENTIMIENTOS
from paddock.interfaz.componentes import recursos
from paddock.interfaz.componentes.tarjetas import etiqueta_sentimiento

TODOS = "__todos__"


def fecha_local(fecha_utc: str, zona: str) -> str:
    try:
        return datetime.fromisoformat(fecha_utc).astimezone(ZoneInfo(zona)).strftime("%Y-%m-%d %H:%M")
    except (ValueError, KeyError):
        return fecha_utc


def tabla(registros: list[Opinion], zona: str, usar_revision: bool = False) -> pd.DataFrame:
    return pd.DataFrame([
        {
            "Fecha": fecha_local(o.fecha_utc, zona),
            "Carrera": o.evento_nombre,
            "Edición": str(o.edicion_anio) if o.edicion_anio else "—",
            "Opinión original": o.opinion_original,
            "Sentimiento": etiqueta_sentimiento(o.sentimiento_efectivo if usar_revision else o.sentimiento),
            "Razón": o.razon,
        }
        for o in registros
    ], columns=["Fecha", "Carrera", "Edición", "Opinión original", "Sentimiento", "Razón"])


def csv_con_bom(registros: list[Opinion]) -> bytes:
    """CSV UTF-8 con BOM para que Excel muestre bien las tildes."""
    df = pd.DataFrame([o.a_dict() for o in registros])
    for col in ("aspectos", "entidades", "revision"):
        if col in df:
            df[col] = df[col].apply(lambda v: json.dumps(v, ensure_ascii=False) if v is not None else "")
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    return buf.getvalue().encode("utf-8-sig")


def filtros_ui(prefijo: str = "f", con_sentimiento: bool = True, con_evento: bool = True) -> FiltrosOpinion:
    cat = recursos.catalogo()
    # Enlace directo «?evento=<id>» (p. ej. desde el mapa): precarga el filtro una sola vez.
    qp_ev = st.query_params.get("evento")
    if qp_ev and cat.evento(qp_ev) and not st.session_state.get(f"{prefijo}_qp"):
        st.session_state[f"{prefijo}_ev"] = qp_ev
        st.session_state[f"{prefijo}_qp"] = True
    c1, c2, c3, c4, c5 = st.columns([1.1, 1.1, 1.6, 0.9, 1])
    with c1:
        disc = st.selectbox("Disciplina", [TODOS, *[d.id for d in cat.disciplinas]], key=f"{prefijo}_disc",
                            format_func=lambda i: "Todas" if i == TODOS else
                            f"{cat.disciplina(i).icono} {cat.disciplina(i).nombre}")  # type: ignore[union-attr]
    with c2:
        camps = [c.id for c in cat.campeonatos if disc == TODOS or c.disciplina_id == disc]
        camp = st.selectbox("Campeonato", [TODOS, *camps], key=f"{prefijo}_camp",
                            format_func=lambda i: "Todos" if i == TODOS else cat.campeonato(i).nombre)  # type: ignore[union-attr]
    ev = TODOS
    with c3:
        evs = [e.id for e in cat.eventos
               if (camp == TODOS or e.campeonato_id == camp)
               and (disc == TODOS or e.id in {x.id for x in cat.eventos_de_disciplina(disc)})]
        if con_evento:
            ev = st.selectbox("Carrera", [TODOS, *evs], key=f"{prefijo}_ev",
                              format_func=lambda i: "Todas" if i == TODOS else cat.evento(i).etiqueta)  # type: ignore[union-attr]
    with c4:
        anio = st.number_input("Edición", min_value=0, max_value=datetime.now().year, value=0, step=1,
                               key=f"{prefijo}_anio", help="0 = todas las ediciones")
    sent = TODOS
    with c5:
        if con_sentimiento:
            sent = st.selectbox("Sentimiento", [TODOS, *SENTIMIENTOS], key=f"{prefijo}_sent",
                                format_func=lambda s: "Todos" if s == TODOS else etiqueta_sentimiento(s))
    return FiltrosOpinion(
        disciplina_id=None if disc == TODOS else disc,
        campeonato_id=None if camp == TODOS else camp,
        evento_id=None if ev == TODOS else ev,
        edicion_anio=int(anio) or None,
        sentimiento=None if sent == TODOS else sent,
    )
