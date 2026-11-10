"""Importa ``opiniones.json`` a la base de datos sin duplicar (por ``id``).

Uso: .venv\\Scripts\\python scripts\\migrar_json_a_bd.py [--json datos/opiniones.json]
Se puede ejecutar varias veces: la segunda vez todo sale como «omitidas».
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from paddock.adaptadores.persistencia.json_repo import RepositorioOpinionesJson
from paddock.adaptadores.persistencia.sql_repo import BaseDatos, SqlRepositorioOpiniones
from paddock.config import Ajustes
from paddock.dominio.entidades import FiltrosOpinion


def migrar(ruta_json: Path, url: str) -> tuple[int, int]:
    origen = RepositorioOpinionesJson(ruta_json).consultar(FiltrosOpinion(incluir_ocultas=True))
    destino = SqlRepositorioOpiniones(BaseDatos(url))
    importadas = omitidas = 0
    for op in sorted(origen, key=lambda o: o.fecha_utc):
        if destino.guardar(op):
            importadas += 1
        else:
            omitidas += 1
    return importadas, omitidas


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    aj = Ajustes()
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--json", type=Path, default=aj.ruta_opiniones)
    a = p.parse_args()
    importadas, omitidas = migrar(a.json, aj.url_bd)
    print(f"Importadas: {importadas} · omitidas (ya existían): {omitidas}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
