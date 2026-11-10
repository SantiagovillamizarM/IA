"""Caso de uso: «¿Qué opina la comunidad?» (v3).

Resume SOLO las opiniones guardadas de un evento (y edición). Mínimo 5. El resumen se guarda y se
reutiliza hasta que haya 10 opiniones nuevas o el usuario pida regenerar (con límite de tasa).
"""

from __future__ import annotations

from dataclasses import dataclass

from paddock.aplicacion.autorizacion import Actor, requerir_sesion
from paddock.dominio.entidades import FiltrosOpinion, Resumen
from paddock.dominio.errores import EntradaInvalidaError, EventoNoEncontradoError
from paddock.puertos.clasificador import Resumidor
from paddock.puertos.repositorios import (
    RepositorioAuditoria,
    RepositorioCatalogo,
    RepositorioOpiniones,
    RepositorioResumenes,
)
from paddock.puertos.servicios import Limitador, Reloj, iso

MINIMO_OPINIONES = 5
NUEVAS_PARA_REGENERAR = 10


@dataclass(frozen=True)
class ResultadoResumen:
    resumen: Resumen
    reutilizado: bool
    nuevas_desde_resumen: int


@dataclass
class ResumirComunidad:
    catalogo: RepositorioCatalogo
    opiniones: RepositorioOpiniones
    resumenes: RepositorioResumenes
    resumidor: Resumidor
    reloj: Reloj
    limitador: Limitador | None = None
    auditoria: RepositorioAuditoria | None = None

    def guardado(self, evento_id: str, edicion: int | None) -> Resumen | None:
        return self.resumenes.obtener(evento_id, edicion)

    def ejecutar(self, evento_id: str, edicion: int | None, actor: Actor | None,
                 regenerar: bool = False) -> ResultadoResumen:
        ev = self.catalogo.obtener().evento(evento_id)
        if ev is None:
            raise EventoNoEncontradoError("La carrera no existe.")
        ops = self.opiniones.consultar(FiltrosOpinion(evento_id=evento_id, edicion_anio=edicion))
        if len(ops) < MINIMO_OPINIONES:
            raise EntradaInvalidaError(
                f"Hacen falta al menos {MINIMO_OPINIONES} opiniones para resumir (hay {len(ops)}).")
        previo = self.resumenes.obtener(evento_id, edicion)
        nuevas = len(ops) - previo.n_opiniones if previo else len(ops)
        if previo and not regenerar and nuevas < NUEVAS_PARA_REGENERAR:
            return ResultadoResumen(previo, True, nuevas)
        a = requerir_sesion(actor)  # generar llama al modelo: exige sesión
        if self.limitador is not None:
            self.limitador.verificar_y_registrar(a.usuario_id, ventana_min=10, maximo=2, prefijo="resumen")
        pares = [(o.sentimiento, o.opinion_original) for o in ops]  # sin nombres de usuario
        texto = self.resumidor.resumir(carrera=ev.nombre, edicion=edicion, opiniones=pares)
        r = Resumen(evento_id=evento_id, edicion_anio=edicion, texto=texto, n_opiniones=len(ops),
                    modelo=self.resumidor.modelo, fecha_utc=iso(self.reloj.ahora()),
                    version_prompt=self.resumidor.version_prompt)
        self.resumenes.guardar(r)
        if self.auditoria is not None:
            self.auditoria.registrar(fecha_utc=r.fecha_utc, usuario_id=a.usuario_id, accion="resumen_generado",
                                     detalle={"evento_id": evento_id, "n": len(ops)})
        return ResultadoResumen(r, False, 0)
