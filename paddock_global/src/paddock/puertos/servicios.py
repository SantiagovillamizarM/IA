"""Puertos de servicios técnicos (reloj, ids, hash) e implementaciones por defecto triviales."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Protocol


class Reloj(Protocol):
    def ahora(self) -> datetime:
        """Fecha y hora actual con zona UTC."""
        ...


class GeneradorId(Protocol):
    def nuevo(self) -> str: ...


class HasherContrasenas(Protocol):
    def hash(self, contrasena: str) -> str: ...

    def verificar(self, hash_guardado: str, contrasena: str) -> bool: ...

    def necesita_rehash(self, hash_guardado: str) -> bool: ...

    def verificar_ficticio(self, contrasena: str) -> None:
        """Gasta el mismo tiempo que una verificación real (correo inexistente)."""
        ...


class Limitador(Protocol):
    def verificar_y_registrar(self, sujeto: str, *, ventana_min: int = 5, maximo: int | None = None,
                              prefijo: str = "op") -> None:
        """Lanza ``LimiteExcedidoError`` si se supera el límite; si no, registra el uso."""
        ...

    def verificar_global(self) -> None: ...


class RelojSistema:
    def ahora(self) -> datetime:
        return datetime.now(UTC)


class GeneradorUuid4:
    def nuevo(self) -> str:
        return str(uuid.uuid4())


def iso(dt: datetime) -> str:
    """ISO 8601 con «+00:00» y sin microsegundos."""
    return dt.astimezone(UTC).replace(microsecond=0).isoformat()
