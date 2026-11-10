"""Sección «Consultar opiniones»: filtros, tabla, recuentos, descarga y corrección manual."""

from __future__ import annotations

import json

import pandas as pd
import streamlit as st

import almacenamiento as alm
from config import RUTA_OPINIONES, SENTIMIENTOS
from ui.comun import EMOJI, NOMBRE_IDIOMA, fecha_local, texto_aspectos


def _fila_tabla(r: dict) -> dict:
    final = alm.sentimiento_final(r)
    corregido = bool(r.get("sentimiento_corregido"))
    return {
        "Fecha": fecha_local(r["fecha_utc"]),
        "Carrera": r["carrera_nombre"],
        "Idioma": NOMBRE_IDIOMA.get(r.get("idioma") or "", "—"),
        "Opinión original": r["opinion_original"],
        "Sentimiento": f"{EMOJI.get(final, '')} {final}" + (" ✏️" if corregido else ""),
        "Modelo dijo": r["sentimiento"] if corregido else "",
        "Aspectos": texto_aspectos(r.get("aspectos")),
        "Razón": r["razon"],
        "Revisar": "⚠️" if r.get("alerta_revision") and not corregido else "",
    }


def _corregir(filtrados: list[dict]) -> None:
    with st.expander("✏️ Corregir la etiqueta de una opinión"):
        st.caption("La etiqueta del modelo se conserva; la corrección se guarda aparte y pasa a ser la "
                   "etiqueta vigente en filtros, recuentos, gráficas y ranking.")
        opciones = {r["id"]: r for r in filtrados}
        rid = st.selectbox(
            "Opinión", list(opciones),
            format_func=lambda i: (
                f"{'⚠️ ' if opciones[i].get('alerta_revision') and not opciones[i].get('sentimiento_corregido') else ''}"
                f"{opciones[i]['carrera_nombre']} · {alm.sentimiento_final(opciones[i])} · "
                f"{opciones[i]['opinion_original'][:70]}"
            ),
            key="corr_registro",
        )
        r = opciones[rid]
        st.markdown(f"> {r['opinion_original']}")
        st.caption(f"Modelo: **{r['sentimiento']}** — {r['razon']}")
        if r.get("alerta_revision"):
            st.caption(f"🔎 {r['alerta_revision']}")
        if r.get("sentimiento_corregido"):
            st.caption(f"Corrección actual: **{r['sentimiento_corregido']}** — {r.get('nota_correccion') or 'sin nota'}")
        nuevo = st.radio("Etiqueta correcta", SENTIMIENTOS, horizontal=True,
                         index=SENTIMIENTOS.index(alm.sentimiento_final(r)),
                         format_func=lambda s: f"{EMOJI[s]} {s}", key=f"corr_valor_{rid}")
        nota = st.text_input("Motivo (opcional)", key=f"corr_nota_{rid}",
                             placeholder="Ej.: tiene un elogio y una crítica, es mixto")
        if st.button("Guardar corrección", key="corr_guardar"):
            try:
                alm.corregir_opinion(RUTA_OPINIONES, rid, nuevo, nota)
            except (alm.ArchivoOpinionesCorruptoError, alm.ErrorEscrituraOpiniones,
                    alm.RegistroNoEncontradoError) as e:
                st.error(f"❌ No se guardó la corrección: {e}")
            else:
                st.toast("✅ Corrección guardada" if nuevo != r["sentimiento"]
                         else "↩️ Se restauró la etiqueta del modelo")
                st.rerun()


def render(carreras_por_id: dict[str, dict]) -> None:
    st.subheader("Consultar opiniones guardadas")
    try:
        registros = alm.cargar_opiniones(RUTA_OPINIONES)["opiniones"]
    except alm.ArchivoOpinionesCorruptoError as e:
        st.error(f"❌ {e}")
        return

    idiomas = sorted({r.get("idioma") for r in registros if r.get("idioma")})
    c1, c2, c3 = st.columns(3)
    filtro_carrera = c1.selectbox(
        "Carrera", ["__todas__", *carreras_por_id],
        format_func=lambda cid: "Todas" if cid == "__todas__" else carreras_por_id[cid]["nombre"],
        key="filtro_carrera",
    )
    filtro_sent = c2.selectbox(
        "Sentimiento", ["__todos__", *SENTIMIENTOS],
        format_func=lambda s: "Todos" if s == "__todos__" else f"{EMOJI[s]} {s}",
        key="filtro_sentimiento",
    )
    filtro_idioma = c3.selectbox(
        "Idioma", ["__todos__", *idiomas],
        format_func=lambda i: "Todos" if i == "__todos__" else NOMBRE_IDIOMA.get(i, i),
        key="filtro_idioma",
    )
    solo_alertas = st.checkbox("Solo opiniones con revisión sugerida (⚠️) sin corregir", key="filtro_alertas")

    filtrados = alm.consultar_opiniones(
        registros,
        carrera_id=None if filtro_carrera == "__todas__" else filtro_carrera,
        sentimiento=None if filtro_sent == "__todos__" else filtro_sent,
        idioma=None if filtro_idioma == "__todos__" else filtro_idioma,
        solo_alertas=solo_alertas,
    )
    conteo = alm.contar_por_sentimiento(filtrados)
    cols = st.columns(5)
    cols[0].metric("Total", len(filtrados))
    for col, s in zip(cols[1:], SENTIMIENTOS):
        col.metric(f"{EMOJI[s]} {s.capitalize()}", conteo[s])

    if not filtrados:
        st.info("No hay opiniones con esos filtros.")
        return

    st.dataframe(pd.DataFrame([_fila_tabla(r) for r in filtrados]), width="stretch", hide_index=True)
    st.download_button(
        "⬇️ Descargar resultados filtrados (JSON)",
        data=json.dumps(filtrados, ensure_ascii=False, indent=2),
        file_name="opiniones_filtradas.json",
        mime="application/json",
    )
    _corregir(filtrados)
