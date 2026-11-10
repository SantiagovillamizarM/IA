"""Configuración central: rutas absolutas, catálogo de modelos y parámetros leídos de .env.

Los nombres de campo OLLAMA_* se conservan por compatibilidad con la versión base;
desde la ampliación «switch de IAs», OLLAMA_MODEL contiene el modelo del proveedor
indicado en PROVEEDOR («ollama» o «gemini») y OLLAMA_TEMPERATURE la temperatura.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, replace
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
PROVEEDORES: tuple[str, ...] = ("ollama", "gemini")

# Catálogo del switch de IAs. La clave es «proveedor:modelo».
MODELOS_DISPONIBLES: list[dict] = [
    {"clave": "ollama:qwen2.5:3b", "etiqueta": "🖥️ Qwen 2.5 3B · local"},
    {"clave": "ollama:llama3.2:3b", "etiqueta": "🖥️ Llama 3.2 3B · local"},
    {"clave": "gemini:gemini-3.5-flash", "etiqueta": "☁️ Gemini 3.5 Flash · nube"},
    {"clave": "gemini:gemini-3.5-flash-lite", "etiqueta": "☁️ Gemini 3.5 Flash-Lite · nube"},
]


def separar_clave(clave: str) -> tuple[str, str]:
    """«gemini:gemini-3.5-flash» → ("gemini", "gemini-3.5-flash"). Sin prefijo → Ollama."""
    proveedor, _, modelo = clave.partition(":")
    if proveedor in PROVEEDORES and modelo:
        return proveedor, modelo
    return "ollama", clave


def hay_clave_google() -> bool:
    return bool(os.getenv("GOOGLE_API_KEY", "").strip())


@dataclass(frozen=True)
class ConfigOllama:
    """Parámetros del modelo activo (local con Ollama o en la nube con Gemini)."""

    OLLAMA_BASE_URL: str
    OLLAMA_MODEL: str
    OLLAMA_TEMPERATURE: float
    OLLAMA_MODEL_COMPARACION: str = "llama3.2:3b"
    PROVEEDOR: str = "ollama"

    @property
    def nombre_modelo(self) -> str:
        """Identificador que se guarda en cada registro, p. ej. «ollama/qwen2.5:3b»."""
        return f"{self.PROVEEDOR}/{self.OLLAMA_MODEL}"

    @property
    def clave(self) -> str:
        return f"{self.PROVEEDOR}:{self.OLLAMA_MODEL}"

    @property
    def es_local(self) -> bool:
        return self.PROVEEDOR == "ollama"


def cargar_config() -> ConfigOllama:
    """Lee la configuración del entorno con valores por defecto seguros."""
    proveedor, modelo = separar_clave(os.getenv("OLLAMA_MODEL", "qwen2.5:3b"))
    return ConfigOllama(
        OLLAMA_BASE_URL=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/"),
        OLLAMA_MODEL=modelo,
        OLLAMA_TEMPERATURE=float(os.getenv("OLLAMA_TEMPERATURE", "0")),
        OLLAMA_MODEL_COMPARACION=os.getenv("OLLAMA_MODEL_COMPARACION", "llama3.2:3b"),
        PROVEEDOR=proveedor,
    )


def config_con_modelo(cfg: ConfigOllama, clave: str, temperatura: float | None = None) -> ConfigOllama:
    """Copia de la configuración con otro modelo («proveedor:modelo» o nombre de Ollama)."""
    proveedor, modelo = separar_clave(clave)
    cambios = {"OLLAMA_MODEL": modelo, "PROVEEDOR": proveedor}
    if temperatura is not None:
        cambios["OLLAMA_TEMPERATURE"] = float(temperatura)
    return replace(cfg, **cambios)


def etiqueta_modelo(clave: str) -> str:
    for m in MODELOS_DISPONIBLES:
        if m["clave"] == clave:
            return m["etiqueta"]
    proveedor, modelo = separar_clave(clave)
    return f"{'🖥️' if proveedor == 'ollama' else '☁️'} {modelo}"
