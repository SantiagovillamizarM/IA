"""Crea una cuenta de administrador. La contraseña se pide con ``getpass``: nunca por argumento ni en .env.

Uso: .venv\\Scripts\\python scripts\\crear_admin.py --email admin@midominio.com --nombre "Admin"
En Docker: docker compose exec app python scripts/crear_admin.py --email … --nombre …
"""

from __future__ import annotations

import argparse
import getpass
import sys

from paddock.config import Ajustes
from paddock.contenedor import crear_contenedor
from paddock.dominio.errores import ErrorPaddock


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--email", required=True)
    p.add_argument("--nombre", default="Administrador")
    a = p.parse_args()
    aj = Ajustes()
    if aj.STORAGE_BACKEND != "sql":
        print("Las cuentas requieren STORAGE_BACKEND=sql en .env.")
        return 2
    c = crear_contenedor(aj)
    contrasena = getpass.getpass("Contraseña (mínimo 12 caracteres): ")
    if contrasena != getpass.getpass("Repite la contraseña: "):
        print("Las contraseñas no coinciden.")
        return 1
    try:
        u = c.cuentas.registrar(a.email, a.nombre, contrasena, rol="admin", forzar=True)
    except ErrorPaddock as e:
        print(f"No se creó la cuenta: {e}")
        return 1
    print(f"Administrador creado: {u.email}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
