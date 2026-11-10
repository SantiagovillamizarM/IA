"""Caso de uso: informe PDF por evento (y edición). Reúne los datos; el adaptador ``informes/pdf.py`` los dibuja."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from paddock.aplicacion.autorizacion import Actor
from paddock.aplicacion.obtener_estadisticas import Estadisticas, calcular
from paddock.dominio.entidades import Disciplina, Evento, FiltrosOpinion, Opinion, Resumen
from paddock.dominio.enums import SENTIMIENTOS
from paddock.dominio.errores import EventoNoEncontradoError, SesionRequeridaError
from paddock.puertos.repositorios import RepositorioCatalogo, RepositorioOpiniones, RepositorioResumenes
from paddock.puertos.servicios import Reloj, iso


@dataclass(frozen=True)
class DatosInforme:
    evento: Evento
    disciplina: Disciplina
    campeonato: str
    edicion: int | None
    estadisticas: Estadisticas
    resumen: Resumen | None
    muestras: dict[str, list[Opinion]] = field(default_factory=dict)
    generado_utc: str = ""


@dataclass
class GenerarInforme:
    catalogo: RepositorioCatalogo
    opiniones: RepositorioOpiniones
    resumenes: RepositorioResumenes | None
    reloj: Reloj
    renderizar: Callable[[DatosInforme], bytes]
    permitir_anonimos: bool = True

    def datos(self, evento_id: str, edicion: int | None, actor: Actor | None = None,
              muestras_por_categoria: int = 3) -> DatosInforme:
        if actor is None and not self.permitir_anonimos:
            raise SesionRequeridaError("Inicia sesión para generar informes.")
        cat = self.catalogo.obtener()
        ev = cat.evento(evento_id)
        if ev is None:
            raise EventoNoEncontradoError("La carrera no existe.")
        regs = self.opiniones.consultar(FiltrosOpinion(evento_id=evento_id, edicion_anio=edicion))
        muestras: dict[str, list[Opinion]] = {s: [] for s in SENTIMIENTOS}
        for o in regs:
            if len(muestras[o.sentimiento]) < muestras_por_categoria:
                muestras[o.sentimiento].append(o)
        camp = cat.campeonato(ev.campeonato_id)
        resumen = self.resumenes.obtener(evento_id, edicion) if self.resumenes is not None else None
        return DatosInforme(evento=ev, disciplina=cat.disciplina_de_evento(ev), campeonato=camp.nombre if camp else "",
                            edicion=edicion, estadisticas=calcular(regs), resumen=resumen, muestras=muestras,
                            generado_utc=iso(self.reloj.ahora()))

    def pdf(self, evento_id: str, edicion: int | None, actor: Actor | None = None) -> bytes:
        return self.renderizar(self.datos(evento_id, edicion, actor))
