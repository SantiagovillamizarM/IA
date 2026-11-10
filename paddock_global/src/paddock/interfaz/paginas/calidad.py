"""Página «🎯 Calidad» (admin): métricas del modelo sobre opiniones revisadas por humanos y rendimiento."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from paddock.aplicacion.calidad import csv_evaluacion, evaluar_pares
from paddock.dominio.enums import SENTIMIENTOS, Rol
from paddock.interfaz.componentes import recursos, sesion
from paddock.interfaz.componentes.graficos import NOMBRE

TODOS = "Todos"
MINIMO_RECOMENDADO = 30


def _fmt(v: float | None) -> str:
    return "—" if v is None else f"{v:.2f}"


def render() -> None:
    st.subheader("🎯 Calidad del modelo")
    c = recursos.contenedor()
    actor = sesion.actor_actual()
    if not c.modo_sql or actor is None or actor.rol != Rol.ADMIN.value:
        st.error("⛔ Acceso denegado: esta página es solo para administradores.")
        return
    todas = c.calidad.revisadas(actor)
    proveedores = sorted({o.modelo.split("/")[0] for o in todas})
    modelos = sorted({o.modelo for o in todas})
    versiones = sorted({o.version_prompt for o in todas})
    f1, f2, f3 = st.columns(3)
    prov = f1.selectbox("Proveedor", [TODOS, *proveedores])
    mod = f2.selectbox("Modelo", [TODOS, *modelos])
    ver = f3.selectbox("Versión del prompt", [TODOS, *versiones])
    ops = c.calidad.revisadas(actor, proveedor=None if prov == TODOS else prov, modelo=None if mod == TODOS else mod,
                              version_prompt=None if ver == TODOS else ver)
    inf = evaluar_pares([(o.revision.sentimiento, o.sentimiento) for o in ops if o.revision])
    if inf.n < MINIMO_RECOMENDADO:
        st.warning(f"Hay {inf.n} opiniones revisadas con estos filtros. Las métricas son orientativas por debajo de "
                   f"{MINIMO_RECOMENDADO}; las etiquetas humanas las ponen los moderadores en «🛡️ Moderación».")
    k = st.columns(3)
    k[0].metric("Opiniones revisadas", inf.n)
    k[1].metric("Exactitud", _fmt(inf.exactitud))
    k[2].metric("F1 macro", _fmt(inf.f1_macro))
    if inf.n:
        st.dataframe(pd.DataFrame([{"Categoría": NOMBRE[s], "Precisión": _fmt(m.precision), "Recall": _fmt(m.recall),
                                    "F1": _fmt(m.f1), "Soporte (humano)": m.soporte}
                                   for s, m in inf.por_clase.items()]), hide_index=True, use_container_width=True)
        z = [[inf.matriz[r][p] for p in SENTIMIENTOS] for r in SENTIMIENTOS]
        fig = px.imshow(z, x=[NOMBRE[s] for s in SENTIMIENTOS], y=[NOMBRE[s] for s in SENTIMIENTOS], text_auto=True,
                        labels={"x": "Etiqueta del modelo", "y": "Etiqueta humana", "color": "n"},
                        color_continuous_scale=["#1d2330", "#24507d", "#2f6fae"], title="Matriz de confusión")
        fig.update_traces(textfont_color="#eef0f3")
        fig.update_layout(coloraxis_showscale=False, height=420, margin={"l": 8, "r": 8, "t": 40, "b": 8})
        st.plotly_chart(fig, use_container_width=True)
        st.download_button("⬇️ Exportar conjunto de evaluación (CSV)", csv_evaluacion(ops),
                           file_name="conjunto_evaluacion.csv", mime="text/csv")

    st.markdown("#### Rendimiento de las llamadas al modelo")
    rend = c.calidad.rendimiento(actor)
    if not rend:
        st.info("Aún no hay métricas de llamadas registradas.")
        return
    st.dataframe(pd.DataFrame([{
        "Proveedor": r.proveedor, "Llamadas": r.llamadas, "Latencia media (ms)": round(r.latencia_media_ms),
        "Latencia p95 (ms)": round(r.latencia_p95_ms), "Tasa de error": f"{100 * r.tasa_error:.1f} %",
        "Errores por tipo": ", ".join(f"{k}: {v}" for k, v in r.errores.items()) or "—",
        "Tokens entrada": r.tokens_entrada, "Tokens salida": r.tokens_salida} for r in rend]),
        hide_index=True, use_container_width=True)


render()
