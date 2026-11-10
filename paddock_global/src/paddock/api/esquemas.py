"""Esquemas de la API REST (entrada y salida). La salida pública nunca incluye ``usuario_id``."""

from __future__ import annotations

from pydantic import BaseModel, Field

from paddock.dominio.entidades import Opinion


class ErrorApi(BaseModel):
    codigo: str
    mensaje: str


class RespuestaError(BaseModel):
    error: ErrorApi


class Salud(BaseModel):
    estado: str
    version: str


class DisciplinaApi(BaseModel):
    id: str
    nombre: str
    icono: str


class CampeonatoApi(BaseModel):
    id: str
    disciplina_id: str
    nombre: str


class EventoApi(BaseModel):
    id: str
    campeonato_id: str
    nombre: str
    pais: str
    sede: str
    lat: float | None = None
    lon: float | None = None
    historico: bool = False


class CatalogoApi(BaseModel):
    disciplinas: list[DisciplinaApi]
    campeonatos: list[CampeonatoApi]
    eventos: list[EventoApi]


class AspectoApi(BaseModel):
    aspecto: str
    sentimiento: str


class OpinionApi(BaseModel):
    id: str
    fecha_utc: str
    evento_id: str
    evento_nombre: str
    disciplina_id: str
    edicion_anio: int | None
    opinion_original: str
    sentimiento: str
    sentimiento_revisado: str | None = None
    razon: str
    aspectos: list[AspectoApi] | None = None
    ironia: bool | None = None
    intensidad: int | None = None
    entidades: list[str] | None = None
    modelo: str
    version_prompt: str
    origen: str

    @classmethod
    def desde(cls, o: Opinion) -> OpinionApi:
        return cls(
            id=o.id, fecha_utc=o.fecha_utc, evento_id=o.evento_id, evento_nombre=o.evento_nombre,
            disciplina_id=o.disciplina_id, edicion_anio=o.edicion_anio, opinion_original=o.opinion_original,
            sentimiento=o.sentimiento, sentimiento_revisado=o.revision.sentimiento if o.revision else None,
            razon=o.razon, aspectos=[AspectoApi(**a) for a in o.aspectos] if o.aspectos else None, ironia=o.ironia,
            intensidad=o.intensidad, entidades=o.entidades, modelo=o.modelo, version_prompt=o.version_prompt,
            origen=o.origen,
        )


class PaginaOpiniones(BaseModel):
    total: int
    limite: int
    desplazamiento: int
    opiniones: list[OpinionApi]


class EstadisticasApi(BaseModel):
    total: int
    por_sentimiento: dict[str, int]
    indice_percepcion: float | None
    eventos_con_opiniones: int


class NuevaOpinion(BaseModel):
    evento_id: str = Field(min_length=3, max_length=80)
    edicion_anio: int | None = Field(default=None, ge=1900)
    opinion: str = Field(min_length=1, max_length=1000)
    registro_id: str | None = Field(default=None, min_length=8, max_length=64, pattern=r"^[A-Za-z0-9-]+$",
                                    description="Opcional: reutilízalo al reintentar para no duplicar")


class ResultadoOpinion(BaseModel):
    estado: str  # guardada | duplicada | no_pertinente
    es_pertinente: bool
    sentimiento: str | None
    razon: str
    opinion: OpinionApi | None = None
