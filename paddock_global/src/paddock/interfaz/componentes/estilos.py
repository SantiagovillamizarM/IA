"""Tema visual «paddock»: pantalla de cronometraje, bandera a cuadros, pianos rojo/blanco y tipografía de carreras.

- Tipografía: Titillium Web (titulares y texto) y JetBrains Mono (cifras), de Google Fonts, con
  respaldo a fuentes del sistema si no hay conexión.
- Los paneles usan grises semitransparentes: funcionan con el tema oscuro (por defecto) y con el claro.
- La cabecera tiene su propio fondo oscuro, así que se ve igual en los dos temas.
- Los colores de sentimiento son los de ``COLOR_SENTIMIENTO`` y siempre van con emoji y texto.
"""

from __future__ import annotations

import streamlit as st

from paddock.dominio.enums import COLOR_SENTIMIENTO

ROJO = "#e10600"

_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Titillium+Web:ital,wght@0,400;0,600;0,700;0,900;1,700;1,900&family=JetBrains+Mono:wght@500;700&display=swap');

:root {
  --pg-rojo: #e10600;
  --pg-rojo-suave: rgba(225, 6, 0, 0.12);
  --pg-panel: rgba(128, 128, 128, 0.08);
  --pg-panel-fuerte: rgba(128, 128, 128, 0.14);
  --pg-borde: rgba(128, 128, 128, 0.24);
  --pg-texto-suave: rgba(128, 128, 128, 0.95);
  --pg-mono: 'JetBrains Mono', ui-monospace, 'Cascadia Mono', Consolas, monospace;
  --pg-titular: 'Titillium Web', 'Segoe UI', system-ui, sans-serif;
  --pg-cuadros: repeating-conic-gradient(#f4f4f4 0% 25%, #111 0% 50%);
  --pg-piano: repeating-linear-gradient(90deg, var(--pg-rojo) 0 22px, #f4f4f4 22px 44px);
}

/* ---------- tipografía general ---------- */
html, body, [data-testid="stMarkdownContainer"], [data-testid="stText"], [data-testid="stCaptionContainer"],
[data-testid="stWidgetLabel"], [data-testid="stSidebarNav"], button, input, textarea {
  font-family: var(--pg-titular);
}
/* Los iconos de Streamlit son ligaduras de Material Symbols: nunca cambiar su fuente */
[data-testid="stIconMaterial"], span[class*="material"], .material-symbols-rounded {
  font-family: "Material Symbols Rounded" !important;
}
[data-testid="stMainBlockContainer"] { padding-top: 1.2rem; max-width: 1280px; }
[data-testid="stHeader"] { background: transparent; }

/* Subtítulos de página (st.subheader) con franja roja tipo cartel de boxes */
[data-testid="stMainBlockContainer"] h3 {
  font-family: var(--pg-titular); font-weight: 900; text-transform: uppercase; letter-spacing: .04em;
  border-left: 5px solid var(--pg-rojo); padding: .05rem 0 .05rem .65rem; margin-top: .4rem;
}
[data-testid="stMainBlockContainer"] h4 {
  font-family: var(--pg-titular); font-weight: 700; letter-spacing: .02em;
}

/* ---------- cabecera tipo pantalla de cronometraje ---------- */
.pg-hero {
  position: relative; overflow: hidden; border-radius: 14px; margin: 0 0 1.1rem 0;
  background:
    radial-gradient(120% 140% at 100% 0%, rgba(225,6,0,.35) 0%, rgba(225,6,0,0) 55%),
    linear-gradient(115deg, #0b0c10 0%, #15171c 55%, #1d1f26 100%);
  border: 1px solid rgba(255,255,255,.08); color: #f2f3f5;
  box-shadow: 0 10px 30px rgba(0,0,0,.25);
}
.pg-hero::after {  /* piano rojo/blanco al pie */
  content: ""; position: absolute; left: 0; right: 0; bottom: 0; height: 7px; background: var(--pg-piano);
}
.pg-hero-cuadros {
  position: absolute; top: 0; right: 0; width: 210px; height: 100%; opacity: .16;
  background: var(--pg-cuadros); background-size: 26px 26px;
  -webkit-mask-image: linear-gradient(90deg, transparent 0%, #000 70%);
          mask-image: linear-gradient(90deg, transparent 0%, #000 70%);
}
.pg-hero-cuerpo { position: relative; display: flex; align-items: center; justify-content: space-between;
  gap: 1.5rem; padding: 1.15rem 1.6rem 1.35rem 1.6rem; flex-wrap: wrap; }
.pg-hero-kicker { font-family: var(--pg-mono); font-size: .72rem; letter-spacing: .22em; text-transform: uppercase;
  color: #ff5a50; margin-bottom: .15rem; }
.pg-hero-titulo { font-family: var(--pg-titular); font-weight: 900; font-style: italic; font-size: 2.6rem;
  line-height: 1; letter-spacing: .01em; text-transform: uppercase; color: #fff; }
.pg-hero-titulo span { color: var(--pg-rojo); }
.pg-hero-sub { font-size: .95rem; color: #c9ccd3; margin-top: .4rem; }
.pg-hero-compacta .pg-hero-cuerpo { padding: .75rem 1.3rem .95rem 1.3rem; }
.pg-hero-compacta .pg-hero-titulo { font-size: 1.75rem; }
.pg-hero-compacta .pg-hero-sub { display: none; }

/* Semáforo de salida: 5 luces. Verde = modelo listo; rojo = no disponible */
.pg-luces { display: flex; gap: .45rem; padding: .55rem .7rem; border-radius: 10px; background: #08090b;
  border: 1px solid rgba(255,255,255,.08); }
.pg-luz { width: 18px; height: 18px; border-radius: 50%; background: #2a2c31;
  box-shadow: inset 0 -2px 3px rgba(0,0,0,.6); }
.pg-luces-ok .pg-luz { background: #22c55e; box-shadow: 0 0 10px rgba(34,197,94,.75), inset 0 -2px 3px rgba(0,0,0,.4); }
.pg-luces-mal .pg-luz { background: #e10600; box-shadow: 0 0 10px rgba(225,6,0,.75), inset 0 -2px 3px rgba(0,0,0,.4); }
.pg-luces-txt { font-family: var(--pg-mono); font-size: .68rem; letter-spacing: .12em; text-transform: uppercase;
  color: #9ba0aa; text-align: center; margin-top: .35rem; }

/* ---------- paneles tipo torre de tiempos ---------- */
[data-testid="stMetric"] {
  background: var(--pg-panel); border: 1px solid var(--pg-borde); border-left: 4px solid var(--pg-rojo);
  border-radius: 10px; padding: .6rem .85rem;
}
[data-testid="stMetricLabel"] p { font-family: var(--pg-titular); font-weight: 700; text-transform: uppercase;
  letter-spacing: .06em; font-size: .78rem !important; opacity: .85; }
[data-testid="stMetricValue"] { font-family: var(--pg-mono); font-weight: 700; }

.pg-torre { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: .7rem; margin: .4rem 0 1rem; }
.pg-celda { position: relative; background: var(--pg-panel); border: 1px solid var(--pg-borde);
  border-radius: 10px; padding: .7rem .9rem .75rem; overflow: hidden; }
.pg-celda::before { content: ""; position: absolute; left: 0; top: 0; bottom: 0; width: 4px; background: var(--pg-rojo); }
.pg-celda-pos { font-family: var(--pg-mono); font-size: .7rem; opacity: .6; letter-spacing: .1em; }
.pg-celda-valor { font-family: var(--pg-mono); font-weight: 700; font-size: 1.9rem; line-height: 1.15; }
.pg-celda-etq { font-weight: 700; text-transform: uppercase; letter-spacing: .07em; font-size: .78rem; opacity: .85; }

/* Barra segmentada de sentimiento de la comunidad */
.pg-barra { display: flex; height: 30px; border-radius: 8px; overflow: hidden; border: 1px solid var(--pg-borde);
  margin: .3rem 0 .4rem; gap: 2px; background: var(--pg-borde); }
.pg-barra > div { display: flex; align-items: center; justify-content: center; color: #fff; font-weight: 700;
  font-size: .82rem; font-family: var(--pg-mono); white-space: nowrap; min-width: 0; }
.pg-leyenda { display: flex; flex-wrap: wrap; gap: .9rem; font-size: .85rem; opacity: .9; }
.pg-leyenda i { display: inline-block; width: 10px; height: 10px; border-radius: 2px; margin-right: .35rem; }

/* Tarjetas de disciplina y pasos */
.pg-rejilla { display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: .7rem; margin: .4rem 0 1rem; }
.pg-disc { background: var(--pg-panel); border: 1px solid var(--pg-borde); border-radius: 12px; padding: .8rem .9rem;
  transition: border-color .15s, transform .15s; }
.pg-disc:hover { border-color: var(--pg-rojo); transform: translateY(-2px); }
.pg-disc-ico { font-size: 1.6rem; line-height: 1; }
.pg-disc-nom { font-weight: 700; font-size: 1.02rem; margin-top: .35rem; }
.pg-disc-det { font-size: .8rem; opacity: .7; }
.pg-pasos { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: .8rem; margin: .4rem 0 1rem; }
.pg-paso { background: var(--pg-panel); border: 1px solid var(--pg-borde); border-radius: 12px; padding: .9rem 1rem; }
.pg-paso-num { display: inline-flex; align-items: center; justify-content: center; width: 30px; height: 30px;
  border-radius: 6px; background: var(--pg-rojo); color: #fff; font-family: var(--pg-mono); font-weight: 700; }
.pg-paso-tit { font-weight: 900; text-transform: uppercase; letter-spacing: .04em; margin: .5rem 0 .2rem; }
.pg-paso-txt { font-size: .9rem; opacity: .85; }

/* ---------- chips y tarjeta de resultado ---------- */
.pg-chip {display:inline-block;padding:0.1rem 0.6rem;border-radius:999px;font-size:0.8rem;font-weight:600;
  border:1px solid var(--pg-borde);margin:0 0.3rem 0.3rem 0;line-height:1.55;}
.pg-chip-evento {background:var(--pg-rojo-suave);border-color:rgba(225,6,0,.45);}
.pg-tarjeta {position:relative;border-radius:12px;margin:0.2rem 0 0.4rem 0;overflow:hidden;
  border:1px solid var(--pg-borde);background:var(--pg-panel);}
.pg-tarjeta-cab {display:flex;align-items:center;justify-content:space-between;gap:.6rem;padding:.5rem .95rem;
  font-family:var(--pg-titular);font-weight:900;text-transform:uppercase;letter-spacing:.06em;color:#fff;}
.pg-tarjeta-cab small {font-family:var(--pg-mono);font-weight:500;letter-spacing:.04em;text-transform:none;opacity:.9;}
.pg-tarjeta-cuerpo {padding:.7rem .95rem .75rem;}
.pg-tarjeta .pg-razon {opacity:0.95;font-size:.98rem;}
.pg-pie {font-size:0.78rem;opacity:0.72;margin-top:0.45rem;font-family:var(--pg-mono);}
.pg-aviso {font-size:0.8rem;opacity:0.75;}

/* ---------- controles ---------- */
[data-testid="stBaseButton-primary"], [data-testid="stBaseButton-primaryFormSubmit"] {
  background: var(--pg-rojo) !important; border-color: var(--pg-rojo) !important; font-weight: 700;
  text-transform: uppercase; letter-spacing: .05em;
}
[data-testid="stBaseButton-primary"]:hover, [data-testid="stBaseButton-primaryFormSubmit"]:hover {
  filter: brightness(1.12);
}
[data-testid="stChatMessage"] { border: 1px solid var(--pg-borde); border-radius: 12px; background: var(--pg-panel); }
[data-testid="stChatInput"] { border-radius: 12px; }
[data-testid="stChatInput"] textarea { font-family: var(--pg-titular); }
[data-testid="stExpander"] details { border-radius: 10px; border-color: var(--pg-borde); }
[data-testid="stDataFrame"] { border-radius: 10px; overflow: hidden; border: 1px solid var(--pg-borde); }

/* ---------- barra lateral ---------- */
[data-testid="stSidebar"] { border-right: 1px solid var(--pg-borde); }
[data-testid="stSidebar"]::before {  /* franja a cuadros en el borde superior */
  content: ""; display: block; height: 8px; background: var(--pg-cuadros); background-size: 8px 8px; opacity: .85;
}
[data-testid="stSidebarNav"] a span { font-family: var(--pg-titular); font-weight: 600; }
[data-testid="stSidebarNavSeparator"] { border-color: var(--pg-borde); }
.pg-lateral-tit { font-family: var(--pg-titular); font-weight: 900; text-transform: uppercase; letter-spacing: .08em;
  font-size: .85rem; border-left: 4px solid var(--pg-rojo); padding-left: .5rem; margin: .3rem 0 .4rem; }
.pg-ficha { background: var(--pg-panel); border: 1px solid var(--pg-borde); border-radius: 10px; padding: .55rem .7rem;
  font-size: .88rem; line-height: 1.45; }
.pg-ficha b { font-weight: 700; }
.pg-modelo { font-family: var(--pg-mono); font-size: .78rem; }

@media (max-width: 640px) {
  .pg-hero-titulo { font-size: 1.8rem; }
  .pg-hero-cuadros { width: 110px; }
  .pg-luces { display: none; }
}
/*REGLAS_SENTIMIENTO*/
</style>
"""


def inyectar() -> None:
    """Una sola inyección por ejecución, desde ``app.py``."""
    reglas = "\n".join(
        f".pg-s-{s} .pg-tarjeta-cab {{background:{c};}} .pg-s-{s} {{border-color:{c}66;}} "
        f".pg-chip-{s} {{background:{c}26;border-color:{c};}}"
        for s, c in COLOR_SENTIMIENTO.items()
    )
    st.markdown(_CSS.replace("/*REGLAS_SENTIMIENTO*/", reglas), unsafe_allow_html=True)
