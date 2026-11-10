"""Adaptadores SQL de todos los puertos de persistencia (SQLAlchemy 2, consultas parametrizadas).

Idempotencia de opiniones: ``INSERT … ON CONFLICT (id) DO NOTHING`` (SQLite y PostgreSQL).
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from sqlalchemy import Engine, create_engine, delete, event, func, or_, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session, sessionmaker

from paddock.adaptadores.persistencia.sql_modelos import (
    AuditoriaFila,
    Base,
    CampeonatoFila,
    DenunciaFila,
    DisciplinaFila,
    EventoFila,
    JergaFila,
    LimiteUsoFila,
    MetricaLlmFila,
    OpinionFila,
    ResumenFila,
    RevisionFila,
    TokenApiFila,
    TrabajoLoteFila,
    UsuarioFila,
)
from paddock.dominio.entidades import (
    Campeonato,
    Catalogo,
    Denuncia,
    Disciplina,
    Evento,
    FiltrosOpinion,
    MetricaLlamada,
    Opinion,
    Resumen,
    Revision,
    TokenApi,
    TrabajoLote,
    Usuario,
)
from paddock.dominio.errores import CatalogoInvalidoError
from paddock.dominio.reglas import catalogo_a_dict, coincide, validar_catalogo

# ======================================================================= conexión


class BaseDatos:
    def __init__(self, url: str, echo: bool = False) -> None:
        kwargs: dict[str, Any] = {"echo": echo, "pool_pre_ping": True}
        if url.startswith("sqlite"):
            kwargs["connect_args"] = {"check_same_thread": False, "timeout": 30}
        self.engine: Engine = create_engine(url, **kwargs)
        if url.startswith("sqlite"):
            @event.listens_for(self.engine, "connect")
            def _pragmas(conexion, _registro):  # type: ignore[no-untyped-def]
                cur = conexion.cursor()
                cur.execute("PRAGMA foreign_keys=ON")
                if ":memory:" not in url:
                    cur.execute("PRAGMA journal_mode=WAL")
                cur.close()
        self._fabrica = sessionmaker(self.engine, expire_on_commit=False)

    @property
    def dialecto(self) -> str:
        return self.engine.dialect.name

    @contextmanager
    def sesion(self) -> Iterator[Session]:
        s = self._fabrica()
        try:
            yield s
            s.commit()
        except Exception:
            s.rollback()
            raise
        finally:
            s.close()

    def crear_esquema(self) -> None:
        """Solo para tests y SQLite en memoria. En producción, ``alembic upgrade head``."""
        Base.metadata.create_all(self.engine)

    def insertar_ignorando(self, s: Session, modelo: type[Base], valores: dict[str, Any]) -> bool:
        tabla = modelo.__table__  # type: ignore[attr-defined]
        if self.dialecto == "postgresql":
            stmt = pg_insert(tabla).values(**valores).on_conflict_do_nothing(index_elements=["id"])
        elif self.dialecto == "sqlite":
            stmt = sqlite_insert(tabla).values(**valores).on_conflict_do_nothing(index_elements=["id"])
        else:  # pragma: no cover - otros motores
            if s.get(modelo, valores["id"]) is not None:
                return False
            s.add(modelo(**valores))
            return True
        return (s.execute(stmt).rowcount or 0) > 0


# ======================================================================= catálogo


class SqlRepositorioCatalogo:
    def __init__(self, bd: BaseDatos) -> None:
        self.bd = bd

    def obtener(self) -> Catalogo:
        with self.bd.sesion() as s:
            discs = s.scalars(select(DisciplinaFila).order_by(DisciplinaFila.orden)).all()
            camps = s.scalars(select(CampeonatoFila).order_by(CampeonatoFila.orden)).all()
            evs = s.scalars(select(EventoFila).order_by(EventoFila.orden)).all()
            if not discs:
                raise CatalogoInvalidoError("El catálogo está vacío. Ejecuta scripts/sembrar_catalogo.py.")
            return Catalogo(
                version=2,
                disciplinas=tuple(Disciplina(d.id, d.nombre, d.icono) for d in discs),
                campeonatos=tuple(Campeonato(c.id, c.disciplina_id, c.nombre) for c in camps),
                eventos=tuple(Evento(e.id, e.campeonato_id, e.nombre, e.pais, e.sede, e.lat, e.lon, e.historico,
                                     e.activo) for e in evs),
            )

    def sembrar(self, catalogo: Catalogo, jerga: dict[str, list[str]]) -> dict[str, int]:
        """Inserta lo que falte (idempotente). No cambia lo que el admin ya editó."""
        n = {"disciplinas": 0, "campeonatos": 0, "eventos": 0, "jerga": 0}
        with self.bd.sesion() as s:
            for i, d in enumerate(catalogo.disciplinas):
                if s.get(DisciplinaFila, d.id) is None:
                    s.add(DisciplinaFila(id=d.id, nombre=d.nombre, icono=d.icono, orden=i))
                    n["disciplinas"] += 1
            s.flush()
            for i, c in enumerate(catalogo.campeonatos):
                if s.get(CampeonatoFila, c.id) is None:
                    s.add(CampeonatoFila(id=c.id, disciplina_id=c.disciplina_id, nombre=c.nombre, orden=i))
                    n["campeonatos"] += 1
            s.flush()
            for i, e in enumerate(catalogo.eventos):
                if s.get(EventoFila, e.id) is None:
                    s.add(EventoFila(id=e.id, campeonato_id=e.campeonato_id, nombre=e.nombre, pais=e.pais,
                                     sede=e.sede, lat=e.lat, lon=e.lon, historico=e.historico, activo=e.activo,
                                     orden=i))
                    n["eventos"] += 1
            for disc_id, terminos in jerga.items():
                if s.get(JergaFila, disc_id) is None and s.get(DisciplinaFila, disc_id) is not None:
                    s.add(JergaFila(disciplina_id=disc_id, terminos=list(terminos)))
                    n["jerga"] += 1
        return n

    def guardar_evento(self, evento: Evento) -> None:
        actual = self.obtener()
        eventos = [e for e in actual.eventos if e.id != evento.id] + [evento]
        validar_catalogo({**catalogo_a_dict(actual), "eventos": [e.__dict__ for e in eventos]})
        with self.bd.sesion() as s:
            fila = s.get(EventoFila, evento.id)
            if fila is None:
                orden = (s.scalar(select(func.max(EventoFila.orden))) or 0) + 1
                s.add(EventoFila(**evento.__dict__, orden=orden))
            else:
                for k, v in evento.__dict__.items():
                    setattr(fila, k, v)

    def obtener_jerga(self) -> dict[str, list[str]]:
        with self.bd.sesion() as s:
            return {j.disciplina_id: list(j.terminos or []) for j in s.scalars(select(JergaFila))}

    def guardar_jerga(self, disciplina_id: str, terminos: list[str]) -> None:
        limpios = [t.strip() for t in terminos if t.strip()]
        with self.bd.sesion() as s:
            fila = s.get(JergaFila, disciplina_id)
            if fila is None:
                s.add(JergaFila(disciplina_id=disciplina_id, terminos=limpios))
            else:
                fila.terminos = limpios


# ======================================================================= opiniones


def _a_opinion(f: OpinionFila) -> Opinion:
    rev = None
    if f.revision_sentimiento:
        rev = Revision(f.revision_sentimiento, f.revision_revisor_id or "", f.revision_fecha_utc or "",
                       f.revision_nota or "")
    return Opinion(
        id=f.id, fecha_utc=f.fecha_utc, evento_id=f.evento_id, evento_nombre=f.evento_nombre,
        disciplina_id=f.disciplina_id, opinion_original=f.opinion_original, sentimiento=f.sentimiento,
        razon=f.razon, modelo=f.modelo, version_prompt=f.version_prompt, edicion_anio=f.edicion_anio,
        usuario_id=f.usuario_id, aspectos=f.aspectos, ironia=f.ironia, intensidad=f.intensidad,
        entidades=f.entidades, origen=f.origen, revision=rev, visible=f.visible,
    )


class SqlRepositorioOpiniones:
    def __init__(self, bd: BaseDatos) -> None:
        self.bd = bd

    def guardar(self, opinion: Opinion) -> bool:
        d = opinion.a_dict()
        rev = d.pop("revision")
        valores = {**d, "revision_sentimiento": rev["sentimiento"] if rev else None,
                   "revision_revisor_id": rev["revisor_id"] if rev else None,
                   "revision_fecha_utc": rev["fecha_utc"] if rev else None,
                   "revision_nota": rev["nota"] if rev else None}
        with self.bd.sesion() as s:
            return self.bd.insertar_ignorando(s, OpinionFila, valores)

    def obtener(self, opinion_id: str) -> Opinion | None:
        with self.bd.sesion() as s:
            f = s.get(OpinionFila, opinion_id)
            return _a_opinion(f) if f else None

    def _select(self, f: FiltrosOpinion):  # type: ignore[no-untyped-def]
        q = select(OpinionFila)
        if not f.incluir_ocultas:
            q = q.where(OpinionFila.visible.is_(True))
        if f.disciplina_id:
            q = q.where(OpinionFila.disciplina_id == f.disciplina_id)
        if f.evento_id:
            q = q.where(OpinionFila.evento_id == f.evento_id)
        if f.evento_ids is not None:
            q = q.where(OpinionFila.evento_id.in_(f.evento_ids or ("__ninguno__",)))
        if f.edicion_anio is not None:
            q = q.where(OpinionFila.edicion_anio == f.edicion_anio)
        if f.sentimiento:
            if f.usar_revision:
                q = q.where(func.coalesce(OpinionFila.revision_sentimiento, OpinionFila.sentimiento) == f.sentimiento)
            else:
                q = q.where(OpinionFila.sentimiento == f.sentimiento)
        if f.usuario_id:
            q = q.where(OpinionFila.usuario_id == f.usuario_id)
        if f.desde_utc:
            q = q.where(OpinionFila.fecha_utc >= f.desde_utc)
        if f.hasta_utc:
            q = q.where(OpinionFila.fecha_utc < f.hasta_utc)
        if f.solo_revisadas:
            q = q.where(OpinionFila.revision_sentimiento.is_not(None))
        return q.order_by(OpinionFila.fecha_utc.desc(), OpinionFila.id)

    def consultar(self, filtros: FiltrosOpinion) -> list[Opinion]:
        en_python = bool(filtros.aspecto or filtros.texto)  # JSON y texto sin tildes: se filtran en Python
        q = self._select(filtros)
        if not en_python:
            if filtros.desplazamiento:
                q = q.offset(filtros.desplazamiento)
            if filtros.limite is not None:
                q = q.limit(filtros.limite)
        with self.bd.sesion() as s:
            ops = [_a_opinion(x) for x in s.scalars(q)]
        if en_python:
            ops = [o for o in ops if coincide(o, filtros)]
            fin = filtros.desplazamiento + filtros.limite if filtros.limite is not None else None
            ops = ops[filtros.desplazamiento:fin]
        return ops

    def contar(self, filtros: FiltrosOpinion) -> int:
        if filtros.aspecto or filtros.texto:
            return len(self.consultar(filtros.con(limite=None, desplazamiento=0)))
        with self.bd.sesion() as s:
            return int(s.scalar(select(func.count()).select_from(self._select(filtros).subquery())) or 0)

    def guardar_revision(self, opinion_id: str, revision: Revision) -> None:
        with self.bd.sesion() as s:
            fila = s.get(OpinionFila, opinion_id)
            if fila is None:
                raise KeyError(opinion_id)
            s.add(RevisionFila(opinion_id=opinion_id, sentimiento=revision.sentimiento,
                               revisor_id=revision.revisor_id, nota=revision.nota, fecha_utc=revision.fecha_utc))
            # La etiqueta del modelo (fila.sentimiento) NO se toca.
            fila.revision_sentimiento = revision.sentimiento
            fila.revision_revisor_id = revision.revisor_id
            fila.revision_fecha_utc = revision.fecha_utc
            fila.revision_nota = revision.nota

    def historial_revisiones(self, opinion_id: str) -> list[Revision]:
        with self.bd.sesion() as s:
            filas = s.scalars(select(RevisionFila).where(RevisionFila.opinion_id == opinion_id)
                              .order_by(RevisionFila.fecha_utc, RevisionFila.id))
            return [Revision(r.sentimiento, r.revisor_id, r.fecha_utc, r.nota) for r in filas]

    def cambiar_visibilidad(self, opinion_id: str, visible: bool) -> None:
        with self.bd.sesion() as s:
            s.execute(update(OpinionFila).where(OpinionFila.id == opinion_id).values(visible=visible))

    def anonimizar_usuario(self, usuario_id: str) -> int:
        with self.bd.sesion() as s:
            r = s.execute(update(OpinionFila).where(OpinionFila.usuario_id == usuario_id).values(usuario_id=None))
            return int(r.rowcount or 0)


# ======================================================================= usuarios y tokens


def _a_usuario(f: UsuarioFila) -> Usuario:
    return Usuario(id=f.id, email=f.email, nombre_visible=f.nombre_visible, hash_contrasena=f.hash_contrasena,
                   rol=f.rol, activo=f.activo, creado_utc=f.creado_utc, ultimo_acceso_utc=f.ultimo_acceso_utc,
                   intentos_fallidos=f.intentos_fallidos, bloqueado_hasta=f.bloqueado_hasta)


class SqlRepositorioUsuarios:
    def __init__(self, bd: BaseDatos) -> None:
        self.bd = bd

    def crear(self, usuario: Usuario) -> None:
        with self.bd.sesion() as s:
            s.add(UsuarioFila(**usuario.__dict__))

    def por_email(self, email: str) -> Usuario | None:
        with self.bd.sesion() as s:
            f = s.scalar(select(UsuarioFila).where(UsuarioFila.email == email.lower()))
            return _a_usuario(f) if f else None

    def por_id(self, usuario_id: str) -> Usuario | None:
        with self.bd.sesion() as s:
            f = s.get(UsuarioFila, usuario_id)
            return _a_usuario(f) if f else None

    def actualizar(self, usuario: Usuario) -> None:
        with self.bd.sesion() as s:
            s.execute(update(UsuarioFila).where(UsuarioFila.id == usuario.id).values(**usuario.__dict__))

    def listar(self) -> list[Usuario]:
        with self.bd.sesion() as s:
            return [_a_usuario(f) for f in s.scalars(select(UsuarioFila).order_by(UsuarioFila.creado_utc))]

    def eliminar(self, usuario_id: str) -> None:
        with self.bd.sesion() as s:
            s.execute(delete(TokenApiFila).where(TokenApiFila.usuario_id == usuario_id))
            s.execute(delete(UsuarioFila).where(UsuarioFila.id == usuario_id))

    def contar(self) -> int:
        with self.bd.sesion() as s:
            return int(s.scalar(select(func.count()).select_from(UsuarioFila)) or 0)


class SqlRepositorioTokens:
    def __init__(self, bd: BaseDatos) -> None:
        self.bd = bd

    @staticmethod
    def _a(f: TokenApiFila) -> TokenApi:
        return TokenApi(f.id, f.usuario_id, f.nombre, f.hash_token, f.creado_utc, f.revocado, f.ultimo_uso_utc)

    def crear(self, token: TokenApi) -> None:
        with self.bd.sesion() as s:
            s.add(TokenApiFila(**token.__dict__))

    def por_hash(self, hash_token: str) -> TokenApi | None:
        with self.bd.sesion() as s:
            f = s.scalar(select(TokenApiFila).where(TokenApiFila.hash_token == hash_token))
            return self._a(f) if f else None

    def de_usuario(self, usuario_id: str) -> list[TokenApi]:
        with self.bd.sesion() as s:
            return [self._a(f) for f in s.scalars(select(TokenApiFila).where(TokenApiFila.usuario_id == usuario_id)
                                                  .order_by(TokenApiFila.creado_utc))]

    def revocar(self, token_id: str, usuario_id: str) -> None:
        with self.bd.sesion() as s:
            s.execute(update(TokenApiFila).where(TokenApiFila.id == token_id, TokenApiFila.usuario_id == usuario_id)
                      .values(revocado=True))

    def marcar_uso(self, token_id: str, fecha_utc: str) -> None:
        with self.bd.sesion() as s:
            s.execute(update(TokenApiFila).where(TokenApiFila.id == token_id).values(ultimo_uso_utc=fecha_utc))


# ======================================================================= operación


class SqlRepositorioAuditoria:
    def __init__(self, bd: BaseDatos) -> None:
        self.bd = bd

    def registrar(self, *, fecha_utc: str, usuario_id: str | None, accion: str,
                  detalle: dict[str, Any] | None = None, ip_hash: str | None = None) -> None:
        with self.bd.sesion() as s:
            s.add(AuditoriaFila(fecha_utc=fecha_utc, usuario_id=usuario_id, accion=accion, detalle=detalle or {},
                                ip_hash=ip_hash))

    def consultar(self, *, accion: str | None = None, usuario_id: str | None = None,
                  limite: int = 200) -> list[dict[str, Any]]:
        q = select(AuditoriaFila).order_by(AuditoriaFila.fecha_utc.desc(), AuditoriaFila.id.desc()).limit(limite)
        if accion:
            q = q.where(AuditoriaFila.accion == accion)
        if usuario_id:
            q = q.where(AuditoriaFila.usuario_id == usuario_id)
        with self.bd.sesion() as s:
            return [{"fecha_utc": a.fecha_utc, "usuario_id": a.usuario_id, "accion": a.accion,
                     "detalle": a.detalle, "ip_hash": a.ip_hash} for a in s.scalars(q)]


class SqlRepositorioLimites:
    def __init__(self, bd: BaseDatos) -> None:
        self.bd = bd

    def registrar(self, clave: str, fecha_utc: str) -> None:
        with self.bd.sesion() as s:
            s.add(LimiteUsoFila(clave=clave, fecha_utc=fecha_utc))

    def contar_desde(self, clave: str, desde_utc: str) -> int:
        with self.bd.sesion() as s:
            return int(s.scalar(select(func.count()).select_from(LimiteUsoFila)
                                .where(LimiteUsoFila.clave == clave, LimiteUsoFila.fecha_utc >= desde_utc)) or 0)

    def purgar_antes(self, fecha_utc: str) -> None:
        with self.bd.sesion() as s:
            s.execute(delete(LimiteUsoFila).where(LimiteUsoFila.fecha_utc < fecha_utc))


class SqlRepositorioMetricas:
    def __init__(self, bd: BaseDatos) -> None:
        self.bd = bd

    def registrar(self, metrica: MetricaLlamada) -> None:
        with self.bd.sesion() as s:
            s.add(MetricaLlmFila(**metrica.__dict__))

    def listar(self, desde_utc: str | None = None) -> list[MetricaLlamada]:
        q = select(MetricaLlmFila).order_by(MetricaLlmFila.fecha_utc)
        if desde_utc:
            q = q.where(MetricaLlmFila.fecha_utc >= desde_utc)
        with self.bd.sesion() as s:
            return [MetricaLlamada(m.fecha_utc, m.proveedor, m.modelo, m.version_prompt, m.latencia_ms, m.exito,
                                   m.tipo_error, m.tokens_entrada, m.tokens_salida) for m in s.scalars(q)]


class SqlRepositorioTrabajos:
    def __init__(self, bd: BaseDatos) -> None:
        self.bd = bd

    @staticmethod
    def _a(f: TrabajoLoteFila) -> TrabajoLote:
        return TrabajoLote(id=f.id, usuario_id=f.usuario_id, estado=f.estado, total=f.total, procesadas=f.procesadas,
                           fallidas=f.fallidas, creado_utc=f.creado_utc, errores=list(f.errores or []),
                           filas=list(f.filas or []), resultados=list(f.resultados or []))

    def crear(self, trabajo: TrabajoLote) -> None:
        with self.bd.sesion() as s:
            s.add(TrabajoLoteFila(**trabajo.__dict__))

    def obtener(self, trabajo_id: str) -> TrabajoLote | None:
        with self.bd.sesion() as s:
            f = s.get(TrabajoLoteFila, trabajo_id)
            return self._a(f) if f else None

    def actualizar(self, trabajo: TrabajoLote) -> None:
        with self.bd.sesion() as s:
            s.execute(update(TrabajoLoteFila).where(TrabajoLoteFila.id == trabajo.id).values(**trabajo.__dict__))

    def siguiente_pendiente(self) -> TrabajoLote | None:
        with self.bd.sesion() as s:
            f = s.scalar(select(TrabajoLoteFila)
                         .where(or_(TrabajoLoteFila.estado == "pendiente", TrabajoLoteFila.estado == "procesando"))
                         .order_by(TrabajoLoteFila.creado_utc).limit(1))
            return self._a(f) if f else None

    def listar(self, usuario_id: str | None = None, limite: int = 50) -> list[TrabajoLote]:
        q = select(TrabajoLoteFila).order_by(TrabajoLoteFila.creado_utc.desc()).limit(limite)
        if usuario_id:
            q = q.where(TrabajoLoteFila.usuario_id == usuario_id)
        with self.bd.sesion() as s:
            return [self._a(f) for f in s.scalars(q)]


class SqlRepositorioResumenes:
    def __init__(self, bd: BaseDatos) -> None:
        self.bd = bd

    def obtener(self, evento_id: str, edicion_anio: int | None) -> Resumen | None:
        q = select(ResumenFila).where(ResumenFila.evento_id == evento_id)
        q = q.where(ResumenFila.edicion_anio.is_(None) if edicion_anio is None
                    else ResumenFila.edicion_anio == edicion_anio)
        with self.bd.sesion() as s:
            f = s.scalar(q.order_by(ResumenFila.fecha_utc.desc()).limit(1))
            return Resumen(f.evento_id, f.edicion_anio, f.texto, f.n_opiniones, f.modelo, f.fecha_utc,
                           f.version_prompt) if f else None

    def guardar(self, resumen: Resumen) -> None:
        with self.bd.sesion() as s:
            s.add(ResumenFila(**resumen.__dict__))


class SqlRepositorioDenuncias:
    def __init__(self, bd: BaseDatos) -> None:
        self.bd = bd

    @staticmethod
    def _a(f: DenunciaFila) -> Denuncia:
        return Denuncia(f.id, f.opinion_id, f.usuario_id, f.motivo, f.fecha_utc, f.atendida)

    def crear(self, denuncia: Denuncia) -> None:
        with self.bd.sesion() as s:
            s.add(DenunciaFila(**denuncia.__dict__))

    def pendientes(self) -> list[Denuncia]:
        with self.bd.sesion() as s:
            return [self._a(f) for f in s.scalars(select(DenunciaFila).where(DenunciaFila.atendida.is_(False))
                                                  .order_by(DenunciaFila.fecha_utc))]

    def de_opinion(self, opinion_id: str) -> list[Denuncia]:
        with self.bd.sesion() as s:
            return [self._a(f) for f in s.scalars(select(DenunciaFila).where(DenunciaFila.opinion_id == opinion_id))]

    def marcar_atendidas(self, opinion_id: str) -> None:
        with self.bd.sesion() as s:
            s.execute(update(DenunciaFila).where(DenunciaFila.opinion_id == opinion_id).values(atendida=True))
