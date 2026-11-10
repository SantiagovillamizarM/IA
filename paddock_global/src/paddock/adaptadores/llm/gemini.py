"""Proveedor de producción: Google Gemini vía ``langchain-google-genai``.

La clave se lee de ``Ajustes.GOOGLE_API_KEY`` (``SecretStr``) y nunca aparece en mensajes ni logs.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from langchain_core.language_models import BaseChatModel

    from paddock.config import Ajustes

_CACHE_VERIFICACION: dict[tuple[str, int], tuple[float, tuple[bool, str]]] = {}
_TTL_S = 300  # como mucho una llamada de verificación cada 5 minutos


def crear_modelo_gemini(aj: Ajustes) -> BaseChatModel:
    from langchain_google_genai import ChatGoogleGenerativeAI

    return ChatGoogleGenerativeAI(
        model=aj.GEMINI_MODEL,
        google_api_key=aj.GOOGLE_API_KEY.get_secret_value(),
        temperature=aj.LLM_TEMPERATURE,
        timeout=60,
        max_retries=0,
        # Verificado el 2026-11-10: con la API «v1» Gemini responde 400 «Developer instruction is
        # not enabled for api version v1» al recibir el mensaje de sistema. «v1beta» sí lo admite.
        api_version="v1beta",
    )


def verificar_gemini(aj: Ajustes) -> tuple[bool, str]:
    """Comprueba que haya clave y consulta los metadatos del modelo (sin generar tokens).

    El resultado se cachea 5 minutos. Nunca muestra la clave.
    """
    if not aj.hay_clave_gemini:
        return False, "Falta GOOGLE_API_KEY en el archivo .env."
    clave_cache = (aj.GEMINI_MODEL, hash(aj.GOOGLE_API_KEY.get_secret_value()))
    ahora = time.monotonic()
    guardado = _CACHE_VERIFICACION.get(clave_cache)
    if guardado and ahora - guardado[0] < _TTL_S:
        return guardado[1]
    resultado = _consultar_modelo(aj)
    _CACHE_VERIFICACION[clave_cache] = (ahora, resultado)
    return resultado


def _consultar_modelo(aj: Ajustes) -> tuple[bool, str]:
    try:
        from google import genai
        from google.genai import errors

        cliente = genai.Client(api_key=aj.GOOGLE_API_KEY.get_secret_value())
        cliente.models.get(model=aj.GEMINI_MODEL)
        return True, f"Gemini listo con {aj.GEMINI_MODEL}."
    except errors.ClientError as e:
        texto = str(e).lower()
        if e.code in (401, 403) or "api key" in texto or "api_key" in texto:
            return False, "La clave de Gemini no es válida. Revisa GOOGLE_API_KEY."
        if e.code == 404:
            return False, f"El modelo «{aj.GEMINI_MODEL}» no existe. Revisa GEMINI_MODEL."
        if e.code == 429:
            return False, "Se superó la cuota de Gemini. Intenta más tarde."
        return False, "Gemini rechazó la verificación. Revisa la configuración."
    except Exception:
        return False, "Gemini no responde. Revisa la conexión a internet e intenta más tarde."
