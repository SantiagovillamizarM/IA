"""Lectura del catálogo, persistencia de opiniones en JSON y consultas.

Supone un único escritor local. La escritura atómica (archivo temporal +
os.replace) evita archivos incompletos, pero NO resuelve escrituras concurrentes.
"""

from __future__ import annotations

import json
import os
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config import SENTIMIENTOS

CAMPOS_CARRERA = ("id", "nombre", "pais", "circuito")
CAMPOS_REGISTRO = (
    "id", "fecha_utc", "carrera_id", "carrera_nombre", "opinion_original",
    "sentimiento", "razon", "modelo", "version_prompt",
)


class CatalogoInvalidoError(Exception):
    """El catálogo de carreras no existe o no cumple el esquema."""


class ArchivoOpinionesCorruptoError(Exception):
    """opiniones.json existe pero no es JSON válido o su esquema es inesperado."""


class ErrorEscrituraOpiniones(Exception):
    """No fue posible escribir opiniones.json."""


class RegistroNoEncontradoError(Exception):
    """No existe un registro con ese id."""


# ---------------------------------------------------------------- catálogo

def cargar_carreras(ruta: Path) -> list[dict]:
    """Lee y valida el catálogo de carreras; no admite identificadores repetidos."""
    try:
        with open(ruta, encoding="utf-8") as f:
            datos = json.load(f)
    except FileNotFoundError as e:
        raise CatalogoInvalidoError(f"No existe el catálogo: {ruta}") from e
    except json.JSONDecodeError as e:
        raise CatalogoInvalidoError(f"El catálogo no es JSON válido: {e}") from e

    if not isinstance(datos, dict) or datos.get("version") != 1:
        raise CatalogoInvalidoError("El catálogo debe ser un objeto con version 1.")
    carreras = datos.get("carreras")
    if not isinstance(carreras, list) or not carreras:
        raise CatalogoInvalidoError("El catálogo debe contener una lista 'carreras' no vacía.")

    vistos: set[str] = set()
    for i, c in enumerate(carreras):
        if not isinstance(c, dict):
            raise CatalogoInvalidoError(f"La carrera en la posición {i} no es un objeto.")
        for campo in CAMPOS_CARRERA:
            valor = c.get(campo)
            if not isinstance(valor, str) or not valor.strip():
                raise CatalogoInvalidoError(
                    f"La carrera en la posición {i} no tiene un '{campo}' válido."
                )
        if c["id"] in vistos:
            raise CatalogoInvalidoError(f"Identificador repetido en el catálogo: {c['id']}")
        vistos.add(c["id"])
    return carreras


# --------------------------------------------------------------- opiniones

def _estructura_vacia() -> dict:
    return {"version": 1, "opiniones": []}


def cargar_opiniones(ruta: Path) -> dict:
    """Lee el diccionario persistente. Si el archivo está dañado, lanza un error y NO lo toca."""
    if not Path(ruta).exists():
        return _estructura_vacia()
    try:
        with open(ruta, encoding="utf-8") as f:
            datos = json.load(f)
    except json.JSONDecodeError as e:
        raise ArchivoOpinionesCorruptoError(
            f"{Path(ruta).name} no contiene JSON válido (línea {e.lineno}). "
            "El archivo se conservó sin cambios."
        ) from e
    except UnicodeDecodeError as e:
        raise ArchivoOpinionesCorruptoError(
            f"{Path(ruta).name} no está en UTF-8. El archivo se conservó sin cambios."
        ) from e

    if not isinstance(datos, dict) or datos.get("version") != 1:
        raise ArchivoOpinionesCorruptoError("Esquema inesperado: se esperaba un objeto con version 1.")
    opiniones = datos.get("opiniones")
    if not isinstance(opiniones, list):
        raise ArchivoOpinionesCorruptoError("Esquema inesperado: 'opiniones' debe ser una lista.")
    for i, r in enumerate(opiniones):
        if not isinstance(r, dict) or any(campo not in r for campo in CAMPOS_REGISTRO):
            raise ArchivoOpinionesCorruptoError(
                f"Esquema inesperado: el registro {i} no tiene todos los campos obligatorios."
            )
    return datos


def crear_registro(
    carrera: dict,
    texto: str,
    analisis: Any,
    modelo: str,
    version_prompt: str = "1.0",
    registro_id: str | None = None,
) -> dict:
    """Construye el registro. El programa aporta id, fecha y metadatos; el modelo, solo el análisis.

    Campos de ampliación (opcionales en registros antiguos): idioma, aspectos y
    alerta_revision. La corrección manual se añade después con corregir_opinion.
    """
    if not getattr(analisis, "es_pertinente", False) or analisis.sentimiento is None:
        raise ValueError("Solo se registran opiniones pertinentes con sentimiento.")
    aspectos = [
        a.model_dump() if hasattr(a, "model_dump") else dict(a)
        for a in (getattr(analisis, "aspectos", None) or [])
    ]
    alerta = None
    if hasattr(analisis, "model_dump"):
        from analisis import alerta_revision
        alerta = alerta_revision(analisis)
    return {
        "id": registro_id or str(uuid.uuid4()),
        "fecha_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "carrera_id": carrera["id"],
        "carrera_nombre": carrera["nombre"],
        "opinion_original": texto.strip(),
        "sentimiento": analisis.sentimiento,
        "razon": analisis.razon,
        "modelo": modelo,
        "version_prompt": version_prompt,
        "idioma": getattr(analisis, "idioma", None),
        "aspectos": aspectos,
        "alerta_revision": alerta,
    }


def _escribir_atomico(ruta: Path, datos: dict) -> None:
    """Escribe en un temporal del mismo directorio y lo reemplaza al final."""
    ruta = Path(ruta)
    tmp_nombre: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=ruta.parent, suffix=".tmp", delete=False
        ) as f:
            tmp_nombre = f.name
            json.dump(datos, f, ensure_ascii=False, indent=2)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_nombre, ruta)
        tmp_nombre = None
    except PermissionError as e:
        raise ErrorEscrituraOpiniones(
            f"Sin permiso para escribir {ruta.name} (¿solo lectura o abierto en otro programa?)."
        ) from e
    except OSError as e:
        raise ErrorEscrituraOpiniones(f"No se pudo escribir {ruta.name}: {e}") from e
    finally:
        if tmp_nombre and os.path.exists(tmp_nombre):
            try:
                os.remove(tmp_nombre)
            except OSError:
                pass


def guardar_opinion(ruta: Path, registro: dict) -> bool:
    """Añade el registro sin perder los anteriores. Devuelve False si ese id ya existía."""
    datos = cargar_opiniones(ruta)  # si está dañado, propaga el error y no escribe
    if any(r["id"] == registro["id"] for r in datos["opiniones"]):
        return False
    datos["opiniones"].append(registro)
    _escribir_atomico(ruta, datos)
    return True


def corregir_opinion(ruta: Path, registro_id: str, nuevo: str, nota: str = "") -> dict:
    """Ampliación: corrección manual. Conserva la etiqueta del modelo en 'sentimiento'.

    Si el nuevo valor coincide con el del modelo, se elimina la corrección.
    """
    if nuevo not in SENTIMIENTOS:
        raise ValueError(f"Sentimiento no válido: {nuevo}")
    datos = cargar_opiniones(ruta)
    for r in datos["opiniones"]:
        if r["id"] == registro_id:
            if nuevo == r["sentimiento"]:
                for campo in ("sentimiento_corregido", "nota_correccion", "fecha_correccion_utc"):
                    r.pop(campo, None)
            else:
                r["sentimiento_corregido"] = nuevo
                r["nota_correccion"] = nota.strip()[:300]
                r["fecha_correccion_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
            _escribir_atomico(ruta, datos)
            return r
    raise RegistroNoEncontradoError(f"No existe el registro {registro_id}.")


# ---------------------------------------------------------------- consultas

def sentimiento_final(r: dict) -> str:
    """Etiqueta vigente: la corrección manual si existe; si no, la del modelo."""
    return r.get("sentimiento_corregido") or r["sentimiento"]


def consultar_opiniones(
    registros: list[dict],
    carrera_id: str | None = None,
    sentimiento: str | None = None,
    idioma: str | None = None,
    solo_alertas: bool = False,
) -> list[dict]:
    """Filtra en memoria (None = todos) y ordena por fecha descendente. No usa el modelo."""
    resultado = [
        r for r in registros
        if (carrera_id is None or r["carrera_id"] == carrera_id)
        and (sentimiento is None or sentimiento_final(r) == sentimiento)
        and (idioma is None or r.get("idioma") == idioma)
        and (not solo_alertas or (r.get("alerta_revision") and not r.get("sentimiento_corregido")))
    ]
    return sorted(resultado, key=lambda r: r["fecha_utc"], reverse=True)


def contar_por_sentimiento(registros: list[dict]) -> dict[str, int]:
    """Cuenta por categoría vigente, incluyendo las que tienen cero registros."""
    conteo = {s: 0 for s in SENTIMIENTOS}
    for r in registros:
        if sentimiento_final(r) in conteo:
            conteo[sentimiento_final(r)] += 1
    return conteo
