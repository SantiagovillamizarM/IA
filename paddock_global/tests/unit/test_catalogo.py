"""Catálogo: validación de la jerarquía Disciplina → Campeonato → Evento."""

from __future__ import annotations

import copy
import json

import pytest

from paddock.adaptadores.persistencia.json_repo import cargar_catalogo
from paddock.config import DATOS
from paddock.dominio.errores import CatalogoInvalidoError
from paddock.dominio.reglas import validar_catalogo

BASE = json.loads((DATOS / "catalogo.json").read_text(encoding="utf-8"))


def test_catalogo_real_valido_y_multidisciplina():
    cat = cargar_catalogo(DATOS / "catalogo.json")
    assert len(cat.disciplinas) >= 6
    assert len(cat.eventos) >= 30
    assert cat.evento_por_defecto().id == "ev-f1-monaco"
    assert cat.evento("ev-res-lemans").etiqueta == "24 Horas de Le Mans — Francia"
    lemans = cat.evento("ev-res-lemans")
    assert cat.disciplina_de_evento(lemans).id == "resistencia"
    assert all(e.id.startswith("ev-") for e in cat.eventos)


def test_selector_encadenado():
    cat = cargar_catalogo(DATOS / "catalogo.json")
    assert [c.id for c in cat.campeonatos_de("formula")] == ["f1", "indycar", "formula_e"]
    assert len(cat.eventos_de("f1")) == 10
    assert all(e.campeonato_id == "wrc" for e in cat.eventos_de("wrc"))


def test_ids_duplicados_error():
    datos = copy.deepcopy(BASE)
    datos["eventos"].append(dict(datos["eventos"][0]))
    with pytest.raises(CatalogoInvalidoError, match="repetidos"):
        validar_catalogo(datos)


def test_referencia_a_campeonato_inexistente_error():
    datos = copy.deepcopy(BASE)
    datos["eventos"][0]["campeonato_id"] = "no-existe"
    with pytest.raises(CatalogoInvalidoError, match="no existe"):
        validar_catalogo(datos)


def test_referencia_a_disciplina_inexistente_error():
    datos = copy.deepcopy(BASE)
    datos["campeonatos"][0]["disciplina_id"] = "no-existe"
    with pytest.raises(CatalogoInvalidoError):
        validar_catalogo(datos)


@pytest.mark.parametrize("mutar", [
    lambda d: d.pop("version"),
    lambda d: d.__setitem__("eventos", []),
    lambda d: d["eventos"][0].__setitem__("nombre", ""),
    lambda d: d["eventos"][0].__setitem__("pais", 7),
    lambda d: d["eventos"][0].__setitem__("lat", "norte"),
    lambda d: d["disciplinas"][0].pop("icono"),
])
def test_esquema_invalido(mutar):
    datos = copy.deepcopy(BASE)
    mutar(datos)
    with pytest.raises(CatalogoInvalidoError):
        validar_catalogo(datos)


def test_archivo_inexistente_o_roto(tmp_path):
    with pytest.raises(CatalogoInvalidoError):
        cargar_catalogo(tmp_path / "nada.json")
    roto = tmp_path / "roto.json"
    roto.write_text("{roto", encoding="utf-8")
    with pytest.raises(CatalogoInvalidoError):
        cargar_catalogo(roto)
