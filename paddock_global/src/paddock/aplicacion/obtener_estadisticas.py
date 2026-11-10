"""Caso de uso: estadísticas para el dashboard y el comparador. Lee de los repositorios, nunca del modelo."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from paddock.aplicacion.autorizacion import Actor
from paddock.aplicacion.consultar_opiniones import ConsultarOpiniones
from paddock.dominio.entidades import FiltrosOpinion, Opinion
from paddock.dominio.enums import SENTIMIENTOS
from paddock.dominio.reglas import contar_entidades, contar_por_sentimiento, indice_percepcion, matriz_aspectos

N_MINIMO_RANKING = 5


@dataclass(frozen=True)
class FilaRanking:
    evento_id: str
    evento_nombre: str
    n: int
    indice: float
    conteo: dict[str, int]


@dataclass(frozen=True)
class Estadisticas:
    total: int
    conteo: dict[str, int]
    porcentajes: dict[str, float]
    eventos_con_opiniones: int
    semanal: dict[str, dict[str, int]]  # lunes ISO → conteo
    por_disciplina: dict[str, dict[str, int]]
    aspectos: dict[str, dict[str, int]]
    entidades: list[tuple[str, int]]
    ranking: list[FilaRanking] = field(default_factory=list)
    indice: float | None = None


def inicio_semana(fecha_utc: str) -> str:
    d = datetime.fromisoformat(fecha_utc).date()
    return (d - timedelta(days=d.weekday())).isoformat()


def calcular(registros: list[Opinion], usar_revision: bool = False) -> Estadisticas:
    def etiqueta(o: Opinion) -> str:
        return o.sentimiento_efectivo if usar_revision else o.sentimiento

    conteo = contar_por_sentimiento(registros, usar_revision)
    total = len(registros)
    semanal: dict[str, dict[str, int]] = defaultdict(lambda: dict.fromkeys(SENTIMIENTOS, 0))
    por_disc: dict[str, dict[str, int]] = defaultdict(lambda: dict.fromkeys(SENTIMIENTOS, 0))
    por_evento: dict[str, list[Opinion]] = defaultdict(list)
    for o in registros:
        semanal[inicio_semana(o.fecha_utc)][etiqueta(o)] += 1
        por_disc[o.disciplina_id][etiqueta(o)] += 1
        por_evento[o.evento_id].append(o)
    ranking = []
    for ev_id, ops in por_evento.items():
        c = contar_por_sentimiento(ops, usar_revision)
        idx = indice_percepcion(c)
        if len(ops) >= N_MINIMO_RANKING and idx is not None:
            ranking.append(FilaRanking(ev_id, ops[0].evento_nombre, len(ops), idx, c))
    ranking.sort(key=lambda r: (-r.indice, -r.n))
    return Estadisticas(
        total=total, conteo=conteo,
        porcentajes={s: (100 * n / total if total else 0.0) for s, n in conteo.items()},
        eventos_con_opiniones=len(por_evento), semanal=dict(sorted(semanal.items())), por_disciplina=dict(por_disc),
        aspectos=matriz_aspectos(registros), entidades=contar_entidades(registros, 10), ranking=ranking,
        indice=indice_percepcion(conteo),
    )


@dataclass
class ObtenerEstadisticas:
    consultar: ConsultarOpiniones

    def ejecutar(self, filtros: FiltrosOpinion, actor: Actor | None = None) -> Estadisticas:
        res = self.consultar.ejecutar(filtros.con(limite=None, desplazamiento=0), actor)
        return calcular(res.registros, filtros.usar_revision)

    def ejemplos(self, registros: list[Opinion], por_categoria: int = 1) -> dict[str, list[Opinion]]:
        salida: dict[str, list[Opinion]] = {s: [] for s in SENTIMIENTOS}
        for o in registros:
            if len(salida[o.sentimiento]) < por_categoria:
                salida[o.sentimiento].append(o)
        return salida
