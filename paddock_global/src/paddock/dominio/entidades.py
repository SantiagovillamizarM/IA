"""Entidades del dominio. Dataclasses puras, sin dependencias de infraestructura."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, replace
from typing import Any

# ======================================================================= catálogo


@dataclass(frozen=True)
class Disciplina:
    id: str
    nombre: str
    icono: str


@dataclass(frozen=True)
class Campeonato:
    id: str
    disciplina_id: str
    nombre: str


@dataclass(frozen=True)
class Evento:
    id: str
    campeonato_id: str
    nombre: str
    pais: str
    sede: str
    lat: float | None = None
    lon: float | None = None
    historico: bool = False
    activo: bool = True

    @property
    def etiqueta(self) -> str:
        """Texto del selector: «{nombre} — {pais}»."""
        return f"{self.nombre} — {self.pais}"


@dataclass(frozen=True)
class Catalogo:
    """Jerarquía Disciplina → Campeonato → Evento, ya validada."""

    version: int
    disciplinas: tuple[Disciplina, ...]
    campeonatos: tuple[Campeonato, ...]
    eventos: tuple[Evento, ...]

    # --- búsquedas
    def disciplina(self, disciplina_id: str) -> Disciplina | None:
        return next((d for d in self.disciplinas if d.id == disciplina_id), None)

    def campeonato(self, campeonato_id: str) -> Campeonato | None:
        return next((c for c in self.campeonatos if c.id == campeonato_id), None)

    def evento(self, evento_id: str) -> Evento | None:
        return next((e for e in self.eventos if e.id == evento_id), None)

    def disciplina_de_evento(self, evento: Evento) -> Disciplina:
        camp = self.campeonato(evento.campeonato_id)
        disc = self.disciplina(camp.disciplina_id) if camp else None
        if disc is None:  # el validador garantiza que no ocurre
            raise ValueError(f"Evento sin disciplina: {evento.id}")
        return disc

    # --- selector encadenado
    def campeonatos_de(self, disciplina_id: str) -> list[Campeonato]:
        return [c for c in self.campeonatos if c.disciplina_id == disciplina_id]

    def eventos_de(self, campeonato_id: str, solo_activos: bool = True) -> list[Evento]:
        return [
            e for e in self.eventos
            if e.campeonato_id == campeonato_id and (e.activo or not solo_activos)
        ]

    def eventos_de_disciplina(self, disciplina_id: str) -> list[Evento]:
        ids = {c.id for c in self.campeonatos_de(disciplina_id)}
        return [e for e in self.eventos if e.campeonato_id in ids]

    def evento_por_defecto(self) -> Evento:
        """La primera carrera de F1 de la lista (o la primera activa si no hay F1)."""
        activos = [e for e in self.eventos if e.activo]
        return next((e for e in activos if e.campeonato_id == "f1"), activos[0])


# ======================================================================= opiniones


@dataclass(frozen=True)
class Revision:
    """Corrección humana. La etiqueta del modelo nunca se sobrescribe."""

    sentimiento: str
    revisor_id: str
    fecha_utc: str
    nota: str = ""


@dataclass(frozen=True)
class Opinion:
    """Registro persistente de una opinión (contrato común a JSON, SQLite y PostgreSQL)."""

    id: str
    fecha_utc: str
    evento_id: str
    evento_nombre: str
    disciplina_id: str
    opinion_original: str
    sentimiento: str
    razon: str
    modelo: str
    version_prompt: str
    edicion_anio: int | None = None
    usuario_id: str | None = None
    aspectos: list[dict[str, str]] | None = None
    ironia: bool | None = None
    intensidad: int | None = None
    entidades: list[str] | None = None
    origen: str = "chat"
    revision: Revision | None = None
    visible: bool = True

    @property
    def sentimiento_efectivo(self) -> str:
        """La etiqueta revisada si existe; si no, la del modelo."""
        return self.revision.sentimiento if self.revision else self.sentimiento

    def con(self, **cambios: Any) -> Opinion:
        return replace(self, **cambios)

    def a_dict(self) -> dict[str, Any]:
        """Diccionario en el orden del contrato (§4.1)."""
        d = asdict(self)
        d["revision"] = asdict(self.revision) if self.revision else None
        orden = [
            "id", "fecha_utc", "evento_id", "evento_nombre", "disciplina_id", "edicion_anio", "usuario_id",
            "opinion_original", "sentimiento", "razon", "aspectos", "ironia", "intensidad", "entidades",
            "modelo", "version_prompt", "origen", "revision", "visible",
        ]
        return {k: d[k] for k in orden}

    @classmethod
    def desde_dict(cls, d: dict[str, Any]) -> Opinion:
        """Acepta registros de v1 (sin campos de v2/v3) por compatibilidad hacia atrás."""
        rev = d.get("revision")
        return cls(
            id=d["id"],
            fecha_utc=d["fecha_utc"],
            evento_id=d["evento_id"],
            evento_nombre=d["evento_nombre"],
            disciplina_id=d.get("disciplina_id") or "",
            opinion_original=d["opinion_original"],
            sentimiento=d["sentimiento"],
            razon=d["razon"],
            modelo=d["modelo"],
            version_prompt=d["version_prompt"],
            edicion_anio=d.get("edicion_anio"),
            usuario_id=d.get("usuario_id"),
            aspectos=d.get("aspectos"),
            ironia=d.get("ironia"),
            intensidad=d.get("intensidad"),
            entidades=d.get("entidades"),
            origen=d.get("origen") or "chat",
            revision=Revision(**rev) if isinstance(rev, dict) else None,
            visible=d.get("visible", True) if d.get("visible") is not None else True,
        )


@dataclass(frozen=True)
class FiltrosOpinion:
    """Filtros opcionales de consulta. Ninguna consulta llama al modelo."""

    disciplina_id: str | None = None
    campeonato_id: str | None = None
    evento_id: str | None = None
    evento_ids: tuple[str, ...] | None = None  # resuelto desde campeonato por el caso de uso
    edicion_anio: int | None = None
    sentimiento: str | None = None
    aspecto: str | None = None
    usuario_id: str | None = None
    desde_utc: str | None = None  # ISO 8601, inclusivo
    hasta_utc: str | None = None  # ISO 8601, exclusivo
    texto: str | None = None
    solo_revisadas: bool = False
    usar_revision: bool = False  # filtra/cuenta por la etiqueta revisada si existe
    incluir_ocultas: bool = False
    limite: int | None = None
    desplazamiento: int = 0

    def con(self, **cambios: Any) -> FiltrosOpinion:
        return replace(self, **cambios)


# ======================================================================= usuarios


@dataclass(frozen=True)
class Usuario:
    id: str
    email: str
    nombre_visible: str
    hash_contrasena: str
    rol: str = "aficionado"
    activo: bool = True
    creado_utc: str = ""
    ultimo_acceso_utc: str | None = None
    intentos_fallidos: int = 0
    bloqueado_hasta: str | None = None

    def con(self, **cambios: Any) -> Usuario:
        return replace(self, **cambios)


@dataclass(frozen=True)
class TokenApi:
    id: str
    usuario_id: str
    nombre: str
    hash_token: str
    creado_utc: str
    revocado: bool = False
    ultimo_uso_utc: str | None = None


# ======================================================================= v3


@dataclass(frozen=True)
class FilaLote:
    numero: int
    evento_id: str
    edicion_anio: int | None
    opinion: str


@dataclass(frozen=True)
class TrabajoLote:
    id: str
    usuario_id: str | None
    estado: str
    total: int
    procesadas: int = 0
    fallidas: int = 0
    creado_utc: str = ""
    errores: list[dict[str, Any]] = field(default_factory=list)
    filas: list[dict[str, Any]] = field(default_factory=list)
    resultados: list[dict[str, Any]] = field(default_factory=list)

    def con(self, **cambios: Any) -> TrabajoLote:
        return replace(self, **cambios)


@dataclass(frozen=True)
class Resumen:
    evento_id: str
    edicion_anio: int | None
    texto: str
    n_opiniones: int
    modelo: str
    fecha_utc: str
    version_prompt: str = ""


@dataclass(frozen=True)
class Denuncia:
    id: str
    opinion_id: str
    usuario_id: str | None
    motivo: str
    fecha_utc: str
    atendida: bool = False


@dataclass(frozen=True)
class MetricaLlamada:
    """Una llamada al LLM, para el panel de calidad. Nunca incluye el texto de la opinión."""

    fecha_utc: str
    proveedor: str
    modelo: str
    version_prompt: str
    latencia_ms: int
    exito: bool
    tipo_error: str | None = None
    tokens_entrada: int | None = None
    tokens_salida: int | None = None
