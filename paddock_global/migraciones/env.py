"""Entorno de Alembic: la URL sale de ``Ajustes`` (``DATABASE_URL``), nunca de alembic.ini."""

from __future__ import annotations

import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from paddock.adaptadores.persistencia.sql_modelos import Base  # noqa: E402
from paddock.config import Ajustes  # noqa: E402

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Permite sobrescribir la URL desde código (tests) con config.attributes["url"].
url = config.attributes.get("url") or Ajustes().url_bd
config.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True,
                      dialect_opts={"paramstyle": "named"}, render_as_batch=url.startswith("sqlite"))
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    conectable = config.attributes.get("connection")
    if conectable is not None:
        context.configure(connection=conectable, target_metadata=target_metadata,
                          render_as_batch=url.startswith("sqlite"))
        with context.begin_transaction():
            context.run_migrations()
        return
    motor = engine_from_config(config.get_section(config.config_ini_section, {}), prefix="sqlalchemy.",
                               poolclass=pool.NullPool)
    with motor.connect() as conexion:
        context.configure(connection=conexion, target_metadata=target_metadata,
                          render_as_batch=url.startswith("sqlite"))
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
