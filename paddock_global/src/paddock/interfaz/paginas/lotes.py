"""Página «📥 Lotes» (moderador y admin): subir un CSV, encolarlo y seguir el progreso del worker."""

from __future__ import annotations

import io
from datetime import timedelta

import pandas as pd
import streamlit as st

from paddock.aplicacion.clasificar_lote import COLUMNAS, MAX_FILAS
from paddock.dominio.enums import Rol
from paddock.dominio.errores import ErrorPaddock
from paddock.interfaz.componentes import recursos, sesion

PLANTILLA = "evento_id,edicion_anio,opinion\nev-res-lemans,2026,La salida al amanecer fue espectacular\n"


def _csv(filas: list[dict]) -> bytes:
    buf = io.StringIO()
    pd.DataFrame(filas).to_csv(buf, index=False)
    return buf.getvalue().encode("utf-8-sig")


@st.fragment(run_every=timedelta(seconds=4))
def _progreso(actor) -> None:  # type: ignore[no-untyped-def]
    c = recursos.contenedor()
    trabajos = c.clasificar_lote.listar(actor)
    if not trabajos:
        st.info("Todavía no hay lotes.")
        return
    for t in trabajos[:10]:
        hechas = t.procesadas + t.fallidas
        with st.container(border=True):
            st.markdown(f"**Lote** `{t.id[:8]}` · {t.creado_utc[:16]} · estado: **{t.estado}**")
            st.progress(hechas / t.total if t.total else 0.0,
                        text=f"{hechas}/{t.total} filas · {t.procesadas} procesadas · {t.fallidas} con error")
            if t.resultados:
                filas = {f["numero"]: f for f in t.filas}
                res = [{"fila": r["fila"], "evento_id": filas.get(r["fila"], {}).get("evento_id"),
                        "opinion": filas.get(r["fila"], {}).get("opinion"), "estado": r["estado"],
                        "sentimiento": r.get("sentimiento"), "registro_id": r.get("registro_id")} for r in t.resultados]
                col1, col2 = st.columns(2)
                col1.download_button("⬇️ Resultado (CSV)", _csv(res), file_name=f"lote_{t.id[:8]}_resultado.csv",
                                     key=f"res_{t.id}")
                if t.errores:
                    col2.download_button("⬇️ Filas fallidas (CSV)", _csv(t.errores),
                                         file_name=f"lote_{t.id[:8]}_errores.csv", key=f"err_{t.id}")


def render() -> None:
    st.subheader("📥 Clasificación por lotes")
    c = recursos.contenedor()
    actor = sesion.actor_actual()
    if not c.modo_sql or actor is None or actor.rol not in (Rol.MODERADOR.value, Rol.ADMIN.value):
        st.error("⛔ Acceso denegado: esta página es solo para moderadores y administradores.")
        return
    st.markdown(f"Sube un CSV UTF-8 con las columnas `{', '.join(COLUMNAS)}` (máximo {MAX_FILAS} filas y 1 MB). "
                "Se valida **todo** antes de encolar. El worker procesa el lote respetando los límites de uso; una "
                "fila con error no detiene el lote y nunca se guarda como neutra.")
    st.download_button("Plantilla CSV", PLANTILLA.encode("utf-8-sig"), file_name="plantilla_lote.csv", mime="text/csv")
    archivo = st.file_uploader("Archivo CSV", type=["csv"], accept_multiple_files=False)
    if archivo is not None and st.button("Validar y encolar", type="primary"):
        try:
            trabajo, val = c.clasificar_lote.crear(actor, archivo.getvalue())
        except ErrorPaddock as e:
            st.error(str(e))
        else:
            if trabajo is None:
                st.error(f"El archivo tiene {len(val.errores)} error(es). No se encoló nada.")
                st.dataframe(pd.DataFrame(val.errores), hide_index=True, use_container_width=True)
            else:
                st.success(f"Lote encolado con {trabajo.total} filas. El worker lo procesará en segundo plano "
                           "(en local: `python -m paddock.worker.procesador_lotes`).")
    st.markdown("#### Mis lotes")
    _progreso(actor)


render()
