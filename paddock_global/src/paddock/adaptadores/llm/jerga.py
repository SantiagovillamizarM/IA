"""Vocabulario por disciplina para el bloque ``{jerga}`` del prompt.

El prompt recibe solo el de la disciplina de la carrera elegida, para no inflar el contexto.
"""

from __future__ import annotations

from collections.abc import Callable

SIN_JERGA = "(sin términos específicos para esta disciplina)"


def formatear_jerga(terminos: list[str]) -> str:
    return ", ".join(terminos) if terminos else SIN_JERGA


def crear_jerga_para(fuente: Callable[[], dict[str, list[str]]]) -> Callable[[str], str]:
    """Devuelve ``jerga_para(disciplina_id) -> str`` leyendo la jerga de ``fuente`` en cada llamada.

    Así la edición que haga el admin (v2) se aplica sin reiniciar.
    """

    def jerga_para(disciplina_id: str) -> str:
        return formatear_jerga(fuente().get(disciplina_id, []))

    return jerga_para
