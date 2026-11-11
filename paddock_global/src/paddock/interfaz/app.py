"""Punto de entrada Streamlit: ``streamlit run src/paddock/interfaz/app.py``.

Navegación multipágina con ``st.navigation`` (el ``chat_input`` queda bien anclado, sin ``st.tabs``).
Cada página es un archivo de ``paginas/`` que se ejecuta como script.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Permite arrancar sin instalar el paquete (pip install -e . también funciona).
_SRC = Path(__file__).resolve().parents[2]
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

import streamlit as st  # noqa: E402

from paddock.dominio.enums import Rol  # noqa: E402
from paddock.interfaz.componentes import barra_lateral, estilos, marca, recursos, sesion  # noqa: E402

PAGINAS = Path(__file__).resolve().parent / "paginas"


def pagina(nombre: str, titulo: str, icono: str, **kw: object) -> st.Page:
    return st.Page(str(PAGINAS / f"{nombre}.py"), title=titulo, icon=icono, url_path=nombre, **kw)  # type: ignore[arg-type]


def paginas() -> dict[str, list[st.Page]]:
    """Las páginas visibles dependen del modo y del rol; además, cada caso de uso comprueba el permiso."""
    c = recursos.contenedor()
    actor = sesion.actor_actual()
    rol = actor.rol if actor else None
    nav: dict[str, list[st.Page]] = {
        "Opinar": [pagina("inicio", "Inicio", "🏁", default=True), pagina("emitir", "Emitir opinión", "🗣️")],
        "Explorar": [pagina("consultar", "Consultar opiniones", "🔎"), pagina("dashboard", "Dashboard", "📊"),
                     pagina("comparar", "Comparar", "⚖️"), pagina("mapa", "Mapa", "🗺️"),
                     pagina("informes", "Informes", "📄")],
    }
    if c.modo_sql:
        nav["Explorar"].insert(3, pagina("resumen", "¿Qué opina la comunidad?", "📝"))
    cuenta = [pagina("cuenta", "Mi cuenta", "👤")] if c.modo_sql else []
    nav["Cuenta"] = [*cuenta, pagina("privacidad", "Privacidad", "🔒")]
    gestion: list[st.Page] = []
    if c.modo_sql and rol in (Rol.MODERADOR.value, Rol.ADMIN.value):
        gestion += [pagina("moderacion", "Moderación", "🛡️"), pagina("lotes", "Lotes", "📥")]
    if c.modo_sql and rol == Rol.ADMIN.value:
        gestion += [pagina("calidad", "Calidad", "🎯"), pagina("admin", "Administración", "⚙️")]
    if gestion:
        nav["Gestión"] = gestion
    return nav


def main() -> None:
    st.set_page_config(page_title="Paddock Global", page_icon="🏁", layout="wide")
    estilos.inyectar()
    marca.logotipo()
    nav = st.navigation(paginas(), expanded=True)  # sin «N more»: Gestión siempre visible
    listo, _ = recursos.estado_proveedor()
    marca.cabecera(modelo_listo=listo, compacta=nav.title != "Inicio")
    barra_lateral.render()
    nav.run()


main()
