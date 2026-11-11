"""Página de inicio: torre de cifras, pulso de la comunidad, disciplinas y cómo funciona."""

from __future__ import annotations

import streamlit as st

from paddock.dominio.entidades import FiltrosOpinion
from paddock.dominio.enums import COLOR_SENTIMIENTO, EMOJI_SENTIMIENTO, SENTIMIENTOS
from paddock.dominio.errores import ErrorPaddock
from paddock.dominio.reglas import contar_por_sentimiento
from paddock.interfaz.componentes import recursos
from paddock.interfaz.componentes.tarjetas import aviso_cifras, e


def _torre(celdas: list[tuple[str, str]]) -> str:
    filas = "".join(
        f'<div class="pg-celda"><div class="pg-celda-pos">P{i}</div><div class="pg-celda-valor">{e(v)}</div>'
        f'<div class="pg-celda-etq">{e(t)}</div></div>'
        for i, (t, v) in enumerate(celdas, start=1)
    )
    return f'<div class="pg-torre">{filas}</div>'


def _barra(conteo: dict[str, int]) -> str:
    total = sum(conteo.values()) or 1
    segs = "".join(
        f'<div style="flex:{n};background:{COLOR_SENTIMIENTO[s]}" title="{s}: {n}">'
        f'{EMOJI_SENTIMIENTO[s]} {round(100 * n / total)}%</div>'
        for s, n in conteo.items() if n
    )
    leyenda = "".join(
        f'<span><i style="background:{COLOR_SENTIMIENTO[s]}"></i>{EMOJI_SENTIMIENTO[s]} {s.capitalize()} · {conteo[s]}</span>'
        for s in SENTIMIENTOS
    )
    return f'<div class="pg-barra">{segs}</div><div class="pg-leyenda">{leyenda}</div>'


def render() -> None:
    c = recursos.contenedor()
    cat = recursos.catalogo()
    try:
        registros = c.repo_opiniones.consultar(FiltrosOpinion())
    except ErrorPaddock:
        registros = None

    st.markdown(_torre([
        ("Disciplinas", str(len(cat.disciplinas))),
        ("Campeonatos", str(len(cat.campeonatos))),
        ("Carreras", str(sum(1 for ev in cat.eventos if ev.activo))),
        ("Opiniones", "—" if registros is None else str(len(registros))),
    ]), unsafe_allow_html=True)

    if registros:
        st.subheader("Pulso de la comunidad")
        st.markdown(_barra(contar_por_sentimiento(registros)), unsafe_allow_html=True)

    st.subheader("Cómo funciona")
    pasos = [
        ("Elige la carrera", "En la barra lateral: disciplina → campeonato → carrera y, si quieres, el año de la edición."),
        ("Opina", "Escribe entre 5 y 1000 caracteres en «🗣️ Emitir opinión». Un modelo de lenguaje la clasifica y "
                  "explica por qué; tu texto se guarda tal cual."),
        ("Explora", "Consulta, filtra y descarga las opiniones, o mira el dashboard, el comparador y el mapa. "
                    "Consultar nunca llama al modelo."),
    ]
    st.markdown('<div class="pg-pasos">' + "".join(
        f'<div class="pg-paso"><span class="pg-paso-num">{i}</span><div class="pg-paso-tit">{e(t)}</div>'
        f'<div class="pg-paso-txt">{e(x)}</div></div>' for i, (t, x) in enumerate(pasos, start=1)
    ) + "</div>", unsafe_allow_html=True)

    st.subheader("Disciplinas en el paddock")
    tarjetas = []
    for d in cat.disciplinas:
        eventos = [ev for ev in cat.eventos_de_disciplina(d.id) if ev.activo]
        campeonatos = ", ".join(x.nombre for x in cat.campeonatos_de(d.id))
        tarjetas.append(
            f'<div class="pg-disc"><div class="pg-disc-ico">{e(d.icono)}</div><div class="pg-disc-nom">{e(d.nombre)}</div>'
            f'<div class="pg-disc-det">{len(eventos)} carreras · {e(campeonatos)}</div></div>'
        )
    st.markdown(f'<div class="pg-rejilla">{"".join(tarjetas)}</div>', unsafe_allow_html=True)

    st.caption("Un texto que no habla de la carrera elegida **no se guarda**, y un fallo **nunca** se registra como «neutro».")
    aviso_cifras()


render()
