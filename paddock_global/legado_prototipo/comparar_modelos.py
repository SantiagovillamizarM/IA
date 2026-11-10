"""Compara varios modelos sobre el conjunto de evaluación multilingüe.

Uso:
    python comparar_modelos.py                       # modelo principal y de comparación de .env
    python comparar_modelos.py ollama:qwen2.5:3b ollama:llama3.2:3b gemini:gemini-3.5-flash

Cada modelo se evalúa con TODOS los casos antes de pasar al siguiente, para no
cargar y descargar modelos locales de la GPU en cada opinión. El primer modelo
es la referencia para medir el acuerdo. Escribe:
    evidencias/comparacion_modelos.json  (lo lee la app)
    evidencias/comparacion_modelos.md    (para el informe)
"""

from __future__ import annotations

import json
import sys
from datetime import datetime

import almacenamiento as alm
from analisis import VERSION_PROMPT, verificar_modelo
from config import (
    EVIDENCIAS_DIR, RUTA_CARRERAS, RUTA_EVALUACION, RUTA_RESULTADOS_COMPARACION,
    cargar_config, config_con_modelo, etiqueta_modelo,
)
from evaluacion import cargar_conjunto, comparar, evaluar_modelo, metricas


def main() -> int:
    base = cargar_config()
    claves = sys.argv[1:] or [base.clave, f"ollama:{base.OLLAMA_MODEL_COMPARACION}"]
    cfgs = [config_con_modelo(base, c) for c in claves]
    claves = [c.clave for c in cfgs]  # normalizadas: «proveedor:modelo»
    if len(set(claves)) < 2:
        print("[ERROR] Indica al menos dos modelos distintos.")
        return 1
    for cfg in cfgs:
        ok, msg = verificar_modelo(cfg)
        if not ok:
            print(f"[ERROR] {cfg.clave}: {msg}")
            return 1

    casos = cargar_conjunto(RUTA_EVALUACION)
    carreras = {c["id"]: c for c in alm.cargar_carreras(RUTA_CARRERAS)}

    resultados: dict[str, list[dict]] = {}
    for cfg in cfgs:
        print(f"\n== {cfg.clave} ({len(casos)} casos, temperatura {cfg.OLLAMA_TEMPERATURE})")
        res = evaluar_modelo(cfg, casos, carreras, progreso=lambda k, n: print(f"  {k}/{n}", end="\r"))
        for f in res:
            marca = "OK " if f["obtenido"] == f["esperado"] else "DIF"
            print(f"  {marca} [{f['idioma']}] esperado={f['esperado']:<13} obtenido={f['obtenido']:<13} {f['texto'][:45]}")
        resultados[cfg.clave] = res

    ref = claves[0]
    informe = {
        "fecha": datetime.now().isoformat(timespec="seconds"),
        "version_prompt": VERSION_PROMPT,
        "temperatura": base.OLLAMA_TEMPERATURE,
        "modelos": claves,
        "referencia": ref,
        "metricas": {c: metricas(resultados[c]) for c in claves},
        "comparacion": {c: comparar(resultados[ref], resultados[c]) for c in claves[1:]},
        "resultados": resultados,
    }
    EVIDENCIAS_DIR.mkdir(exist_ok=True)
    RUTA_RESULTADOS_COMPARACION.write_text(json.dumps(informe, ensure_ascii=False, indent=2), encoding="utf-8")

    m = informe["metricas"]
    nombres = [etiqueta_modelo(c) for c in claves]
    with open(EVIDENCIAS_DIR / "comparacion_modelos.md", "w", encoding="utf-8") as f:
        f.write(f"# Comparación de modelos y evaluación por idioma\n\n"
                f"Prompt v{VERSION_PROMPT} · temperatura {base.OLLAMA_TEMPERATURE} · {informe['fecha']} · "
                f"{len(casos)} casos ficticios etiquetados a mano (`datos/conjunto_evaluacion.json`).\n\n")
        f.write("| Métrica | " + " | ".join(nombres) + " |\n|---|" + "---|" * len(claves) + "\n")

        def fila(titulo, valor):
            f.write(f"| {titulo} | " + " | ".join(valor(m[c]) for c in claves) + " |\n")

        fila("Casos evaluados", lambda x: f"{x['casos']}" + (f" (+{x['no_evaluados']} sin servicio)" if x["no_evaluados"] else ""))
        fila("Exactitud global", lambda x: f"{x['exactitud']}%")
        for i in m[ref]["por_idioma"]:
            fila(f"Exactitud `{i}` ({m[ref]['por_idioma'][i]['casos']} casos)",
                 lambda x, i=i: f"{x['por_idioma'].get(i, {}).get('exactitud', '—')}%")
        for k in m[ref]["por_categoria"]:
            fila(f"Acierto en «{k}» ({m[ref]['por_categoria'][k]['casos']} casos)",
                 lambda x, k=k: f"{x['por_categoria'].get(k, {}).get('exactitud', '—')}%")
        fila("Idioma detectado correctamente", lambda x: f"{x['idioma_detectado_ok']}%")
        fila("Respuestas inválidas (error)", lambda x: str(x["errores"]))
        fila("Tiempo medio por opinión", lambda x: f"{x['segundos_promedio']} s")

        f.write(f"\n## Acuerdo con {etiqueta_modelo(ref)}\n\n| Modelo | Acuerdo | Kappa de Cohen |\n|---|---|---|\n")
        for c, comp in informe["comparacion"].items():
            f.write(f"| {etiqueta_modelo(c)} | {comp['acuerdo']}% | {comp['kappa']} |\n")

        f.write("\n## Detalle por caso\n\n| Id | Idioma | Texto | Esperado | " + " | ".join(nombres)
                + " |\n|---|---|---|---|" + "---|" * len(claves) + "\n")
        for idx, caso in enumerate(casos):
            celdas = []
            for c in claves:
                r = resultados[c][idx]
                celdas.append(f"{r['obtenido']} {'✅' if r['obtenido'] == r['esperado'] else '❌'}")
            f.write(f"| {caso['id']} | {caso['idioma']} | {caso['texto']} | {caso['esperado']} | "
                    + " | ".join(celdas) + " |\n")

    print("\n" + "  ·  ".join(f"{c}: {m[c]['exactitud']}% ({m[c]['segundos_promedio']} s)" for c in claves))
    return 0


if __name__ == "__main__":
    sys.exit(main())
