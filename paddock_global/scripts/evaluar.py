"""Reclasifica el conjunto de opiniones revisadas por humanos con otro proveedor, modelo o prompt, SIN guardar
nada en «opiniones», y escribe un informe en evidencias/metricas/.

Uso:
    .venv\\Scripts\\python scripts\\evaluar.py --proveedor ollama --version-prompt 2.0
    .venv\\Scripts\\python scripts\\evaluar.py --proveedor gemini --modelo gemini-2.5-flash --version-prompt 2.0 --pausa 13

Requiere STORAGE_BACKEND=sql y opiniones revisadas en «🛡️ Moderación» (etiquetas humanas reales).
"""

from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime

from paddock.adaptadores.llm.cadena import crear_clasificador
from paddock.aplicacion.calidad import evaluar_pares
from paddock.config import EVIDENCIAS, Ajustes
from paddock.contenedor import crear_contenedor
from paddock.dominio.entidades import FiltrosOpinion
from paddock.dominio.enums import SENTIMIENTOS
from paddock.dominio.errores import CuotaExcedidaError, ErrorClasificacion


def _f(v: float | None) -> str:
    return "—" if v is None else f"{v:.3f}"


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--proveedor", choices=["ollama", "gemini"], required=True)
    p.add_argument("--version-prompt", choices=["1.0", "2.0"], required=True)
    p.add_argument("--modelo", default=None)
    p.add_argument("--pausa", type=float, default=None)
    a = p.parse_args()
    base = Ajustes()
    if base.STORAGE_BACKEND != "sql":
        print("Requiere STORAGE_BACKEND=sql.")
        return 2
    cambios: dict[str, object] = {"LLM_PROVIDER": a.proveedor, "VERSION_PROMPT": a.version_prompt}
    if a.modelo:
        cambios["GEMINI_MODEL" if a.proveedor == "gemini" else "OLLAMA_MODEL"] = a.modelo
    aj = base.model_copy(update=cambios)
    c = crear_contenedor(aj)
    pausa = a.pausa if a.pausa is not None else (13.0 if a.proveedor == "gemini" else 0.0)
    revisadas = c.repo_opiniones.consultar(FiltrosOpinion(solo_revisadas=True, incluir_ocultas=True))
    if not revisadas:
        print("No hay opiniones revisadas por humanos. Revisa al menos 30 en «🛡️ Moderación» y vuelve a ejecutar.")
        return 1
    cat = c.repo_catalogo.obtener()
    clf = crear_clasificador(aj, c.jerga_para, version_prompt=a.version_prompt)
    pares_nuevos, pares_original, filas, errores = [], [], [], 0
    for i, o in enumerate(revisadas):
        ev = cat.evento(o.evento_id)
        if ev is None or o.revision is None:
            continue
        disc = cat.disciplina_de_evento(ev)
        if i and pausa:
            time.sleep(pausa)
        try:
            r = clf.clasificar(texto=o.opinion_original, carrera=ev.nombre, disciplina=disc.nombre,
                               disciplina_id=disc.id, edicion=o.edicion_anio)
            nuevo = r.analisis.sentimiento if r.analisis.es_pertinente else "no_pertinente"
        except CuotaExcedidaError:
            print("Cuota excedida: se detiene la evaluación con lo obtenido hasta ahora.")
            break
        except ErrorClasificacion as e:
            nuevo, errores = f"error:{type(e).__name__}", errores + 1
        humano = o.revision.sentimiento
        pares_original.append((humano, o.sentimiento))
        if nuevo in SENTIMIENTOS:
            pares_nuevos.append((humano, nuevo))
        filas.append((o.opinion_original, humano, o.sentimiento, nuevo))
        print(f"{'✅' if nuevo == humano else '❌'} humano={humano:8} original={o.sentimiento:8} nuevo={nuevo}")
    nuevo_inf, orig_inf = evaluar_pares(pares_nuevos), evaluar_pares(pares_original)
    nombre = f"evaluacion_{aj.modelo_activo.replace('/', '_').replace(':', '-')}_{a.version_prompt}.md"
    salida = EVIDENCIAS / "metricas" / nombre
    salida.parent.mkdir(parents=True, exist_ok=True)
    lineas = [f"# Evaluación sobre {len(filas)} opiniones revisadas por humanos",
              "", f"{datetime.now():%Y-%m-%d %H:%M} · candidato: `{aj.modelo_activo}` · prompt {a.version_prompt}. "
              "No se guardó nada en «opiniones».", "",
              "| Métrica | Etiqueta original guardada | Candidato |", "| --- | --- | --- |",
              f"| Exactitud | {_f(orig_inf.exactitud)} | {_f(nuevo_inf.exactitud)} |",
              f"| F1 macro | {_f(orig_inf.f1_macro)} | {_f(nuevo_inf.f1_macro)} |",
              f"| n comparables | {orig_inf.n} | {nuevo_inf.n} (no pertinentes o errores: {len(filas) - nuevo_inf.n}) |", ""]
    lineas += ["| Categoría | Precisión | Recall | F1 | Soporte |", "| --- | --- | --- | --- | --- |"]
    lineas += [f"| {s} | {_f(m.precision)} | {_f(m.recall)} | {_f(m.f1)} | {m.soporte} |"
               for s, m in nuevo_inf.por_clase.items()]
    lineas += ["", "| Opinión | Humano | Original | Candidato |", "| --- | --- | --- | --- |"]
    lineas += [f"| {t.replace('|', '/')} | {h} | {o} | {n} |" for t, h, o, n in filas]
    salida.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    print(f"\nInforme: {salida}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
