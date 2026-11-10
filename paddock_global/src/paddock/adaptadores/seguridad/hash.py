"""Hash de contraseñas (argon2id), de tokens de API (SHA-256) y de IP (HMAC con sal)."""

from __future__ import annotations

import hashlib
import hmac
import ipaddress
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError


class HasherArgon2:
    """argon2id con los parámetros recomendados por ``argon2-cffi`` (RFC 9106, perfil de bajo consumo)."""

    def __init__(self) -> None:
        self._ph = PasswordHasher()  # tipo argon2id por defecto
        self._ficticio = self._ph.hash(secrets.token_urlsafe(16))

    def hash(self, contrasena: str) -> str:
        return self._ph.hash(contrasena)

    def verificar(self, hash_guardado: str, contrasena: str) -> bool:
        try:
            return self._ph.verify(hash_guardado, contrasena)
        except (VerifyMismatchError, VerificationError, InvalidHashError):
            return False

    def verificar_ficticio(self, contrasena: str) -> None:
        """Iguala el tiempo de respuesta cuando el correo no existe (evita enumerar cuentas)."""
        self.verificar(self._ficticio, contrasena)

    def necesita_rehash(self, hash_guardado: str) -> bool:
        try:
            return self._ph.check_needs_rehash(hash_guardado)
        except InvalidHashError:
            return True


def nuevo_token_api() -> str:
    """Token aleatorio de 256 bits con prefijo reconocible. Se muestra UNA vez y se guarda solo su hash."""
    return "pg_" + secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    # SHA-256 basta: el token tiene 256 bits de entropía (no es una contraseña elegida por una persona).
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def hash_ip(ip: str | None, sal: str) -> str | None:
    """La IP nunca se guarda en claro: HMAC-SHA256 con una sal del servidor (``SAL_HASH_IP``)."""
    if not ip:
        return None
    return hmac.new(sal.encode("utf-8"), ip.encode("utf-8"), hashlib.sha256).hexdigest()


def _es_confiable(ip: str, proxies_confiables: set[str]) -> bool:
    try:
        direccion = ipaddress.ip_address(ip)
    except ValueError:
        return False
    for p in proxies_confiables:
        try:
            if direccion in ipaddress.ip_network(p, strict=False):
                return True
        except ValueError:
            continue
    return False


def ip_cliente(remota: str | None, x_forwarded_for: str | None, proxies_confiables: set[str]) -> str | None:
    """Toma la IP de ``X-Forwarded-For`` solo si la conexión viene de un proxy de confianza (IP o CIDR)."""
    if remota and x_forwarded_for and _es_confiable(remota, proxies_confiables):
        return x_forwarded_for.split(",")[0].strip() or remota
    return remota
