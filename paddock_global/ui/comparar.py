"""Sección «Comparar modelos»: comparación en vivo y resultados de la evaluación multilingüe."""

from __future__ import annotations

import json
import time

import pandas as pd
import streamlit as st

from analisis import ErrorClasificacion, analizar_opinion, validar_texto, EntradaInvalidaError
from config import RUTA_RESULTADOS_COMPARACION, ConfigOllama, config_con_modelo
from ui.comun import EMOJI, NOMBRE_IDIOMA, cadena_de, texto_aspectos


def _comparacion_en_vivo(carrera_sel: dict, cfg: ConfigOllama) -> None:
    modelos = (cfg.OLLAMA_MODEL, cfg.OLLAMA_MODEL_COMPARACION)
    st.markdown(f"#### ⚡ Comparación en vivo · {carrera_sel['nombre']}")
    st.caption(f"Clasifica la misma opinión con **{modelos[0]}** y **{modelos[1]}**. No se guarda nada. "
               "La primera vez cada modelo tarda en cargarse; en una GPU de 3 GB se turnan.")
    texto = st.text_area("Opinión a comparar", key="comp_texto",
                         placeholder="Ej.: El trazado es una maravilla, pero la organización fue un caos")
    if not st.button("Comparar", type="primary", key="comp_boton"):
        return
    try:
        texto = validar_texto(texto)
    except EntradaInvalidaError as e:
        st.warning(f"✋ {e}")
        return
    cols = st.columns(2)
    for col, modelo in zip(cols, modelos):
        c = config_con_modelo(cfg, modelo)
        with col:
            st.markdown(f"**{modelo}**")
            t0 = time.time()
            with st.spinner("Clasificando…"):
                try:
                    a = analizar_opinion(carrera_sel, texto, cfg=c, cadena=cadena_de(c))
                except ErrorClasificacion as e:
                    st.error(str(e))
                    continue
            if a.es_pertinente:
                st.markdown(f"### {EMOJI[a.sentimiento]} {a.sentimiento}")
            else:
                st.markdown("### 🚫 no pertinente")
            st.write(a.razon)
            if a.aspectos:
                st.caption(texto_aspectos([x.model_dump() for x in a.aspectos]))
            st.caption(f"Idioma: {NOMBRE_IDIOMA.get(a.idioma, a.idioma)} · {time.time() - t0:.1f} s")


def _informe() -> None:
    st.markdown("#### 📋 Evaluación sobre el conjunto multilingüe")
    if not RUTA_RESULTADOS_COMPARACION.exists():
        st.info("Aún no hay resultados. Ejecuta en la terminal: `python comparar_modelos.py` (~5 min).")
        return
    inf = json.loads(RUTA_RESULTADOS_COMPARACION.read_text(encoding="utf-8"))
    a, b = inf["modelo_a"], inf["modelo_b"]
    ma, mb = inf["metricas"][a], inf["metricas"][b]
    st.caption(f"{ma['casos']} opiniones ficticias etiquetadas a mano en "
               f"{', '.join(NOMBRE_IDIOMA.get(i, i) for i in ma['por_idioma'])} · prompt v{inf['version_prompt']} · "
               f"{inf['fecha'].replace('T', ' ')} · para actualizar: `python comparar_modelos.py`")

    c = st.columns(4)
    c[0].metric(f"Exactitud {a}", f"{ma['exactitud']}%")
    c[1].metric(f"Exactitud {b}", f"{mb['exactitud']}%", delta=f"{mb['exactitud'] - ma['exactitud']:+.1f} pts")
    c[2].metric("Acuerdo entre modelos", f"{inf['comparacion']['acuerdo']}%")
    c[3].metric("Kappa de Cohen", inf["comparacion"]["kappa"],
                help="Acuerdo corregido por azar: 1 = total, 0 = el que se esperaría por casualidad.")

    filas = [{"Métrica": f"Idioma: {NOMBRE_IDIOMA.get(i, i)} ({ma['por_idioma'][i]['casos']} casos)",
              a: f"{ma['por_idioma'][i]['exactitud']}%", b: f"{mb['por_idioma'][i]['exactitud']}%"}
             for i in ma["por_idioma"]]
    filas += [{"Métrica": f"Categoría «{k}» ({ma['por_categoria'][k]['casos']} casos)",
               a: f"{ma['por_categoria'][k]['exactitud']}%", b: f"{mb['por_categoria'][k]['exactitud']}%"}
              for k in ma["por_categoria"]]
    filas += [
        {"Métrica": "Idioma detectado correctamente", a: f"{ma['idioma_detectado_ok']}%", b: f"{mb['idioma_detectado_ok']}%"},
        {"Métrica": "Respuestas inválidas", a: str(ma["errores"]), b: str(mb["errores"])},
        {"Métrica": "Tiempo medio por opinión", a: f"{ma['segundos_promedio']} s", b: f"{mb['segundos_promedio']} s"},
    ]
    st.dataframe(pd.DataFrame(filas), width="stretch", hide_index=True)

    with st.expander(f"Casos en que discrepan ({len(inf['comparacion']['desacuerdos'])})"):
        st.dataframe(pd.DataFrame([{
            "Idioma": d["idioma"], "Opinión": d["texto"], "Esperado": d["esperado"], a: d["modelo_a"], b: d["modelo_b"],
        } for d in inf["comparacion"]["desacuerdos"]]), width="stretch", hide_index=True)
    with st.expander("Detalle de todos los casos"):
        st.dataframe(pd.DataFrame([{
            "Idioma": x["idioma"], "Opinión": x["texto"], "Esperado": x["esperado"],
            a: ("✅ " if x["obtenido"] == x["esperado"] else "❌ ") + x["obtenido"],
            b: ("✅ " if y["obtenido"] == y["esperado"] else "❌ ") + y["obtenido"],
        } for x, y in zip(inf["resultados"][a], inf["resultados"][b])]), width="stretch", hide_index=True)


def render(carrera_sel: dict, cfg: ConfigOllama) -> None:
    st.subheader("Comparar modelos")
    _informe()
    st.divider()
    _comparacion_en_vivo(carrera_sel, cfg)
