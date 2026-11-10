"""Modelos SQLAlchemy 2 (SQLite en desarrollo, PostgreSQL 16 en producción).

Las fechas se guardan como texto ISO 8601 con «+00:00»: se comparan bien lexicográficamente y
coinciden con el contrato JSON. ``aspectos``/``entidades`` usan JSON (JSONB en PostgreSQL).
Todo cambio de esquema va por una migración de Alembic (``migraciones/``).
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import JSON, Boolean, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

JsonFlexible = JSON().with_variant(JSONB(), "postgresql")
FECHA = String(32)


class Base(DeclarativeBase):
    pass


# ======================================================================= catálogo


class DisciplinaFila(Base):
    __tablename__ = "disciplinas"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120))
    icono: Mapped[str] = mapped_column(String(16))
    orden: Mapped[int] = mapped_column(Integer, default=0)


class CampeonatoFila(Base):
    __tablename__ = "campeonatos"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    disciplina_id: Mapped[str] = mapped_column(ForeignKey("disciplinas.id"))
    nombre: Mapped[str] = mapped_column(String(120))
    orden: Mapped[int] = mapped_column(Integer, default=0)


class EventoFila(Base):
    __tablename__ = "eventos"
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    campeonato_id: Mapped[str] = mapped_column(ForeignKey("campeonatos.id"))
    nombre: Mapped[str] = mapped_column(String(160))
    pais: Mapped[str] = mapped_column(String(120))
    sede: Mapped[str] = mapped_column(String(160))
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lon: Mapped[float | None] = mapped_column(Float, nullable=True)
    historico: Mapped[bool] = mapped_column(Boolean, default=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    orden: Mapped[int] = mapped_column(Integer, default=0)


class JergaFila(Base):
    __tablename__ = "jerga"
    disciplina_id: Mapped[str] = mapped_column(ForeignKey("disciplinas.id"), primary_key=True)
    terminos: Mapped[list[str]] = mapped_column(JsonFlexible, default=list)


# ======================================================================= usuarios


class UsuarioFila(Base):
    __tablename__ = "usuarios"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    nombre_visible: Mapped[str] = mapped_column(String(80))
    hash_contrasena: Mapped[str] = mapped_column(String(255))
    rol: Mapped[str] = mapped_column(String(20), default="aficionado")
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    creado_utc: Mapped[str] = mapped_column(FECHA)
    ultimo_acceso_utc: Mapped[str | None] = mapped_column(FECHA, nullable=True)
    intentos_fallidos: Mapped[int] = mapped_column(Integer, default=0)
    bloqueado_hasta: Mapped[str | None] = mapped_column(FECHA, nullable=True)


class TokenApiFila(Base):
    __tablename__ = "tokens_api"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    usuario_id: Mapped[str] = mapped_column(ForeignKey("usuarios.id", ondelete="CASCADE"), index=True)
    nombre: Mapped[str] = mapped_column(String(80))
    hash_token: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    creado_utc: Mapped[str] = mapped_column(FECHA)
    revocado: Mapped[bool] = mapped_column(Boolean, default=False)
    ultimo_uso_utc: Mapped[str | None] = mapped_column(FECHA, nullable=True)


# ======================================================================= opiniones


class OpinionFila(Base):
    __tablename__ = "opiniones"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    fecha_utc: Mapped[str] = mapped_column(FECHA)
    evento_id: Mapped[str] = mapped_column(String(80))
    evento_nombre: Mapped[str] = mapped_column(String(160))
    disciplina_id: Mapped[str] = mapped_column(String(64))
    edicion_anio: Mapped[int | None] = mapped_column(Integer, nullable=True)
    usuario_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    opinion_original: Mapped[str] = mapped_column(Text)
    sentimiento: Mapped[str] = mapped_column(String(10))
    razon: Mapped[str] = mapped_column(String(400))
    aspectos: Mapped[list[dict[str, str]] | None] = mapped_column(JsonFlexible, nullable=True)
    ironia: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    intensidad: Mapped[int | None] = mapped_column(Integer, nullable=True)
    entidades: Mapped[list[str] | None] = mapped_column(JsonFlexible, nullable=True)
    modelo: Mapped[str] = mapped_column(String(120))
    version_prompt: Mapped[str] = mapped_column(String(10))
    origen: Mapped[str] = mapped_column(String(10), default="chat")
    visible: Mapped[bool] = mapped_column(Boolean, default=True)
    # Última revisión humana (desnormalizada para filtrar); el historial completo está en «revisiones».
    revision_sentimiento: Mapped[str | None] = mapped_column(String(10), nullable=True)
    revision_revisor_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    revision_fecha_utc: Mapped[str | None] = mapped_column(FECHA, nullable=True)
    revision_nota: Mapped[str | None] = mapped_column(String(500), nullable=True)

    __table_args__ = (
        Index("ix_opiniones_evento_id", "evento_id"),
        Index("ix_opiniones_sentimiento", "sentimiento"),
        Index("ix_opiniones_fecha_utc", "fecha_utc"),
        Index("ix_opiniones_usuario_id", "usuario_id"),
    )


class RevisionFila(Base):
    __tablename__ = "revisiones"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    opinion_id: Mapped[str] = mapped_column(ForeignKey("opiniones.id"), index=True)
    sentimiento: Mapped[str] = mapped_column(String(10))
    revisor_id: Mapped[str] = mapped_column(String(36))
    nota: Mapped[str] = mapped_column(String(500), default="")
    fecha_utc: Mapped[str] = mapped_column(FECHA)


class DenunciaFila(Base):
    __tablename__ = "denuncias"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    opinion_id: Mapped[str] = mapped_column(ForeignKey("opiniones.id"), index=True)
    usuario_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    motivo: Mapped[str] = mapped_column(String(20))
    fecha_utc: Mapped[str] = mapped_column(FECHA)
    atendida: Mapped[bool] = mapped_column(Boolean, default=False)


# ======================================================================= v3


class TrabajoLoteFila(Base):
    __tablename__ = "trabajos_lote"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    usuario_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    estado: Mapped[str] = mapped_column(String(12), index=True)
    total: Mapped[int] = mapped_column(Integer)
    procesadas: Mapped[int] = mapped_column(Integer, default=0)
    fallidas: Mapped[int] = mapped_column(Integer, default=0)
    creado_utc: Mapped[str] = mapped_column(FECHA)
    errores: Mapped[list[dict[str, Any]]] = mapped_column(JsonFlexible, default=list)
    filas: Mapped[list[dict[str, Any]]] = mapped_column(JsonFlexible, default=list)
    resultados: Mapped[list[dict[str, Any]]] = mapped_column(JsonFlexible, default=list)


class ResumenFila(Base):
    __tablename__ = "resumenes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    evento_id: Mapped[str] = mapped_column(String(80), index=True)
    edicion_anio: Mapped[int | None] = mapped_column(Integer, nullable=True)
    texto: Mapped[str] = mapped_column(Text)
    n_opiniones: Mapped[int] = mapped_column(Integer)
    modelo: Mapped[str] = mapped_column(String(120))
    version_prompt: Mapped[str] = mapped_column(String(10), default="")
    fecha_utc: Mapped[str] = mapped_column(FECHA)


# ======================================================================= operación


class AuditoriaFila(Base):
    __tablename__ = "auditoria"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    fecha_utc: Mapped[str] = mapped_column(FECHA, index=True)
    usuario_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    accion: Mapped[str] = mapped_column(String(60), index=True)
    detalle: Mapped[dict[str, Any]] = mapped_column(JsonFlexible, default=dict)
    ip_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)


class LimiteUsoFila(Base):
    __tablename__ = "limites_uso"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    clave: Mapped[str] = mapped_column(String(120))
    fecha_utc: Mapped[str] = mapped_column(FECHA)
    __table_args__ = (Index("ix_limites_clave_fecha", "clave", "fecha_utc"),)


class MetricaLlmFila(Base):
    __tablename__ = "metricas_llm"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    fecha_utc: Mapped[str] = mapped_column(FECHA, index=True)
    proveedor: Mapped[str] = mapped_column(String(20))
    modelo: Mapped[str] = mapped_column(String(80))
    version_prompt: Mapped[str] = mapped_column(String(10))
    latencia_ms: Mapped[int] = mapped_column(Integer)
    exito: Mapped[bool] = mapped_column(Boolean)
    tipo_error: Mapped[str | None] = mapped_column(String(60), nullable=True)
    tokens_entrada: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tokens_salida: Mapped[int | None] = mapped_column(Integer, nullable=True)
