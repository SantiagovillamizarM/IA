"""Adaptadores en memoria. En modo JSON (taller) sustituyen a las tablas auxiliares de SQL.

No persisten entre reinicios: el limitador y la auditoría duraderos requieren ``STORAGE_BACKEND=sql``.
"""

from __future__ import annotations

import threading
from typing import Any

from paddock.dominio.entidades import FiltrosOpinion, MetricaLlamada, Opinion, Revision
from paddock.dominio.reglas import aplicar_filtros, coincide


class RepositorioLimitesMemoria:
    def __init__(self) -> None:
        self._eventos: list[tuple[str, str]] = []
        self._lock = threading.Lock()

    def registrar(self, clave: str, fecha_utc: str) -> None:
        with self._lock:
            self._eventos.append((clave, fecha_utc))

    def contar_desde(self, clave: str, desde_utc: str) -> int:
        with self._lock:
            return sum(1 for c, f in self._eventos if c == clave and f >= desde_utc)

    def purgar_antes(self, fecha_utc: str) -> None:
        with self._lock:
            self._eventos = [(c, f) for c, f in self._eventos if f >= fecha_utc]


class RepositorioAuditoriaMemoria:
    def __init__(self) -> None:
        self.registros: list[dict[str, Any]] = []

    def registrar(self, *, fecha_utc: str, usuario_id: str | None, accion: str,
                  detalle: dict[str, Any] | None = None, ip_hash: str | None = None) -> None:
        self.registros.append({"fecha_utc": fecha_utc, "usuario_id": usuario_id, "accion": accion,
                               "detalle": detalle or {}, "ip_hash": ip_hash})

    def consultar(self, *, accion: str | None = None, usuario_id: str | None = None,
                  limite: int = 200) -> list[dict[str, Any]]:
        res = [r for r in reversed(self.registros)
               if (accion is None or r["accion"] == accion) and (usuario_id is None or r["usuario_id"] == usuario_id)]
        return res[:limite]


class RepositorioMetricasMemoria:
    def __init__(self) -> None:
        self.metricas: list[MetricaLlamada] = []

    def registrar(self, metrica: MetricaLlamada) -> None:
        self.metricas.append(metrica)

    def listar(self, desde_utc: str | None = None) -> list[MetricaLlamada]:
        return [m for m in self.metricas if desde_utc is None or m.fecha_utc >= desde_utc]


class RepositorioOpinionesMemoria:
    """Útil en tests de casos de uso."""

    def __init__(self) -> None:
        self.datos: dict[str, Opinion] = {}
        self.revisiones: dict[str, list[Revision]] = {}

    def guardar(self, opinion: Opinion) -> bool:
        if opinion.id in self.datos:
            return False
        self.datos[opinion.id] = opinion
        return True

    def obtener(self, opinion_id: str) -> Opinion | None:
        return self.datos.get(opinion_id)

    def consultar(self, filtros: FiltrosOpinion) -> list[Opinion]:
        return aplicar_filtros(self.datos.values(), filtros)

    def contar(self, filtros: FiltrosOpinion) -> int:
        return sum(1 for o in self.datos.values() if coincide(o, filtros))

    def guardar_revision(self, opinion_id: str, revision: Revision) -> None:
        self.revisiones.setdefault(opinion_id, []).append(revision)
        self.datos[opinion_id] = self.datos[opinion_id].con(revision=revision)

    def historial_revisiones(self, opinion_id: str) -> list[Revision]:
        return list(self.revisiones.get(opinion_id, []))

    def cambiar_visibilidad(self, opinion_id: str, visible: bool) -> None:
        self.datos[opinion_id] = self.datos[opinion_id].con(visible=visible)

    def anonimizar_usuario(self, usuario_id: str) -> int:
        n = 0
        for k, o in list(self.datos.items()):
            if o.usuario_id == usuario_id:
                self.datos[k] = o.con(usuario_id=None)
                n += 1
        return n
