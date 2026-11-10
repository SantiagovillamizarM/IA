"""Siembra opiniones ficticias pasando por el **clasificador real** (``EmitirOpinion``, origen «semilla»).

Imprime «esperado vs. obtenido». Si el modelo discrepa, el registro NO se edita: se anota en la
evidencia. Comprueba ≥12 registros, ≥4 eventos y las 4 categorías; si falta alguna, prueba opiniones
de reserva de esa categoría y documenta los intentos.

Uso:
    .venv\\Scripts\\python scripts\\sembrar_datos.py --proveedor ollama
    .venv\\Scripts\\python scripts\\sembrar_datos.py --proveedor gemini --pausa 13 --reiniciar
"""

from __future__ import annotations

import argparse
import shutil
import sys
import time
from collections import Counter
from datetime import datetime
from uuid import uuid4

from paddock.aplicacion.emitir_opinion import SolicitudOpinion
from paddock.config import EVIDENCIAS, Ajustes
from paddock.contenedor import crear_contenedor
from paddock.dominio import errores as err
from paddock.dominio.entidades import FiltrosOpinion

# (evento_id, esperado, texto). Escritas para la siembra; no coinciden con el prompt ni con la aceptación.
OPINIONES: list[tuple[str, str, str]] = [
    # 24 Horas de Le Mans
    ("ev-res-lemans", "positivo", "El ambiente del camping y los fuegos artificiales del sábado me encantaron"),
    ("ev-res-lemans", "negativo", "Las colas para salir del aparcamiento duraron tres horas, una organización pésima"),
    ("ev-res-lemans", "neutro", "Vi la carrera completa desde la curva de Arnage con dos amigos"),
    ("ev-res-lemans", "mixto", "La pelea por la victoria fue apasionante, aunque las entradas estaban carísimas"),
    # Gran Premio de Mónaco
    ("ev-f1-monaco", "positivo", "Ver los coches rozar los muros en la Piscina es un espectáculo único"),
    ("ev-f1-monaco", "negativo", "Una carrera soporífera, nadie pudo adelantar en toda la tarde"),
    ("ev-f1-monaco", "neutro", "El circuito pasa por el túnel y luego baja hacia la chicane del puerto"),
    ("ev-f1-monaco", "mixto", "El escenario del puerto es una joya, lástima que todo se decidiera con la estrategia en boxes"),
    # Rally de Finlandia
    ("ev-wrc-finlandia", "positivo", "Los bosques y los saltos hacen de este rally el más espectacular del calendario"),
    ("ev-wrc-finlandia", "negativo", "Pasé horas en el barro esperando y cancelaron la especial sin avisar, qué desastre"),
    ("ev-wrc-finlandia", "neutro", "Los tramos son de tierra rápida y atraviesan zonas de lagos"),
    ("ev-wrc-finlandia", "mixto", "Los saltos fueron brutales, pero la señal de la transmisión se perdía cada dos minutos"),
    # Daytona 500
    ("ev-nascar-daytona-500", "positivo", "El final con tres coches lado a lado en el banking me dejó sin aliento"),
    ("ev-nascar-daytona-500", "negativo", "Demasiadas cautions, la carrera se hizo eterna y aburrida"),
    ("ev-nascar-daytona-500", "neutro", "La carrera se divide en stages y al final puede haber un green-white-checkered"),
    ("ev-nascar-daytona-500", "mixto", "La emoción del rebufo es increíble, aunque el Big One acabó con medio pelotón"),
    # Rally Dakar
    ("ev-dakar", "positivo", "Las imágenes de las dunas al amanecer son lo más bonito que he visto en un rally"),
    ("ev-dakar", "negativo", "La navegación fue un caos y la organización nunca explicó las penalizaciones"),
    ("ev-dakar", "neutro", "Cada etapa termina en un bivac donde los equipos reparan los vehículos"),
    ("ev-dakar", "mixto", "Los paisajes son impresionantes, pero los resúmenes de televisión duraban apenas cinco minutos"),
    # Gran Premio de Italia (MotoGP)
    ("ev-motogp-italia", "positivo", "Mugello lleno de banderas amarillas y la afición cantando es algo que todo motero debe vivir"),
    ("ev-motogp-italia", "negativo", "Una caída en la primera curva arruinó la carrera y el resto no tuvo ninguna emoción"),
    ("ev-motogp-italia", "neutro", "La recta principal es larga y termina en una frenada fuerte antes de la primera curva"),
    ("ev-motogp-italia", "mixto", "El adelantamiento de la última vuelta fue de película, pero la long lap penalty fue injusta"),
]

# Reserva por si falta alguna categoría tras la siembra principal.
RESERVA: dict[str, list[tuple[str, str]]] = {
    "positivo": [("ev-f1-japon", "Las eses de Suzuka son una maravilla para ver desde la tribuna")],
    "negativo": [("ev-f1-las-vegas", "Precios absurdos y una pista sin alma, no vuelvo")],
    "neutro": [("ev-res-spa", "La carrera empieza el sábado por la tarde y se corre con coches GT3"),
               ("ev-indy-500", "Son doscientas vueltas a un óvalo de dos millas y media")],
    "mixto": [("ev-f1-italia", "El público de Monza es único, pero la salida de los aficionados fue un caos"),
              ("ev-res-bathurst", "La bajada de la montaña es impresionante, aunque hubo demasiados coches de seguridad")],
}


def clasificar(c, evento_id: str, texto: str, pausa_429: float):
    for intento in range(4):
        try:
            return c.emitir_opinion.ejecutar(
                SolicitudOpinion(texto=texto, evento_id=evento_id, registro_id=str(uuid4()), origen="semilla"),
                aplicar_limite=False,
            )
        except err.CuotaExcedidaError:
            if intento == 3:
                raise
            print(f"   429: espero {pausa_429:.0f} s…")
            time.sleep(pausa_429)
    raise RuntimeError("inalcanzable")


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--proveedor", choices=["ollama", "gemini"], default=None)
    p.add_argument("--version-prompt", choices=["1.0", "2.0"], default=None)
    p.add_argument("--pausa", type=float, default=None, help="Segundos entre llamadas (Gemini gratis: 13)")
    p.add_argument("--reiniciar", action="store_true", help="Copia de seguridad y vacía opiniones.json")
    p.add_argument("--modelo", default=None, help="Sustituye GEMINI_MODEL u OLLAMA_MODEL en esta ejecución")
    p.add_argument("--categoria", choices=["positivo", "negativo", "neutro", "mixto"], default=None,
                   help="Siembra solo las opiniones (y reservas) de esa categoría esperada")
    a = p.parse_args()

    base = Ajustes()
    cambios: dict[str, object] = {}
    if a.proveedor:
        cambios["LLM_PROVIDER"] = a.proveedor
    if a.version_prompt:
        cambios["VERSION_PROMPT"] = a.version_prompt
    if a.modelo:
        prov = a.proveedor or base.LLM_PROVIDER
        cambios["GEMINI_MODEL" if prov == "gemini" else "OLLAMA_MODEL"] = a.modelo
    aj = base.model_copy(update=cambios)
    pausa = a.pausa if a.pausa is not None else (13.0 if aj.LLM_PROVIDER == "gemini" else aj.SEMILLA_PAUSA_S)
    c = crear_contenedor(aj)
    # La siembra es un proceso de operador (sin usuario): en modo SQL no se exige sesión aquí.
    c.emitir_opinion.exigir_sesion = False

    if a.reiniciar:
        if aj.STORAGE_BACKEND != "json":
            print("--reiniciar solo aplica al modo JSON. Para SQL usa scripts/respaldo_bd.sh.")
            return 2
        ruta = aj.ruta_opiniones
        if ruta.exists():
            copia = ruta.with_name(f"opiniones.backup-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json")
            shutil.copy2(ruta, copia)
            print(f"Copia de seguridad: {copia.name}")
        from paddock.adaptadores.persistencia.json_repo import escribir_json_atomico, estructura_vacia

        escribir_json_atomico(ruta, estructura_vacia())

    ok, msg = c.verificar_proveedor()
    print(f"{'🟢' if ok else '🔴'} {msg}")
    if not ok:
        return 1

    filas = []

    def procesar(evento_id: str, esperado: str, texto: str, fase: str) -> str | None:
        t0 = time.perf_counter()
        try:
            r = clasificar(c, evento_id, texto, 30)
            obtenido = r.analisis.sentimiento if r.analisis.es_pertinente else "no pertinente"
            estado = "guardada" if r.estado == "guardada" else r.estado.replace("_", " ")
            razon = r.analisis.razon
        except err.ErrorPaddock as e:
            obtenido, estado, razon = f"error ({type(e).__name__})", "no guardada", str(e)
        dt = time.perf_counter() - t0
        marca = "✅" if obtenido == esperado else "❌"
        ev = c.repo_catalogo.obtener().evento(evento_id)
        filas.append((fase, ev.nombre, texto, esperado, obtenido, marca, estado, razon, dt))
        print(f"{marca} [{dt:5.1f}s] {ev.nombre[:28]:28} esperado={esperado:8} obtenido={obtenido:14} → {estado}")
        if pausa:
            time.sleep(pausa)
        return obtenido if estado == "guardada" else None

    principales = [o for o in OPINIONES if a.categoria in (None, o[1])]
    if a.categoria:
        principales += [(ev, a.categoria, tx) for ev, tx in RESERVA[a.categoria]]
    for evento_id, esperado, texto in principales:
        procesar(evento_id, esperado, texto, "principal" if a.categoria is None else f"categoría {a.categoria}")

    # Comprobación de mínimos sobre lo realmente guardado
    def resumen():
        regs = c.repo_opiniones.consultar(FiltrosOpinion(incluir_ocultas=True))
        semillas = [r for r in regs if r.origen == "semilla"]
        return len(semillas), len({r.evento_id for r in semillas}), Counter(r.sentimiento for r in semillas)

    n, n_ev, cats = resumen()
    intentos_reserva = []
    for categoria in ("positivo", "negativo", "neutro", "mixto"):
        for evento_id, texto in RESERVA[categoria]:
            if cats.get(categoria, 0) > 0:
                break
            print(f"Falta la categoría «{categoria}»: intento con una opinión de reserva.")
            obtenido = procesar(evento_id, categoria, texto, f"reserva ({categoria})")
            intentos_reserva.append((categoria, texto, obtenido))
            n, n_ev, cats = resumen()

    cumple = n >= 12 and n_ev >= 4 and all(cats.get(s, 0) > 0 for s in ("positivo", "negativo", "neutro", "mixto"))
    aciertos = sum(1 for f in filas if f[5] == "✅")
    sufijo = f"_{a.categoria}" if a.categoria else ""
    sufijo += "_sql" if aj.STORAGE_BACKEND == "sql" else ""
    salida = EVIDENCIAS / f"siembra_{aj.LLM_PROVIDER}_{aj.VERSION_PROMPT}{sufijo}.md"
    lineas = [
        f"# Siembra de datos · {c.clasificador.modelo} · prompt {aj.VERSION_PROMPT}",
        "",
        f"Ejecutado el {datetime.now().strftime('%Y-%m-%d %H:%M')} con `scripts/sembrar_datos.py`. Cada opinión pasó "
        "por el clasificador real; las discrepancias **no** se corrigieron en los registros.",
        "",
        "| Fase | Carrera | Opinión | Esperado | Obtenido | ¿Coincide? | Estado | Razón del modelo | Tiempo |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for f in filas:
        lineas.append("| " + " | ".join(str(x).replace("|", "\\|") for x in f[:8]) + f" | {f[8]:.1f} s |")
    lineas += [
        "",
        f"**Coinciden:** {aciertos}/{len(filas)}.",
        "",
        "## Comprobación de mínimos (registros con origen «semilla»)",
        "",
        f"- Registros guardados: **{n}** (mínimo 12)",
        f"- Eventos distintos: **{n_ev}** (mínimo 4)",
        f"- Por categoría: {dict(cats)}",
        f"- Resultado: {'✅ cumple' if cumple else '❌ no cumple'}",
    ]
    if intentos_reserva:
        lineas += ["", "## Intentos con opiniones de reserva", ""]
        lineas += [f"- Faltaba «{cat}»: «{t}» → {ob or 'no guardada'}" for cat, t, ob in intentos_reserva]
    salida.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    print(f"\n{n} registros, {n_ev} eventos, {dict(cats)} → {'cumple' if cumple else 'NO cumple'}")
    print(f"Evidencia: {salida}")
    return 0 if cumple else 3


if __name__ == "__main__":
    raise SystemExit(main())
