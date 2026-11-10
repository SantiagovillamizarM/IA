"""Control de acceso en los casos de uso (no solo ocultando páginas)."""

from __future__ import annotations

from dataclasses import dataclass

from paddock.dominio.enums import Rol
from paddock.dominio.errores import PermisoDenegadoError, SesionRequeridaError

_JERARQUIA = {Rol.AFICIONADO.value: 1, Rol.MODERADOR.value: 2, Rol.ADMIN.value: 3}


@dataclass(frozen=True)
class Actor:
    """Quién ejecuta la acción. ``None`` en lugar de un Actor significa anónimo."""

    usuario_id: str
    rol: str
    email: str = ""
    nombre: str = ""


def requerir_sesion(actor: Actor | None) -> Actor:
    if actor is None:
        raise SesionRequeridaError("Debes iniciar sesión para hacer esto.")
    return actor


def requerir_rol(actor: Actor | None, minimo: Rol) -> Actor:
    """Exige un rol igual o superior a ``minimo`` (aficionado < moderador < admin)."""
    actor = requerir_sesion(actor)
    if _JERARQUIA.get(actor.rol, 0) < _JERARQUIA[minimo.value]:
        raise PermisoDenegadoError("No tienes permiso para esta acción.")
    return actor


def tiene_rol(actor: Actor | None, minimo: Rol) -> bool:
    return actor is not None and _JERARQUIA.get(actor.rol, 0) >= _JERARQUIA[minimo.value]
