"""Carga ``datos/catalogo.json`` y ``datos/jerga.json`` en la base de datos (idempotente).

Inserta solo lo que falta: no deshace los cambios que el admin haya hecho desde la UI.
Uso: .venv\\Scripts\\python scripts\\sembrar_catalogo.py   (requiere STORAGE_BACKEND=sql y migraciones aplicadas)
"""

from __future__ import annotations

import sys

from paddock.adaptadores.persistencia.json_repo import cargar_catalogo, cargar_jerga
from paddock.adaptadores.persistencia.sql_repo import BaseDatos, SqlRepositorioCatalogo
from paddock.config import Ajustes


def sembrar(url: str, aj: Ajustes) -> dict[str, int]:
    repo = SqlRepositorioCatalogo(BaseDatos(url))
    return repo.sembrar(cargar_catalogo(aj.ruta_catalogo), cargar_jerga(aj.ruta_jerga))


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    aj = Ajustes()
    n = sembrar(aj.url_bd, aj)
    print(f"Catálogo sembrado (solo lo que faltaba): {n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
