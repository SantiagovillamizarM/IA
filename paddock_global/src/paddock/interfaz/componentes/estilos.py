"""CSS mínimo para tarjetas y chips. Usa variables del tema para no romper el modo claro."""

from __future__ import annotations

import streamlit as st

from paddock.dominio.enums import COLOR_SENTIMIENTO

_CSS = """
<style>
.pg-chip {display:inline-block;padding:0.12rem 0.6rem;border-radius:999px;font-size:0.82rem;
  border:1px solid rgba(128,128,128,0.35);margin:0 0.3rem 0.3rem 0;line-height:1.5;}
.pg-chip-evento {background:rgba(214,52,44,0.10);}
.pg-tarjeta {border-radius:0.6rem;padding:0.8rem 1rem;margin:0.2rem 0 0.4rem 0;
  border:1px solid rgba(128,128,128,0.30);border-left-width:6px;}
.pg-tarjeta .pg-titulo {font-weight:700;font-size:1.05rem;margin-bottom:0.25rem;}
.pg-tarjeta .pg-razon {opacity:0.92;}
.pg-pie {font-size:0.78rem;opacity:0.7;margin-top:0.35rem;}
.pg-aviso {font-size:0.8rem;opacity:0.75;}
%s
</style>
"""


def inyectar() -> None:
    reglas = "\n".join(
        f".pg-s-{s} {{border-left-color:{c} !important;}} .pg-chip-{s} {{background:{c}22;border-color:{c};}}"
        for s, c in COLOR_SENTIMIENTO.items()
    )
    st.markdown(_CSS % reglas, unsafe_allow_html=True)
