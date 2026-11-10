"""Añade ``allowedHosts`` y ``corsAllowedOrigins`` a ``.streamlit/config.toml`` a partir de ``DOMINIO``.

Lo ejecuta ``despliegue/entrypoint.sh`` al arrancar el contenedor. Idempotente.
"""

from __future__ import annotations

import os
import re
import sys
import tomllib
from pathlib import Path

_DOMINIO = re.compile(r"^[a-z0-9.-]+$")


def configurar(ruta: Path, dominio: str) -> bool:
    if not _DOMINIO.match(dominio):
        raise ValueError(f"DOMINIO no válido: {dominio!r}")
    texto = ruta.read_text(encoding="utf-8")
    if "allowedHosts" in tomllib.loads(texto).get("server", {}):
        return False
    extra = (f'allowedHosts = ["{dominio}", "localhost", "127.0.0.1"]\n'
             f'corsAllowedOrigins = ["https://{dominio}"]\n')
    nuevo = texto.replace("[server]\n", "[server]\n" + extra, 1)
    tomllib.loads(nuevo)  # valida antes de escribir
    ruta.write_text(nuevo, encoding="utf-8")
    return True


def main() -> int:
    dominio = os.environ.get("DOMINIO", "").strip().lower()
    if not dominio:
        return 0
    cambiado = configurar(Path(".streamlit/config.toml"), dominio)
    print(f"Streamlit restringido a {dominio}" if cambiado else "Streamlit ya estaba configurado.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
