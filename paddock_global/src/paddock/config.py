"""Configuración única de la aplicación: ``Ajustes`` lee ``.env`` y valida los tipos.

Las rutas relativas se resuelven contra la raíz del proyecto (``RAIZ``), no contra el
directorio desde el que se arranca Streamlit.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# PADDOCK_RAIZ permite fijar la raíz cuando el paquete no se ejecuta desde src/ (p. ej. en Docker).
RAIZ: Path = Path(os.environ.get("PADDOCK_RAIZ") or Path(__file__).resolve().parents[2])
DATOS: Path = RAIZ / "datos"
EVIDENCIAS: Path = RAIZ / "evidencias"


class Ajustes(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=RAIZ / ".env", env_file_encoding="utf-8", extra="ignore", case_sensitive=True
    )

    # --- LLM
    LLM_PROVIDER: Literal["gemini", "ollama"] = "ollama"
    LLM_TEMPERATURE: float = Field(default=0.0, ge=0.0, le=2.0)
    LLM_FALLBACK: Literal["none"] = "none"
    GOOGLE_API_KEY: SecretStr = SecretStr("")
    GEMINI_MODEL: str = "gemini-2.5-flash"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen2.5:3b"
    VERSION_PROMPT: Literal["1.0", "2.0"] = "2.0"

    # --- persistencia
    STORAGE_BACKEND: Literal["json", "sql"] = "json"
    OPINIONES_JSON: str = "datos/opiniones.json"
    CATALOGO_JSON: str = "datos/catalogo.json"
    JERGA_JSON: str = "datos/jerga.json"
    DATABASE_URL: str = "sqlite:///datos/paddock.db"
    POSTGRES_PASSWORD: SecretStr = SecretStr("")

    # --- seguridad y uso
    PERMITIR_ANONIMOS: bool = True
    REGISTRO_ABIERTO: bool = True
    SESION_MINUTOS: int = Field(default=60, ge=1)
    LIMITE_OPINIONES_5MIN: int = Field(default=10, ge=1)
    LIMITE_LLM_DIARIO: int = Field(default=1000, ge=1)
    SAL_HASH_IP: SecretStr = SecretStr("")
    ZONA_HORARIA: str = "America/Bogota"
    API_DOCS: bool = False
    PROXY_CONFIABLE: str = "127.0.0.1"

    # --- lotes y resúmenes (v3)
    LOTE_PAUSA_S: float = Field(default=1.0, ge=0.0)
    WORKER_INTERVALO_S: float = Field(default=5.0, ge=0.5)
    SEMILLA_PAUSA_S: float = Field(default=0.0, ge=0.0)

    @field_validator("OLLAMA_BASE_URL")
    @classmethod
    def _sin_barra_final(cls, v: str) -> str:
        return v.rstrip("/")

    # --- derivados
    @property
    def ruta_opiniones(self) -> Path:
        return _resolver(self.OPINIONES_JSON)

    @property
    def ruta_catalogo(self) -> Path:
        return _resolver(self.CATALOGO_JSON)

    @property
    def ruta_jerga(self) -> Path:
        return _resolver(self.JERGA_JSON)

    @property
    def url_bd(self) -> str:
        """``DATABASE_URL`` con la ruta de SQLite resuelta y el driver pg8000 para PostgreSQL."""
        url = self.DATABASE_URL
        if url.startswith("sqlite:///") and not url.startswith("sqlite:////") and ":memory:" not in url:
            ruta = url.removeprefix("sqlite:///")
            if not Path(ruta).is_absolute():
                return f"sqlite:///{(RAIZ / ruta).as_posix()}"
        if url.startswith("postgresql://") or url.startswith("postgres://"):
            return "postgresql+pg8000://" + url.split("://", 1)[1]
        return url

    @property
    def modelo_activo(self) -> str:
        nombre = self.GEMINI_MODEL if self.LLM_PROVIDER == "gemini" else self.OLLAMA_MODEL
        return f"{self.LLM_PROVIDER}/{nombre}"

    @property
    def hay_clave_gemini(self) -> bool:
        clave = self.GOOGLE_API_KEY.get_secret_value().strip()
        return bool(clave) and clave not in {"pon-tu-clave-aqui", "tu_clave_de_google_ai_studio"}


def _resolver(ruta: str) -> Path:
    p = Path(ruta)
    return p if p.is_absolute() else (RAIZ / p).resolve()


@lru_cache(maxsize=1)
def obtener_ajustes() -> Ajustes:
    return Ajustes()
