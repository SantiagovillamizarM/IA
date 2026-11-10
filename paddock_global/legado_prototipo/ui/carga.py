"""Sección «Carga masiva»: clasificar muchas opiniones desde un CSV."""

from __future__ import annotations

import pandas as pd
import streamlit as st

import almacenamiento as alm
import carga_masiva as cm
from config import DATOS_DIR, ConfigOllama
from ui.comun import EMOJI, cadena_de

ESTADOS = {
    "guardada": "✅ guardada", "ya_existia": "↩️ ya existía", "no_pertinente": "🚫 no pertinente",
    "invalida": "✋ inválida", "error": "❌ error",
}


def render(carreras: list[dict], cfg: ConfigOllama) -> None:
    st.subheader("Carga masiva desde CSV")
    st.markdown(
        "El archivo necesita dos columnas: **`carrera`** (id como `c001` o el nombre exacto) y "
        f"**`opinion`**. Separador `,` o `;`. Máximo {cm.MAX_FILAS} filas. "
        "Subir el mismo archivo otra vez **no duplica** registros."
    )
    ejemplo = (DATOS_DIR / "ejemplo_carga.csv").read_bytes()
    st.download_button("⬇️ Descargar CSV de ejemplo", ejemplo, "ejemplo_carga.csv", "text/csv")

    archivo = st.file_uploader("Sube tu CSV", type=["csv"])
    if archivo is None:
        return
    try:
        filas = cm.leer_csv(archivo.getvalue(), carreras)
    except cm.CSVInvalidoError as e:
        st.error(f"❌ {e}")
        return

    validas = [f for f in filas if not f.error]
    st.dataframe(pd.DataFrame([{
        "Fila": f.numero,
        "Carrera": f.carrera["nombre"] if f.carrera else "—",
        "Opinión": f.texto,
        "Validación": f"✋ {f.error}" if f.error else "✔️ lista",
    } for f in filas]), width="stretch", hide_index=True)
    st.caption(f"{len(validas)} de {len(filas)} filas listas para clasificar · "
               f"tiempo estimado ≈ {len(validas) * 6} s (más ~1 min si el modelo no está cargado).")

    if not validas or not st.button(f"🚀 Clasificar {len(validas)} opiniones", type="primary"):
        return

    barra = st.progress(0.0, text="Preparando…")

    def progreso(k: int, n: int, f) -> None:
        barra.progress((k - 1) / n, text=f"Clasificando {k}/{n}: {f.texto[:60]}…")

    try:
        resultados = cm.procesar_filas(filas, cfg, cadena=cadena_de(cfg), progreso=progreso)
    except (alm.ArchivoOpinionesCorruptoError, alm.ErrorEscrituraOpiniones) as e:
        barra.empty()
        st.error(f"❌ Se detuvo la carga: {e}. Las filas ya guardadas se conservan.")
        return
    barra.progress(1.0, text="Terminado")

    resumen = {k: sum(r.estado == k for r in resultados) for k in ESTADOS}
    st.success(" · ".join(f"{ESTADOS[k]}: {v}" for k, v in resumen.items() if v))
    if any(r.estado == "error" for r in resultados) and len(resultados) < len(filas):
        st.warning("La carga se detuvo porque Ollama dejó de responder. Vuelve a subir el archivo: "
                   "las filas ya guardadas no se duplicarán.")
    df = pd.DataFrame([{
        "Fila": r.numero, "Carrera": r.carrera, "Opinión": r.opinion,
        "Estado": ESTADOS[r.estado],
        "Sentimiento": f"{EMOJI[r.sentimiento]} {r.sentimiento}" if r.sentimiento else "",
        "Detalle": r.razon,
    } for r in resultados])
    st.dataframe(df, width="stretch", hide_index=True)
    st.download_button("⬇️ Descargar resultados (CSV)", df.to_csv(index=False, sep=";").encode("utf-8-sig"),
                       "resultados_carga.csv", "text/csv")
