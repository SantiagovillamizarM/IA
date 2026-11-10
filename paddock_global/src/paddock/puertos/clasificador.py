"""Puertos de los servicios de IA."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from paddock.dominio.analisis import ResultadoClasificacion


class ClasificadorSentimiento(Protocol):
    """Clasifica UNA opinión. Nunca recibe el historial del chat ni texto vacío.

    Lanza una subclase de ``ErrorClasificacion`` ante cualquier fallo; nunca devuelve
    un sentimiento por defecto.
    """

    @property
    def proveedor(self) -> str: ...

    @property
    def modelo(self) -> str:
        """Identificador «proveedor/modelo» que se guarda en cada registro."""
        ...

    @property
    def version_prompt(self) -> str: ...

    def clasificar(
        self, *, texto: str, carrera: str, disciplina: str, disciplina_id: str, edicion: int | None
    ) -> ResultadoClasificacion: ...


class Resumidor(Protocol):
    """Resume las opiniones guardadas de un evento (v3)."""

    @property
    def modelo(self) -> str: ...

    @property
    def version_prompt(self) -> str: ...

    def resumir(self, *, carrera: str, edicion: int | None, opiniones: Sequence[tuple[str, str]]) -> str:
        """``opiniones`` es una lista de pares (sentimiento, texto). Devuelve el resumen en español."""
        ...
