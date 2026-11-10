"""Worker de lotes: consume la cola ``trabajos_lote`` (contenedor aparte en producción).

Uso: python -m paddock.worker.procesador_lotes [--una-vez]
"""

from __future__ import annotations

import argparse
import logging
import signal
import sys
import time

from paddock.config import Ajustes
from paddock.contenedor import Contenedor, crear_contenedor

log = logging.getLogger("paddock.worker")
_parar = False


def _senal(*_args: object) -> None:
    global _parar
    _parar = True
    log.info("Señal recibida: el worker se detendrá al terminar la fila actual.")


def ciclo(c: Contenedor) -> bool:
    """Procesa un trabajo pendiente. Devuelve ``True`` si había alguno."""
    trabajo = c.repo_trabajos.siguiente_pendiente()
    if trabajo is None:
        return False
    log.info("Procesando lote %s (%d filas)", trabajo.id, trabajo.total)
    resultado = c.procesador_lotes.procesar(trabajo)
    if resultado.estado == "pendiente":  # tope diario: esperar antes de reintentar
        log.warning("Lote %s en pausa por el límite diario.", trabajo.id)
        time.sleep(max(c.ajustes.WORKER_INTERVALO_S, 60))
    return True


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--una-vez", action="store_true", help="Procesa lo pendiente y termina")
    a = p.parse_args(argv)
    aj = Ajustes()
    if aj.STORAGE_BACKEND != "sql":
        log.error("El worker requiere STORAGE_BACKEND=sql.")
        return 2
    c = crear_contenedor(aj)
    c.emitir_opinion.exigir_sesion = True  # cada fila se emite en nombre del dueño del lote
    signal.signal(signal.SIGTERM, _senal)
    signal.signal(signal.SIGINT, _senal)
    log.info("Worker de lotes iniciado (modelo %s).", aj.modelo_activo)
    while not _parar:
        try:
            hubo = ciclo(c)
        except Exception:  # noqa: BLE001 - el worker no debe morir por un error inesperado
            log.exception("Error inesperado en el worker; se reintenta en el siguiente ciclo.")
            hubo = False
        if a.una_vez and not hubo:
            break
        if not hubo:
            time.sleep(aj.WORKER_INTERVALO_S)
    return 0


if __name__ == "__main__":
    sys.exit(main())
