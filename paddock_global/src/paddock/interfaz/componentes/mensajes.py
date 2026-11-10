"""Un mensaje distinto por tipo de error. Nunca muestra trazas ni claves."""

from __future__ import annotations

from typing import Literal

import streamlit as st

from paddock.dominio import errores as err

Nivel = Literal["warning", "error"]


def describir_error(e: Exception, proveedor: str, modelo: str) -> tuple[Nivel, str]:
    """Devuelve (nivel, mensaje con la solución) para cada tipo de error."""
    if isinstance(e, err.EntradaInvalidaError | err.EventoNoEncontradoError):
        return "warning", f"✋ {e}"
    if isinstance(e, err.LimiteExcedidoError):
        return "warning", f"⏳ {e}"
    if isinstance(e, err.SesionRequeridaError | err.SesionExpiradaError):
        return "warning", f"🔐 {e}"
    if isinstance(e, err.ProveedorNoDisponibleError):
        if proveedor == "ollama":
            return "error", "🔌 Ollama no responde. Abre la app Ollama o ejecuta `ollama serve` y vuelve a enviar."
        return "error", "🔌 Gemini no responde, intenta más tarde."
    if isinstance(e, err.ModeloNoEncontradoError):
        if proveedor == "ollama":
            return "error", f"📦 El modelo no está descargado. Ejecuta `ollama pull {modelo}`."
        return "error", "📦 El modelo de Gemini no existe: revisa `GEMINI_MODEL` en el archivo .env."
    if isinstance(e, err.CredencialInvalidaError):
        return "error", "🔑 La clave del proveedor no es válida. Revisa `GOOGLE_API_KEY` en el archivo .env."
    if isinstance(e, err.CuotaExcedidaError):
        return "error", "🚦 Se superó la cuota del proveedor (429). Espera un minuto e intenta de nuevo."
    if isinstance(e, err.ContenidoBloqueadoError):
        return "error", "🛑 Los filtros de seguridad del proveedor bloquearon la respuesta."
    if isinstance(e, err.RespuestaInvalidaError):
        return "error", ("🧩 El modelo devolvió una respuesta inválida o incoherente (se reintentó una vez). "
                         "Intenta reformular la opinión.")
    if isinstance(e, err.ArchivoOpinionesCorruptoError):
        return "error", f"🗂️ {e}"
    if isinstance(e, err.ErrorEscrituraOpiniones):
        return "error", f"💾 {e}"
    if isinstance(e, err.ErrorPaddock):
        return "error", f"⚠️ {e}"
    return "error", "⚠️ Ocurrió un error inesperado."


def mostrar(nivel: Nivel, mensaje: str) -> None:
    (st.warning if nivel == "warning" else st.error)(mensaje)


def mostrar_error(e: Exception, proveedor: str, modelo: str) -> tuple[Nivel, str]:
    nivel, mensaje = describir_error(e, proveedor, modelo)
    mostrar(nivel, mensaje)
    return nivel, mensaje
