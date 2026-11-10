"""Contratos de salida del modelo (Pydantic). Son parte del dominio: no dependen de LangChain.

``AnalisisOpinion`` es el esquema del taller y no cambia. ``AnalisisDetallado`` lo extiende (v2).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, Field

Sentimiento = Literal["positivo", "negativo", "neutro", "mixto"]
Aspecto = Literal[
    "trazado", "organizacion", "ambiente", "estrategia", "clima",
    "reglamento", "pilotos_equipos", "vehiculos", "transmision", "seguridad", "otro",
]


class AnalisisOpinion(BaseModel):
    es_pertinente: bool = Field(description="Indica si el texto es una opinión sobre la carrera seleccionada")
    sentimiento: Sentimiento | None = Field(description="Categoría; null si no es pertinente")
    razon: str = Field(
        min_length=1, max_length=300, description="Justificación breve, en español y en tercera persona"
    )


class AspectoValorado(BaseModel):
    aspecto: Aspecto
    sentimiento: Literal["positivo", "negativo", "neutro"]


class AnalisisDetallado(AnalisisOpinion):
    aspectos: list[AspectoValorado] = Field(default_factory=list, max_length=6)
    ironia: bool = Field(description="True si el texto usa ironía o sarcasmo")
    intensidad: int | None = Field(
        default=None, ge=1, le=5, description="1 = tibia, 5 = muy fuerte; null si no es pertinente"
    )
    entidades: list[str] = Field(
        default_factory=list, max_length=10,
        description="Pilotos, equipos o marcas mencionados literalmente en el texto",
    )


@dataclass(frozen=True)
class ResultadoClasificacion:
    """Lo que devuelve un ``ClasificadorSentimiento``: el análisis y los metadatos de la llamada."""

    analisis: AnalisisOpinion
    modelo: str  # «proveedor/modelo», p. ej. «ollama/qwen2.5:3b»
    version_prompt: str
    latencia_ms: int = 0
    tokens_entrada: int | None = None
    tokens_salida: int | None = None
    intentos: int = 1
