"""Página «📊 Dashboard»: KPIs, evolución, disciplinas, aspectos, entidades y ranking.

Lee de los repositorios (nunca del modelo) y se cachea con ``st.cache_data``; la caché se vacía al guardar.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta

import pandas as pd
import streamlit as st

from paddock.aplicacion.obtener_estadisticas import N_MINIMO_RANKING, Estadisticas, calcular
from paddock.dominio.entidades import FiltrosOpinion
from paddock.dominio.enums import SENTIMIENTOS
from paddock.interfaz.componentes import graficos, recursos, sesion
from paddock.interfaz.componentes.filtros import filtros_ui
from paddock.interfaz.componentes.tarjetas import ETIQUETA_ASPECTO, aviso_cifras, etiqueta_sentimiento


@st.cache_data(ttl=300, show_spinner=False)
def estadisticas(filtros: FiltrosOpinion) -> Estadisticas:
    c = recursos.contenedor()
    regs = c.repo_opiniones.consultar(c.consultar_opiniones.resolver(filtros).con(limite=None, desplazamiento=0))
    return calcular(regs, filtros.usar_revision)


def filtros_dashboard(prefijo: str) -> FiltrosOpinion:
    f = filtros_ui(prefijo, con_sentimiento=False, con_evento=False)
    hoy = date.today()
    rango = st.date_input("Rango de fechas", value=(hoy - timedelta(days=365), hoy), key=f"{prefijo}_rango",
                          format="YYYY-MM-DD")
    if isinstance(rango, tuple) and len(rango) == 2:
        desde = datetime.combine(rango[0], time.min).astimezone().isoformat()
        hasta = datetime.combine(rango[1] + timedelta(days=1), time.min).astimezone().isoformat()
        f = f.con(desde_utc=_utc(desde), hasta_utc=_utc(hasta))
    return f


def _utc(iso_local: str) -> str:
    from paddock.puertos.servicios import iso

    return iso(datetime.fromisoformat(iso_local))


def render() -> None:
    st.subheader("📊 Dashboard")
    c = recursos.contenedor()
    if sesion.actor_actual() is None and not c.consultar_opiniones.permitir_anonimos:
        st.info("🔐 Inicia sesión en «Mi cuenta» para ver el dashboard.")
        return
    f = filtros_dashboard("d")
    e = estadisticas(f)
    if e.total == 0:
        st.info("No hay opiniones con esos filtros.")
        return

    k = st.columns(6)
    k[0].metric("Opiniones", e.total)
    for col, s in zip(k[1:5], SENTIMIENTOS, strict=True):
        col.metric(etiqueta_sentimiento(s), f"{e.porcentajes[s]:.0f} %", help=f"{e.conteo[s]} opiniones")
    k[5].metric("Carreras con opiniones", e.eventos_con_opiniones)

    st.plotly_chart(graficos.lineas_semanales(e.semanal), use_container_width=True)
    cat = recursos.catalogo()
    etiquetas_disc = {d.id: f"{d.icono} {d.nombre}" for d in cat.disciplinas}
    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(graficos.barras_100(e.por_disciplina, etiquetas_disc, "Sentimiento por disciplina (100 %)"),
                        use_container_width=True)
    with c2:
        if any(sum(v.values()) for v in e.aspectos.values()):
            st.plotly_chart(graficos.mapa_calor_aspectos(e.aspectos, ETIQUETA_ASPECTO), use_container_width=True)
        else:
            st.info("Aún no hay aspectos valorados (llegan con el prompt 2.0).")
    if e.entidades:
        st.plotly_chart(graficos.barras_entidades(e.entidades), use_container_width=True)

    st.markdown(f"#### Ranking por índice de percepción (n ≥ {N_MINIMO_RANKING})")
    st.caption("Índice = (positivas − negativas) / total, entre −1 y +1. Solo carreras con al menos "
               f"{N_MINIMO_RANKING} opiniones; n al lado.")
    if e.ranking:
        st.dataframe(pd.DataFrame([{"Carrera": r.evento_nombre, "n": r.n, "Índice": round(r.indice, 2),
                                    "😀": r.conteo["positivo"], "😞": r.conteo["negativo"], "😐": r.conteo["neutro"],
                                    "🤔": r.conteo["mixto"]} for r in e.ranking]),
                     hide_index=True, use_container_width=True,
                     column_config={"Índice": st.column_config.ProgressColumn(min_value=-1, max_value=1, format="%.2f")})
    else:
        st.info(f"Ninguna carrera llega a {N_MINIMO_RANKING} opiniones con estos filtros.")
    aviso_cifras()


render()
