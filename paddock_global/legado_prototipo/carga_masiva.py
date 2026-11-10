"""Ampliación: carga masiva de opiniones desde un CSV.

Formato: columnas `carrera` (id como c001 o nombre exacto) y `opinion`.
Separador coma o punto y coma (Excel en español usa «;»). UTF-8 o Latin-1.

Idempotencia: el id de cada registro se deriva del contenido del archivo y del
número de fila (uuid5). Subir dos veces el mismo archivo no duplica registros.
"""

from __future__ import annotations

import csv
import hashlib
import io
import uuid
from dataclasses import dataclass, field
from typing import Callable

import almacenamiento as alm
from analisis import (
    VERSION_PROMPT,
    EntradaInvalidaError,
    ErrorClasificacion,
    ServicioNoDisponibleError,
    analizar_opinion,
    validar_texto,
)
from config import RUTA_OPINIONES, ConfigOllama

MAX_FILAS = 100
_NAMESPACE = uuid.UUID("6f1c2a7e-3d4b-4c5a-9e8f-0a1b2c3d4e5f")


class CSVInvalidoError(Exception):
    """El archivo no tiene el formato esperado."""


@dataclass
class FilaCSV:
    numero: int            # número de fila en el archivo (1 = primera fila de datos)
    carrera: dict | None
    texto: str
    registro_id: str
    error: str | None = None


@dataclass
class ResultadoFila:
    numero: int
    carrera: str
    opinion: str
    estado: str            # guardada | ya_existia | no_pertinente | invalida | error
    sentimiento: str | None = None
    razon: str = ""
    extra: dict = field(default_factory=dict)


def _decodificar(contenido: bytes) -> str:
    for codificacion in ("utf-8-sig", "latin-1"):
        try:
            return contenido.decode(codificacion)
        except UnicodeDecodeError:
            continue
    raise CSVInvalidoError("No se pudo leer el archivo como texto.")


def leer_csv(contenido: bytes, carreras: list[dict]) -> list[FilaCSV]:
    """Valida el CSV y devuelve las filas (con error por fila si corresponde). No llama al modelo."""
    texto = _decodificar(contenido)
    if not texto.strip():
        raise CSVInvalidoError("El archivo está vacío.")
    try:
        dialecto = csv.Sniffer().sniff(texto[:2048], delimiters=",;")
    except csv.Error:
        dialecto = csv.excel
    lector = csv.DictReader(io.StringIO(texto), dialect=dialecto)
    columnas = {(c or "").strip().lower(): c for c in (lector.fieldnames or [])}
    if "carrera" not in columnas or "opinion" not in columnas:
        raise CSVInvalidoError(
            "El CSV debe tener las columnas «carrera» y «opinion». "
            f"Columnas encontradas: {list(columnas) or 'ninguna'}."
        )

    por_id = {c["id"].lower(): c for c in carreras}
    por_nombre = {c["nombre"].lower(): c for c in carreras}
    huella = hashlib.sha256(contenido).hexdigest()

    filas: list[FilaCSV] = []
    for i, fila in enumerate(lector, start=1):
        if i > MAX_FILAS:
            raise CSVInvalidoError(f"Máximo {MAX_FILAS} opiniones por archivo.")
        clave = (fila.get(columnas["carrera"]) or "").strip().lower()
        carrera = por_id.get(clave) or por_nombre.get(clave)
        texto_op = fila.get(columnas["opinion"]) or ""
        error = None
        if carrera is None:
            error = f"Carrera desconocida: «{clave or '(vacía)'}»."
        else:
            try:
                texto_op = validar_texto(texto_op)
            except EntradaInvalidaError as e:
                error = str(e)
        filas.append(FilaCSV(
            numero=i, carrera=carrera, texto=texto_op.strip(),
            registro_id=str(uuid.uuid5(_NAMESPACE, f"{huella}:{i}")), error=error,
        ))
    if not filas:
        raise CSVInvalidoError("El CSV no tiene filas de datos.")
    return filas


def procesar_filas(
    filas: list[FilaCSV],
    cfg: ConfigOllama,
    cadena=None,
    progreso: Callable[[int, int, FilaCSV], None] | None = None,
    ruta=RUTA_OPINIONES,
) -> list[ResultadoFila]:
    """Clasifica y guarda fila por fila. Si el proveedor deja de responder, se detiene (lo ya guardado queda)."""
    existentes = {r["id"] for r in alm.cargar_opiniones(ruta)["opiniones"]}
    resultados: list[ResultadoFila] = []
    for k, f in enumerate(filas, start=1):
        if progreso:
            progreso(k, len(filas), f)
        nombre = f.carrera["nombre"] if f.carrera else "?"
        if f.error:
            resultados.append(ResultadoFila(f.numero, nombre, f.texto, "invalida", razon=f.error))
            continue
        if f.registro_id in existentes:
            resultados.append(ResultadoFila(f.numero, nombre, f.texto, "ya_existia",
                                            razon="Esta fila ya se había cargado antes."))
            continue
        try:
            a = analizar_opinion(f.carrera, f.texto, cfg=cfg, cadena=cadena)
        except ServicioNoDisponibleError as e:  # Ollama caído, sin internet o cuota de Gemini
            resultados.append(ResultadoFila(f.numero, nombre, f.texto, "error", razon=str(e)))
            break
        except ErrorClasificacion as e:
            resultados.append(ResultadoFila(f.numero, nombre, f.texto, "error", razon=str(e)))
            continue
        if not a.es_pertinente:
            resultados.append(ResultadoFila(f.numero, nombre, f.texto, "no_pertinente", razon=a.razon))
            continue
        reg = alm.crear_registro(f.carrera, f.texto, a, cfg.nombre_modelo, VERSION_PROMPT,
                                 registro_id=f.registro_id, temperatura=cfg.OLLAMA_TEMPERATURE)
        alm.guardar_opinion(ruta, reg)
        existentes.add(f.registro_id)
        resultados.append(ResultadoFila(f.numero, nombre, f.texto, "guardada", a.sentimiento, a.razon,
                                        {"idioma": a.idioma}))
    return resultados
