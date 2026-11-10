"""Sección «Comparar modelos»: informe de la evaluación multilingüe y comparación en vivo."""

from __future__ import annotations

import json
import time

import pandas as pd
import streamlit as st

from analisis import EntradaInvalidaError, ErrorClasificacion, analizar_opinion, validar_texto
from config import (
    MODELOS_DISPONIBLES, RUTA_RESULTADOS_COMPARACION, ConfigOllama, config_con_modelo,
    etiqueta_modelo, hay_clave_google,
)
from ui.comun import EMOJI, NOMBRE_IDIOMA, cadena_de, texto_aspectos


def _normalizar(inf: dict) -> dict:
    """Admite el formato anterior del informe (modelo_a / modelo_b)."""
    if "modelos" in inf:
        return inf
    a, b = inf["modelo_a"], inf["modelo_b"]
    return {**inf, "modelos": [a, b], "referencia": a, "comparacion": {b: inf["comparacion"]}}


def _informe() -> None:
    st.markdown("#### 📋 Evaluación sobre el conjunto multilingüe")
    if not RUTA_RESULTADOS_COMPARACION.exists():
        st.info("Aún no hay resultados. Ejecuta en la terminal: `python comparar_modelos.py`.")
        return
    inf = _normalizar(json.loads(RUTA_RESULTADOS_COMPARACION.read_text(encoding="utf-8")))
    modelos, m, ref = inf["modelos"], inf["metricas"], inf["referencia"]
    nombre = {c: etiqueta_modelo(c) for c in modelos}
    st.caption(f"{m[ref]['casos']} opiniones ficticias etiquetadas a mano en "
               f"{', '.join(NOMBRE_IDIOMA.get(i, i) for i in m[ref]['por_idioma'])} · prompt v{inf['version_prompt']} · "
               f"temperatura {inf.get('temperatura', 0)} · {inf['fecha'].replace('T', ' ')}. "
               "Para actualizar: `python comparar_modelos.py modelo1 modelo2 …`")

    cols = st.columns(len(modelos))
    mejor = max((m[c]["exactitud"] or 0) for c in modelos)
    for col, c in zip(cols, modelos):
        col.metric(nombre[c], f"{m[c]['exactitud']}%", help="Exactitud global",
                   delta="mejor" if m[c]["exactitud"] == mejor else None, delta_color="off")
        col.caption(f"⏱️ {m[c]['segundos_promedio']} s por opinión · {m[c]['casos']} casos"
                    + (f" · ⚠️ {m[c].get('no_evaluados')} sin servicio" if m[c].get("no_evaluados") else ""))

    filas = []
    for i in m[ref]["por_idioma"]:
        filas.append({"Métrica": f"Idioma: {NOMBRE_IDIOMA.get(i, i)} ({m[ref]['por_idioma'][i]['casos']})",
                      **{nombre[c]: f"{m[c]['por_idioma'].get(i, {}).get('exactitud', '—')}%" for c in modelos}})
    for k in m[ref]["por_categoria"]:
        filas.append({"Métrica": f"Categoría «{k}» ({m[ref]['por_categoria'][k]['casos']})",
                      **{nombre[c]: f"{m[c]['por_categoria'].get(k, {}).get('exactitud', '—')}%" for c in modelos}})
    filas.append({"Métrica": "Idioma detectado", **{nombre[c]: f"{m[c]['idioma_detectado_ok']}%" for c in modelos}})
    filas.append({"Métrica": "Respuestas inválidas", **{nombre[c]: str(m[c]["errores"]) for c in modelos}})
    for c, comp in inf["comparacion"].items():
        filas.append({"Métrica": f"Acuerdo con {nombre[ref]} (kappa)",
                      **{nombre[x]: "—" for x in modelos}, nombre[c]: f"{comp['acuerdo']}% ({comp['kappa']})"})
    st.dataframe(pd.DataFrame(filas), width="stretch", hide_index=True)

    with st.expander("Detalle de todos los casos"):
        res = inf["resultados"]
        st.dataframe(pd.DataFrame([{
            "Idioma": caso["idioma"], "Opinión": caso["texto"], "Esperado": caso["esperado"],
            **{nombre[c]: ("✅ " if res[c][i]["obtenido"] == caso["esperado"] else "❌ ") + res[c][i]["obtenido"]
               for c in modelos},
        } for i, caso in enumerate(res[ref])]), width="stretch", hide_index=True)


def _comparacion_en_vivo(carrera_sel: dict, cfg: ConfigOllama) -> None:
    st.markdown(f"#### ⚡ Comparación en vivo · {carrera_sel['nombre']}")
    disponibles = [x["clave"] for x in MODELOS_DISPONIBLES
                   if x["clave"].startswith("ollama:") or hay_clave_google()]
    por_defecto = [cfg.clave] + [c for c in disponibles if c != cfg.clave][:1]
    elegidos = st.multiselect("Modelos a comparar (2 o 3)", disponibles, default=por_defecto,
                              format_func=etiqueta_modelo, max_selections=3, key="comp_modelos")
    st.caption(f"Todos usan la temperatura elegida en la barra lateral ({cfg.OLLAMA_TEMPERATURE:.1f}). "
               "No se guarda nada. Los modelos locales se turnan en la GPU, así que la primera vez tardan más.")
    texto = st.text_area("Opinión a comparar", key="comp_texto",
                         placeholder="Ej.: El trazado es una maravilla, pero la organización fue un caos")
    if not st.button("Comparar", type="primary", key="comp_boton"):
        return
    if len(elegidos) < 2:
        st.warning("Elige al menos dos modelos.")
        return
    try:
        texto = validar_texto(texto)
    except EntradaInvalidaError as e:
        st.warning(f"✋ {e}")
        return
    for col, clave in zip(st.columns(len(elegidos)), elegidos):
        c = config_con_modelo(cfg, clave, temperatura=cfg.OLLAMA_TEMPERATURE)
        with col:
            st.markdown(f"**{etiqueta_modelo(clave)}**")
            t0 = time.time()
            with st.spinner("Clasificando…"):
                try:
                    a = analizar_opinion(carrera_sel, texto, cfg=c, cadena=cadena_de(c))
                except ErrorClasificacion as e:
                    st.error(str(e))
                    continue
            st.markdown(f"### {EMOJI[a.sentimiento]} {a.sentimiento}" if a.es_pertinente else "### 🚫 no pertinente")
            st.write(a.razon)
            if a.aspectos:
                st.caption(texto_aspectos([x.model_dump() for x in a.aspectos]))
            st.caption(f"Idioma: {NOMBRE_IDIOMA.get(a.idioma, a.idioma)} · {time.time() - t0:.1f} s")


def render(carrera_sel: dict, cfg: ConfigOllama) -> None:
    st.subheader("Comparar modelos")
    _informe()
    st.divider()
    _comparacion_en_vivo(carrera_sel, cfg)
