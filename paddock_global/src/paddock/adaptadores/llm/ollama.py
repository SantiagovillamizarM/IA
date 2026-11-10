"""Proveedor de desarrollo: Ollama local (``qwen2.5:3b`` por defecto) vía ``langchain-ollama``."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from langchain_core.language_models import BaseChatModel

    from paddock.config import Ajustes


def crear_modelo_ollama(aj: Ajustes) -> BaseChatModel:
    from langchain_ollama import ChatOllama

    return ChatOllama(
        model=aj.OLLAMA_MODEL,
        base_url=aj.OLLAMA_BASE_URL,
        temperature=aj.LLM_TEMPERATURE,
        num_ctx=2048,
        keep_alive="30m",
        client_kwargs={"timeout": 180},
    )


def modelos_instalados(base_url: str, timeout: float = 3.0) -> list[str]:
    """Nombres de modelos descargados según ``GET /api/tags``."""
    if not base_url.startswith(("http://", "https://")):
        raise ValueError("OLLAMA_BASE_URL debe empezar por http:// o https://")
    with urllib.request.urlopen(f"{base_url}/api/tags", timeout=timeout) as r:  # noqa: S310 (URL validada)
        datos = json.loads(r.read().decode("utf-8"))
    return [m.get("name", "") for m in datos.get("models", [])]


def _coincide(modelo: str, instalados: list[str]) -> bool:
    candidatos = {modelo, f"{modelo}:latest"} if ":" not in modelo else {modelo}
    return any(n in candidatos for n in instalados)


def verificar_ollama(aj: Ajustes) -> tuple[bool, str]:
    try:
        instalados = modelos_instalados(aj.OLLAMA_BASE_URL)
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        return False, (
            f"Ollama no responde en {aj.OLLAMA_BASE_URL}. Abre la app Ollama o ejecuta `ollama serve`."
        )
    except json.JSONDecodeError:
        return False, "Ollama respondió con un formato inesperado."
    if not _coincide(aj.OLLAMA_MODEL, instalados):
        return False, f"El modelo «{aj.OLLAMA_MODEL}» no está descargado. Ejecuta `ollama pull {aj.OLLAMA_MODEL}`."
    return True, f"Ollama listo con {aj.OLLAMA_MODEL}."
