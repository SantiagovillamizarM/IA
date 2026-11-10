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

from paddock.interfaz.componentes import barra_lateral, estilos  # noqa: E402

PAGINAS = Path(__file__).resolve().parent / "paginas"


def pagina(nombre: str, titulo: str, icono: str, **kw: object) -> st.Page:
    return st.Page(str(PAGINAS / f"{nombre}.py"), title=titulo, icon=icono, url_path=nombre, **kw)  # type: ignore[arg-type]


def paginas() -> list[st.Page]:
    return [
        pagina("inicio", "Inicio", "🏁", default=True),
        pagina("emitir", "Emitir opinión", "🗣️"),
        pagina("consultar", "Consultar opiniones", "🔎"),
    ]


def main() -> None:
    st.set_page_config(page_title="Paddock Global", page_icon="🏁", layout="wide")
    estilos.inyectar()
    nav = st.navigation(paginas())
    st.title("🏁 Paddock Global")
    st.caption("Análisis de sentimientos LangChain · opiniones del mundo de las carreras")
    barra_lateral.render()
    nav.run()


main()
