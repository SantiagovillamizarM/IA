"""Gráficos Plotly reutilizables. Todos leen de los repositorios (nunca del modelo).

Colores fijos por sentimiento + codificación secundaria (emoji y nombre en leyenda, etiquetas y
tooltips; separación de 2 px entre segmentos): el par verde/rojo no se distingue bien con
deuteranopía (ΔE 6,0 medido), así que la identidad nunca depende solo del color.
"""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from paddock.dominio.enums import COLOR_SENTIMIENTO, EMOJI_SENTIMIENTO, SENTIMIENTOS

NOMBRE = {s: f"{EMOJI_SENTIMIENTO[s]} {s.capitalize()}" for s in SENTIMIENTOS}
COLORES = {NOMBRE[s]: COLOR_SENTIMIENTO[s] for s in SENTIMIENTOS}
NOTA = "Solo opiniones registradas en Paddock Global."


def _estilo(fig: go.Figure, alto: int = 360) -> go.Figure:
    fig.update_layout(height=alto, margin={"l": 8, "r": 8, "t": 40, "b": 8}, legend_title_text="",
                      hoverlabel={"namelength": -1}, bargap=0.25)
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(gridcolor="rgba(128,128,128,0.18)")
    return fig


def barras_distribucion(conteo: dict[str, int], titulo: str = "Distribución") -> go.Figure:
    df = pd.DataFrame({"Sentimiento": [NOMBRE[s] for s in SENTIMIENTOS], "Opiniones": [conteo[s] for s in SENTIMIENTOS]})
    fig = px.bar(df, x="Sentimiento", y="Opiniones", color="Sentimiento", color_discrete_map=COLORES, text="Opiniones",
                 title=titulo)
    fig.update_traces(marker_line_width=0, textposition="outside", cliponaxis=False)
    return _estilo(fig, 300).update_layout(showlegend=False)


def lineas_semanales(semanal: dict[str, dict[str, int]]) -> go.Figure:
    filas = [{"Semana": sem, "Sentimiento": NOMBRE[s], "Opiniones": c[s]} for sem, c in semanal.items() for s in SENTIMIENTOS]
    df = pd.DataFrame(filas)
    fig = px.line(df, x="Semana", y="Opiniones", color="Sentimiento", color_discrete_map=COLORES, markers=True,
                  title="Evolución semanal por sentimiento", category_orders={"Sentimiento": list(COLORES)})
    fig.update_traces(line_width=2, marker_size=8)
    # Semanas como categorías: con pocas semanas un eje temporal continuo muestra milisegundos.
    fig.update_xaxes(type="category", title="Semana (lunes)")
    fig.update_layout(hovermode="x unified")
    return _estilo(fig)


def barras_100(por_grupo: dict[str, dict[str, int]], etiquetas: dict[str, str], titulo: str) -> go.Figure:
    filas = []
    for g, c in por_grupo.items():
        total = sum(c.values()) or 1
        for s in SENTIMIENTOS:
            filas.append({"Grupo": etiquetas.get(g, g), "Sentimiento": NOMBRE[s], "Porcentaje": 100 * c[s] / total,
                          "Opiniones": c[s]})
    df = pd.DataFrame(filas)
    fig = px.bar(df, y="Grupo", x="Porcentaje", color="Sentimiento", orientation="h", color_discrete_map=COLORES,
                 category_orders={"Sentimiento": list(COLORES)}, hover_data={"Opiniones": True, "Porcentaje": ":.0f"},
                 text=df["Porcentaje"].map(lambda v: f"{v:.0f}%" if v >= 12 else ""), title=titulo)
    fig.update_traces(marker_line_width=2, marker_line_color="rgba(21,23,28,1)", textposition="inside")
    fig.update_layout(barmode="stack", xaxis_title="% de opiniones", yaxis_title="")
    return _estilo(fig, max(260, 60 + 42 * len(por_grupo)))


def mapa_calor_aspectos(matriz: dict[str, dict[str, int]], etiquetas: dict[str, str]) -> go.Figure:
    filas = [a for a, c in matriz.items() if sum(c.values())]
    if not filas:
        filas = list(matriz)
    cols = ["positivo", "negativo", "neutro"]
    z = [[matriz[a][s] for s in cols] for a in filas]
    fig = px.imshow(z, x=[NOMBRE[s] for s in cols], y=[etiquetas.get(a, a) for a in filas], text_auto=True,
                    color_continuous_scale=["#1d2330", "#24507d", "#2f6fae"], aspect="auto",
                    title="Aspectos valorados × sentimiento (número de menciones)")
    fig.update_layout(coloraxis_showscale=False)
    fig.update_traces(textfont_color="#eef0f3")  # escala oscura: el texto claro se lee en todas las celdas
    return _estilo(fig, max(280, 50 + 32 * len(filas)))


def barras_entidades(entidades: list[tuple[str, int]]) -> go.Figure:
    df = pd.DataFrame(entidades, columns=["Entidad", "Menciones"]).iloc[::-1]
    fig = px.bar(df, x="Menciones", y="Entidad", orientation="h", text="Menciones",
                 title="Top 10 de pilotos, equipos y marcas mencionados")
    fig.update_traces(marker_color="#6fa8dc", marker_line_width=0, textposition="outside", cliponaxis=False,
                      width=0.6 if len(df) > 2 else 0.35)
    return _estilo(fig, max(200, 60 + 30 * len(df)))
