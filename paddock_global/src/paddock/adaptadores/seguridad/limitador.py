"""Limitador de tasa (OWASP LLM10: consumo sin límite).

- Por usuario: ``LIMITE_OPINIONES_5MIN`` llamadas al modelo cada 5 minutos.
- Global: ``LIMITE_LLM_DIARIO`` llamadas al modelo por día UTC (protege la cuota de Gemini).

Se comprueba **antes** de llamar al modelo: la llamada 11 se rechaza sin tocar el LLM.
"""

from __future__ import annotations

from datetime import timedelta

from paddock.dominio.errores import LimiteExcedidoError
from paddock.puertos.repositorios import RepositorioLimites
from paddock.puertos.servicios import Reloj, iso

CLAVE_GLOBAL = "llm:global"


class LimitadorTasa:
    def __init__(self, repo: RepositorioLimites, reloj: Reloj, *, por_usuario_5min: int, global_diario: int) -> None:
        self.repo = repo
        self.reloj = reloj
        self.por_usuario_5min = por_usuario_5min
        self.global_diario = global_diario

    def verificar_y_registrar(self, sujeto: str, *, ventana_min: int = 5, maximo: int | None = None,
                              prefijo: str = "op") -> None:
        """Lanza ``LimiteExcedidoError`` si se supera algún límite; si no, registra el uso."""
        ahora = self.reloj.ahora()
        clave = f"{prefijo}:{sujeto}"
        limite = maximo if maximo is not None else self.por_usuario_5min
        if self.repo.contar_desde(clave, iso(ahora - timedelta(minutes=ventana_min))) >= limite:
            raise LimiteExcedidoError(
                f"Has alcanzado el límite de {limite} envíos cada {ventana_min} minutos. Espera un poco."
            )
        inicio_dia = ahora.replace(hour=0, minute=0, second=0, microsecond=0)
        if self.repo.contar_desde(CLAVE_GLOBAL, iso(inicio_dia)) >= self.global_diario:
            raise LimiteExcedidoError("Se alcanzó el límite diario de análisis de la plataforma. Intenta mañana.")
        marca = iso(ahora)
        self.repo.registrar(clave, marca)
        self.repo.registrar(CLAVE_GLOBAL, marca)

    def verificar_global(self) -> None:
        """Solo el tope diario (lo usa el worker de lotes)."""
        ahora = self.reloj.ahora()
        inicio_dia = ahora.replace(hour=0, minute=0, second=0, microsecond=0)
        if self.repo.contar_desde(CLAVE_GLOBAL, iso(inicio_dia)) >= self.global_diario:
            raise LimiteExcedidoError("Se alcanzó el límite diario de análisis de la plataforma.")
        self.repo.registrar(CLAVE_GLOBAL, iso(ahora))

    def purgar(self) -> None:
        self.repo.purgar_antes(iso(self.reloj.ahora() - timedelta(days=2)))
