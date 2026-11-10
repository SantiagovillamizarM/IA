"""Cuentas, sesión, autorización por rol y limitador persistente (SQLite real en tmp_path)."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from paddock.adaptadores.llm.falso import ClasificadorFalso
from paddock.adaptadores.persistencia.json_repo import cargar_catalogo, cargar_jerga
from paddock.adaptadores.persistencia.sql_repo import (
    BaseDatos,
    SqlRepositorioAuditoria,
    SqlRepositorioCatalogo,
    SqlRepositorioLimites,
    SqlRepositorioOpiniones,
    SqlRepositorioUsuarios,
)
from paddock.adaptadores.seguridad.hash import HasherArgon2, hash_ip, hash_token, ip_cliente, nuevo_token_api
from paddock.adaptadores.seguridad.limitador import LimitadorTasa
from paddock.aplicacion.autorizacion import Actor, requerir_rol
from paddock.aplicacion.emitir_opinion import EmitirOpinion, SolicitudOpinion
from paddock.aplicacion.gestionar_catalogo import GestionarCatalogo
from paddock.aplicacion.usuarios import ServicioCuentas
from paddock.config import DATOS
from paddock.dominio import errores as err
from paddock.dominio.entidades import Evento, FiltrosOpinion
from paddock.dominio.enums import Rol
from paddock.dominio.reglas import sesion_expirada
from paddock.puertos.servicios import GeneradorUuid4
from tests.conftest import RelojFijo, opinion_ejemplo

pytestmark = pytest.mark.integracion
CLAVE = "Tres-Palabras-Largas-9"


@pytest.fixture
def entorno(tmp_path):
    bd = BaseDatos(f"sqlite:///{(tmp_path / 'u.db').as_posix()}")
    bd.crear_esquema()
    SqlRepositorioCatalogo(bd).sembrar(cargar_catalogo(DATOS / "catalogo.json"), cargar_jerga(DATOS / "jerga.json"))
    reloj = RelojFijo()
    cuentas = ServicioCuentas(
        usuarios=SqlRepositorioUsuarios(bd), opiniones=SqlRepositorioOpiniones(bd), auditoria=SqlRepositorioAuditoria(bd),
        hasher=HasherArgon2(), reloj=reloj, ids=GeneradorUuid4(), contrasenas_comunes={"password1234"},
    )
    return bd, reloj, cuentas


def test_hash_argon2id_verificable(entorno):
    _, _, cuentas = entorno
    u = cuentas.registrar("Ana@Ejemplo.com", "Ana", CLAVE)
    assert u.email == "ana@ejemplo.com"
    assert u.hash_contrasena.startswith("$argon2id$")
    assert CLAVE not in u.hash_contrasena
    assert cuentas.hasher.verificar(u.hash_contrasena, CLAVE)
    assert not cuentas.hasher.verificar(u.hash_contrasena, "otra-clave-larga-1")


def test_registro_valida_politica(entorno):
    _, _, cuentas = entorno
    with pytest.raises(err.EntradaInvalidaError):
        cuentas.registrar("b@ejemplo.com", "Bea", "corta")
    with pytest.raises(err.EntradaInvalidaError):
        cuentas.registrar("b@ejemplo.com", "Bea", "password1234")
    cuentas.registrar("b@ejemplo.com", "Bea", CLAVE)
    with pytest.raises(err.EntradaInvalidaError):
        cuentas.registrar("B@EJEMPLO.COM", "Bea2", CLAVE)
    cuentas.registro_abierto = False
    with pytest.raises(err.RegistroCerradoError):
        cuentas.registrar("c@ejemplo.com", "Ceci", CLAVE)
    assert cuentas.registrar("admin@ejemplo.com", "Admin", CLAVE, rol="admin", forzar=True).rol == "admin"


def test_login_y_mensaje_generico(entorno):
    _, _, cuentas = entorno
    cuentas.registrar("ana@ejemplo.com", "Ana", CLAVE)
    actor = cuentas.iniciar_sesion("  ANA@ejemplo.com ", CLAVE)
    assert actor.rol == "aficionado" and actor.email == "ana@ejemplo.com"
    with pytest.raises(err.CredencialesIncorrectasError) as e1:
        cuentas.iniciar_sesion("ana@ejemplo.com", "contraseña-equivocada")
    with pytest.raises(err.CredencialesIncorrectasError) as e2:
        cuentas.iniciar_sesion("nadie@ejemplo.com", CLAVE)
    assert str(e1.value) == str(e2.value) == "Correo o contraseña incorrectos."


def test_bloqueo_tras_5_intentos_y_desbloqueo_a_los_15_min(entorno):
    _, reloj, cuentas = entorno
    cuentas.registrar("ana@ejemplo.com", "Ana", CLAVE)
    for _ in range(5):
        with pytest.raises(err.CredencialesIncorrectasError):
            cuentas.iniciar_sesion("ana@ejemplo.com", "mal-mal-mal-mal")
    with pytest.raises(err.CuentaBloqueadaError):
        cuentas.iniciar_sesion("ana@ejemplo.com", CLAVE)  # ni con la buena
    reloj.avanzar(minutes=15, seconds=1)
    assert cuentas.iniciar_sesion("ana@ejemplo.com", CLAVE).email == "ana@ejemplo.com"
    acciones = [r["accion"] for r in cuentas.auditoria.consultar()]
    assert "cuenta_bloqueada" in acciones and "login" in acciones


def test_expiracion_de_sesion():
    t0 = datetime(2026, 11, 10, 12, 0)
    assert not sesion_expirada(t0, t0 + timedelta(minutes=60), 60)
    assert sesion_expirada(t0, t0 + timedelta(minutes=60, seconds=1), 60)


def test_autorizacion_en_casos_de_uso(entorno):
    bd, reloj, cuentas = entorno
    aficionado = Actor("u-1", "aficionado")
    moderador = Actor("u-2", "moderador")
    admin = Actor("u-3", "admin")
    with pytest.raises(err.SesionRequeridaError):
        requerir_rol(None, Rol.AFICIONADO)
    for actor in (aficionado, moderador):
        with pytest.raises(err.PermisoDenegadoError):
            cuentas.listar(actor)
        with pytest.raises(err.PermisoDenegadoError):
            cuentas.consultar_auditoria(actor)
    with pytest.raises(err.PermisoDenegadoError):
        requerir_rol(aficionado, Rol.MODERADOR)
    requerir_rol(moderador, Rol.MODERADOR)
    gc = GestionarCatalogo(catalogo=SqlRepositorioCatalogo(bd), auditoria=SqlRepositorioAuditoria(bd), reloj=reloj)
    with pytest.raises(err.PermisoDenegadoError):
        gc.cambiar_activo(aficionado, "ev-f1-monaco", False)
    gc.cambiar_activo(admin, "ev-f1-monaco", False)
    assert SqlRepositorioCatalogo(bd).obtener().evento("ev-f1-monaco").activo is False
    with pytest.raises(err.EntradaInvalidaError):
        gc.anadir_evento(admin, Evento("mal id", "f1", "X", "Y", "Z"))
    gc.anadir_evento(admin, Evento("ev-f1-nuevo", "f1", "GP Nuevo", "País", "Sede", 1.0, 2.0))
    gc.editar_jerga(admin, "rally", ["tramo"])
    assert cuentas.listar(admin) == []


def test_admin_cambia_rol_y_bloquea(entorno):
    _, _, cuentas = entorno
    admin_u = cuentas.registrar("admin@ejemplo.com", "Admin", CLAVE, rol="admin", forzar=True)
    ana = cuentas.registrar("ana@ejemplo.com", "Ana", CLAVE)
    admin = cuentas.iniciar_sesion("admin@ejemplo.com", CLAVE)
    cuentas.cambiar_rol(admin, ana.id, "moderador")
    assert cuentas.iniciar_sesion("ana@ejemplo.com", CLAVE).rol == "moderador"
    with pytest.raises(err.EntradaInvalidaError):
        cuentas.cambiar_rol(admin, admin_u.id, "aficionado")
    cuentas.cambiar_activo(admin, ana.id, False)
    with pytest.raises(err.CredencialesIncorrectasError):
        cuentas.iniciar_sesion("ana@ejemplo.com", CLAVE)
    assert "cambio_rol" in [r["accion"] for r in cuentas.consultar_auditoria(admin)]


def test_exportar_y_eliminar_cuenta_anonimiza(entorno):
    bd, _, cuentas = entorno
    ana = cuentas.registrar("ana@ejemplo.com", "Ana", CLAVE)
    actor = cuentas.iniciar_sesion("ana@ejemplo.com", CLAVE)
    repo = SqlRepositorioOpiniones(bd)
    repo.guardar(opinion_ejemplo(1, usuario_id=ana.id))
    datos = cuentas.exportar_mis_datos(actor)
    assert datos["cuenta"]["email"] == "ana@ejemplo.com" and len(datos["opiniones"]) == 1
    assert "hash_contrasena" not in datos["cuenta"]
    with pytest.raises(err.CredencialesIncorrectasError):
        cuentas.eliminar_mi_cuenta(actor, "equivocada-larga-1")
    assert cuentas.eliminar_mi_cuenta(actor, CLAVE) == 1
    assert repo.obtener(opinion_ejemplo(1).id).usuario_id is None
    assert repo.contar(FiltrosOpinion()) == 1  # la opinión sigue, anónima
    with pytest.raises(err.CredencialesIncorrectasError):
        cuentas.iniciar_sesion("ana@ejemplo.com", CLAVE)


def test_limitador_persistente_rechaza_la_11_sin_llamar_al_modelo(entorno, tmp_path):
    bd, reloj, _ = entorno
    clf = ClasificadorFalso()
    limitador = LimitadorTasa(SqlRepositorioLimites(bd), reloj, por_usuario_5min=10, global_diario=1000)
    uc = EmitirOpinion(catalogo=SqlRepositorioCatalogo(bd), opiniones=SqlRepositorioOpiniones(bd), clasificador=clf,
                       reloj=reloj, limitador=limitador, exigir_sesion=True)
    actor = Actor("u-1", "aficionado")
    for i in range(10):
        uc.ejecutar(SolicitudOpinion("La salida al amanecer es pura magia", "ev-res-lemans", f"r{i}"), actor=actor)
    # Un limitador nuevo sobre la misma BD (= otro proceso o un reinicio) sigue contando
    limitador2 = LimitadorTasa(SqlRepositorioLimites(bd), reloj, por_usuario_5min=10, global_diario=1000)
    uc.limitador = limitador2
    with pytest.raises(err.LimiteExcedidoError):
        uc.ejecutar(SolicitudOpinion("La salida al amanecer es pura magia", "ev-res-lemans", "r10"), actor=actor)
    assert len(clf.llamadas) == 10


def test_limite_global_diario(entorno):
    bd, reloj, _ = entorno
    lim = LimitadorTasa(SqlRepositorioLimites(bd), reloj, por_usuario_5min=100, global_diario=3)
    for i in range(3):
        lim.verificar_y_registrar(f"u{i}")
    with pytest.raises(err.LimiteExcedidoError, match="diario"):
        lim.verificar_y_registrar("otro")
    with pytest.raises(err.LimiteExcedidoError):
        lim.verificar_global()


def test_hashes_de_ip_y_token():
    assert hash_ip("1.2.3.4", "sal") != "1.2.3.4" and len(hash_ip("1.2.3.4", "sal")) == 64
    assert hash_ip("1.2.3.4", "sal") != hash_ip("1.2.3.4", "otra")
    assert hash_ip(None, "sal") is None
    t = nuevo_token_api()
    assert t.startswith("pg_") and len(hash_token(t)) == 64
    assert ip_cliente("127.0.0.1", "9.9.9.9, 127.0.0.1", {"127.0.0.1"}) == "9.9.9.9"
    assert ip_cliente("5.5.5.5", "9.9.9.9", {"127.0.0.1"}) == "5.5.5.5"  # XFF falsificable: se ignora


def test_ip_cliente_con_rango_cidr_del_bridge_de_docker():
    assert ip_cliente("172.18.0.1", "203.0.113.7", {"172.16.0.0/12"}) == "203.0.113.7"
    assert ip_cliente("8.8.8.8", "203.0.113.7", {"172.16.0.0/12"}) == "8.8.8.8"
    assert ip_cliente("no-ip", "203.0.113.7", {"172.16.0.0/12"}) == "no-ip"
