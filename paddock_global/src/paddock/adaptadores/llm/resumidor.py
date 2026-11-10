"""Resumidor LangChain con map-reduce: grupos de 30 opiniones → resúmenes parciales → resumen final."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Any

from langchain_core.output_parsers import StrOutputParser

from paddock.adaptadores.llm import prompts
from paddock.adaptadores.llm.cadena import crear_modelo, traducir_error
from paddock.dominio.errores import RespuestaInvalidaError

if TYPE_CHECKING:
    from langchain_core.language_models import BaseChatModel

    from paddock.config import Ajustes

TAM_GRUPO = 30


def _bloque(opiniones: Sequence[tuple[str, str]]) -> str:
    # Cada opinión va en una línea con su etiqueta; los delimitadores del usuario se neutralizan.
    return "\n".join(f"- [{s}] {prompts.neutralizar_delimitadores(t)}" for s, t in opiniones)


class ResumidorLangChain:
    def __init__(self, modelo_chat: BaseChatModel, *, proveedor: str, nombre_modelo: str) -> None:
        self._proveedor = proveedor
        self._nombre = nombre_modelo
        self._final = prompts.plantilla_resumen() | modelo_chat | StrOutputParser()
        self._parcial = prompts.plantilla_resumen_parcial() | modelo_chat | StrOutputParser()

    @property
    def modelo(self) -> str:
        return f"{self._proveedor}/{self._nombre}"

    @property
    def version_prompt(self) -> str:
        return prompts.VERSION_PROMPT_RESUMEN

    def _invocar(self, cadena: Any, entrada: dict[str, Any]) -> str:
        try:
            texto = cadena.invoke(entrada)
        except Exception as e:  # noqa: BLE001 - se traduce a un error propio
            raise traducir_error(e, self._proveedor, self._nombre) from e
        if not isinstance(texto, str) or not texto.strip():
            raise RespuestaInvalidaError("El modelo devolvió un resumen vacío.")
        return texto.strip()

    def resumir(self, *, carrera: str, edicion: int | None, opiniones: Sequence[tuple[str, str]]) -> str:
        ed = str(edicion) if edicion else "todas"
        if len(opiniones) <= TAM_GRUPO:
            return self._invocar(self._final, {"carrera": carrera, "edicion": ed, "n": len(opiniones),
                                               "opiniones": _bloque(opiniones)})
        parciales = []
        for i in range(0, len(opiniones), TAM_GRUPO):
            grupo = opiniones[i:i + TAM_GRUPO]
            parciales.append(self._invocar(self._parcial, {"carrera": carrera, "opiniones": _bloque(grupo)}))
        unido = "\n\n".join(f"Grupo {k + 1}:\n{p}" for k, p in enumerate(parciales))
        return self._invocar(self._final, {"carrera": carrera, "edicion": ed, "n": len(opiniones), "opiniones": unido})


def crear_resumidor(aj: Ajustes) -> ResumidorLangChain:
    nombre = aj.GEMINI_MODEL if aj.LLM_PROVIDER == "gemini" else aj.OLLAMA_MODEL
    return ResumidorLangChain(crear_modelo(aj), proveedor=aj.LLM_PROVIDER, nombre_modelo=nombre)


class ResumidorFalso:
    """Determinista, para tests: cuenta opiniones por categoría."""

    def __init__(self) -> None:
        self.llamadas = 0

    @property
    def modelo(self) -> str:
        return "falso/resumidor"

    @property
    def version_prompt(self) -> str:
        return prompts.VERSION_PROMPT_RESUMEN

    def resumir(self, *, carrera: str, edicion: int | None, opiniones: Sequence[tuple[str, str]]) -> str:
        self.llamadas += 1
        pos = sum(1 for s, _ in opiniones if s == "positivo")
        neg = sum(1 for s, _ in opiniones if s == "negativo")
        return (f"Este resumen se basa en {len(opiniones)} opiniones registradas en Paddock Global. "
                f"Lo que se elogia: {pos} opiniones positivas. Lo que se critica: {neg} opiniones negativas.")
