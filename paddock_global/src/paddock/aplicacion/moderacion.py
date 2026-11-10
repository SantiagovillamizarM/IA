"""Casos de uso de moderación: cola priorizada, revisión humana, denuncias y ocultación.

La etiqueta del modelo **nunca** se sobrescribe: la revisión se guarda aparte (historial completo).
Ninguna opinión se borra: un moderador solo puede ocultarla (``visible=false``).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from paddock.aplicacion.autorizacion import Actor, requerir_rol, requerir_sesion
from paddock.dominio.entidades import Denuncia, FiltrosOpinion, Opinion, Revision
from paddock.dominio.enums import SENTIMIENTOS, MotivoDenuncia, Rol
from paddock.dominio.errores import EntradaInvalidaError
from paddock.puertos.repositorios import RepositorioAuditoria, RepositorioDenuncias, RepositorioOpiniones
from paddock.puertos.servicios import GeneradorId, Reloj, iso


@dataclass(frozen=True)
class ElementoCola:
    opinion: Opinion
    prioridad: int
    motivos: tuple[str, ...]
    denuncias: int


def prioridad(op: Opinion, n_denuncias: int) -> tuple[int, list[str]]:
    """Primero las denunciadas, luego ironía, intensidad baja con sentimiento fuerte y mixtas."""
    puntos, motivos = 0, []
    if n_denuncias:
        puntos += 10 + n_denuncias
        motivos.append(f"denunciada ×{n_denuncias}")
    if op.ironia:
        puntos += 5
        motivos.append("ironía")
    if op.intensidad is not None and op.intensidad <= 2 and op.sentimiento in ("positivo", "negativo"):
        puntos += 3
        motivos.append("intensidad baja con sentimiento fuerte")
    if op.sentimiento == "mixto":
        puntos += 2
        motivos.append("mixta")
    return puntos, motivos


@dataclass
class Moderacion:
    opiniones: RepositorioOpiniones
    denuncias: RepositorioDenuncias
    auditoria: RepositorioAuditoria
    reloj: Reloj
    ids: GeneradorId

    def _audit(self, actor: Actor, accion: str, **detalle: Any) -> None:
        self.auditoria.registrar(fecha_utc=iso(self.reloj.ahora()), usuario_id=actor.usuario_id, accion=accion,
                                 detalle=detalle)

    def cola(self, actor: Actor | None, limite: int = 50, incluir_revisadas: bool = False) -> list[ElementoCola]:
        requerir_rol(actor, Rol.MODERADOR)
        por_opinion: dict[str, int] = {}
        for d in self.denuncias.pendientes():
            por_opinion[d.opinion_id] = por_opinion.get(d.opinion_id, 0) + 1
        elementos = []
        for op in self.opiniones.consultar(FiltrosOpinion(incluir_ocultas=True)):
            n = por_opinion.get(op.id, 0)
            if (op.revision is not None and not incluir_revisadas and not n) or (not op.visible and not n):
                continue
            puntos, motivos = prioridad(op, n)
            elementos.append(ElementoCola(op, puntos, tuple(motivos), n))
        elementos.sort(key=lambda e: (-e.prioridad, e.opinion.fecha_utc))
        return elementos[:limite]

    def revisar(self, actor: Actor | None, opinion_id: str, sentimiento: str, nota: str = "") -> Revision:
        """Confirma (mismo sentimiento) o corrige. Se guarda en «revisiones»; la etiqueta del modelo no cambia."""
        a = requerir_rol(actor, Rol.MODERADOR)
        if sentimiento not in SENTIMIENTOS:
            raise EntradaInvalidaError("Sentimiento no válido.")
        nota = (nota or "").strip()
        if len(nota) > 500:
            raise EntradaInvalidaError("La nota no puede superar 500 caracteres.")
        op = self.opiniones.obtener(opinion_id)
        if op is None:
            raise EntradaInvalidaError("La opinión no existe.")
        rev = Revision(sentimiento=sentimiento, revisor_id=a.usuario_id, fecha_utc=iso(self.reloj.ahora()), nota=nota)
        self.opiniones.guardar_revision(opinion_id, rev)
        self.denuncias.marcar_atendidas(opinion_id)
        self._audit(a, "revision", opinion_id=opinion_id, modelo=op.sentimiento, humano=sentimiento,
                    confirma=op.sentimiento == sentimiento)
        return rev

    def cambiar_visibilidad(self, actor: Actor | None, opinion_id: str, visible: bool) -> None:
        a = requerir_rol(actor, Rol.MODERADOR)
        if self.opiniones.obtener(opinion_id) is None:
            raise EntradaInvalidaError("La opinión no existe.")
        self.opiniones.cambiar_visibilidad(opinion_id, visible)
        self.denuncias.marcar_atendidas(opinion_id)
        self._audit(a, "opinion_mostrada" if visible else "opinion_ocultada", opinion_id=opinion_id)

    def denunciar(self, actor: Actor | None, opinion_id: str, motivo: str) -> Denuncia:
        a = requerir_sesion(actor)
        if motivo not in {m.value for m in MotivoDenuncia}:
            raise EntradaInvalidaError("Motivo de denuncia no válido.")
        if self.opiniones.obtener(opinion_id) is None:
            raise EntradaInvalidaError("La opinión no existe.")
        if any(d.usuario_id == a.usuario_id and not d.atendida for d in self.denuncias.de_opinion(opinion_id)):
            raise EntradaInvalidaError("Ya denunciaste esta opinión; un moderador la revisará.")
        d = Denuncia(id=self.ids.nuevo(), opinion_id=opinion_id, usuario_id=a.usuario_id, motivo=motivo,
                     fecha_utc=iso(self.reloj.ahora()))
        self.denuncias.crear(d)
        self._audit(a, "denuncia", opinion_id=opinion_id, motivo=motivo)
        return d
