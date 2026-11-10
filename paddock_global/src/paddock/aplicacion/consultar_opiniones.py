"""Caso de uso: consultar opiniones y sus recuentos. **Nunca** llama al modelo."""

from __future__ import annotations

from dataclasses import dataclass

from paddock.aplicacion.autorizacion import Actor
from paddock.dominio.entidades import FiltrosOpinion, Opinion
from paddock.dominio.errores import SesionRequeridaError
from paddock.dominio.reglas import contar_por_sentimiento
from paddock.puertos.repositorios import RepositorioCatalogo, RepositorioOpiniones


@dataclass(frozen=True)
class ResultadoConsulta:
    registros: list[Opinion]
    total: int
    por_sentimiento: dict[str, int]


class ConsultarOpiniones:
    def __init__(self, *, opiniones: RepositorioOpiniones, catalogo: RepositorioCatalogo,
                 permitir_anonimos: bool = True) -> None:
        self.opiniones = opiniones
        self.catalogo = catalogo
        self.permitir_anonimos = permitir_anonimos

    def resolver(self, filtros: FiltrosOpinion) -> FiltrosOpinion:
        """Traduce el filtro de campeonato a la lista de eventos (el registro no guarda el campeonato)."""
        if filtros.campeonato_id and not filtros.evento_id:
            ids = tuple(e.id for e in self.catalogo.obtener().eventos_de(filtros.campeonato_id, solo_activos=False))
            return filtros.con(evento_ids=ids)
        return filtros

    def ejecutar(self, filtros: FiltrosOpinion, actor: Actor | None = None) -> ResultadoConsulta:
        if actor is None and not self.permitir_anonimos:
            raise SesionRequeridaError("Inicia sesión para consultar las opiniones.")
        f = self.resolver(filtros)
        # Tabla y recuentos salen de los MISMOS registros filtrados.
        todos = self.opiniones.consultar(f.con(limite=None, desplazamiento=0))
        pagina = todos[f.desplazamiento: (f.desplazamiento + f.limite) if f.limite else None]
        return ResultadoConsulta(
            registros=pagina, total=len(todos),
            por_sentimiento=contar_por_sentimiento(todos, usar_revision=f.usar_revision),
        )
