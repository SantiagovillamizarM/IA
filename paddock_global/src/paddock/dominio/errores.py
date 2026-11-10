"""Excepciones del dominio. Los mensajes están en español y se pueden mostrar al usuario.

Ningún mensaje incluye claves, trazas ni datos internos del proveedor.
"""

from __future__ import annotations


class ErrorPaddock(Exception):
    """Base de todos los errores propios de la aplicación."""


# ---------------------------------------------------------------- entrada


class EntradaInvalidaError(ErrorPaddock):
    """El texto o un dato introducido por el usuario no cumple las reglas."""


class EventoNoEncontradoError(ErrorPaddock):
    """El evento indicado no existe en el catálogo o está desactivado."""


# ---------------------------------------------------------------- catálogo


class CatalogoInvalidoError(ErrorPaddock):
    """El catálogo no existe, no es JSON válido o incumple el esquema."""


# ---------------------------------------------------------------- clasificación


class ErrorClasificacion(ErrorPaddock):
    """Base de los fallos al obtener el análisis del modelo."""


class ProveedorNoDisponibleError(ErrorClasificacion):
    """Servidor caído, tiempo de espera agotado o sin red."""


class ModeloNoEncontradoError(ErrorClasificacion):
    """Modelo no descargado (Ollama) o nombre inválido (Gemini)."""


class CredencialInvalidaError(ErrorClasificacion):
    """Clave rechazada por el proveedor (401/403)."""


class CuotaExcedidaError(ErrorClasificacion):
    """El proveedor respondió 429: se superó la cuota."""


class ContenidoBloqueadoError(ErrorClasificacion):
    """Los filtros de seguridad del proveedor bloquearon la respuesta."""


class RespuestaInvalidaError(ErrorClasificacion):
    """La respuesta no se pudo parsear, no pasó la validación o es incoherente."""


class AnalisisIncoherenteError(RespuestaInvalidaError):
    """La pertinencia, el sentimiento y los campos detallados se contradicen."""


# ---------------------------------------------------------------- persistencia


class ErrorPersistencia(ErrorPaddock):
    """Base de los fallos de almacenamiento."""


class ArchivoOpinionesCorruptoError(ErrorPersistencia):
    """opiniones.json existe pero no es JSON válido o tiene un esquema inesperado."""


class ErrorEscrituraOpiniones(ErrorPersistencia):
    """No se pudo escribir el archivo de opiniones (permisos, disco, etc.)."""


class FuncionNoDisponibleError(ErrorPaddock):
    """La función requiere otro modo de almacenamiento (por ejemplo, SQL)."""


# ---------------------------------------------------------------- seguridad


class ErrorSeguridad(ErrorPaddock):
    """Base de los errores de autenticación, autorización y límites."""


class CredencialesIncorrectasError(ErrorSeguridad):
    """Correo o contraseña incorrectos (mensaje genérico a propósito)."""

    def __init__(self, mensaje: str = "Correo o contraseña incorrectos.") -> None:
        super().__init__(mensaje)


class CuentaBloqueadaError(ErrorSeguridad):
    """Demasiados intentos fallidos: la cuenta está bloqueada temporalmente."""


class SesionRequeridaError(ErrorSeguridad):
    """La acción exige iniciar sesión."""


class SesionExpiradaError(ErrorSeguridad):
    """La sesión caducó por inactividad."""


class PermisoDenegadoError(ErrorSeguridad):
    """El rol del usuario no permite la acción."""


class LimiteExcedidoError(ErrorSeguridad):
    """Se superó el límite de tasa (por usuario o global diario)."""


class RegistroCerradoError(ErrorSeguridad):
    """El registro de nuevas cuentas está desactivado."""


class TokenInvalidoError(ErrorSeguridad):
    """Token de API ausente, desconocido o revocado."""
