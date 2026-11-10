"""Sección «Estadísticas»: gráfica por carrera, ranking y aspectos. No llama al modelo."""

from __future__ import annotations

import pandas as pd
import streamlit as st

import almacenamiento as alm
import estadisticas as est
from config import RUTA_OPINIONES, SENTIMIENTOS
from ui.comun import EMOJI, NOMBRE_ASPECTO, NOMBRE_IDIOMA, grafica_apilada


def render() -> None:
    st.subheader("Estadísticas de las opiniones registradas")
    st.caption("Calculadas solo con las opiniones guardadas en esta app (no representan la opinión mundial). "
               "Usan la etiqueta vigente: la corrección manual si existe; si no, la del modelo.")
    try:
        registros = alm.cargar_opiniones(RUTA_OPINIONES)["opiniones"]
    except alm.ArchivoOpinionesCorruptoError as e:
        st.error(f"❌ {e}")
        return
    if not registros:
        st.info("Todavía no hay opiniones guardadas.")
        return

    conteo = alm.contar_por_sentimiento(registros)
    cols = st.columns(5)
    cols[0].metric("Opiniones", len(registros))
    for col, s in zip(cols[1:], SENTIMIENTOS):
        col.metric(f"{EMOJI[s]} {s.capitalize()}", conteo[s])

    # ---------------------------------------------------------- gráfica por carrera
    st.markdown("#### 📊 Sentimiento por carrera")
    porcentaje = st.toggle("Mostrar en porcentaje", key="graf_pct")
    df = pd.DataFrame(est.conteo_por_carrera(registros))
    st.altair_chart(grafica_apilada(df, "carrera", "% de opiniones" if porcentaje else "Opiniones", porcentaje),
                    width="stretch")
    with st.expander("Ver como tabla"):
        tabla = df.pivot_table(index="carrera", columns="sentimiento", values="n", fill_value=0)
        tabla = tabla.reindex(columns=[s for s in SENTIMIENTOS if s in tabla.columns])
        tabla["total"] = tabla.sum(axis=1)
        st.dataframe(tabla.sort_values("total", ascending=False), width="stretch")

    # ------------------------------------------------------------------- ranking
    st.markdown("#### 🏆 Ranking de carreras")
    minimo = st.slider("Mínimo de opiniones para entrar al ranking", 1, 10, 2)
    ranking = est.ranking_carreras(registros, minimo=minimo)
    filas = []
    puesto = 0
    for f in ranking:
        if f["suficiente"]:
            puesto += 1
            medalla = {1: "🥇", 2: "🥈", 3: "🥉"}.get(puesto, f"{puesto}.")
        else:
            medalla = "—"
        filas.append({
            "Puesto": medalla, "Carrera": f["carrera"], "Opiniones": f["opiniones"],
            "Índice": f["indice"],
            "😀": f["positivo"], "😞": f["negativo"], "😐": f["neutro"], "🤔": f["mixto"],
            "Nota": "" if f["suficiente"] else "pocas opiniones",
        })
    st.dataframe(
        pd.DataFrame(filas), width="stretch", hide_index=True,
        column_config={"Índice": st.column_config.ProgressColumn(
            "Índice de percepción", min_value=-100, max_value=100, format="%.0f",
            help="(positivas − negativas) ÷ total × 100. Neutras y mixtas cuentan en el total.")},
    )

    # ------------------------------------------------------------------ aspectos
    st.markdown("#### 🔍 ¿De qué hablan los aficionados?")
    aspectos = est.conteo_por_aspecto(registros)
    if not aspectos:
        st.info("Las opiniones guardadas no tienen aspectos detectados (se registran desde el prompt v2.0).")
    else:
        dfa = pd.DataFrame(aspectos)
        dfa["aspecto"] = dfa["aspecto"].map(lambda a: NOMBRE_ASPECTO.get(a, a))
        st.altair_chart(grafica_apilada(dfa, "aspecto", "Menciones", False,
                                        dominio=("positivo", "negativo", "neutro")), width="stretch")
        st.caption("Cada opinión puede mencionar varios aspectos; cada mención tiene su propia valoración.")

    # ------------------------------------------------------------------- idiomas
    idiomas = est.resumen_idiomas(registros)
    st.markdown("#### 🌍 Idiomas")
    st.write(" · ".join(f"**{NOMBRE_IDIOMA.get(k, k)}:** {v}" for k, v in
                        sorted(idiomas.items(), key=lambda kv: -kv[1])))
