"""Experimento: ¿cuánto cambia la etiqueta al subir la temperatura?

Clasifica varias veces la MISMA opinión con distintas temperaturas y mide la
estabilidad: % de repeticiones que coinciden con la etiqueta más frecuente.
No guarda nada en opiniones.json.

Uso:
    python experimento_temperatura.py                          # modelo de .env
    python experimento_temperatura.py gemini:gemini-3.5-flash
"""

from __future__ import annotations

import sys
from collections import Counter
from datetime import datetime

from analisis import ErrorClasificacion, analizar_opinion, crear_cadena, verificar_modelo
from config import EVIDENCIAS_DIR, cargar_config, config_con_modelo

TEMPERATURAS = (0.0, 0.5, 1.0)
REPETICIONES = 4
OPINIONES = [  # casos ambiguos: es donde la temperatura más se nota
    ({"id": "c002", "nombre": "24 Horas de Nürburgring"},
     "El Nordschleife es una maravilla, aunque la niebla dejó la carrera detenida casi toda la noche"),
    ({"id": "c001", "nombre": "24 Horas de Le Mans"},
     "Los aficionados acampando en el bosque crean un ambiente único en el mundo"),
]


def main() -> int:
    base = cargar_config()
    if len(sys.argv) > 1:
        base = config_con_modelo(base, sys.argv[1])
    ok, msg = verificar_modelo(base)
    if not ok:
        print(f"[ERROR] {msg}")
        return 1

    filas = []
    for t in TEMPERATURAS:
        cfg = config_con_modelo(base, base.clave, temperatura=t)
        cadena = crear_cadena(cfg)
        for carrera, texto in OPINIONES:
            etiquetas = []
            for _ in range(REPETICIONES):
                try:
                    a = analizar_opinion(carrera, texto, cfg=cfg, cadena=cadena)
                    etiquetas.append(a.sentimiento if a.es_pertinente else "no pertinente")
                except ErrorClasificacion as e:
                    etiquetas.append("ERROR")
                    print("  error:", e)
            conteo = Counter(etiquetas)
            estabilidad = round(100 * conteo.most_common(1)[0][1] / len(etiquetas))
            filas.append((t, texto, dict(conteo), estabilidad))
            print(f"T={t:.1f} | estabilidad {estabilidad:3d}% | {dict(conteo)} | {texto[:50]}")

    EVIDENCIAS_DIR.mkdir(exist_ok=True)
    nombre = base.OLLAMA_MODEL.replace(":", "_")
    with open(EVIDENCIAS_DIR / f"experimento_temperatura_{nombre}.md", "w", encoding="utf-8") as f:
        f.write(f"# Experimento de temperatura · `{base.nombre_modelo}`\n\n"
                f"{datetime.now():%Y-%m-%d %H:%M} · {REPETICIONES} repeticiones por opinión y temperatura. "
                "Estabilidad = % de repeticiones iguales a la etiqueta más frecuente.\n\n"
                "| Temperatura | Opinión | Etiquetas obtenidas | Estabilidad |\n|---|---|---|---|\n")
        for t, texto, conteo, est in filas:
            etiquetas = ", ".join(f"{k} ×{v}" for k, v in conteo.items())
            f.write(f"| {t:.1f} | {texto} | {etiquetas} | {est}% |\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
