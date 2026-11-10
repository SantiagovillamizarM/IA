"""Fixtures comunes. Ningún test llama a Gemini ni a Ollama: se usa ``ClasificadorFalso``."""

from __future__ import annotations

import shutil
from datetime import UTC, datetime
from pathlib import Path

import pytest

from paddock.adaptadores.llm.falso import ClasificadorFalso
from paddock.adaptadores.persistencia.json_repo import RepositorioCatalogoJson, RepositorioOpinionesJson
from paddock.adaptadores.persistencia.memoria import (
    RepositorioAuditoriaMemoria,
    RepositorioLimitesMemoria,
)
from paddock.adaptadores.seguridad.limitador import LimitadorTasa
from paddock.aplicacion.emitir_opinion import EmitirOpinion
from paddock.config import DATOS
from paddock.dominio.entidades import Opinion


class RelojFijo:
    def __init__(self, ahora: datetime | None = None) -> None:
        self._ahora = ahora or datetime(2026, 11, 9, 15, 30, tzinfo=UTC)

    def ahora(self) -> datetime:
        return self._ahora

    def avanzar(self, **kwargs: float) -> None:
        from datetime import timedelta

        self._ahora = self._ahora + timedelta(**kwargs)


@pytest.fixture
def reloj() -> RelojFijo:
    return RelojFijo()


@pytest.fixture
def dir_datos(tmp_path: Path) -> Path:
    d = tmp_path / "datos"
    d.mkdir()
    shutil.copy(DATOS / "catalogo.json", d / "catalogo.json")
    shutil.copy(DATOS / "jerga.json", d / "jerga.json")
    return d


@pytest.fixture
def repo_catalogo(dir_datos: Path) -> RepositorioCatalogoJson:
    return RepositorioCatalogoJson(dir_datos / "catalogo.json", dir_datos / "jerga.json")


@pytest.fixture
def ruta_opiniones(dir_datos: Path) -> Path:
    return dir_datos / "opiniones.json"


@pytest.fixture
def repo_json(ruta_opiniones: Path) -> RepositorioOpinionesJson:
    return RepositorioOpinionesJson(ruta_opiniones)


@pytest.fixture
def clasificador() -> ClasificadorFalso:
    return ClasificadorFalso(detallado=False)


@pytest.fixture
def auditoria() -> RepositorioAuditoriaMemoria:
    return RepositorioAuditoriaMemoria()


@pytest.fixture
def emitir(repo_catalogo, repo_json, clasificador, reloj, auditoria) -> EmitirOpinion:
    limitador = LimitadorTasa(RepositorioLimitesMemoria(), reloj, por_usuario_5min=10, global_diario=1000)
    return EmitirOpinion(catalogo=repo_catalogo, opiniones=repo_json, clasificador=clasificador, reloj=reloj,
                         limitador=limitador, auditoria=auditoria)


def opinion_ejemplo(i: int = 1, **cambios) -> Opinion:
    base = Opinion(
        id=f"00000000-0000-4000-8000-{i:012d}",
        fecha_utc=f"2026-11-0{1 + (i % 8)}T15:30:00+00:00",
        evento_id="ev-res-lemans",
        evento_nombre="24 Horas de Le Mans",
        disciplina_id="resistencia",
        edicion_anio=2026,
        opinion_original="La salida al amanecer es pura magia",
        sentimiento="positivo",
        razon="El aficionado expresa admiración.",
        modelo="falso/determinista",
        version_prompt="1.0",
    )
    return base.con(**cambios) if cambios else base
