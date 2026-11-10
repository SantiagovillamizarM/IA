"""Compara dos modelos de Ollama sobre el conjunto de evaluación multilingüe.

Uso:
    python comparar_modelos.py                          # modelos de .env
    python comparar_modelos.py qwen2.5:3b llama3.2:3b   # modelos explícitos

Primero evalúa TODOS los casos con el modelo A y luego con el B, para no cargar
y descargar modelos de la GPU en cada opinión. Escribe:
    evidencias/comparacion_modelos.json  (lo lee la app)
    evidencias/comparacion_modelos.md    (para el informe)
"""

from __future__ import annotations

import json
import sys
from datetime import datetime

import almacenamiento as alm
from analisis import VERSION_PROMPT, verificar_ollama
from config import (
    EVIDENCIAS_DIR, RUTA_CARRERAS, RUTA_EVALUACION, RUTA_RESULTADOS_COMPARACION,
    cargar_config, config_con_modelo,
)
from evaluacion import cargar_conjunto, comparar, evaluar_modelo, metricas


def main() -> int:
    base = cargar_config()
    modelo_a = sys.argv[1] if len(sys.argv) > 1 else base.OLLAMA_MODEL
    modelo_b = sys.argv[2] if len(sys.argv) > 2 else base.OLLAMA_MODEL_COMPARACION
    cfg_a, cfg_b = config_con_modelo(base, modelo_a), config_con_modelo(base, modelo_b)
    for cfg in (cfg_a, cfg_b):
        ok, msg = verificar_ollama(cfg)
        if not ok:
            print(f"[ERROR] {msg}")
            return 1

    casos = cargar_conjunto(RUTA_EVALUACION)
    carreras = {c["id"]: c for c in alm.cargar_carreras(RUTA_CARRERAS)}

    resultados = {}
    for cfg in (cfg_a, cfg_b):
        print(f"\n== {cfg.OLLAMA_MODEL} ({len(casos)} casos)")
        res = evaluar_modelo(cfg, casos, carreras,
                             progreso=lambda k, n: print(f"  {k}/{n}", end="\r"))
        for f in res:
            marca = "OK " if f["obtenido"] == f["esperado"] else "DIF"
            print(f"  {marca} [{f['idioma']}] esperado={f['esperado']:<13} obtenido={f['obtenido']:<13} {f['texto'][:45]}")
        resultados[cfg.OLLAMA_MODEL] = res

    res_a, res_b = resultados[modelo_a], resultados[modelo_b]
    informe = {
        "fecha": datetime.now().isoformat(timespec="seconds"),
        "version_prompt": VERSION_PROMPT,
        "modelo_a": modelo_a,
        "modelo_b": modelo_b,
        "metricas": {modelo_a: metricas(res_a), modelo_b: metricas(res_b)},
        "comparacion": comparar(res_a, res_b),
        "resultados": {modelo_a: res_a, modelo_b: res_b},
    }
    EVIDENCIAS_DIR.mkdir(exist_ok=True)
    RUTA_RESULTADOS_COMPARACION.write_text(json.dumps(informe, ensure_ascii=False, indent=2), encoding="utf-8")

    ma, mb = informe["metricas"][modelo_a], informe["metricas"][modelo_b]
    idiomas = list(ma["por_idioma"])
    with open(EVIDENCIAS_DIR / "comparacion_modelos.md", "w", encoding="utf-8") as f:
        f.write(f"# Comparación de modelos y evaluación por idioma\n\n"
                f"Prompt v{VERSION_PROMPT} · temperatura {base.OLLAMA_TEMPERATURE} · {informe['fecha']} · "
                f"{len(casos)} casos ficticios etiquetados a mano (`datos/conjunto_evaluacion.json`).\n\n")
        f.write(f"| Métrica | {modelo_a} | {modelo_b} |\n|---|---|---|\n")
        f.write(f"| Exactitud global | {ma['exactitud']}% | {mb['exactitud']}% |\n")
        for i in idiomas:
            f.write(f"| Exactitud `{i}` ({ma['por_idioma'][i]['casos']} casos) | "
                    f"{ma['por_idioma'][i]['exactitud']}% | {mb['por_idioma'][i]['exactitud']}% |\n")
        for c in ma["por_categoria"]:
            f.write(f"| Acierto en «{c}» ({ma['por_categoria'][c]['casos']} casos) | "
                    f"{ma['por_categoria'][c]['exactitud']}% | {mb['por_categoria'][c]['exactitud']}% |\n")
        f.write(f"| Idioma detectado correctamente | {ma['idioma_detectado_ok']}% | {mb['idioma_detectado_ok']}% |\n")
        f.write(f"| Respuestas inválidas (error) | {ma['errores']} | {mb['errores']} |\n")
        f.write(f"| Tiempo medio por opinión | {ma['segundos_promedio']} s | {mb['segundos_promedio']} s |\n\n")
        comp = informe["comparacion"]
        f.write(f"**Acuerdo entre modelos:** {comp['acuerdo']}% · **kappa de Cohen:** {comp['kappa']}\n\n")
        f.write("## Casos en que los modelos discrepan\n\n| Idioma | Texto | Esperado | "
                f"{modelo_a} | {modelo_b} |\n|---|---|---|---|---|\n")
        for d in comp["desacuerdos"]:
            f.write(f"| {d['idioma']} | {d['texto']} | {d['esperado']} | {d['modelo_a']} | {d['modelo_b']} |\n")
        f.write("\n## Detalle por caso\n\n| Id | Idioma | Texto | Esperado | "
                f"{modelo_a} | {modelo_b} |\n|---|---|---|---|---|---|\n")
        for a, b in zip(res_a, res_b):
            ok = lambda x: "✅" if x["obtenido"] == x["esperado"] else "❌"
            f.write(f"| {a['id']} | {a['idioma']} | {a['texto']} | {a['esperado']} | "
                    f"{a['obtenido']} {ok(a)} | {b['obtenido']} {ok(b)} |\n")

    print(f"\n{modelo_a}: {ma['exactitud']}%  ·  {modelo_b}: {mb['exactitud']}%  ·  "
          f"acuerdo {informe['comparacion']['acuerdo']}%  ·  kappa {informe['comparacion']['kappa']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
