"""Tokens personales para la API REST (v3): se muestran una sola vez y se guardan como hash; revocables."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from paddock.aplicacion.autorizacion import Actor, requerir_sesion
from paddock.aplicacion.usuarios import actor_de
from paddock.dominio.entidades import TokenApi
from paddock.dominio.errores import EntradaInvalidaError, TokenInvalidoError
from paddock.puertos.repositorios import RepositorioAuditoria, RepositorioTokens, RepositorioUsuarios
from paddock.puertos.servicios import GeneradorId, Reloj, iso

MAX_TOKENS = 5


@dataclass
class TokensApi:
    tokens: RepositorioTokens
    usuarios: RepositorioUsuarios
    auditoria: RepositorioAuditoria
    reloj: Reloj
    ids: GeneradorId
    generar: Callable[[], str]
    hashear: Callable[[str], str]

    def crear(self, actor: Actor | None, nombre: str) -> str:
        a = requerir_sesion(actor)
        nombre = (nombre or "").strip()
        if not 2 <= len(nombre) <= 40:
            raise EntradaInvalidaError("El nombre del token debe tener entre 2 y 40 caracteres.")
        activos = [t for t in self.tokens.de_usuario(a.usuario_id) if not t.revocado]
        if len(activos) >= MAX_TOKENS:
            raise EntradaInvalidaError(f"Máximo {MAX_TOKENS} tokens activos. Revoca alguno.")
        plano = self.generar()
        t = TokenApi(id=self.ids.nuevo(), usuario_id=a.usuario_id, nombre=nombre, hash_token=self.hashear(plano),
                     creado_utc=iso(self.reloj.ahora()))
        self.tokens.crear(t)
        self.auditoria.registrar(fecha_utc=t.creado_utc, usuario_id=a.usuario_id, accion="token_creado",
                                 detalle={"token_id": t.id, "nombre": nombre})
        return plano

    def listar(self, actor: Actor | None) -> list[TokenApi]:
        a = requerir_sesion(actor)
        return self.tokens.de_usuario(a.usuario_id)

    def revocar(self, actor: Actor | None, token_id: str) -> None:
        a = requerir_sesion(actor)
        self.tokens.revocar(token_id, a.usuario_id)
        self.auditoria.registrar(fecha_utc=iso(self.reloj.ahora()), usuario_id=a.usuario_id, accion="token_revocado",
                                 detalle={"token_id": token_id})

    def autenticar(self, token: str | None) -> Actor:
        if not token or not token.startswith("pg_"):
            raise TokenInvalidoError("Token ausente o con formato inválido.")
        t = self.tokens.por_hash(self.hashear(token))
        if t is None or t.revocado:
            raise TokenInvalidoError("Token desconocido o revocado.")
        u = self.usuarios.por_id(t.usuario_id)
        if u is None or not u.activo:
            raise TokenInvalidoError("La cuenta del token no está activa.")
        self.tokens.marcar_uso(t.id, iso(self.reloj.ahora()))
        return actor_de(u)
