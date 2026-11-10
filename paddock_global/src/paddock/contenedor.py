"""Inyección de dependencias: arma los adaptadores según ``Ajustes``.

- ``STORAGE_BACKEND=json`` (modo taller): catálogo y opiniones en JSON, sin cuentas; limitador,
  auditoría y métricas en memoria.
- ``STORAGE_BACKEND=sql``: todo en SQLite/PostgreSQL (SQLAlchemy), con cuentas y roles.

La interfaz, la API, el worker y los scripts piden aquí los casos de uso; ninguno crea adaptadores.
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
from paddock.aplicacion.gestionar_catalogo import GestionarCatalogo
from paddock.aplicacion.obtener_estadisticas import ObtenerEstadisticas
from paddock.config import DATOS, Ajustes
from paddock.dominio.errores import FuncionNoDisponibleError
from paddock.puertos.clasificador import ClasificadorSentimiento
from paddock.puertos.servicios import GeneradorUuid4, RelojSistema


def _solo_sql(nombre: str) -> FuncionNoDisponibleError:
    return FuncionNoDisponibleError(f"«{nombre}» requiere STORAGE_BACKEND=sql.")


@dataclass
class Contenedor:
    ajustes: Ajustes
    clasificador_forzado: ClasificadorSentimiento | None = None
    resumidor_forzado: Any = None
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

    @cached_property
    def bd(self) -> Any:
        if not self.modo_sql:
            raise _solo_sql("La base de datos")
        from paddock.adaptadores.persistencia.sql_repo import BaseDatos

        return BaseDatos(self.ajustes.url_bd)

    def _sql(self, clase: str) -> Any:
        from paddock.adaptadores.persistencia import sql_repo

        return getattr(sql_repo, clase)(self.bd)

    # ------------------------------------------------------------ persistencia
    @cached_property
    def repo_catalogo(self) -> Any:
        if self.modo_sql:
            return self._sql("SqlRepositorioCatalogo")
        return RepositorioCatalogoJson(self.ajustes.ruta_catalogo, self.ajustes.ruta_jerga)

    @cached_property
    def repo_opiniones(self) -> Any:
        if self.modo_sql:
            return self._sql("SqlRepositorioOpiniones")
        return RepositorioOpinionesJson(self.ajustes.ruta_opiniones)

    @cached_property
    def repo_limites(self) -> Any:
        return self._sql("SqlRepositorioLimites") if self.modo_sql else RepositorioLimitesMemoria()

    @cached_property
    def repo_auditoria(self) -> Any:
        return self._sql("SqlRepositorioAuditoria") if self.modo_sql else RepositorioAuditoriaMemoria()

    @cached_property
    def repo_metricas(self) -> Any:
        return self._sql("SqlRepositorioMetricas") if self.modo_sql else RepositorioMetricasMemoria()

    @cached_property
    def repo_usuarios(self) -> Any:
        if not self.modo_sql:
            raise _solo_sql("Las cuentas de usuario")
        return self._sql("SqlRepositorioUsuarios")

    @cached_property
    def repo_tokens(self) -> Any:
        if not self.modo_sql:
            raise _solo_sql("Los tokens de API")
        return self._sql("SqlRepositorioTokens")

    @cached_property
    def repo_trabajos(self) -> Any:
        if not self.modo_sql:
            raise _solo_sql("La clasificación por lotes")
        return self._sql("SqlRepositorioTrabajos")

    @cached_property
    def repo_resumenes(self) -> Any:
        if not self.modo_sql:
            raise _solo_sql("Los resúmenes de comunidad")
        return self._sql("SqlRepositorioResumenes")

    @cached_property
    def repo_denuncias(self) -> Any:
        if not self.modo_sql:
            raise _solo_sql("Las denuncias")
        return self._sql("SqlRepositorioDenuncias")

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

    @cached_property
    def hasher(self) -> Any:
        from paddock.adaptadores.seguridad.hash import HasherArgon2

        return HasherArgon2()

    @cached_property
    def contrasenas_comunes(self) -> set[str]:
        ruta = DATOS / "contrasenas_comunes.txt"
        if not ruta.exists():
            return set()
        return {linea.strip().lower() for linea in ruta.read_text(encoding="utf-8").splitlines() if linea.strip()}

    def hash_ip(self, ip: str | None) -> str | None:
        from paddock.adaptadores.seguridad.hash import hash_ip

        return hash_ip(ip, self.ajustes.SAL_HASH_IP.get_secret_value() or "sin-sal")

    # ------------------------------------------------------------ casos de uso
    @cached_property
    def emitir_opinion(self) -> EmitirOpinion:
        return EmitirOpinion(
            catalogo=self.repo_catalogo, opiniones=self.repo_opiniones, clasificador=self.clasificador,
            reloj=self.reloj, limitador=self.limitador, auditoria=self.repo_auditoria,
            exigir_sesion=self.exigir_sesion_para_emitir,
        )

    @cached_property
    def consultar_opiniones(self) -> ConsultarOpiniones:
        return ConsultarOpiniones(opiniones=self.repo_opiniones, catalogo=self.repo_catalogo,
                                  permitir_anonimos=self.ajustes.PERMITIR_ANONIMOS or not self.modo_sql)

    @cached_property
    def estadisticas(self) -> ObtenerEstadisticas:
        return ObtenerEstadisticas(self.consultar_opiniones)

    @cached_property
    def cuentas(self) -> Any:
        from paddock.aplicacion.usuarios import ServicioCuentas

        return ServicioCuentas(
            usuarios=self.repo_usuarios, opiniones=self.repo_opiniones, auditoria=self.repo_auditoria,
            hasher=self.hasher, reloj=self.reloj, ids=self.generador_id,
            contrasenas_comunes=self.contrasenas_comunes, registro_abierto=self.ajustes.REGISTRO_ABIERTO,
        )

    @cached_property
    def gestionar_catalogo(self) -> GestionarCatalogo:
        return GestionarCatalogo(catalogo=self.repo_catalogo, auditoria=self.repo_auditoria, reloj=self.reloj)

    # ------------------------------------------------------------ v3
    @cached_property
    def resumidor(self) -> Any:
        if self.resumidor_forzado is not None:
            return self.resumidor_forzado
        from paddock.adaptadores.llm.resumidor import crear_resumidor

        return crear_resumidor(self.ajustes)

    @cached_property
    def moderacion(self) -> Any:
        from paddock.aplicacion.moderacion import Moderacion

        return Moderacion(opiniones=self.repo_opiniones, denuncias=self.repo_denuncias, auditoria=self.repo_auditoria,
                          reloj=self.reloj, ids=self.generador_id)

    @cached_property
    def calidad(self) -> Any:
        from paddock.aplicacion.calidad import CalidadModelo

        return CalidadModelo(opiniones=self.repo_opiniones, metricas=self.repo_metricas)

    @cached_property
    def clasificar_lote(self) -> Any:
        from paddock.aplicacion.clasificar_lote import ClasificarLote

        return ClasificarLote(catalogo=self.repo_catalogo, trabajos=self.repo_trabajos, auditoria=self.repo_auditoria,
                              reloj=self.reloj, ids=self.generador_id)

    @cached_property
    def procesador_lotes(self) -> Any:
        from paddock.aplicacion.clasificar_lote import ProcesadorLotes

        return ProcesadorLotes(trabajos=self.repo_trabajos, opiniones=self.repo_opiniones, emitir=self.emitir_opinion,
                               limitador=self.limitador, pausa_s=self.ajustes.LOTE_PAUSA_S)

    @cached_property
    def resumir_comunidad(self) -> Any:
        from paddock.aplicacion.resumir_comunidad import ResumirComunidad

        return ResumirComunidad(catalogo=self.repo_catalogo, opiniones=self.repo_opiniones,
                                resumenes=self.repo_resumenes, resumidor=self.resumidor, reloj=self.reloj,
                                limitador=self.limitador, auditoria=self.repo_auditoria)

    @cached_property
    def informes(self) -> Any:
        from functools import partial

        from paddock.adaptadores.informes.pdf import generar_pdf
        from paddock.aplicacion.generar_informe import GenerarInforme

        return GenerarInforme(catalogo=self.repo_catalogo, opiniones=self.repo_opiniones,
                              resumenes=self.repo_resumenes if self.modo_sql else None, reloj=self.reloj,
                              renderizar=partial(generar_pdf, zona=self.ajustes.ZONA_HORARIA),
                              permitir_anonimos=self.ajustes.PERMITIR_ANONIMOS or not self.modo_sql)

    @cached_property
    def tokens_api(self) -> Any:
        from paddock.adaptadores.seguridad.hash import hash_token, nuevo_token_api
        from paddock.aplicacion.tokens_api import TokensApi

        return TokensApi(tokens=self.repo_tokens, usuarios=self.repo_usuarios, auditoria=self.repo_auditoria,
                         reloj=self.reloj, ids=self.generador_id, generar=nuevo_token_api, hashear=hash_token)


def crear_contenedor(ajustes: Ajustes | None = None, **kwargs: Any) -> Contenedor:
    from paddock.config import obtener_ajustes

    return Contenedor(ajustes=ajustes or obtener_ajustes(), **kwargs)
