"""Configuración central: rutas absolutas y parámetros de Ollama leídos de .env."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# Las rutas se calculan desde la ubicación de este archivo, no desde el
# directorio en el que se ejecuta Streamlit.
BASE_DIR: Path = Path(__file__).resolve().parent
DATOS_DIR: Path = BASE_DIR / "datos"
RUTA_CARRERAS: Path = DATOS_DIR / "carreras.json"
RUTA_OPINIONES: Path = DATOS_DIR / "opiniones.json"
EVIDENCIAS_DIR: Path = BASE_DIR / "evidencias"
RUTA_EVALUACION: Path = DATOS_DIR / "conjunto_evaluacion.json"
RUTA_RESULTADOS_COMPARACION: Path = EVIDENCIAS_DIR / "comparacion_modelos.json"

load_dotenv(BASE_DIR / ".env")

SENTIMIENTOS: tuple[str, ...] = ("positivo", "negativo", "neutro", "mixto")
LONGITUD_MIN: int = 5
LONGITUD_MAX: int = 1000


@dataclass(frozen=True)
class ConfigOllama:
    """Parámetros de conexión con el servidor local de Ollama."""

    OLLAMA_BASE_URL: str
    OLLAMA_MODEL: str
    OLLAMA_TEMPERATURE: float
    OLLAMA_MODEL_COMPARACION: str = "llama3.2:3b"

    @property
    def nombre_modelo(self) -> str:
        """Identificador que se guarda en cada registro."""
        return f"ollama/{self.OLLAMA_MODEL}"


def cargar_config() -> ConfigOllama:
    """Lee la configuración del entorno con valores por defecto seguros."""
    return ConfigOllama(
        OLLAMA_BASE_URL=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/"),
        OLLAMA_MODEL=os.getenv("OLLAMA_MODEL", "qwen2.5:3b"),
        OLLAMA_TEMPERATURE=float(os.getenv("OLLAMA_TEMPERATURE", "0")),
        OLLAMA_MODEL_COMPARACION=os.getenv("OLLAMA_MODEL_COMPARACION", "llama3.2:3b"),
    )


def config_con_modelo(cfg: ConfigOllama, modelo: str) -> ConfigOllama:
    """Copia de la configuración usando otro modelo (para comparar)."""
    from dataclasses import replace

    return replace(cfg, OLLAMA_MODEL=modelo)
