"""Autenticación de la API con tokens personales (``Authorization: Bearer pg_…``)."""

from __future__ import annotations

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from paddock.aplicacion.autorizacion import Actor
from paddock.contenedor import Contenedor
from paddock.dominio.errores import TokenInvalidoError

_bearer = HTTPBearer(auto_error=False, description="Token personal creado en «Mi cuenta»")


def contenedor(request: Request) -> Contenedor:
    return request.app.state.contenedor


def actor_opcional(cred: HTTPAuthorizationCredentials | None = Depends(_bearer),
                   c: Contenedor = Depends(contenedor)) -> Actor | None:
    if cred is None:
        return None
    return c.tokens_api.autenticar(cred.credentials)


def actor_requerido(actor: Actor | None = Depends(actor_opcional)) -> Actor:
    if actor is None:
        raise TokenInvalidoError("Falta la cabecera Authorization: Bearer <token>.")
    return actor
