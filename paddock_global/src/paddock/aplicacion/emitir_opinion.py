"""Caso de uso: emitir una opinión.

Flujo: ``validar_texto`` → limitador → clasificador (LLM) → Pydantic + ``validar_coherencia``
→ ``crear_registro`` → ``RepositorioOpiniones.guardar`` (idempotente por id).
Cualquier fallo corta el flujo, se propaga y **no** se guarda nada.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Literal

from paddock.aplicacion.autorizacion import Actor
from paddock.dominio.analisis import AnalisisOpinion
from paddock.dominio.entidades import Evento, Opinion
from paddock.dominio.errores import EventoNoEncontradoError, SesionRequeridaError
from paddock.dominio.reglas import (
    crear_registro,
    detectar_inyeccion,
    validar_coherencia,
    validar_edicion,
    validar_texto,
)
from paddock.puertos.clasificador import ClasificadorSentimiento
from paddock.puertos.repositorios import RepositorioAuditoria, RepositorioCatalogo, RepositorioOpiniones
from paddock.puertos.servicios import Limitador, Reloj, iso

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class SolicitudOpinion:
    texto: str
    evento_id: str
    registro_id: str  # lo genera la interfaz UNA sola vez por envío (evita duplicar en un rerun)
    edicion_anio: int | None = None
    origen: str = "chat"


@dataclass(frozen=True)
class ResultadoEmision:
    estado: Literal["guardada", "duplicada", "no_pertinente"]
    analisis: AnalisisOpinion
    evento: Evento
    modelo: str
    registro: Opinion | None = None
    latencia_ms: int = 0


class EmitirOpinion:
    def __init__(
        self,
        *,
        catalogo: RepositorioCatalogo,
        opiniones: RepositorioOpiniones,
        clasificador: ClasificadorSentimiento,
        reloj: Reloj,
        limitador: Limitador | None = None,
        auditoria: RepositorioAuditoria | None = None,
        exigir_sesion: bool = False,
    ) -> None:
        self.catalogo = catalogo
        self.opiniones = opiniones
        self.clasificador = clasificador
        self.reloj = reloj
        self.limitador = limitador
        self.auditoria = auditoria
        self.exigir_sesion = exigir_sesion

    def ejecutar(self, solicitud: SolicitudOpinion, actor: Actor | None = None,
                 sujeto_limite: str | None = None, aplicar_limite: bool = True) -> ResultadoEmision:
        if self.exigir_sesion and actor is None:
            raise SesionRequeridaError("Debes iniciar sesión para emitir opiniones.")

        # 1. Validación de entrada (sin modelo)
        texto = validar_texto(solicitud.texto)
        edicion = validar_edicion(solicitud.edicion_anio, self.reloj.ahora().year)
        catalogo = self.catalogo.obtener()
        evento = catalogo.evento(solicitud.evento_id)
        if evento is None or not evento.activo:
            raise EventoNoEncontradoError("La carrera seleccionada no existe o no está disponible.")
        disciplina = catalogo.disciplina_de_evento(evento)

        # 2. Limitador de tasa (antes de llamar al modelo)
        if self.limitador is not None and aplicar_limite:
            sujeto = actor.usuario_id if actor else (sujeto_limite or "anonimo")
            self.limitador.verificar_y_registrar(sujeto)

        # 3. Heurística de inyección: solo se registra, nunca bloquea (LLM01)
        if detectar_inyeccion(texto) and self.auditoria is not None:
            self.auditoria.registrar(
                fecha_utc=iso(self.reloj.ahora()), usuario_id=actor.usuario_id if actor else None,
                accion="posible_inyeccion_prompt", detalle={"evento_id": evento.id, "longitud": len(texto)},
            )

        # 4. Clasificación (lanza ErrorClasificacion; nunca hay sentimiento por defecto)
        resultado = self.clasificador.clasificar(
            texto=texto, carrera=evento.nombre, disciplina=disciplina.nombre,
            disciplina_id=disciplina.id, edicion=edicion,
        )
        analisis = resultado.analisis
        validar_coherencia(analisis)

        if not analisis.es_pertinente:
            return ResultadoEmision(estado="no_pertinente", analisis=analisis, evento=evento,
                                    modelo=resultado.modelo, latencia_ms=resultado.latencia_ms)

        # 5. Registro y guardado idempotente
        registro = crear_registro(
            registro_id=solicitud.registro_id, fecha_utc=iso(self.reloj.ahora()), evento=evento,
            disciplina=disciplina, texto=texto, analisis=analisis, modelo=resultado.modelo,
            version_prompt=resultado.version_prompt, edicion_anio=edicion,
            usuario_id=actor.usuario_id if actor else None, origen=solicitud.origen,
        )
        insertado = self.opiniones.guardar(registro)
        return ResultadoEmision(
            estado="guardada" if insertado else "duplicada", analisis=analisis, evento=evento,
            modelo=resultado.modelo, registro=registro, latencia_ms=resultado.latencia_ms,
        )
