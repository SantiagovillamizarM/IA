"""Genera registros ficticios pasando por el clasificador REAL (Ollama).

Uso:
    python sembrar_datos.py               # añade sin borrar
    python sembrar_datos.py --reiniciar   # copia de seguridad + archivo vacío
"""

from __future__ import annotations

import argparse
import shutil
import sys
from datetime import datetime

import almacenamiento as alm
from analisis import VERSION_PROMPT, ErrorClasificacion, analizar_opinion, verificar_ollama
from config import EVIDENCIAS_DIR, RUTA_CARRERAS, RUTA_OPINIONES, SENTIMIENTOS, cargar_config

# (carrera_id, opinión ficticia, sentimiento esperado)
OPINIONES = [
    ("c001", "Ver amanecer en la Sarthe con los coches todavía a fondo me puso la piel de gallina", "positivo"),
    ("c001", "La entrada era carísima y desde la tribuna casi no se veía la pista", "negativo"),
    ("c001", "Este año la largada fue a las cuatro de la tarde, hora local", "neutro"),
    ("c001", "La pelea por la victoria fue apasionante, pero los cortes de la transmisión fueron constantes", "mixto"),
    ("c002", "Los aficionados acampando en el bosque crean un ambiente único en el mundo", "positivo"),
    ("c002", "La organización fue un desastre: horas de bandera roja sin información para el público", "negativo"),
    ("c002", "La vuelta combina el trazado de Gran Premio con el Nordschleife", "neutro"),
    ("c002", "El Nordschleife es una maravilla, aunque la niebla dejó la carrera detenida casi toda la noche", "mixto"),
    ("c003", "Los peraltes de noche con los prototipos a toda velocidad son un espectáculo increíble", "positivo"),
    ("c003", "Me aburrí muchísimo, fue una procesión con demasiadas neutralizaciones", "negativo"),
    ("c003", "La carrera se disputa a finales de enero y abre la temporada", "neutro"),
    ("c003", "Me encantó la variedad de categorías, pero el tráfico en pista causó accidentes absurdos", "mixto"),
    ("c004", "Ver a los GT3 subir Eau Rouge bajo la lluvia es lo más emocionante que he visto", "positivo"),
    ("c004", "El BoP arruinó la competencia, ganó el que mejor negoció con los comisarios", "negativo"),
    ("c004", "La carrera reúne a más de cincuenta coches de la categoría GT3", "neutro"),
    ("c004", "El circuito es precioso, lástima que los atascos para salir del parking duraron horas", "mixto"),
    # Ampliación multilingüe
    ("c001", "The atmosphere at Le Mans during the night is something every fan should experience", "positivo"),
    ("c003", "La course était interminable, trop de drapeaux jaunes et aucun suspense", "negativo"),
    ("c002", "Das Rennen führt über die Nordschleife und die Grand-Prix-Strecke", "neutro"),
    ("c004", "A subida da Eau Rouge é sensacional, mas a chuva atrapalhou demais a corrida", "mixto"),
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reiniciar", action="store_true", help="Respalda y vacía opiniones.json")
    args = parser.parse_args()

    cfg = cargar_config()
    ok, msg = verificar_ollama(cfg)
    if not ok:
        print(f"[ERROR] {msg}")
        return 1

    if args.reiniciar and RUTA_OPINIONES.exists():
        respaldo = RUTA_OPINIONES.with_name(f"opiniones.backup-{datetime.now():%Y%m%d-%H%M%S}.json")
        shutil.copy2(RUTA_OPINIONES, respaldo)
        alm._escribir_atomico(RUTA_OPINIONES, {"version": 1, "opiniones": []})
        print(f"Copia de seguridad: {respaldo.name}")

    carreras = {c["id"]: c for c in alm.cargar_carreras(RUTA_CARRERAS)}
    filas = []
    for cid, texto, esperado in OPINIONES:
        carrera = carreras[cid]
        try:
            a = analizar_opinion(carrera, texto, cfg=cfg)
        except ErrorClasificacion as e:
            filas.append((carrera["nombre"], texto, esperado, f"ERROR: {e}", "", False))
            print(f"[ERROR] {texto[:50]}… → {e}")
            continue
        obtenido = a.sentimiento if a.es_pertinente else "no pertinente"
        if a.es_pertinente:
            reg = alm.crear_registro(carrera, texto, a, cfg.nombre_modelo, VERSION_PROMPT)
            alm.guardar_opinion(RUTA_OPINIONES, reg)
        coincide = obtenido == esperado
        filas.append((carrera["nombre"], texto, esperado, obtenido, a.razon, coincide))
        print(f"{'OK ' if coincide else 'DIF'} | {carrera['nombre']:<24} | esperado={esperado:<8} obtenido={obtenido}")

    registros = alm.cargar_opiniones(RUTA_OPINIONES)["opiniones"]
    conteo = alm.contar_por_sentimiento(registros)
    n_carreras = len({r["carrera_id"] for r in registros})
    print(f"\nTotal en archivo: {len(registros)} · carreras: {n_carreras} · por sentimiento: {conteo}")
    cumple = len(registros) >= 12 and n_carreras >= 4 and all(v > 0 for v in conteo.values())
    print("Mínimo del taller (≥12 registros, ≥4 carreras, 4 categorías):", "CUMPLE" if cumple else "NO CUMPLE")

    EVIDENCIAS_DIR.mkdir(exist_ok=True)
    with open(EVIDENCIAS_DIR / "siembra_resultados.md", "w", encoding="utf-8") as f:
        f.write(f"# Siembra de datos ficticios\n\nModelo: `{cfg.nombre_modelo}` · prompt v{VERSION_PROMPT} · "
                f"{datetime.now():%Y-%m-%d %H:%M}\n\n")
        f.write("| Carrera | Opinión | Esperado | Obtenido | Razón del modelo | ¿Coincide? |\n|---|---|---|---|---|---|\n")
        for c, t, e, o, r, ok_ in filas:
            f.write(f"| {c} | {t} | {e} | {o} | {r.replace('|', '/')} | {'✅' if ok_ else '❌'} |\n")
        aciertos = sum(1 for *_x, ok_ in filas if ok_)
        f.write(f"\n**Aciertos:** {aciertos}/{len(filas)}. Los registros se guardaron con la clasificación "
                f"del modelo, sin corregirla a mano.\n\n**Archivo final:** {len(registros)} registros, "
                f"{n_carreras} carreras, conteo {conteo}.\n")
    return 0 if cumple else 2


if __name__ == "__main__":
    sys.exit(main())
