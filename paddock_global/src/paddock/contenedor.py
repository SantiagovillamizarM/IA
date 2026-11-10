"""Inyección de dependencias: arma los adaptadores según ``Ajustes``.

La interfaz, la API, el worker y los scripts piden aquí los casos de uso; ninguno crea
adaptadores por su cuenta.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import cached_property
from typing import Any

from paddock.adaptadores.llm.jerga import crear_jerga_para
from paddock.adaptadores.persistencia.json_repo import RepositorioCatalogoJson, RepositorioOpinionesJson
from paddock.adaptadores.persistencia.memoria import (
    RepositorioAuditoriaMemoria,
    RepositorioLimitesMemoria,
    RepositorioMetricasMemoria,
)
from paddock.adaptadores.seguridad.limitador import LimitadorTasa
from paddock.aplicacion.consultar_opiniones import ConsultarOpiniones
from paddock.aplicacion.emitir_opinion import EmitirOpinion
from paddock.config import Ajustes
from paddock.puertos.clasificador import ClasificadorSentimiento
from paddock.puertos.servicios import GeneradorUuid4, RelojSistema


@dataclass
class Contenedor:
    ajustes: Ajustes
    clasificador_forzado: ClasificadorSentimiento | None = None
    _extra: dict[str, Any] = field(default_factory=dict)

    # ------------------------------------------------------------ servicios básicos
    @cached_property
    def reloj(self) -> RelojSistema:
        return RelojSistema()

    @cached_property
    def generador_id(self) -> GeneradorUuid4:
        return GeneradorUuid4()

    @property
    def modo_sql(self) -> bool:
        return self.ajustes.STORAGE_BACKEND == "sql"

    @property
    def exigir_sesion_para_emitir(self) -> bool:
        """Modo taller (JSON): sin cuentas. Modo SQL: emitir exige sesión."""
        return self.modo_sql

    # ------------------------------------------------------------ persistencia
    @cached_property
    def repo_catalogo(self) -> Any:
        return RepositorioCatalogoJson(self.ajustes.ruta_catalogo, self.ajustes.ruta_jerga)

    @cached_property
    def repo_opiniones(self) -> Any:
        return RepositorioOpinionesJson(self.ajustes.ruta_opiniones)

    @cached_property
    def repo_limites(self) -> Any:
        return RepositorioLimitesMemoria()

    @cached_property
    def repo_auditoria(self) -> Any:
        return RepositorioAuditoriaMemoria()

    @cached_property
    def repo_metricas(self) -> Any:
        return RepositorioMetricasMemoria()

    # ------------------------------------------------------------ LLM
    def jerga_para(self, disciplina_id: str) -> str:
        return crear_jerga_para(self.repo_catalogo.obtener_jerga)(disciplina_id)

    @cached_property
    def clasificador(self) -> ClasificadorSentimiento:
        if self.clasificador_forzado is not None:
            return self.clasificador_forzado
        from paddock.adaptadores.llm.cadena import crear_clasificador

        return crear_clasificador(self.ajustes, self.jerga_para, observador=self.repo_metricas.registrar)

    def verificar_proveedor(self) -> tuple[bool, str]:
        from paddock.adaptadores.llm.cadena import verificar_proveedor

        return verificar_proveedor(self.ajustes)

    # ------------------------------------------------------------ seguridad
    @cached_property
    def limitador(self) -> LimitadorTasa:
        return LimitadorTasa(
            self.repo_limites, self.reloj,
            por_usuario_5min=self.ajustes.LIMITE_OPINIONES_5MIN, global_diario=self.ajustes.LIMITE_LLM_DIARIO,
        )

    # ------------------------------------------------------------ casos de uso
    @cached_property
    def emitir_opinion(self) -> EmitirOpinion:
        return EmitirOpinion(
            catalogo=self.repo_catalogo, opiniones=self.repo_opiniones, clasificador=self.clasificador,
            reloj=self.reloj, limitador=self.limitador, auditoria=self.repo_auditoria,
            exigir_sesion=False,
        )

    @cached_property
    def consultar_opiniones(self) -> ConsultarOpiniones:
        return ConsultarOpiniones(opiniones=self.repo_opiniones, catalogo=self.repo_catalogo, permitir_anonimos=True)


def crear_contenedor(ajustes: Ajustes | None = None, **kwargs: Any) -> Contenedor:
    from paddock.config import obtener_ajustes

    return Contenedor(ajustes=ajustes or obtener_ajustes(), **kwargs)
