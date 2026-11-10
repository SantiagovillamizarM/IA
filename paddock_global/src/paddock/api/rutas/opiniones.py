"""Rutas de la API. Reutilizan los casos de uso: la API no tiene lógica de negocio propia."""

from __future__ import annotations

from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, Query, Response

from paddock import __version__
from paddock.api.auth import actor_opcional, actor_requerido, contenedor
from paddock.api.esquemas import (
    CampeonatoApi,
    CatalogoApi,
    DisciplinaApi,
    EstadisticasApi,
    EventoApi,
    NuevaOpinion,
    OpinionApi,
    PaginaOpiniones,
    ResultadoOpinion,
    Salud,
)
from paddock.aplicacion.autorizacion import Actor
from paddock.aplicacion.emitir_opinion import SolicitudOpinion
from paddock.contenedor import Contenedor
from paddock.dominio.entidades import FiltrosOpinion
from paddock.dominio.enums import SENTIMIENTOS

router = APIRouter(prefix="/api")


@router.get("/salud", response_model=Salud, tags=["operación"])
def salud() -> Salud:
    return Salud(estado="ok", version=__version__)


@router.get("/catalogo", response_model=CatalogoApi, tags=["catálogo"])
def catalogo(c: Contenedor = Depends(contenedor)) -> CatalogoApi:
    cat = c.repo_catalogo.obtener()
    return CatalogoApi(
        disciplinas=[DisciplinaApi(**d.__dict__) for d in cat.disciplinas],
        campeonatos=[CampeonatoApi(**x.__dict__) for x in cat.campeonatos],
        eventos=[EventoApi(**{k: v for k, v in e.__dict__.items() if k != "activo"}) for e in cat.eventos if e.activo],
    )


def _filtros(
    disciplina_id: str | None = None, campeonato_id: str | None = None, evento_id: str | None = None,
    edicion_anio: Annotated[int | None, Query(ge=1900)] = None,
    sentimiento: Annotated[str | None, Query(pattern="^(positivo|negativo|neutro|mixto)$")] = None,
    etiqueta: Annotated[str, Query(pattern="^(modelo|revisada)$")] = "modelo",
    limite: Annotated[int, Query(ge=1, le=100)] = 20, desplazamiento: Annotated[int, Query(ge=0)] = 0,
) -> FiltrosOpinion:
    return FiltrosOpinion(disciplina_id=disciplina_id, campeonato_id=campeonato_id, evento_id=evento_id,
                          edicion_anio=edicion_anio, sentimiento=sentimiento, usar_revision=etiqueta == "revisada",
                          limite=limite, desplazamiento=desplazamiento)


@router.get("/opiniones", response_model=PaginaOpiniones, tags=["opiniones"])
def listar(f: FiltrosOpinion = Depends(_filtros), actor: Actor | None = Depends(actor_opcional),
           c: Contenedor = Depends(contenedor)) -> PaginaOpiniones:
    res = c.consultar_opiniones.ejecutar(f, actor)
    return PaginaOpiniones(total=res.total, limite=f.limite or 0, desplazamiento=f.desplazamiento,
                           opiniones=[OpinionApi.desde(o) for o in res.registros])


@router.get("/estadisticas", response_model=EstadisticasApi, tags=["opiniones"])
def estadisticas(f: FiltrosOpinion = Depends(_filtros), actor: Actor | None = Depends(actor_opcional),
                 c: Contenedor = Depends(contenedor)) -> EstadisticasApi:
    e = c.estadisticas.ejecutar(f.con(limite=None, desplazamiento=0), actor)
    return EstadisticasApi(total=e.total, por_sentimiento={s: e.conteo[s] for s in SENTIMIENTOS},
                           indice_percepcion=e.indice, eventos_con_opiniones=e.eventos_con_opiniones)


@router.post("/opiniones", response_model=ResultadoOpinion, status_code=201, tags=["opiniones"],
             responses={200: {"description": "No pertinente o duplicada: no se guardó nada nuevo"}})
def crear(datos: NuevaOpinion, response: Response, actor: Actor = Depends(actor_requerido),
          c: Contenedor = Depends(contenedor)) -> ResultadoOpinion:
    r = c.emitir_opinion.ejecutar(
        SolicitudOpinion(texto=datos.opinion, evento_id=datos.evento_id, edicion_anio=datos.edicion_anio,
                         registro_id=datos.registro_id or str(uuid4()), origen="api"),
        actor=actor,  # mismo limitador de tasa que la interfaz (por usuario)
    )
    if r.estado != "guardada":
        response.status_code = 200
    return ResultadoOpinion(estado=r.estado, es_pertinente=r.analisis.es_pertinente,
                            sentimiento=r.analisis.sentimiento, razon=r.analisis.razon,
                            opinion=OpinionApi.desde(r.registro) if r.registro else None)
