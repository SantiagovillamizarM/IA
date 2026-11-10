"""API REST de Paddock Global (FastAPI). ``uvicorn paddock.api.main:app``.

Errores uniformes ``{"error": {"codigo", "mensaje"}}`` y sin trazas. ``/api/docs`` solo si ``API_DOCS=true``.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from paddock import __version__
from paddock.api.rutas.opiniones import router
from paddock.contenedor import Contenedor, crear_contenedor
from paddock.dominio import errores as err

log = logging.getLogger("paddock.api")

# Tipo de error → (estado HTTP, código estable)
_MAPA: list[tuple[type[Exception], int, str]] = [
    (err.TokenInvalidoError, 401, "no_autenticado"),
    (err.SesionRequeridaError, 401, "no_autenticado"),
    (err.CredencialesIncorrectasError, 401, "no_autenticado"),
    (err.PermisoDenegadoError, 403, "prohibido"),
    (err.LimiteExcedidoError, 429, "limite_excedido"),
    (err.EntradaInvalidaError, 422, "entrada_invalida"),
    (err.EventoNoEncontradoError, 404, "evento_no_encontrado"),
    (err.CuotaExcedidaError, 503, "cuota_proveedor"),
    (err.ProveedorNoDisponibleError, 503, "proveedor_no_disponible"),
    (err.ModeloNoEncontradoError, 503, "modelo_no_disponible"),
    (err.CredencialInvalidaError, 503, "proveedor_mal_configurado"),
    (err.ContenidoBloqueadoError, 422, "contenido_bloqueado"),
    (err.RespuestaInvalidaError, 502, "respuesta_invalida_modelo"),
    (err.ErrorClasificacion, 502, "error_clasificacion"),
    (err.FuncionNoDisponibleError, 501, "no_disponible"),
    (err.ErrorPersistencia, 500, "error_almacenamiento"),
]


def _error(estado: int, codigo: str, mensaje: str, cabeceras: dict[str, str] | None = None) -> JSONResponse:
    return JSONResponse(status_code=estado, content={"error": {"codigo": codigo, "mensaje": mensaje}},
                        headers=cabeceras)


def crear_app(contenedor: Contenedor | None = None) -> FastAPI:
    c = contenedor or crear_contenedor()
    docs = c.ajustes.API_DOCS
    app = FastAPI(title="Paddock Global API", version=__version__,
                  description="Opiniones del mundo de las carreras clasificadas con LangChain. "
                              "Las cifras reflejan solo las opiniones registradas en la app.",
                  docs_url="/api/docs" if docs else None, redoc_url=None,
                  openapi_url="/api/openapi.json" if docs else None)
    app.state.contenedor = c
    app.include_router(router)

    @app.exception_handler(err.ErrorPaddock)
    async def _paddock(_req: Request, e: err.ErrorPaddock) -> JSONResponse:
        for tipo, estado, codigo in _MAPA:
            if isinstance(e, tipo):
                cab = {"WWW-Authenticate": "Bearer"} if estado == 401 else None
                return _error(estado, codigo, str(e), cab)
        return _error(400, "error", str(e))

    @app.exception_handler(RequestValidationError)
    async def _validacion(_req: Request, e: RequestValidationError) -> JSONResponse:
        campos = ", ".join(".".join(str(p) for p in x.get("loc", [])[1:]) for x in e.errors()) or "petición"
        return _error(422, "entrada_invalida", f"Datos no válidos en: {campos}.")

    @app.exception_handler(StarletteHTTPException)
    async def _http(_req: Request, e: StarletteHTTPException) -> JSONResponse:
        codigo = {401: "no_autenticado", 403: "prohibido", 404: "no_encontrado", 405: "metodo_no_permitido"}
        return _error(e.status_code, codigo.get(e.status_code, "error"), str(e.detail))

    @app.exception_handler(Exception)
    async def _inesperado(_req: Request, e: Exception) -> JSONResponse:
        log.error("Error inesperado en la API: %s", type(e).__name__)  # sin traza ni datos al cliente
        return _error(500, "error_interno", "Ocurrió un error interno.")

    return app


def __getattr__(nombre: str) -> FastAPI:
    # «app» se crea al primer acceso (uvicorn paddock.api.main:app), no al importar el módulo en los tests.
    if nombre == "app":
        aplicacion = crear_app()
        globals()["app"] = aplicacion
        return aplicacion
    raise AttributeError(nombre)
