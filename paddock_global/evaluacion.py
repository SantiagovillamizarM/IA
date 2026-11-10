"""Ampliación: evaluación por idioma y comparación entre dos modelos.

Usa datos/conjunto_evaluacion.json (opiniones ficticias etiquetadas a mano en
es/en/fr/de/pt). Nunca guarda nada en opiniones.json.
"""

from __future__ import annotations

import json
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Callable

from analisis import ErrorClasificacion, OllamaNoDisponibleError, analizar_opinion, crear_cadena
from config import ConfigOllama

ETIQUETAS = ("positivo", "negativo", "neutro", "mixto", "no pertinente")


def cargar_conjunto(ruta: Path) -> list[dict]:
    with open(ruta, encoding="utf-8") as f:
        return json.load(f)["casos"]


def evaluar_modelo(
    cfg: ConfigOllama,
    casos: list[dict],
    carreras_por_id: dict[str, dict],
    progreso: Callable[[int, int], None] | None = None,
) -> list[dict]:
    """Clasifica cada caso con el modelo de `cfg` y devuelve resultado por caso."""
    cadena = crear_cadena(cfg)
    resultados = []
    for k, caso in enumerate(casos, start=1):
        if progreso:
            progreso(k, len(casos))
        t0 = time.time()
        fila = {**caso, "modelo": cfg.OLLAMA_MODEL}
        try:
            a = analizar_opinion(carreras_por_id[caso["carrera_id"]], caso["texto"], cfg=cfg, cadena=cadena)
            fila.update(
                obtenido=a.sentimiento if a.es_pertinente else "no pertinente",
                idioma_detectado=a.idioma,
                razon=a.razon,
                aspectos=[x.model_dump() for x in a.aspectos],
            )
        except OllamaNoDisponibleError:
            raise
        except ErrorClasificacion as e:
            fila.update(obtenido="ERROR", idioma_detectado=None, razon=str(e), aspectos=[])
        fila["segundos"] = round(time.time() - t0, 1)
        resultados.append(fila)
    return resultados


def metricas(resultados: list[dict]) -> dict:
    """Exactitud global, por idioma y por categoría esperada; acierto de idioma; tiempo medio."""
    def exactitud(filas):
        return round(100 * sum(f["obtenido"] == f["esperado"] for f in filas) / len(filas), 1) if filas else None

    por_idioma = defaultdict(list)
    por_cat = defaultdict(list)
    for f in resultados:
        por_idioma[f["idioma"]].append(f)
        por_cat[f["esperado"]].append(f)
    return {
        "casos": len(resultados),
        "exactitud": exactitud(resultados),
        "por_idioma": {k: {"casos": len(v), "exactitud": exactitud(v)} for k, v in por_idioma.items()},
        "por_categoria": {k: {"casos": len(v), "exactitud": exactitud(v)} for k, v in por_cat.items()},
        "idioma_detectado_ok": round(
            100 * sum(f["idioma_detectado"] == f["idioma"] for f in resultados) / len(resultados), 1
        ),
        "errores": sum(f["obtenido"] == "ERROR" for f in resultados),
        "segundos_promedio": round(sum(f["segundos"] for f in resultados) / len(resultados), 1),
    }


def kappa_cohen(a: list[str], b: list[str]) -> float | None:
    """Acuerdo entre dos clasificadores corregido por azar (1 = total, 0 = como el azar)."""
    n = len(a)
    if n == 0:
        return None
    observado = sum(x == y for x, y in zip(a, b)) / n
    ca, cb = Counter(a), Counter(b)
    esperado = sum(ca[k] * cb[k] for k in set(ca) | set(cb)) / (n * n)
    return round((observado - esperado) / (1 - esperado), 3) if esperado < 1 else 1.0


def comparar(res_a: list[dict], res_b: list[dict]) -> dict:
    """Acuerdo entre modelos y lista de casos en que discrepan."""
    obt_a = [f["obtenido"] for f in res_a]
    obt_b = [f["obtenido"] for f in res_b]
    desacuerdos = [
        {"id": a["id"], "idioma": a["idioma"], "texto": a["texto"], "esperado": a["esperado"],
         "modelo_a": a["obtenido"], "modelo_b": b["obtenido"]}
        for a, b in zip(res_a, res_b) if a["obtenido"] != b["obtenido"]
    ]
    return {
        "acuerdo": round(100 * sum(x == y for x, y in zip(obt_a, obt_b)) / len(obt_a), 1),
        "kappa": kappa_cohen(obt_a, obt_b),
        "desacuerdos": desacuerdos,
    }
