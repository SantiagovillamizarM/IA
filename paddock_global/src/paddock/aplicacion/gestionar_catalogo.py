"""Caso de uso: administración del catálogo y de la jerga (solo admin)."""

from __future__ import annotations

import re
from dataclasses import dataclass, replace

from paddock.aplicacion.autorizacion import Actor, requerir_rol
from paddock.dominio.entidades import Evento
from paddock.dominio.enums import Rol
from paddock.dominio.errores import EntradaInvalidaError
from paddock.puertos.repositorios import RepositorioAuditoria, RepositorioCatalogo
from paddock.puertos.servicios import Reloj, iso

_SLUG = re.compile(r"^ev-[a-z0-9]+(-[a-z0-9]+)*$")


@dataclass
class GestionarCatalogo:
    catalogo: RepositorioCatalogo
    auditoria: RepositorioAuditoria
    reloj: Reloj

    def _audit(self, actor: Actor, accion: str, **detalle: object) -> None:
        self.auditoria.registrar(fecha_utc=iso(self.reloj.ahora()), usuario_id=actor.usuario_id, accion=accion,
                                 detalle=dict(detalle))

    def cambiar_activo(self, actor: Actor | None, evento_id: str, activo: bool) -> None:
        a = requerir_rol(actor, Rol.ADMIN)
        ev = self.catalogo.obtener().evento(evento_id)
        if ev is None:
            raise EntradaInvalidaError("El evento no existe.")
        self.catalogo.guardar_evento(replace(ev, activo=activo))
        self._audit(a, "evento_activado" if activo else "evento_desactivado", evento_id=evento_id)

    def anadir_evento(self, actor: Actor | None, evento: Evento) -> None:
        a = requerir_rol(actor, Rol.ADMIN)
        cat = self.catalogo.obtener()
        if not _SLUG.match(evento.id):
            raise EntradaInvalidaError("El id debe ser un slug que empiece por «ev-» (minúsculas, números y guiones).")
        if cat.evento(evento.id) is not None:
            raise EntradaInvalidaError("Ya existe un evento con ese id.")
        if cat.campeonato(evento.campeonato_id) is None:
            raise EntradaInvalidaError("El campeonato no existe.")
        for campo in ("nombre", "pais", "sede"):
            valor = getattr(evento, campo).strip()
            if not 2 <= len(valor) <= 120:
                raise EntradaInvalidaError(f"El campo «{campo}» debe tener entre 2 y 120 caracteres.")
        if evento.lat is not None and not -90 <= evento.lat <= 90:
            raise EntradaInvalidaError("La latitud debe estar entre -90 y 90.")
        if evento.lon is not None and not -180 <= evento.lon <= 180:
            raise EntradaInvalidaError("La longitud debe estar entre -180 y 180.")
        self.catalogo.guardar_evento(evento)
        self._audit(a, "evento_creado", evento_id=evento.id)

    def editar_jerga(self, actor: Actor | None, disciplina_id: str, terminos: list[str]) -> None:
        a = requerir_rol(actor, Rol.ADMIN)
        if self.catalogo.obtener().disciplina(disciplina_id) is None:
            raise EntradaInvalidaError("La disciplina no existe.")
        limpios = [t.strip() for t in terminos if t.strip()]
        if len(limpios) > 40 or any(len(t) > 40 for t in limpios):
            raise EntradaInvalidaError("Máximo 40 términos de hasta 40 caracteres.")
        self.catalogo.guardar_jerga(disciplina_id, limpios)
        self._audit(a, "jerga_editada", disciplina_id=disciplina_id, n=len(limpios))
