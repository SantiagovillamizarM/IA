"""Ampliación: estadísticas basadas EXCLUSIVAMENTE en los registros de la app.

No llama al modelo. Usa la etiqueta vigente (corrección manual si existe).
"""

from __future__ import annotations

from collections import Counter

from almacenamiento import contar_por_sentimiento, sentimiento_final
from config import SENTIMIENTOS

PESO = {"positivo": 1, "negativo": -1, "neutro": 0, "mixto": 0}


def conteo_por_carrera(registros: list[dict]) -> list[dict]:
    """Filas largas {carrera, sentimiento, n} para la gráfica apilada."""
    c = Counter((r["carrera_nombre"], sentimiento_final(r)) for r in registros)
    return [{"carrera": car, "sentimiento": s, "n": n} for (car, s), n in c.items()]


def ranking_carreras(registros: list[dict], minimo: int = 2) -> list[dict]:
    """Índice de percepción por carrera = (positivas − negativas) / total × 100.

    Va de −100 (todas negativas) a +100 (todas positivas). Neutras y mixtas
    cuentan en el total pero no suman ni restan. Las carreras con menos de
    `minimo` opiniones se marcan y van al final: con tan pocos datos el índice
    no es representativo.
    """
    por_carrera: dict[str, list[dict]] = {}
    for r in registros:
        por_carrera.setdefault(r["carrera_id"], []).append(r)

    filas = []
    for cid, regs in por_carrera.items():
        conteo = contar_por_sentimiento(regs)
        total = len(regs)
        indice = round(100 * sum(PESO[sentimiento_final(r)] for r in regs) / total, 1)
        filas.append({
            "carrera_id": cid,
            "carrera": regs[0]["carrera_nombre"],
            "opiniones": total,
            **conteo,
            "indice": indice,
            "suficiente": total >= minimo,
        })
    filas.sort(key=lambda f: (not f["suficiente"], -f["indice"], -f["opiniones"]))
    return filas


def conteo_por_aspecto(registros: list[dict]) -> list[dict]:
    """Filas {aspecto, sentimiento, n} a partir de los aspectos detectados."""
    c = Counter(
        (a["aspecto"], a["sentimiento"])
        for r in registros for a in (r.get("aspectos") or [])
    )
    return [{"aspecto": asp, "sentimiento": s, "n": n} for (asp, s), n in c.items()]


def resumen_idiomas(registros: list[dict]) -> dict[str, int]:
    return dict(Counter(r.get("idioma") or "sin dato" for r in registros))


__all__ = ["SENTIMIENTOS", "conteo_por_carrera", "ranking_carreras", "conteo_por_aspecto", "resumen_idiomas"]
