"""Enumeraciones del dominio. Heredan de ``str`` para serializarse sin conversión."""

from __future__ import annotations

from enum import StrEnum


class Sentimiento(StrEnum):
    POSITIVO = "positivo"
    NEGATIVO = "negativo"
    NEUTRO = "neutro"
    MIXTO = "mixto"


SENTIMIENTOS: tuple[str, ...] = tuple(s.value for s in Sentimiento)

# Emoji y color fijos por sentimiento en toda la app (el emoji evita depender solo del color).
EMOJI_SENTIMIENTO: dict[str, str] = {"positivo": "😀", "negativo": "😞", "neutro": "😐", "mixto": "🤔"}
COLOR_SENTIMIENTO: dict[str, str] = {
    "positivo": "#2e9e5b",
    "negativo": "#d6342c",
    "neutro": "#8a8f98",
    "mixto": "#e0a526",
}


class Aspecto(StrEnum):
    TRAZADO = "trazado"
    ORGANIZACION = "organizacion"
    AMBIENTE = "ambiente"
    ESTRATEGIA = "estrategia"
    CLIMA = "clima"
    REGLAMENTO = "reglamento"
    PILOTOS_EQUIPOS = "pilotos_equipos"
    VEHICULOS = "vehiculos"
    TRANSMISION = "transmision"
    SEGURIDAD = "seguridad"
    OTRO = "otro"


ASPECTOS: tuple[str, ...] = tuple(a.value for a in Aspecto)


class Rol(StrEnum):
    AFICIONADO = "aficionado"
    MODERADOR = "moderador"
    ADMIN = "admin"


class Origen(StrEnum):
    CHAT = "chat"
    LOTE = "lote"
    SEMILLA = "semilla"
    API = "api"


class EstadoTrabajo(StrEnum):
    PENDIENTE = "pendiente"
    PROCESANDO = "procesando"
    TERMINADO = "terminado"
    FALLIDO = "fallido"


class MotivoDenuncia(StrEnum):
    SPAM = "spam"
    OFENSIVA = "ofensiva"
    MAL_CLASIFICADA = "mal_clasificada"
