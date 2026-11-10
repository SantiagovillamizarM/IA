"""Cadena LangChain del clasificador y traducción de errores de los proveedores.

Cadena: ``prompt | modelo.with_structured_output(Esquema, method="json_schema", include_raw=True)``.
El resultado ``{"raw", "parsed", "parsing_error"}`` distingue un fallo de parseo de uno de conexión.

Política de reintentos (los clientes van con ``max_retries=0``):
- ``RespuestaInvalidaError``: un reintento inmediato.
- ``ProveedorNoDisponibleError``: un reintento tras 2 s.
- El resto no se reintenta. Nunca se devuelve un sentimiento por defecto.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from pydantic import ValidationError

from paddock.adaptadores.llm import prompts
from paddock.adaptadores.llm.gemini import crear_modelo_gemini, verificar_gemini
from paddock.adaptadores.llm.ollama import crear_modelo_ollama, verificar_ollama
from paddock.dominio.analisis import AnalisisOpinion, ResultadoClasificacion
from paddock.dominio.entidades import MetricaLlamada
from paddock.dominio.errores import (
    ContenidoBloqueadoError,
    CredencialInvalidaError,
    CuotaExcedidaError,
    ErrorClasificacion,
    ModeloNoEncontradoError,
    ProveedorNoDisponibleError,
    RespuestaInvalidaError,
)
from paddock.dominio.reglas import validar_coherencia
from paddock.puertos.servicios import RelojSistema, iso

if TYPE_CHECKING:
    from langchain_core.language_models import BaseChatModel
    from langchain_core.runnables import Runnable

    from paddock.config import Ajustes

log = logging.getLogger("paddock.llm")

_FINISH_BLOQUEO = {"SAFETY", "PROHIBITED_CONTENT", "BLOCKLIST", "RECITATION", "SPII"}


def crear_modelo(aj: Ajustes) -> BaseChatModel:
    if aj.LLM_PROVIDER == "gemini":
        if not aj.hay_clave_gemini:
            raise CredencialInvalidaError("Falta GOOGLE_API_KEY en el archivo .env para usar Gemini.")
        return crear_modelo_gemini(aj)
    return crear_modelo_ollama(aj)


def verificar_proveedor(aj: Ajustes) -> tuple[bool, str]:
    """🟢/🔴: Ollama → ``/api/tags`` y modelo descargado. Gemini → clave y metadatos del modelo."""
    return verificar_gemini(aj) if aj.LLM_PROVIDER == "gemini" else verificar_ollama(aj)


# ======================================================================= traducción de errores


def _mensaje_modelo_ausente(proveedor: str, modelo: str) -> str:
    if proveedor == "ollama":
        return f"El modelo «{modelo}» no está descargado en Ollama. Ejecuta `ollama pull {modelo}`."
    return f"El modelo «{modelo}» no existe en Gemini. Revisa GEMINI_MODEL en el archivo .env."


def _mensaje_caido(proveedor: str) -> str:
    if proveedor == "ollama":
        return "Ollama no responde. Abre la app Ollama o ejecuta `ollama serve`."
    return "Gemini no responde. Intenta más tarde."


def traducir_error(e: BaseException, proveedor: str, modelo: str) -> ErrorClasificacion:
    """Convierte la excepción del proveedor en un error propio, sin filtrar claves ni trazas."""
    if isinstance(e, ErrorClasificacion):
        return e

    from langchain_core import exceptions as lc

    texto = str(e).lower()
    nombre = type(e).__name__

    # --- jerarquía estándar de langchain-core (langchain-google-genai 4.x la usa)
    if isinstance(e, lc.ModelAuthenticationError | lc.ModelPermissionDeniedError):
        return CredencialInvalidaError("La clave del proveedor no es válida o no tiene permisos.")
    if isinstance(e, lc.ModelRateLimitError):
        return CuotaExcedidaError("Se superó la cuota del proveedor (429). Espera un momento e intenta de nuevo.")
    if isinstance(e, lc.ModelNotFoundError):
        return ModeloNoEncontradoError(_mensaje_modelo_ausente(proveedor, modelo))
    if isinstance(e, lc.ModelRefusalError):
        return ContenidoBloqueadoError("Los filtros de seguridad del proveedor bloquearon la respuesta.")
    if isinstance(e, lc.ModelInvalidRequestError):
        if "api key" in texto or "api_key" in texto:
            return CredencialInvalidaError("La clave del proveedor no es válida.")
        return RespuestaInvalidaError("El proveedor rechazó la solicitud.")
    if isinstance(e, lc.ModelTimeoutError | lc.ModelConnectionError | lc.ModelAPIError):
        return ProveedorNoDisponibleError(_mensaje_caido(proveedor))

    # --- SDK de Google sin envolver
    try:
        from google.genai import errors as gerr

        if isinstance(e, gerr.ClientError):
            if e.code in (401, 403) or "api key" in texto:
                return CredencialInvalidaError("La clave del proveedor no es válida.")
            if e.code == 404:
                return ModeloNoEncontradoError(_mensaje_modelo_ausente(proveedor, modelo))
            if e.code == 429:
                return CuotaExcedidaError("Se superó la cuota del proveedor (429).")
            return RespuestaInvalidaError("El proveedor rechazó la solicitud.")
        if isinstance(e, gerr.ServerError):
            return ProveedorNoDisponibleError(_mensaje_caido(proveedor))
    except ImportError:  # pragma: no cover
        pass

    # --- paquete ollama
    try:
        import ollama

        if isinstance(e, ollama.ResponseError):
            if e.status_code == 404 or "not found" in texto:
                return ModeloNoEncontradoError(_mensaje_modelo_ausente(proveedor, modelo))
            if e.status_code >= 500 or e.status_code == -1:
                return ProveedorNoDisponibleError(_mensaje_caido(proveedor))
            return RespuestaInvalidaError("Ollama rechazó la solicitud.")
    except ImportError:  # pragma: no cover
        pass

    # --- red
    try:
        import httpx

        if isinstance(e, httpx.TimeoutException | httpx.ConnectError | httpx.NetworkError):
            return ProveedorNoDisponibleError(_mensaje_caido(proveedor))
    except ImportError:  # pragma: no cover
        pass
    if isinstance(e, ConnectionError | TimeoutError) or "connection refused" in texto or "connect" in nombre.lower():
        return ProveedorNoDisponibleError(_mensaje_caido(proveedor))
    if isinstance(e, ValidationError | ValueError):
        return RespuestaInvalidaError("La respuesta del modelo no cumple el formato esperado.")
    log.warning("Error no clasificado del proveedor %s: %s", proveedor, nombre)
    return ErrorClasificacion("Ocurrió un error inesperado al clasificar. Intenta de nuevo.")


# ======================================================================= clasificador


class ClasificadorLangChain:
    """Adaptador de ``ClasificadorSentimiento`` para cualquier ``BaseChatModel`` con salida estructurada."""

    def __init__(
        self,
        modelo_chat: BaseChatModel,
        *,
        proveedor: str,
        nombre_modelo: str,
        version_prompt: str,
        jerga_para: Callable[[str], str],
        observador: Callable[[MetricaLlamada], None] | None = None,
        espera_reintento_s: float = 2.0,
    ) -> None:
        self._proveedor = proveedor
        self._nombre_modelo = nombre_modelo
        self._version = version_prompt
        self._jerga_para = jerga_para
        self._observador = observador
        self._espera = espera_reintento_s
        self._esquema = prompts.esquema(version_prompt)
        self._cadena: Runnable[Any, Any] = prompts.plantilla(version_prompt) | modelo_chat.with_structured_output(
            self._esquema, method="json_schema", include_raw=True
        )

    @property
    def proveedor(self) -> str:
        return self._proveedor

    @property
    def modelo(self) -> str:
        return f"{self._proveedor}/{self._nombre_modelo}"

    @property
    def version_prompt(self) -> str:
        return self._version

    # ------------------------------------------------------------------
    def clasificar(
        self, *, texto: str, carrera: str, disciplina: str, disciplina_id: str, edicion: int | None
    ) -> ResultadoClasificacion:
        if not texto or not texto.strip():  # defensa: el caso de uso ya valida
            raise ValueError("El clasificador nunca se llama con texto vacío.")
        entrada = {
            "disciplina": disciplina,
            "jerga": self._jerga_para(disciplina_id),
            "carrera": carrera,
            "edicion": str(edicion) if edicion else "sin especificar",
            "opinion": prompts.neutralizar_delimitadores(texto),
        }
        reintento_invalida = reintento_red = False
        intentos = 0
        while True:
            intentos += 1
            try:
                res = self._una_llamada(entrada)
                return ResultadoClasificacion(
                    analisis=res[0], modelo=self.modelo, version_prompt=self._version,
                    latencia_ms=res[1], tokens_entrada=res[2], tokens_salida=res[3], intentos=intentos,
                )
            except RespuestaInvalidaError:
                if reintento_invalida:
                    raise
                reintento_invalida = True
                log.info("Respuesta inválida de %s; se reintenta una vez.", self.modelo)
            except ProveedorNoDisponibleError:
                if reintento_red:
                    raise
                reintento_red = True
                log.info("%s no disponible; se reintenta en %.0f s.", self.modelo, self._espera)
                time.sleep(self._espera)

    def _una_llamada(self, entrada: dict[str, str]) -> tuple[AnalisisOpinion, int, int | None, int | None]:
        inicio = time.perf_counter()
        tokens_in = tokens_out = None
        try:
            try:
                salida = self._cadena.invoke(entrada)
            except Exception as e:  # noqa: BLE001 - se traduce a un error propio
                raise traducir_error(e, self._proveedor, self._nombre_modelo) from e
            raw = salida.get("raw") if isinstance(salida, dict) else None
            uso = getattr(raw, "usage_metadata", None) or {}
            tokens_in, tokens_out = uso.get("input_tokens"), uso.get("output_tokens")
            meta = getattr(raw, "response_metadata", None) or {}
            if str(meta.get("finish_reason", "")).upper() in _FINISH_BLOQUEO:
                raise ContenidoBloqueadoError("Los filtros de seguridad del proveedor bloquearon la respuesta.")
            if salida.get("parsing_error") is not None or salida.get("parsed") is None:
                raise RespuestaInvalidaError("La respuesta del modelo no cumple el formato esperado.")
            parsed = salida["parsed"]
            analisis = parsed if isinstance(parsed, self._esquema) else self._esquema.model_validate(parsed)
            validar_coherencia(analisis)  # AnalisisIncoherenteError es una RespuestaInvalidaError
            latencia = int((time.perf_counter() - inicio) * 1000)
            self._notificar(latencia, True, None, tokens_in, tokens_out)
            return analisis, latencia, tokens_in, tokens_out  # type: ignore[return-value]
        except ValidationError as e:
            self._notificar(int((time.perf_counter() - inicio) * 1000), False, "RespuestaInvalidaError",
                            tokens_in, tokens_out)
            raise RespuestaInvalidaError("La respuesta del modelo no pasó la validación.") from e
        except ErrorClasificacion as e:
            self._notificar(int((time.perf_counter() - inicio) * 1000), False, type(e).__name__,
                            tokens_in, tokens_out)
            raise

    def _notificar(self, latencia: int, exito: bool, error: str | None,
                   tokens_in: int | None, tokens_out: int | None) -> None:
        # Nunca se registra el texto de la opinión.
        log.info("llm proveedor=%s modelo=%s latencia_ms=%d exito=%s error=%s tokens=%s/%s",
                 self._proveedor, self._nombre_modelo, latencia, exito, error, tokens_in, tokens_out)
        if self._observador is None:
            return
        try:
            self._observador(MetricaLlamada(
                fecha_utc=iso(RelojSistema().ahora()), proveedor=self._proveedor, modelo=self._nombre_modelo,
                version_prompt=self._version, latencia_ms=latencia, exito=exito, tipo_error=error,
                tokens_entrada=tokens_in, tokens_salida=tokens_out,
            ))
        except Exception:  # noqa: BLE001 - las métricas nunca rompen la clasificación
            log.warning("No se pudo registrar la métrica de la llamada.")


def crear_clasificador(
    aj: Ajustes,
    jerga_para: Callable[[str], str],
    observador: Callable[[MetricaLlamada], None] | None = None,
    version_prompt: str | None = None,
) -> ClasificadorLangChain:
    nombre = aj.GEMINI_MODEL if aj.LLM_PROVIDER == "gemini" else aj.OLLAMA_MODEL
    return ClasificadorLangChain(
        crear_modelo(aj), proveedor=aj.LLM_PROVIDER, nombre_modelo=nombre,
        version_prompt=version_prompt or aj.VERSION_PROMPT, jerga_para=jerga_para, observador=observador,
    )
