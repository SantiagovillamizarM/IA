"""Prueba rápida: 5 opiniones con cada proveedor disponible (Ollama y, si hay clave, Gemini).

Uso: .venv\\Scripts\\python scripts\\probar_proveedores.py [--proveedor ollama|gemini] [--version-prompt 1.0|2.0]
"""

from __future__ import annotations

import argparse
import sys
import time

from paddock.adaptadores.llm.cadena import crear_clasificador, verificar_proveedor
from paddock.adaptadores.llm.jerga import crear_jerga_para
from paddock.adaptadores.persistencia.json_repo import cargar_catalogo, cargar_jerga
from paddock.config import Ajustes
from paddock.dominio.errores import ErrorClasificacion

CASOS = [
    ("ev-f1-japon", "Las eses de Suzuka son una delicia para ver en cámara lenta"),
    ("ev-wrc-safari", "El polvo no dejaba ver nada y la transmisión fue un caos"),
    ("ev-res-sebring", "La pista de Sebring tiene baches porque usa pistas de un antiguo aeródromo"),
    ("ev-nascar-daytona-500", "Final de infarto, aunque el Big One dejó fuera a medio pelotón"),
    ("ev-motogp-paises-bajos", "Mañana me toca lavar el carro"),
]


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    p = argparse.ArgumentParser()
    p.add_argument("--proveedor", choices=["ollama", "gemini"], action="append")
    p.add_argument("--version-prompt", default=None)
    a = p.parse_args()
    base = Ajustes()
    catalogo = cargar_catalogo(base.ruta_catalogo)
    jerga_para = crear_jerga_para(lambda: cargar_jerga(base.ruta_jerga))
    for prov in a.proveedor or ["ollama", "gemini"]:
        aj = base.model_copy(update={"LLM_PROVIDER": prov})
        ok, msg = verificar_proveedor(aj)
        print(f"\n=== {prov}: {'🟢' if ok else '🔴'} {msg}")
        if not ok:
            continue
        clf = crear_clasificador(aj, jerga_para, version_prompt=a.version_prompt)
        for evento_id, texto in CASOS:
            ev = catalogo.evento(evento_id)
            assert ev is not None
            disc = catalogo.disciplina_de_evento(ev)
            t0 = time.perf_counter()
            try:
                r = clf.clasificar(texto=texto, carrera=ev.nombre, disciplina=disc.nombre,
                                   disciplina_id=disc.id, edicion=None)
                an = r.analisis
                etiqueta = an.sentimiento if an.es_pertinente else "no pertinente"
                print(f"[{time.perf_counter()-t0:5.1f}s] {ev.nombre}: «{texto}» → {etiqueta} | {an.razon}")
                extra = an.model_dump(exclude={"es_pertinente", "sentimiento", "razon"})
                if extra:
                    print(f"         {extra}")
            except ErrorClasificacion as e:
                print(f"[{time.perf_counter()-t0:5.1f}s] ERROR {type(e).__name__}: {e}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
