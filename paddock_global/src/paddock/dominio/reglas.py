"""Reglas puras del dominio: validación, coherencia, filtros y recuentos.

Ninguna función de este módulo hace E/S ni llama al modelo.
"""

from __future__ import annotations

import logging
import re
import unicodedata
from collections import Counter
from collections.abc import Iterable, Sequence
from datetime import datetime
from typing import Any

from paddock.dominio.analisis import AnalisisDetallado, AnalisisOpinion
from paddock.dominio.entidades import (
    Campeonato,
    Catalogo,
    Disciplina,
    Evento,
    FiltrosOpinion,
    Opinion,
)
from paddock.dominio.enums import ASPECTOS, SENTIMIENTOS
from paddock.dominio.errores import (
    AnalisisIncoherenteError,
    CatalogoInvalidoError,
    EntradaInvalidaError,
)

log = logging.getLogger(__name__)

LONGITUD_MIN = 5
LONGITUD_MAX = 1000
ANIO_MIN = 1900

# ======================================================================= texto


def validar_texto(texto: str | None) -> str:
    """Quita espacios exteriores y exige entre 5 y 1000 caracteres, sin caracteres de control.

    Se permiten saltos de línea (\\n, \\r) y tabuladores. Devuelve el texto limpio.
    """
    limpio = (texto or "").strip()
    if not limpio:
        raise EntradaInvalidaError("La opinión está vacía.")
    if len(limpio) < LONGITUD_MIN:
        raise EntradaInvalidaError(f"La opinión debe tener al menos {LONGITUD_MIN} caracteres.")
    if len(limpio) > LONGITUD_MAX:
        raise EntradaInvalidaError(
            f"La opinión supera el máximo de {LONGITUD_MAX} caracteres (tiene {len(limpio)})."
        )
    for c in limpio:
        if c in "\n\r\t":
            continue
        if unicodedata.category(c) in ("Cc", "Cf") and c not in "‍":
            raise EntradaInvalidaError("La opinión contiene caracteres de control no permitidos.")
    return limpio


def validar_edicion(anio: int | None, anio_actual: int) -> int | None:
    """La edición es opcional; si se indica, debe estar entre 1900 y el año actual."""
    if anio is None:
        return None
    if isinstance(anio, bool) or not isinstance(anio, int):
        raise EntradaInvalidaError("El año de la edición debe ser un número entero.")
    if not ANIO_MIN <= anio <= anio_actual:
        raise EntradaInvalidaError(f"El año de la edición debe estar entre {ANIO_MIN} y {anio_actual}.")
    return anio


# ======================================================================= análisis


def validar_coherencia(analisis: AnalisisOpinion) -> None:
    """Comprueba la relación entre pertinencia, sentimiento y campos detallados.

    El esquema Pydantic no puede expresar estas reglas por sí solo.
    """
    if analisis.es_pertinente and analisis.sentimiento is None:
        raise AnalisisIncoherenteError("El modelo marcó la opinión como pertinente pero sin sentimiento.")
    if not analisis.es_pertinente and analisis.sentimiento is not None:
        raise AnalisisIncoherenteError("El modelo marcó la opinión como no pertinente pero con sentimiento.")
    if isinstance(analisis, AnalisisDetallado):
        if not analisis.es_pertinente and (analisis.aspectos or analisis.intensidad is not None):
            raise AnalisisIncoherenteError("Una opinión no pertinente no puede tener aspectos ni intensidad.")
        if analisis.sentimiento == "mixto" and analisis.aspectos:
            polaridades = {a.sentimiento for a in analisis.aspectos}
            if not {"positivo", "negativo"} <= polaridades:
                raise AnalisisIncoherenteError(
                    "Una opinión mixta con aspectos debe tener al menos uno positivo y uno negativo."
                )


def filtrar_entidades(entidades: Iterable[str], texto: str) -> tuple[list[str], list[str]]:
    """Conserva solo las entidades que aparecen literalmente en el texto (sin distinguir mayúsculas).

    Devuelve ``(conservadas, descartadas)``. Descartar no es un error.
    """
    base = texto.casefold()
    conservadas: list[str] = []
    descartadas: list[str] = []
    vistas: set[str] = set()
    for ent in entidades:
        limpia = ent.strip()
        if not limpia or limpia.casefold() in vistas:
            continue
        if limpia.casefold() in base:
            conservadas.append(limpia)
            vistas.add(limpia.casefold())
        else:
            descartadas.append(limpia)
    if descartadas:
        log.info("Entidades no literales descartadas: %d", len(descartadas))
    return conservadas, descartadas


def crear_registro(
    *,
    registro_id: str,
    fecha_utc: str,
    evento: Evento,
    disciplina: Disciplina,
    texto: str,
    analisis: AnalisisOpinion,
    modelo: str,
    version_prompt: str,
    edicion_anio: int | None,
    usuario_id: str | None,
    origen: str,
) -> Opinion:
    """Arma el registro. El programa aporta id, fecha, evento y metadatos; el modelo solo el análisis."""
    if not analisis.es_pertinente or analisis.sentimiento is None:
        raise AnalisisIncoherenteError("No se crea un registro para un texto no pertinente.")
    aspectos: list[dict[str, str]] | None = None
    ironia: bool | None = None
    intensidad: int | None = None
    entidades: list[str] | None = None
    if isinstance(analisis, AnalisisDetallado):
        aspectos = [a.model_dump() for a in analisis.aspectos]
        ironia, intensidad = analisis.ironia, analisis.intensidad
        entidades, _ = filtrar_entidades(analisis.entidades, texto)
    return Opinion(
        id=registro_id,
        fecha_utc=fecha_utc,
        evento_id=evento.id,
        evento_nombre=evento.nombre,
        disciplina_id=disciplina.id,
        edicion_anio=edicion_anio,
        usuario_id=usuario_id,
        opinion_original=texto.strip(),
        sentimiento=analisis.sentimiento,
        razon=analisis.razon,
        aspectos=aspectos,
        ironia=ironia,
        intensidad=intensidad,
        entidades=entidades,
        modelo=modelo,
        version_prompt=version_prompt,
        origen=origen,
    )


# ======================================================================= catálogo


def _texto_obligatorio(obj: dict[str, Any], campo: str, contexto: str) -> str:
    valor = obj.get(campo)
    if not isinstance(valor, str) or not valor.strip():
        raise CatalogoInvalidoError(f"{contexto}: el campo «{campo}» debe ser un texto no vacío.")
    return valor


def _ids_unicos(items: Sequence[dict[str, Any]], nombre: str) -> None:
    repetidos = [i for i, n in Counter(x.get("id") for x in items).items() if n > 1]
    if repetidos:
        raise CatalogoInvalidoError(f"Hay ids repetidos en «{nombre}»: {', '.join(map(str, repetidos))}.")


def validar_catalogo(datos: Any) -> Catalogo:
    """Valida el diccionario del catálogo (§3.3) y devuelve la entidad ``Catalogo``."""
    if not isinstance(datos, dict):
        raise CatalogoInvalidoError("El catálogo debe ser un objeto JSON.")
    version = datos.get("version")
    if not isinstance(version, int) or isinstance(version, bool):
        raise CatalogoInvalidoError("El catálogo debe tener un campo «version» entero.")
    listas: dict[str, list[dict[str, Any]]] = {}
    for nombre in ("disciplinas", "campeonatos", "eventos"):
        lista = datos.get(nombre)
        if not isinstance(lista, list) or not lista:
            raise CatalogoInvalidoError(f"«{nombre}» debe ser una lista no vacía.")
        if not all(isinstance(x, dict) for x in lista):
            raise CatalogoInvalidoError(f"Cada elemento de «{nombre}» debe ser un objeto.")
        _ids_unicos(lista, nombre)
        listas[nombre] = lista

    disciplinas = tuple(
        Disciplina(
            id=_texto_obligatorio(d, "id", "Disciplina"),
            nombre=_texto_obligatorio(d, "nombre", f"Disciplina {d.get('id')}"),
            icono=_texto_obligatorio(d, "icono", f"Disciplina {d.get('id')}"),
        )
        for d in listas["disciplinas"]
    )
    ids_disc = {d.id for d in disciplinas}
    campeonatos: list[Campeonato] = []
    for c in listas["campeonatos"]:
        ctx = f"Campeonato {c.get('id')}"
        camp = Campeonato(
            id=_texto_obligatorio(c, "id", "Campeonato"),
            disciplina_id=_texto_obligatorio(c, "disciplina_id", ctx),
            nombre=_texto_obligatorio(c, "nombre", ctx),
        )
        if camp.disciplina_id not in ids_disc:
            raise CatalogoInvalidoError(f"{ctx}: la disciplina «{camp.disciplina_id}» no existe.")
        campeonatos.append(camp)
    ids_camp = {c.id for c in campeonatos}
    eventos: list[Evento] = []
    for e in listas["eventos"]:
        ctx = f"Evento {e.get('id')}"
        lat, lon = e.get("lat"), e.get("lon")
        for nombre_coord, valor in (("lat", lat), ("lon", lon)):
            if valor is not None and (isinstance(valor, bool) or not isinstance(valor, int | float)):
                raise CatalogoInvalidoError(f"{ctx}: «{nombre_coord}» debe ser numérico.")
        ev = Evento(
            id=_texto_obligatorio(e, "id", "Evento"),
            campeonato_id=_texto_obligatorio(e, "campeonato_id", ctx),
            nombre=_texto_obligatorio(e, "nombre", ctx),
            pais=_texto_obligatorio(e, "pais", ctx),
            sede=_texto_obligatorio(e, "sede", ctx),
            lat=float(lat) if lat is not None else None,
            lon=float(lon) if lon is not None else None,
            historico=bool(e.get("historico", False)),
            activo=bool(e.get("activo", True)),
        )
        if ev.campeonato_id not in ids_camp:
            raise CatalogoInvalidoError(f"{ctx}: el campeonato «{ev.campeonato_id}» no existe.")
        eventos.append(ev)
    return Catalogo(
        version=version, disciplinas=disciplinas, campeonatos=tuple(campeonatos), eventos=tuple(eventos)
    )


def catalogo_a_dict(catalogo: Catalogo) -> dict[str, Any]:
    return {
        "version": catalogo.version,
        "disciplinas": [d.__dict__ for d in catalogo.disciplinas],
        "campeonatos": [c.__dict__ for c in catalogo.campeonatos],
        "eventos": [e.__dict__ for e in catalogo.eventos],
    }


# ======================================================================= consultas


def _normalizar(texto: str) -> str:
    sin_tildes = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in sin_tildes if not unicodedata.combining(c)).casefold()


def coincide(op: Opinion, f: FiltrosOpinion) -> bool:
    """¿El registro cumple los filtros? (sin paginación)."""
    if not f.incluir_ocultas and not op.visible:
        return False
    if f.disciplina_id and op.disciplina_id != f.disciplina_id:
        return False
    if f.evento_id and op.evento_id != f.evento_id:
        return False
    if f.evento_ids is not None and op.evento_id not in f.evento_ids:
        return False
    if f.edicion_anio is not None and op.edicion_anio != f.edicion_anio:
        return False
    if f.sentimiento:
        etiqueta = op.sentimiento_efectivo if f.usar_revision else op.sentimiento
        if etiqueta != f.sentimiento:
            return False
    if f.aspecto and not any(a.get("aspecto") == f.aspecto for a in (op.aspectos or [])):
        return False
    if f.usuario_id and op.usuario_id != f.usuario_id:
        return False
    if f.desde_utc and op.fecha_utc < f.desde_utc:
        return False
    if f.hasta_utc and op.fecha_utc >= f.hasta_utc:
        return False
    if f.texto and _normalizar(f.texto.strip()) not in _normalizar(op.opinion_original):
        return False
    return not (f.solo_revisadas and op.revision is None)


def aplicar_filtros(registros: Iterable[Opinion], f: FiltrosOpinion) -> list[Opinion]:
    """Filtra, ordena por fecha descendente y pagina."""
    filtrados = sorted((op for op in registros if coincide(op, f)), key=lambda o: o.fecha_utc, reverse=True)
    inicio = max(f.desplazamiento, 0)
    fin = inicio + f.limite if f.limite is not None else None
    return filtrados[inicio:fin]


def contar_por_sentimiento(registros: Iterable[Opinion], usar_revision: bool = False) -> dict[str, int]:
    """Devuelve siempre las 4 categorías, incluidas las que valen 0."""
    conteo = dict.fromkeys(SENTIMIENTOS, 0)
    for op in registros:
        etiqueta = op.sentimiento_efectivo if usar_revision else op.sentimiento
        if etiqueta in conteo:
            conteo[etiqueta] += 1
    return conteo


def indice_percepcion(conteo: dict[str, int]) -> float | None:
    """(positivas − negativas) / total. ``None`` si no hay opiniones."""
    total = sum(conteo.values())
    if total == 0:
        return None
    return (conteo.get("positivo", 0) - conteo.get("negativo", 0)) / total


def matriz_aspectos(registros: Iterable[Opinion]) -> dict[str, dict[str, int]]:
    """Conteo aspecto × polaridad a partir de los aspectos valorados."""
    m = {a: {"positivo": 0, "negativo": 0, "neutro": 0} for a in ASPECTOS}
    for op in registros:
        for a in op.aspectos or []:
            if a.get("aspecto") in m and a.get("sentimiento") in m[a["aspecto"]]:
                m[a["aspecto"]][a["sentimiento"]] += 1
    return m


def contar_entidades(registros: Iterable[Opinion], top: int = 10) -> list[tuple[str, int]]:
    c: Counter[str] = Counter()
    for op in registros:
        for e in op.entidades or []:
            c[e.strip()] += 1
    return c.most_common(top)


# ======================================================================= seguridad

_PATRONES_INYECCION = [
    r"ignora\w*\s+(las|tus|todas|el)?\s*(reglas|instrucciones|anteriores)",
    r"ignore\s+(all|the|previous|your)?\s*(rules|instructions)",
    r"system\s*prompt",
    r"prompt\s+del\s+sistema",
    r"revela\w*\s+(tu|el)\s+prompt",
    r"</?\s*opinion\s*>",
    r"\bsistema\s*:",
    r"\bsystem\s*:",
    r"responde\s+(solo\s+)?[\"«]?aprobado",
    r"cambia\w*\s+(de|el)\s+formato",
    r"clasifica\w*\s+todo\s+como",
]
_REGEX_INYECCION = re.compile("|".join(_PATRONES_INYECCION), re.IGNORECASE)


def detectar_inyeccion(texto: str) -> bool:
    """Heurística SOLO para registrar en auditoría (LLM01). Nunca se usa para bloquear."""
    return bool(_REGEX_INYECCION.search(texto))


_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def normalizar_email(email: str) -> str:
    limpio = (email or "").strip().lower()
    if not _EMAIL.match(limpio) or len(limpio) > 254:
        raise EntradaInvalidaError("El correo no tiene un formato válido.")
    return limpio


def validar_contrasena(contrasena: str, comunes: set[str], email: str | None = None) -> None:
    """Mínimo 12 caracteres; rechaza contraseñas comunes y las que contienen el correo."""
    if len(contrasena) < 12:
        raise EntradaInvalidaError("La contraseña debe tener al menos 12 caracteres.")
    if len(contrasena) > 128:
        raise EntradaInvalidaError("La contraseña no puede superar 128 caracteres.")
    if contrasena.lower() in comunes:
        raise EntradaInvalidaError("Esa contraseña es demasiado común. Elige otra.")
    if email and email.split("@")[0].lower() in contrasena.lower() and len(email.split("@")[0]) >= 4:
        raise EntradaInvalidaError("La contraseña no debe contener tu correo.")


def sesion_expirada(ultima_actividad: datetime, ahora: datetime, minutos: int) -> bool:
    return (ahora - ultima_actividad).total_seconds() > minutos * 60
