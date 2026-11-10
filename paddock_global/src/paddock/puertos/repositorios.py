"""Puertos de persistencia. Los implementan los adaptadores JSON y SQL."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Protocol

from paddock.dominio.entidades import (
    Catalogo,
    Denuncia,
    Evento,
    FiltrosOpinion,
    MetricaLlamada,
    Opinion,
    Resumen,
    Revision,
    TokenApi,
    TrabajoLote,
    Usuario,
)


class RepositorioCatalogo(Protocol):
    def obtener(self) -> Catalogo: ...

    def guardar_evento(self, evento: Evento) -> None:
        """Añade o actualiza un evento (activar/desactivar, nuevo)."""
        ...

    def obtener_jerga(self) -> dict[str, list[str]]: ...

    def guardar_jerga(self, disciplina_id: str, terminos: list[str]) -> None: ...


class RepositorioOpiniones(Protocol):
    def guardar(self, opinion: Opinion) -> bool:
        """Idempotente por ``id``: devuelve ``True`` si insertó y ``False`` si ya existía."""
        ...

    def obtener(self, opinion_id: str) -> Opinion | None: ...

    def consultar(self, filtros: FiltrosOpinion) -> list[Opinion]:
        """Filtra, ordena por fecha descendente y pagina. Nunca llama al modelo."""
        ...

    def contar(self, filtros: FiltrosOpinion) -> int: ...

    def guardar_revision(self, opinion_id: str, revision: Revision) -> None:
        """Guarda la corrección humana aparte; la etiqueta del modelo no cambia."""
        ...

    def historial_revisiones(self, opinion_id: str) -> list[Revision]: ...

    def cambiar_visibilidad(self, opinion_id: str, visible: bool) -> None: ...

    def anonimizar_usuario(self, usuario_id: str) -> int:
        """Pone ``usuario_id = null`` en las opiniones del usuario. Devuelve cuántas cambió."""
        ...


class RepositorioUsuarios(Protocol):
    def crear(self, usuario: Usuario) -> None: ...

    def por_email(self, email: str) -> Usuario | None: ...

    def por_id(self, usuario_id: str) -> Usuario | None: ...

    def actualizar(self, usuario: Usuario) -> None: ...

    def listar(self) -> list[Usuario]: ...

    def eliminar(self, usuario_id: str) -> None: ...

    def contar(self) -> int: ...


class RepositorioTokens(Protocol):
    def crear(self, token: TokenApi) -> None: ...

    def por_hash(self, hash_token: str) -> TokenApi | None: ...

    def de_usuario(self, usuario_id: str) -> list[TokenApi]: ...

    def revocar(self, token_id: str, usuario_id: str) -> None: ...

    def marcar_uso(self, token_id: str, fecha_utc: str) -> None: ...


class RepositorioAuditoria(Protocol):
    def registrar(self, *, fecha_utc: str, usuario_id: str | None, accion: str,
                  detalle: dict[str, Any] | None = None, ip_hash: str | None = None) -> None: ...

    def consultar(self, *, accion: str | None = None, usuario_id: str | None = None,
                  limite: int = 200) -> list[dict[str, Any]]: ...


class RepositorioLimites(Protocol):
    """Contador persistente para el limitador de tasa."""

    def registrar(self, clave: str, fecha_utc: str) -> None: ...

    def contar_desde(self, clave: str, desde_utc: str) -> int: ...

    def purgar_antes(self, fecha_utc: str) -> None: ...


class RepositorioMetricas(Protocol):
    def registrar(self, metrica: MetricaLlamada) -> None: ...

    def listar(self, desde_utc: str | None = None) -> list[MetricaLlamada]: ...


class RepositorioTrabajos(Protocol):
    def crear(self, trabajo: TrabajoLote) -> None: ...

    def obtener(self, trabajo_id: str) -> TrabajoLote | None: ...

    def actualizar(self, trabajo: TrabajoLote) -> None: ...

    def siguiente_pendiente(self) -> TrabajoLote | None: ...

    def listar(self, usuario_id: str | None = None, limite: int = 50) -> list[TrabajoLote]: ...


class RepositorioResumenes(Protocol):
    def obtener(self, evento_id: str, edicion_anio: int | None) -> Resumen | None: ...

    def guardar(self, resumen: Resumen) -> None: ...


class RepositorioDenuncias(Protocol):
    def crear(self, denuncia: Denuncia) -> None: ...

    def pendientes(self) -> list[Denuncia]: ...

    def de_opinion(self, opinion_id: str) -> list[Denuncia]: ...

    def marcar_atendidas(self, opinion_id: str) -> None: ...


__all__ = [
    "RepositorioAuditoria",
    "RepositorioCatalogo",
    "RepositorioDenuncias",
    "RepositorioLimites",
    "RepositorioMetricas",
    "RepositorioOpiniones",
    "RepositorioResumenes",
    "RepositorioTokens",
    "RepositorioTrabajos",
    "RepositorioUsuarios",
    "Sequence",
]
