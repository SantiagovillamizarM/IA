"""Elementos compartidos por las secciones: colores, emojis, cadena en caché y gráficas."""

from __future__ import annotations

from datetime import datetime

import altair as alt
import pandas as pd
import streamlit as st

from analisis import crear_cadena
from config import SENTIMIENTOS, ConfigOllama

EMOJI = {"positivo": "😀", "negativo": "😞", "neutro": "😐", "mixto": "🤔"}
EMOJI_ASPECTO = {"positivo": "👍", "negativo": "👎", "neutro": "•"}
NOMBRE_ASPECTO = {
    "trazado": "Trazado", "organizacion": "Organización", "clima": "Clima",
    "reglamento": "Reglamento", "ambiente": "Ambiente", "transmision": "Transmisión",
    "competencia": "Competencia", "logistica": "Logística",
}
NOMBRE_IDIOMA = {
    "es": "Español", "en": "Inglés", "fr": "Francés", "de": "Alemán",
    "pt": "Portugués", "it": "Italiano", "otro": "Otro",
}

# Paletas categóricas validadas (scripts/validate_palette.js, fondo claro y oscuro):
# un color fijo por sentimiento, nunca por rango. La app sigue el tema del sistema.
TEMAS = {
    "light": {
        "color": {"positivo": "#1baf7a", "negativo": "#e34948", "neutro": "#2a78d6", "mixto": "#eda100"},
        "superficie": "#ffffff", "rejilla": "#e1e0d9", "tinta": "#52514e",
    },
    "dark": {
        "color": {"positivo": "#199e70", "negativo": "#d03b3b", "neutro": "#3987e5", "mixto": "#c98500"},
        "superficie": "#0e1117", "rejilla": "#2c2c2a", "tinta": "#c3c2b7",
    },
}


def tema_actual() -> dict:
    """Paleta del tema que está viendo el usuario (claro u oscuro)."""
    try:
        tipo = st.context.theme.type or "light"
    except Exception:
        tipo = "light"
    return TEMAS.get(tipo, TEMAS["light"])


@st.cache_resource(show_spinner=False)
def obtener_cadena(proveedor: str, base_url: str, modelo: str, temperatura: float):
    """Una cadena prompt | modelo por combinación proveedor/modelo/temperatura."""
    return crear_cadena(ConfigOllama(base_url, modelo, temperatura, PROVEEDOR=proveedor))


def cadena_de(cfg: ConfigOllama):
    return obtener_cadena(cfg.PROVEEDOR, cfg.OLLAMA_BASE_URL, cfg.OLLAMA_MODEL, cfg.OLLAMA_TEMPERATURE)


def fecha_local(iso: str) -> str:
    return datetime.fromisoformat(iso).astimezone().strftime("%Y-%m-%d %H:%M")


def texto_aspectos(aspectos: list[dict] | None) -> str:
    return " · ".join(
        f"{EMOJI_ASPECTO[a['sentimiento']]} {NOMBRE_ASPECTO.get(a['aspecto'], a['aspecto'])}"
        for a in (aspectos or [])
    )


def grafica_apilada(df: pd.DataFrame, categoria: str, titulo_eje: str, porcentaje: bool,
                    dominio: tuple[str, ...] = SENTIMIENTOS) -> alt.Chart:
    """Barras horizontales apiladas por sentimiento, con tooltip y leyenda."""
    t = tema_actual()
    orden_cat = (df.groupby(categoria)["n"].sum().sort_values(ascending=False).index.tolist())
    df = df.copy()
    df["orden"] = df["sentimiento"].map({s: i for i, s in enumerate(dominio)})
    df["porcentaje"] = df["n"] / df.groupby(categoria)["n"].transform("sum")
    alto = max(140, 34 * len(orden_cat) + 60)
    return (
        alt.Chart(df)
        .mark_bar(stroke=t["superficie"], strokeWidth=2, height={"band": 0.7})
        .encode(
            y=alt.Y(f"{categoria}:N", sort=orden_cat, title=None,
                    axis=alt.Axis(labelLimit=220, labelColor=t["tinta"], ticks=False, domain=False)),
            x=alt.X("n:Q", stack="normalize" if porcentaje else "zero", title=titulo_eje,
                    axis=alt.Axis(format="%" if porcentaje else "d", tickMinStep=1,
                                  gridColor=t["rejilla"], labelColor=t["tinta"], titleColor=t["tinta"], domain=False)),
            color=alt.Color("sentimiento:N",
                            scale=alt.Scale(domain=list(dominio), range=[t["color"][s] for s in dominio]),
                            legend=alt.Legend(orient="top", title=None, labelColor=t["tinta"])),
            order=alt.Order("orden:Q"),
            tooltip=[
                alt.Tooltip(f"{categoria}:N", title=categoria.capitalize()),
                alt.Tooltip("sentimiento:N", title="Sentimiento"),
                alt.Tooltip("n:Q", title="Opiniones"),
                alt.Tooltip("porcentaje:Q", title="% del total", format=".0%"),
            ],
        )
        .properties(height=alto)
        .configure_view(stroke=None)
    )
