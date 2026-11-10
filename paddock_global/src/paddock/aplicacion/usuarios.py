"""Casos de uso de cuentas: registro, inicio/cierre de sesión, gestión por el admin y «Mi cuenta».

El control de acceso se hace aquí (``requerir_rol``), no solo ocultando páginas.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from paddock.aplicacion.autorizacion import Actor, requerir_rol, requerir_sesion
from paddock.dominio.entidades import FiltrosOpinion, Usuario
from paddock.dominio.enums import Rol
from paddock.dominio.errores import (
    CredencialesIncorrectasError,
    CuentaBloqueadaError,
    EntradaInvalidaError,
    PermisoDenegadoError,
    RegistroCerradoError,
)
from paddock.dominio.reglas import normalizar_email, validar_contrasena
from paddock.puertos.repositorios import RepositorioAuditoria, RepositorioOpiniones, RepositorioUsuarios
from paddock.puertos.servicios import GeneradorId, HasherContrasenas, Reloj, iso

MAX_INTENTOS = 5
MINUTOS_BLOQUEO = 15


def actor_de(u: Usuario) -> Actor:
    return Actor(usuario_id=u.id, rol=u.rol, email=u.email, nombre=u.nombre_visible)


@dataclass
class ServicioCuentas:
    usuarios: RepositorioUsuarios
    opiniones: RepositorioOpiniones
    auditoria: RepositorioAuditoria
    hasher: HasherContrasenas
    reloj: Reloj
    ids: GeneradorId
    contrasenas_comunes: set[str]
    registro_abierto: bool = True

    def _audit(self, accion: str, usuario_id: str | None, ip_hash: str | None = None, **detalle: Any) -> None:
        self.auditoria.registrar(fecha_utc=iso(self.reloj.ahora()), usuario_id=usuario_id, accion=accion,
                                 detalle=detalle, ip_hash=ip_hash)

    # ------------------------------------------------------------ RegistrarUsuario
    def registrar(self, email: str, nombre_visible: str, contrasena: str, *, rol: str = Rol.AFICIONADO.value,
                  forzar: bool = False, ip_hash: str | None = None) -> Usuario:
        """``forzar`` solo lo usa ``scripts/crear_admin.py`` (ignora REGISTRO_ABIERTO)."""
        if not self.registro_abierto and not forzar:
            raise RegistroCerradoError("El registro de nuevas cuentas está cerrado.")
        email_n = normalizar_email(email)
        nombre = (nombre_visible or "").strip()
        if not 2 <= len(nombre) <= 40:
            raise EntradaInvalidaError("El nombre visible debe tener entre 2 y 40 caracteres.")
        validar_contrasena(contrasena, self.contrasenas_comunes, email_n)
        if rol not in {r.value for r in Rol}:
            raise EntradaInvalidaError("Rol desconocido.")
        if self.usuarios.por_email(email_n) is not None:
            # Mensaje neutro: no confirma de forma explícita que el correo existe.
            raise EntradaInvalidaError("No se pudo crear la cuenta con esos datos. Si ya tienes una, inicia sesión.")
        u = Usuario(id=self.ids.nuevo(), email=email_n, nombre_visible=nombre,
                    hash_contrasena=self.hasher.hash(contrasena), rol=rol, creado_utc=iso(self.reloj.ahora()))
        self.usuarios.crear(u)
        self._audit("registro", u.id, ip_hash, rol=rol)
        return u

    # ------------------------------------------------------------ IniciarSesion
    def iniciar_sesion(self, email: str, contrasena: str, ip_hash: str | None = None) -> Actor:
        ahora = self.reloj.ahora()
        try:
            email_n = normalizar_email(email)
        except EntradaInvalidaError:
            self.hasher.verificar_ficticio(contrasena)
            raise CredencialesIncorrectasError() from None
        u = self.usuarios.por_email(email_n)
        if u is None:
            self.hasher.verificar_ficticio(contrasena)
            self._audit("login_fallido", None, ip_hash, motivo="desconocido")
            raise CredencialesIncorrectasError()
        if u.bloqueado_hasta and datetime.fromisoformat(u.bloqueado_hasta) > ahora:
            self._audit("login_bloqueado", u.id, ip_hash)
            raise CuentaBloqueadaError(
                f"Demasiados intentos fallidos. Espera {MINUTOS_BLOQUEO} minutos e inténtalo de nuevo.")
        if not self.hasher.verificar(u.hash_contrasena, contrasena) or not u.activo:
            intentos = u.intentos_fallidos + 1
            cambios: dict[str, Any] = {"intentos_fallidos": intentos}
            if intentos >= MAX_INTENTOS:
                cambios = {"intentos_fallidos": 0, "bloqueado_hasta": iso(ahora + timedelta(minutes=MINUTOS_BLOQUEO))}
                self._audit("cuenta_bloqueada", u.id, ip_hash, minutos=MINUTOS_BLOQUEO)
            self.usuarios.actualizar(u.con(**cambios))
            self._audit("login_fallido", u.id, ip_hash, intentos=intentos)
            raise CredencialesIncorrectasError()
        nuevo_hash = u.hash_contrasena
        if self.hasher.necesita_rehash(u.hash_contrasena):
            nuevo_hash = self.hasher.hash(contrasena)
        u = u.con(intentos_fallidos=0, bloqueado_hasta=None, ultimo_acceso_utc=iso(ahora), hash_contrasena=nuevo_hash)
        self.usuarios.actualizar(u)
        self._audit("login", u.id, ip_hash)
        return actor_de(u)

    def cerrar_sesion(self, actor: Actor | None, ip_hash: str | None = None) -> None:
        if actor is not None:
            self._audit("logout", actor.usuario_id, ip_hash)

    def refrescar(self, actor: Actor) -> Actor | None:
        """Relee el usuario (rol o estado pueden haber cambiado). ``None`` si ya no existe o está inactivo."""
        u = self.usuarios.por_id(actor.usuario_id)
        return actor_de(u) if u and u.activo else None

    # ------------------------------------------------------------ Mi cuenta
    def exportar_mis_datos(self, actor: Actor | None) -> dict[str, Any]:
        a = requerir_sesion(actor)
        u = self.usuarios.por_id(a.usuario_id)
        if u is None:
            raise PermisoDenegadoError("La cuenta no existe.")
        ops = self.opiniones.consultar(FiltrosOpinion(usuario_id=a.usuario_id, incluir_ocultas=True))
        self._audit("exportar_datos", a.usuario_id)
        return {
            "cuenta": {"id": u.id, "email": u.email, "nombre_visible": u.nombre_visible, "rol": u.rol,
                       "creado_utc": u.creado_utc, "ultimo_acceso_utc": u.ultimo_acceso_utc},
            "opiniones": [o.a_dict() for o in ops],
        }

    def eliminar_mi_cuenta(self, actor: Actor | None, contrasena: str) -> int:
        """Borra la cuenta y anonimiza sus opiniones (``usuario_id = null``). Devuelve cuántas anonimizó."""
        a = requerir_sesion(actor)
        u = self.usuarios.por_id(a.usuario_id)
        if u is None or not self.hasher.verificar(u.hash_contrasena, contrasena):
            raise CredencialesIncorrectasError("La contraseña no es correcta.")
        n = self.opiniones.anonimizar_usuario(u.id)
        self.usuarios.eliminar(u.id)
        self._audit("cuenta_eliminada", None, opiniones_anonimizadas=n)
        return n

    # ------------------------------------------------------------ administración (solo admin)
    def listar(self, actor: Actor | None) -> list[Usuario]:
        requerir_rol(actor, Rol.ADMIN)
        return self.usuarios.listar()

    def cambiar_rol(self, actor: Actor | None, usuario_id: str, rol: str) -> None:
        admin = requerir_rol(actor, Rol.ADMIN)
        if rol not in {r.value for r in Rol}:
            raise EntradaInvalidaError("Rol desconocido.")
        if usuario_id == admin.usuario_id and rol != Rol.ADMIN.value:
            raise EntradaInvalidaError("No puedes quitarte el rol de administrador a ti mismo.")
        u = self.usuarios.por_id(usuario_id)
        if u is None:
            raise EntradaInvalidaError("Usuario no encontrado.")
        self.usuarios.actualizar(u.con(rol=rol))
        self._audit("cambio_rol", admin.usuario_id, objetivo=usuario_id, antes=u.rol, despues=rol)

    def cambiar_activo(self, actor: Actor | None, usuario_id: str, activo: bool) -> None:
        admin = requerir_rol(actor, Rol.ADMIN)
        if usuario_id == admin.usuario_id:
            raise EntradaInvalidaError("No puedes desactivar tu propia cuenta.")
        u = self.usuarios.por_id(usuario_id)
        if u is None:
            raise EntradaInvalidaError("Usuario no encontrado.")
        self.usuarios.actualizar(u.con(activo=activo, bloqueado_hasta=None, intentos_fallidos=0))
        self._audit("usuario_activado" if activo else "usuario_bloqueado", admin.usuario_id, objetivo=usuario_id)

    def consultar_auditoria(self, actor: Actor | None, accion: str | None = None,
                            usuario_id: str | None = None, limite: int = 200) -> list[dict[str, Any]]:
        requerir_rol(actor, Rol.ADMIN)
        return self.auditoria.consultar(accion=accion, usuario_id=usuario_id, limite=limite)
