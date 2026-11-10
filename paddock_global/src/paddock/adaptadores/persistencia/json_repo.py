"""Persistencia del modo taller: ``catalogo.json``, ``jerga.json`` y ``opiniones.json``.

Supone **un único escritor local**. La escritura atómica (temporal + ``os.replace``) evita
archivos a medio escribir, pero no resuelve la concurrencia entre procesos: para varios
usuarios a la vez se usa el adaptador SQL (PostgreSQL).
"""

from __future__ import annotations

import contextlib
import json
import os
import tempfile
from dataclasses import replace
from pathlib import Path
from typing import Any

from paddock.dominio.entidades import Catalogo, Evento, FiltrosOpinion, Opinion, Revision
from paddock.dominio.enums import SENTIMIENTOS
from paddock.dominio.errores import (
    ArchivoOpinionesCorruptoError,
    CatalogoInvalidoError,
    ErrorEscrituraOpiniones,
)
from paddock.dominio.reglas import aplicar_filtros, catalogo_a_dict, coincide, validar_catalogo

CAMPOS_OBLIGATORIOS = (
    "id", "fecha_utc", "evento_id", "evento_nombre", "opinion_original",
    "sentimiento", "razon", "modelo", "version_prompt",
)


# ======================================================================= escritura atómica


def escribir_json_atomico(ruta: Path, datos: Any) -> None:
    """Escribe en un temporal del mismo directorio y lo reemplaza de forma atómica.

    Ante cualquier fallo borra el temporal, deja el original intacto y lanza
    ``ErrorEscrituraOpiniones`` con un mensaje comprensible.
    """
    ruta = Path(ruta)
    tmp_nombre: str | None = None
    try:
        ruta.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=ruta.parent, suffix=".tmp", delete=False
        ) as tmp:
            tmp_nombre = tmp.name
            json.dump(datos, tmp, ensure_ascii=False, indent=2)
            tmp.write("\n")
            tmp.flush()
            os.fsync(tmp.fileno())
        os.replace(tmp_nombre, ruta)
        tmp_nombre = None
    except PermissionError as e:
        raise ErrorEscrituraOpiniones(
            f"No hay permiso para escribir «{ruta.name}». Comprueba que no esté marcado como de solo "
            "lectura ni abierto en otro programa (en Windows: attrib -R)."
        ) from e
    except OSError as e:
        raise ErrorEscrituraOpiniones(f"No se pudo escribir «{ruta.name}»: {e.strerror or e}.") from e
    finally:
        if tmp_nombre is not None:
            with contextlib.suppress(OSError):
                os.unlink(tmp_nombre)


# ======================================================================= opiniones (funciones del taller)


def estructura_vacia() -> dict[str, Any]:
    return {"version": 1, "opiniones": []}


def _validar_estructura(datos: Any, nombre: str) -> None:
    if not isinstance(datos, dict) or not isinstance(datos.get("opiniones"), list):
        raise ArchivoOpinionesCorruptoError(
            f"«{nombre}» tiene un esquema inesperado: se esperaba un objeto con la lista «opiniones»."
        )
    version = datos.get("version")
    if not isinstance(version, int) or isinstance(version, bool):
        raise ArchivoOpinionesCorruptoError(f"«{nombre}» no tiene un campo «version» entero.")
    vistos: set[str] = set()
    for i, reg in enumerate(datos["opiniones"]):
        if not isinstance(reg, dict):
            raise ArchivoOpinionesCorruptoError(f"«{nombre}»: el registro {i} no es un objeto.")
        faltan = [c for c in CAMPOS_OBLIGATORIOS if not isinstance(reg.get(c), str)]
        if faltan:
            raise ArchivoOpinionesCorruptoError(
                f"«{nombre}»: al registro {i} le faltan campos obligatorios: {', '.join(faltan)}."
            )
        if reg["sentimiento"] not in SENTIMIENTOS:
            raise ArchivoOpinionesCorruptoError(f"«{nombre}»: el registro {i} tiene un sentimiento inválido.")
        if reg["id"] in vistos:
            raise ArchivoOpinionesCorruptoError(f"«{nombre}»: el id {reg['id']} está repetido.")
        vistos.add(reg["id"])


def cargar_opiniones(ruta: Path) -> dict[str, Any]:
    """Si no existe, devuelve la estructura vacía **sin escribir**. Si está dañado, lanza error sin tocarlo."""
    ruta = Path(ruta)
    if not ruta.exists():
        return estructura_vacia()
    try:
        texto = ruta.read_text(encoding="utf-8")
    except UnicodeDecodeError as e:
        raise ArchivoOpinionesCorruptoError(f"«{ruta.name}» no está codificado en UTF-8.") from e
    except PermissionError as e:
        raise ArchivoOpinionesCorruptoError(f"No hay permiso para leer «{ruta.name}».") from e
    try:
        datos = json.loads(texto)
    except json.JSONDecodeError as e:
        raise ArchivoOpinionesCorruptoError(
            f"«{ruta.name}» no es un JSON válido (línea {e.lineno}, columna {e.colno}). "
            "El archivo se conservó sin cambios: repáralo o restaura una copia."
        ) from e
    _validar_estructura(datos, ruta.name)
    return datos


def guardar_opinion(ruta: Path, registro: dict[str, Any]) -> bool:
    """Añade el registro sin perder los anteriores. Idempotente por ``id``.

    Devuelve ``True`` si lo añadió y ``False`` si ya existía. Si el archivo está dañado,
    propaga ``ArchivoOpinionesCorruptoError`` y no escribe nada.
    """
    datos = cargar_opiniones(ruta)
    if any(r.get("id") == registro["id"] for r in datos["opiniones"]):
        return False
    datos["opiniones"].append(registro)
    escribir_json_atomico(Path(ruta), datos)
    return True


def consultar_opiniones(
    registros: list[dict[str, Any]], evento_id: str | None = None, sentimiento: str | None = None
) -> list[dict[str, Any]]:
    """Versión del taller: filtra diccionarios por evento y sentimiento sin consultar al modelo."""
    return [
        r for r in registros
        if (evento_id is None or r.get("evento_id") == evento_id)
        and (sentimiento is None or r.get("sentimiento") == sentimiento)
    ]


# ======================================================================= adaptador del puerto


class RepositorioOpinionesJson:
    """Implementa ``RepositorioOpiniones`` sobre ``opiniones.json``."""

    def __init__(self, ruta: Path) -> None:
        self.ruta = Path(ruta)

    def _todas(self) -> list[Opinion]:
        return [Opinion.desde_dict(r) for r in cargar_opiniones(self.ruta)["opiniones"]]

    def guardar(self, opinion: Opinion) -> bool:
        return guardar_opinion(self.ruta, opinion.a_dict())

    def obtener(self, opinion_id: str) -> Opinion | None:
        return next((o for o in self._todas() if o.id == opinion_id), None)

    def consultar(self, filtros: FiltrosOpinion) -> list[Opinion]:
        return aplicar_filtros(self._todas(), filtros)

    def contar(self, filtros: FiltrosOpinion) -> int:
        return sum(1 for o in self._todas() if coincide(o, filtros))

    def _modificar(self, opinion_id: str, **cambios: Any) -> None:
        datos = cargar_opiniones(self.ruta)
        for i, reg in enumerate(datos["opiniones"]):
            if reg["id"] == opinion_id:
                datos["opiniones"][i] = replace(Opinion.desde_dict(reg), **cambios).a_dict()
                escribir_json_atomico(self.ruta, datos)
                return
        raise KeyError(opinion_id)

    def guardar_revision(self, opinion_id: str, revision: Revision) -> None:
        # En JSON solo se conserva la última revisión; el historial completo vive en SQL.
        self._modificar(opinion_id, revision=revision)

    def historial_revisiones(self, opinion_id: str) -> list[Revision]:
        op = self.obtener(opinion_id)
        return [op.revision] if op and op.revision else []

    def cambiar_visibilidad(self, opinion_id: str, visible: bool) -> None:
        self._modificar(opinion_id, visible=visible)

    def anonimizar_usuario(self, usuario_id: str) -> int:
        datos = cargar_opiniones(self.ruta)
        n = 0
        for reg in datos["opiniones"]:
            if reg.get("usuario_id") == usuario_id:
                reg["usuario_id"] = None
                n += 1
        if n:
            escribir_json_atomico(self.ruta, datos)
        return n


# ======================================================================= catálogo y jerga


def cargar_catalogo(ruta: Path) -> Catalogo:
    """Lee y valida ``catalogo.json``: versión, listas no vacías, ids únicos y referencias válidas."""
    ruta = Path(ruta)
    try:
        datos = json.loads(ruta.read_text(encoding="utf-8"))
    except FileNotFoundError as e:
        raise CatalogoInvalidoError(f"No se encontró el catálogo «{ruta.name}».") from e
    except json.JSONDecodeError as e:
        raise CatalogoInvalidoError(f"«{ruta.name}» no es un JSON válido (línea {e.lineno}).") from e
    return validar_catalogo(datos)


def cargar_jerga(ruta: Path) -> dict[str, list[str]]:
    ruta = Path(ruta)
    if not ruta.exists():
        return {}
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    jerga = datos.get("jerga", {}) if isinstance(datos, dict) else {}
    return {k: [str(t) for t in v] for k, v in jerga.items() if isinstance(v, list)}


class RepositorioCatalogoJson:
    """Catálogo leído de ``catalogo.json``. Se recarga si cambia la fecha de modificación."""

    def __init__(self, ruta_catalogo: Path, ruta_jerga: Path) -> None:
        self.ruta = Path(ruta_catalogo)
        self.ruta_jerga = Path(ruta_jerga)
        self._cache: tuple[float, Catalogo] | None = None

    def obtener(self) -> Catalogo:
        mtime = self.ruta.stat().st_mtime if self.ruta.exists() else -1.0
        if self._cache is None or self._cache[0] != mtime:
            self._cache = (mtime, cargar_catalogo(self.ruta))
        return self._cache[1]

    def guardar_evento(self, evento: Evento) -> None:
        catalogo = self.obtener()
        eventos = [e for e in catalogo.eventos if e.id != evento.id]
        existente = next((i for i, e in enumerate(catalogo.eventos) if e.id == evento.id), None)
        if existente is None:
            eventos.append(evento)
        else:
            eventos.insert(existente, evento)
        nuevo = replace(catalogo, eventos=tuple(eventos))
        datos = catalogo_a_dict(nuevo)
        validar_catalogo(datos)
        escribir_json_atomico(self.ruta, datos)
        self._cache = None

    def obtener_jerga(self) -> dict[str, list[str]]:
        return cargar_jerga(self.ruta_jerga)

    def guardar_jerga(self, disciplina_id: str, terminos: list[str]) -> None:
        jerga = self.obtener_jerga()
        jerga[disciplina_id] = [t.strip() for t in terminos if t.strip()]
        escribir_json_atomico(self.ruta_jerga, {"version": 1, "jerga": jerga})
