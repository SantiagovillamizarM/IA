"""Clasificación por lotes (v3).

- ``ClasificarLote.crear``: valida TODO el CSV (``evento_id``, ``edicion_anio``, ``opinion``; máx. 500 filas
  y 1 MB) antes de encolar. Si hay errores, no encola y los devuelve por fila.
- ``ProcesadorLotes.procesar``: lo ejecuta el worker. Ids deterministas (``uuid5`` del trabajo + fila), así
  que reprocesar no duplica. Un fallo en una fila no detiene el lote ni se registra como neutro. Respeta el
  tope diario global: si se alcanza, el trabajo queda pendiente y continúa después.
"""

from __future__ import annotations

import csv
import io
import logging
import time
import uuid
from dataclasses import dataclass
from typing import Any

from paddock.aplicacion.autorizacion import Actor, requerir_rol
from paddock.aplicacion.emitir_opinion import EmitirOpinion, SolicitudOpinion
from paddock.dominio.entidades import Catalogo, TrabajoLote
from paddock.dominio.enums import EstadoTrabajo, Rol
from paddock.dominio.errores import EntradaInvalidaError, ErrorPaddock, LimiteExcedidoError
from paddock.dominio.reglas import validar_edicion, validar_texto
from paddock.puertos.repositorios import (
    RepositorioAuditoria,
    RepositorioCatalogo,
    RepositorioOpiniones,
    RepositorioTrabajos,
)
from paddock.puertos.servicios import GeneradorId, Limitador, Reloj, iso

log = logging.getLogger(__name__)

MAX_FILAS = 500
MAX_BYTES = 1_000_000
COLUMNAS = ("evento_id", "edicion_anio", "opinion")
ESPACIO_LOTES = uuid.UUID("6f1c9b0e-6c1e-4f9a-9a57-5a2d1b7c3e10")


def id_fila(trabajo_id: str, numero: int) -> str:
    """Id determinista de la opinión de una fila: reprocesar el mismo trabajo no duplica."""
    return str(uuid.uuid5(ESPACIO_LOTES, f"{trabajo_id}:{numero}"))


@dataclass(frozen=True)
class ResultadoValidacion:
    filas: list[dict[str, Any]]
    errores: list[dict[str, Any]]

    @property
    def valido(self) -> bool:
        return not self.errores and bool(self.filas)


def validar_csv(contenido: bytes, catalogo: Catalogo, anio_actual: int) -> ResultadoValidacion:
    errores: list[dict[str, Any]] = []
    if len(contenido) > MAX_BYTES:
        return ResultadoValidacion([], [{"fila": 0, "error": "El archivo supera 1 MB."}])
    try:
        texto = contenido.decode("utf-8-sig")
    except UnicodeDecodeError:
        return ResultadoValidacion([], [{"fila": 0, "error": "El archivo no está en UTF-8."}])
    lector = csv.DictReader(io.StringIO(texto))
    if lector.fieldnames is None or [c.strip() for c in lector.fieldnames] != list(COLUMNAS):
        error = f"Las columnas deben ser exactamente: {', '.join(COLUMNAS)}."
        return ResultadoValidacion([], [{"fila": 0, "error": error}])
    filas: list[dict[str, Any]] = []
    for numero, reg in enumerate(lector, start=1):
        if numero > MAX_FILAS:
            errores.append({"fila": numero, "error": f"Se superó el máximo de {MAX_FILAS} filas."})
            break
        try:
            ev_id = (reg.get("evento_id") or "").strip()
            ev = catalogo.evento(ev_id)
            if ev is None or not ev.activo:
                raise EntradaInvalidaError(f"El evento «{ev_id}» no existe o está inactivo.")
            anio_txt = (reg.get("edicion_anio") or "").strip()
            if anio_txt and not anio_txt.isdigit():
                raise EntradaInvalidaError("edicion_anio debe ser un año o estar vacío.")
            anio = validar_edicion(int(anio_txt) if anio_txt else None, anio_actual)
            texto_op = validar_texto(reg.get("opinion"))
            filas.append({"numero": numero, "evento_id": ev_id, "edicion_anio": anio, "opinion": texto_op})
        except EntradaInvalidaError as e:
            errores.append({"fila": numero, "error": str(e)})
    if not filas and not errores:
        errores.append({"fila": 0, "error": "El archivo no tiene filas."})
    return ResultadoValidacion(filas, errores)


@dataclass
class ClasificarLote:
    catalogo: RepositorioCatalogo
    trabajos: RepositorioTrabajos
    auditoria: RepositorioAuditoria
    reloj: Reloj
    ids: GeneradorId

    def crear(self, actor: Actor | None, contenido: bytes) -> tuple[TrabajoLote | None, ResultadoValidacion]:
        a = requerir_rol(actor, Rol.MODERADOR)
        val = validar_csv(contenido, self.catalogo.obtener(), self.reloj.ahora().year)
        if not val.valido:
            return None, val
        t = TrabajoLote(id=self.ids.nuevo(), usuario_id=a.usuario_id, estado=EstadoTrabajo.PENDIENTE.value,
                        total=len(val.filas), creado_utc=iso(self.reloj.ahora()), filas=val.filas)
        self.trabajos.crear(t)
        self.auditoria.registrar(fecha_utc=t.creado_utc, usuario_id=a.usuario_id, accion="lote_creado",
                                 detalle={"trabajo_id": t.id, "filas": t.total})
        return t, val

    def listar(self, actor: Actor | None) -> list[TrabajoLote]:
        a = requerir_rol(actor, Rol.MODERADOR)
        return self.trabajos.listar(None if a.rol == Rol.ADMIN.value else a.usuario_id)

    def obtener(self, actor: Actor | None, trabajo_id: str) -> TrabajoLote | None:
        requerir_rol(actor, Rol.MODERADOR)
        return self.trabajos.obtener(trabajo_id)


@dataclass
class ProcesadorLotes:
    trabajos: RepositorioTrabajos
    opiniones: RepositorioOpiniones
    emitir: EmitirOpinion
    limitador: Limitador | None
    pausa_s: float = 0.0

    def procesar(self, trabajo: TrabajoLote) -> TrabajoLote:
        t = trabajo.con(estado=EstadoTrabajo.PROCESANDO.value, procesadas=0, fallidas=0, errores=[], resultados=[])
        self.trabajos.actualizar(t)
        actor = Actor(usuario_id=t.usuario_id or "worker", rol=Rol.MODERADOR.value)
        procesadas = fallidas = 0
        errores: list[dict[str, Any]] = []
        resultados: list[dict[str, Any]] = []
        for fila in t.filas:
            numero = int(fila["numero"])
            rid = id_fila(t.id, numero)
            previa = self.opiniones.obtener(rid)
            if previa is not None:  # ya guardada en una ejecución anterior: no se vuelve a llamar al modelo
                procesadas += 1
                resultados.append({"fila": numero, "estado": "guardada", "sentimiento": previa.sentimiento,
                                   "registro_id": rid, "previa": True})
                continue
            try:
                if self.limitador is not None:
                    self.limitador.verificar_global()
                r = self.emitir.ejecutar(
                    SolicitudOpinion(texto=fila["opinion"], evento_id=fila["evento_id"], registro_id=rid,
                                     edicion_anio=fila.get("edicion_anio"), origen="lote"),
                    actor=actor, aplicar_limite=False,
                )
                procesadas += 1
                resultados.append({"fila": numero, "estado": r.estado, "registro_id": rid,
                                   "sentimiento": r.analisis.sentimiento, "razon": r.analisis.razon})
            except LimiteExcedidoError as e:
                # Tope diario alcanzado: se guarda el progreso y el trabajo sigue pendiente.
                t = t.con(estado=EstadoTrabajo.PENDIENTE.value, procesadas=procesadas, fallidas=fallidas,
                          errores=[*errores, {"fila": numero, "error": f"{e} (se reanudará)"}], resultados=resultados)
                self.trabajos.actualizar(t)
                return t
            except ErrorPaddock as e:  # una fila con error no detiene el lote y NUNCA se guarda como neutro
                fallidas += 1
                errores.append({"fila": numero, "error": f"{type(e).__name__}: {e}"})
                resultados.append({"fila": numero, "estado": "error", "registro_id": None, "sentimiento": None})
            t = t.con(procesadas=procesadas, fallidas=fallidas, errores=errores, resultados=resultados)
            self.trabajos.actualizar(t)
            if self.pausa_s:
                time.sleep(self.pausa_s)
        t = t.con(estado=EstadoTrabajo.TERMINADO.value, procesadas=procesadas, fallidas=fallidas, errores=errores,
                  resultados=resultados)
        self.trabajos.actualizar(t)
        log.info("Lote %s terminado: %d procesadas, %d fallidas", t.id, procesadas, fallidas)
        return t
