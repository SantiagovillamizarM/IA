"""Tarjetas y chips. Todo texto que viene del usuario o del modelo se escapa con ``html.escape``
(OWASP LLM05 / XSS): nunca se interpreta como HTML.
"""

from __future__ import annotations

import html
from typing import Any

import streamlit as st

from paddock.dominio.enums import EMOJI_SENTIMIENTO

ETIQUETA_ASPECTO = {
    "trazado": "Trazado", "organizacion": "Organización", "ambiente": "Ambiente", "estrategia": "Estrategia",
    "clima": "Clima", "reglamento": "Reglamento", "pilotos_equipos": "Pilotos y equipos",
    "vehiculos": "Vehículos", "transmision": "Transmisión", "seguridad": "Seguridad", "otro": "Otro",
}


def e(texto: Any) -> str:
    return html.escape(str(texto), quote=True)


def etiqueta_sentimiento(s: str | None) -> str:
    if not s:
        return "—"
    return f"{EMOJI_SENTIMIENTO.get(s, '')} {s.capitalize()}"


def texto_chip_evento(icono: str, nombre: str, edicion: int | None) -> str:
    return f"{icono} {nombre}" + (f" · {edicion}" if edicion else "")


def chip_evento(icono: str, nombre: str, edicion: int | None) -> None:
    st.markdown(f'<span class="pg-chip pg-chip-evento">{e(texto_chip_evento(icono, nombre, edicion))}</span>',
                unsafe_allow_html=True)


def chips_aspectos(aspectos: list[dict[str, str]] | None) -> str:
    if not aspectos:
        return ""
    partes = []
    for a in aspectos:
        s = a.get("sentimiento", "neutro")
        nombre = ETIQUETA_ASPECTO.get(a.get("aspecto", ""), a.get("aspecto", ""))
        partes.append(f'<span class="pg-chip pg-chip-{e(s)}">{EMOJI_SENTIMIENTO.get(s, "")} {e(nombre)}</span>')
    return "".join(partes)


def tarjeta_resultado(analisis: dict[str, Any], modelo: str, estado: str) -> None:
    """Tarjeta con cabecera del color del sentimiento (como una bandera de pista), razón y detalles de v2."""
    s = analisis.get("sentimiento")
    intensidad = analisis.get("intensidad")
    barra = ""
    if intensidad:
        n = int(intensidad)
        barra = f"<small>intensidad {'■' * n}{'□' * (5 - n)}</small>"
    partes = [
        f'<div class="pg-tarjeta pg-s-{e(s)}">',
        f'<div class="pg-tarjeta-cab"><span>{e(etiqueta_sentimiento(s))}</span>{barra}</div>',
        '<div class="pg-tarjeta-cuerpo">',
        f'<div class="pg-razon">{e(analisis.get("razon", ""))}</div>',
    ]
    chips = chips_aspectos(analisis.get("aspectos"))
    if chips:
        partes.append(f'<div style="margin-top:0.55rem">{chips}</div>')
    extra = []
    if analisis.get("ironia"):
        extra.append("🎭 Ironía detectada")
    if analisis.get("entidades"):
        extra.append("Menciona: " + ", ".join(analisis["entidades"]))
    if extra:
        partes.append(f'<div class="pg-pie">{e(" · ".join(extra))}</div>')
    partes.append(f'<div class="pg-pie">{e(estado)} · clasificado por {e(modelo)}</div></div></div>')
    st.markdown("".join(partes), unsafe_allow_html=True)


def aviso_cifras() -> None:
    st.caption("Las cifras reflejan solo las opiniones registradas en Paddock Global, no la opinión mundial. "
               "El catálogo es una selección didáctica, no un calendario oficial ni un ranking.")
