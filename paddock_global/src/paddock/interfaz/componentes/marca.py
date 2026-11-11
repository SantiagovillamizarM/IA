"""Identidad visual: cabecera de cronometraje con semáforo de salida y logotipo de la barra lateral."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

RECURSOS = Path(__file__).resolve().parents[1] / "recursos"


def logotipo() -> None:
    """Logotipo arriba de la navegación (y su icono cuando la barra está plegada)."""
    st.logo(str(RECURSOS / "logo.svg"), icon_image=str(RECURSOS / "icono.svg"), size="large")


def cabecera(modelo_listo: bool, compacta: bool = False) -> None:
    """Pantalla de cronometraje. Las 5 luces se encienden en verde si el modelo está listo y en rojo si no."""
    estado = "ok" if modelo_listo else "mal"
    texto = "Modelo listo" if modelo_listo else "Modelo no disponible"
    luces = "".join('<div class="pg-luz"></div>' for _ in range(5))
    clase = "pg-hero pg-hero-compacta" if compacta else "pg-hero"
    html = f"""<div class="{clase}">
  <div class="pg-hero-cuadros"></div>
  <div class="pg-hero-cuerpo">
    <div>
      <div class="pg-hero-kicker">Análisis de sentimientos LangChain</div>
      <div class="pg-hero-titulo">Paddock <span>Global</span></div>
      <div class="pg-hero-sub">Opiniones del mundo de las carreras · Fórmula 1 · Resistencia · Rally · Dakar ·
        IndyCar · NASCAR · Fórmula E · MotoGP</div>
    </div>
    <div title="{texto}">
      <div class="pg-luces pg-luces-{estado}">{luces}</div>
      <div class="pg-luces-txt">{texto}</div>
    </div>
  </div>
</div>"""
    # Sin sangría ni líneas vacías: el Markdown trataría la sangría de 4 espacios como bloque de código.
    st.markdown(" ".join(linea.strip() for linea in html.splitlines()), unsafe_allow_html=True)
