"""Página «🗺️ Mapa»: un punto por carrera; color = índice de percepción; tamaño = número de opiniones."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from paddock.aplicacion.obtener_estadisticas import calcular
from paddock.dominio.entidades import FiltrosOpinion
from paddock.dominio.reglas import contar_por_sentimiento, indice_percepcion
from paddock.interfaz.componentes import recursos, sesion
from paddock.interfaz.componentes.filtros import filtros_ui
from paddock.interfaz.componentes.tarjetas import aviso_cifras, etiqueta_sentimiento


@st.cache_data(ttl=300, show_spinner=False)
def _datos(filtros: FiltrosOpinion) -> pd.DataFrame:
    c = recursos.contenedor()
    cat = c.repo_catalogo.obtener()
    regs = c.repo_opiniones.consultar(c.consultar_opiniones.resolver(filtros))
    filas = []
    for e in cat.eventos:
        if e.lat is None or e.lon is None:
            continue
        if filtros.disciplina_id and cat.disciplina_de_evento(e).id != filtros.disciplina_id:
            continue
        ops = [o for o in regs if o.evento_id == e.id]
        conteo = contar_por_sentimiento(ops)
        idx = indice_percepcion(conteo)
        filas.append({"evento_id": e.id, "Carrera": e.nombre, "País": e.pais, "Sede": e.sede, "lat": e.lat, "lon": e.lon,
                      "Opiniones": len(ops), "Índice": idx if idx is not None else 0.0,
                      "Índice (texto)": f"{idx:+.2f}" if idx is not None else "sin opiniones",
                      "Disciplina": cat.disciplina_de_evento(e).nombre})
    return pd.DataFrame(filas)


def render() -> None:
    st.subheader("🗺️ Mapa de percepción")
    c = recursos.contenedor()
    if sesion.actor_actual() is None and not c.consultar_opiniones.permitir_anonimos:
        st.info("🔐 Inicia sesión para ver el mapa.")
        return
    f = filtros_ui("m", con_sentimiento=False, con_evento=False)
    df = _datos(f)
    if df.empty:
        st.info("No hay carreras con esos filtros.")
        return
    df["Tamaño"] = 6 + df["Opiniones"] * 2.5
    fig = px.scatter_geo(df, lat="lat", lon="lon", size="Tamaño", color="Índice", hover_name="Carrera",
                         hover_data={"País": True, "Opiniones": True, "Índice (texto)": True, "lat": False, "lon": False,
                                     "Tamaño": False, "Índice": False},
                         color_continuous_scale=["#d6342c", "#8a8f98", "#2e9e5b"], range_color=(-1, 1),
                         custom_data=["evento_id"], projection="natural earth")
    fig.update_geos(showcountries=True, countrycolor="rgba(128,128,128,0.4)", showland=True,
                    landcolor="rgba(128,128,128,0.12)", bgcolor="rgba(0,0,0,0)", showocean=False)
    fig.update_layout(height=520, margin={"l": 0, "r": 0, "t": 10, "b": 0},
                      coloraxis_colorbar={"title": "Índice", "tickvals": [-1, 0, 1], "ticktext": ["−1", "0", "+1"]})
    st.caption("Color: índice de percepción (rojo −1 · gris 0 · verde +1). Tamaño: número de opiniones. "
               "Las carreras sin opiniones aparecen en gris y pequeñas. Selecciona un punto para ver su ficha.")
    evento = st.plotly_chart(fig, use_container_width=True, on_select="rerun", selection_mode="points", key="mapa_sel")
    puntos = (evento or {}).get("selection", {}).get("points", []) if isinstance(evento, dict) else \
        getattr(getattr(evento, "selection", None), "points", [])
    if puntos:
        ev_id = puntos[0].get("customdata", [None])[0]
        cat = recursos.catalogo()
        e = cat.evento(ev_id) if ev_id else None
        if e is not None:
            regs = c.repo_opiniones.consultar(f.con(evento_id=e.id))
            est = calcular(regs)
            with st.container(border=True):
                st.markdown(f"### {cat.disciplina_de_evento(e).icono} {e.nombre}")
                st.markdown(f"📍 {e.pais} · {e.sede}" + (" · 🏛️ histórica" if e.historico else ""))
                st.markdown(" · ".join(f"{etiqueta_sentimiento(s)}: {n}" for s, n in est.conteo.items()))
                st.page_link("paginas/consultar.py", label="🔎 Ver sus opiniones", query_params={"evento": e.id})
    aviso_cifras()


render()
