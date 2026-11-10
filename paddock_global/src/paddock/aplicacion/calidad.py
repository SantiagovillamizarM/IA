"""Calidad del modelo: métricas sobre las opiniones revisadas por humanos y rendimiento de las llamadas.

Las métricas solo usan etiquetas humanas reales (revisiones); nunca se inventan.
"""

from __future__ import annotations

import csv
import io
import math
from collections import Counter, defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field

from paddock.aplicacion.autorizacion import Actor, requerir_rol
from paddock.dominio.entidades import FiltrosOpinion, MetricaLlamada, Opinion
from paddock.dominio.enums import SENTIMIENTOS, Rol
from paddock.puertos.repositorios import RepositorioMetricas, RepositorioOpiniones


@dataclass(frozen=True)
class MetricasClase:
    precision: float | None
    recall: float | None
    f1: float | None
    soporte: int


@dataclass(frozen=True)
class InformeCalidad:
    n: int
    exactitud: float | None
    por_clase: dict[str, MetricasClase]
    f1_macro: float | None
    matriz: dict[str, dict[str, int]]  # real (humano) → predicho (modelo) → n
    etiquetas: tuple[str, ...] = SENTIMIENTOS


@dataclass(frozen=True)
class RendimientoProveedor:
    proveedor: str
    llamadas: int
    latencia_media_ms: float
    latencia_p95_ms: float
    tasa_error: float
    errores: dict[str, int] = field(default_factory=dict)
    tokens_entrada: int = 0
    tokens_salida: int = 0


def _div(a: float, b: float) -> float | None:
    return a / b if b else None


def evaluar_pares(pares: Sequence[tuple[str, str]], etiquetas: Sequence[str] = SENTIMIENTOS) -> InformeCalidad:
    """``pares`` = (humano, modelo). Precisión, recall y F1 por clase; exactitud y F1 macro."""
    matriz = {r: dict.fromkeys(etiquetas, 0) for r in etiquetas}
    for real, pred in pares:
        if real in matriz and pred in matriz[real]:
            matriz[real][pred] += 1
    n = sum(sum(f.values()) for f in matriz.values())
    aciertos = sum(matriz[e][e] for e in etiquetas)
    por_clase: dict[str, MetricasClase] = {}
    for e in etiquetas:
        vp = matriz[e][e]
        pred_e = sum(matriz[r][e] for r in etiquetas)
        real_e = sum(matriz[e].values())
        p, r = _div(vp, pred_e), _div(vp, real_e)
        f1 = (2 * p * r / (p + r)) if p is not None and r is not None and (p + r) > 0 else (0.0 if real_e else None)
        por_clase[e] = MetricasClase(p, r, f1, real_e)
    f1s = [m.f1 for m in por_clase.values() if m.soporte and m.f1 is not None]
    return InformeCalidad(n=n, exactitud=_div(aciertos, n), por_clase=por_clase,
                          f1_macro=sum(f1s) / len(f1s) if f1s else None, matriz=matriz, etiquetas=tuple(etiquetas))


def percentil(valores: Sequence[float], p: float) -> float:
    """Percentil con interpolación lineal (p entre 0 y 100)."""
    if not valores:
        return 0.0
    orden = sorted(valores)
    k = (len(orden) - 1) * p / 100
    bajo, alto = math.floor(k), math.ceil(k)
    return float(orden[bajo] + (orden[alto] - orden[bajo]) * (k - bajo))


def rendimiento(metricas: Iterable[MetricaLlamada]) -> list[RendimientoProveedor]:
    grupos: dict[str, list[MetricaLlamada]] = defaultdict(list)
    for m in metricas:
        grupos[m.proveedor].append(m)
    salida = []
    for prov, ms in sorted(grupos.items()):
        lat = [m.latencia_ms for m in ms if m.exito]
        errores = Counter(m.tipo_error or "desconocido" for m in ms if not m.exito)
        salida.append(RendimientoProveedor(
            proveedor=prov, llamadas=len(ms), latencia_media_ms=sum(lat) / len(lat) if lat else 0.0,
            latencia_p95_ms=percentil(lat, 95), tasa_error=sum(errores.values()) / len(ms), errores=dict(errores),
            tokens_entrada=sum(m.tokens_entrada or 0 for m in ms), tokens_salida=sum(m.tokens_salida or 0 for m in ms),
        ))
    return salida


def filtrar_revisadas(ops: Iterable[Opinion], proveedor: str | None = None, modelo: str | None = None,
                      version_prompt: str | None = None) -> list[Opinion]:
    res = []
    for o in ops:
        if o.revision is None:
            continue
        prov, _, nombre = o.modelo.partition("/")
        if proveedor and prov != proveedor:
            continue
        if modelo and o.modelo != modelo and nombre != modelo:
            continue
        if version_prompt and o.version_prompt != version_prompt:
            continue
        res.append(o)
    return res


def csv_evaluacion(ops: Iterable[Opinion]) -> bytes:
    """Conjunto de evaluación: texto, etiqueta del modelo y etiqueta humana (UTF-8 con BOM)."""
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["id", "evento_id", "edicion_anio", "opinion", "etiqueta_modelo", "etiqueta_humana", "modelo",
                "version_prompt"])
    for o in ops:
        if o.revision is None:
            continue
        w.writerow([o.id, o.evento_id, o.edicion_anio or "", o.opinion_original, o.sentimiento, o.revision.sentimiento,
                    o.modelo, o.version_prompt])
    return buf.getvalue().encode("utf-8-sig")


@dataclass
class CalidadModelo:
    opiniones: RepositorioOpiniones
    metricas: RepositorioMetricas

    def revisadas(self, actor: Actor | None, proveedor: str | None = None, modelo: str | None = None,
                  version_prompt: str | None = None) -> list[Opinion]:
        requerir_rol(actor, Rol.ADMIN)
        ops = self.opiniones.consultar(FiltrosOpinion(solo_revisadas=True, incluir_ocultas=True))
        return filtrar_revisadas(ops, proveedor, modelo, version_prompt)

    def informe(self, actor: Actor | None, **filtros: str | None) -> InformeCalidad:
        ops = self.revisadas(actor, **filtros)
        return evaluar_pares([(o.revision.sentimiento, o.sentimiento) for o in ops if o.revision])

    def rendimiento(self, actor: Actor | None) -> list[RendimientoProveedor]:
        requerir_rol(actor, Rol.ADMIN)
        return rendimiento(self.metricas.listar())
