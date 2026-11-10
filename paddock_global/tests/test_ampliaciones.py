"""Pruebas de las ampliaciones (no requieren Ollama)."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import almacenamiento as alm  # noqa: E402
import carga_masiva as cm  # noqa: E402
import estadisticas as est  # noqa: E402
from analisis import AnalisisOpinion, AspectoOpinion, alerta_revision  # noqa: E402
from config import RUTA_CARRERAS, cargar_config  # noqa: E402
from evaluacion import comparar, kappa_cohen, metricas  # noqa: E402

LE_MANS = {"id": "c001", "nombre": "24 Horas de Le Mans", "pais": "Francia", "circuito": "Sarthe"}
DAYTONA = {"id": "c003", "nombre": "24 Horas de Daytona", "pais": "EE. UU.", "circuito": "Daytona"}


def analisis(sent="positivo", aspectos=(), idioma="es", pert=True):
    return AnalisisOpinion(
        es_pertinente=pert, idioma=idioma, sentimiento=sent if pert else None, razon="Razón de prueba.",
        aspectos=[AspectoOpinion(aspecto=a, sentimiento=s) for a, s in aspectos],
    )


def reg(sent="positivo", carrera=LE_MANS, aspectos=(), idioma="es", texto="Una opinión de prueba"):
    return alm.crear_registro(carrera, texto, analisis(sent, aspectos, idioma), "ollama/x", "2.0")


# ------------------------------------------------------- aspectos y alerta

def test_alerta_aspectos_contradictorios():
    a = analisis("negativo", [("trazado", "positivo"), ("clima", "negativo")])
    assert "mixto" not in (alerta_revision(analisis("mixto", [("trazado", "positivo"), ("clima", "negativo")])) or "")
    assert alerta_revision(a) is not None
    assert alerta_revision(analisis("positivo", [("ambiente", "positivo")])) is None
    assert alerta_revision(analisis("neutro", [("ambiente", "positivo")])) is not None
    assert alerta_revision(analisis(None, pert=False)) is None


def test_registro_incluye_idioma_aspectos_y_alerta():
    r = reg("negativo", aspectos=[("trazado", "positivo"), ("clima", "negativo")], idioma="fr")
    assert r["idioma"] == "fr"
    assert r["aspectos"] == [{"aspecto": "trazado", "sentimiento": "positivo"},
                             {"aspecto": "clima", "sentimiento": "negativo"}]
    assert r["alerta_revision"]


def test_registros_antiguos_sin_campos_nuevos_siguen_cargando(tmp_path):
    ruta = tmp_path / "opiniones.json"
    viejo = {k: v for k, v in reg().items() if k not in ("idioma", "aspectos", "alerta_revision")}
    ruta.write_text(json.dumps({"version": 1, "opiniones": [viejo]}), encoding="utf-8")
    regs = alm.cargar_opiniones(ruta)["opiniones"]
    assert alm.consultar_opiniones(regs, idioma=None) == regs
    assert est.conteo_por_aspecto(regs) == []


# --------------------------------------------------------- corrección manual

def test_correccion_conserva_original_y_cambia_vigente(tmp_path):
    ruta = tmp_path / "opiniones.json"
    r = reg("negativo")
    alm.guardar_opinion(ruta, r)
    alm.corregir_opinion(ruta, r["id"], "mixto", "  tiene elogio y crítica  ")
    guardado = alm.cargar_opiniones(ruta)["opiniones"][0]
    assert guardado["sentimiento"] == "negativo"
    assert guardado["sentimiento_corregido"] == "mixto"
    assert guardado["nota_correccion"] == "tiene elogio y crítica"
    assert alm.sentimiento_final(guardado) == "mixto"
    assert len(alm.consultar_opiniones([guardado], sentimiento="mixto")) == 1
    assert alm.consultar_opiniones([guardado], sentimiento="negativo") == []
    assert alm.contar_por_sentimiento([guardado])["mixto"] == 1


def test_correccion_igual_al_modelo_restaura(tmp_path):
    ruta = tmp_path / "opiniones.json"
    r = reg("negativo")
    alm.guardar_opinion(ruta, r)
    alm.corregir_opinion(ruta, r["id"], "mixto")
    alm.corregir_opinion(ruta, r["id"], "negativo")
    guardado = alm.cargar_opiniones(ruta)["opiniones"][0]
    assert "sentimiento_corregido" not in guardado


def test_correccion_errores(tmp_path):
    ruta = tmp_path / "opiniones.json"
    alm.guardar_opinion(ruta, reg())
    with pytest.raises(alm.RegistroNoEncontradoError):
        alm.corregir_opinion(ruta, "no-existe", "mixto")
    with pytest.raises(ValueError):
        alm.corregir_opinion(ruta, alm.cargar_opiniones(ruta)["opiniones"][0]["id"], "feliz")
    ruta.write_bytes(b"{roto")
    with pytest.raises(alm.ArchivoOpinionesCorruptoError):
        alm.corregir_opinion(ruta, "x", "mixto")
    assert ruta.read_bytes() == b"{roto"


def test_filtro_solo_alertas_excluye_corregidas():
    con_alerta = reg("negativo", aspectos=[("trazado", "positivo"), ("clima", "negativo")])
    corregida = {**con_alerta, "id": "otro", "sentimiento_corregido": "mixto"}
    sin_alerta = reg("positivo")
    assert alm.consultar_opiniones([con_alerta, corregida, sin_alerta], solo_alertas=True) == [con_alerta]


# ------------------------------------------------------------- estadísticas

def test_ranking_indice_y_minimo():
    regs = [reg("positivo"), reg("positivo"), reg("negativo"), reg("mixto"),
            reg("negativo", carrera=DAYTONA)]
    ranking = est.ranking_carreras(regs, minimo=2)
    assert ranking[0]["carrera_id"] == "c001"
    assert ranking[0]["indice"] == 25.0          # (2 − 1) / 4 × 100
    assert ranking[0]["suficiente"] is True
    assert ranking[1]["carrera_id"] == "c003" and ranking[1]["suficiente"] is False


def test_ranking_usa_correcciones():
    r = {**reg("negativo"), "sentimiento_corregido": "positivo"}
    assert est.ranking_carreras([r], minimo=1)[0]["indice"] == 100.0


def test_conteos_para_graficas():
    regs = [reg("positivo", aspectos=[("trazado", "positivo")]),
            reg("negativo", aspectos=[("trazado", "negativo"), ("clima", "negativo")])]
    filas = {(f["carrera"], f["sentimiento"]): f["n"] for f in est.conteo_por_carrera(regs)}
    assert filas == {("24 Horas de Le Mans", "positivo"): 1, ("24 Horas de Le Mans", "negativo"): 1}
    asp = {(f["aspecto"], f["sentimiento"]): f["n"] for f in est.conteo_por_aspecto(regs)}
    assert asp == {("trazado", "positivo"): 1, ("trazado", "negativo"): 1, ("clima", "negativo"): 1}


# ------------------------------------------------------------- carga masiva

CARRERAS = alm.cargar_carreras(RUTA_CARRERAS)


def test_csv_punto_y_coma_con_id_y_nombre():
    contenido = "carrera;opinion\nc001;Gran carrera nocturna\n24 Horas de Daytona;Muy aburrida la carrera\n".encode("utf-8-sig")
    filas = cm.leer_csv(contenido, CARRERAS)
    assert [f.carrera["id"] for f in filas] == ["c001", "c003"]
    assert all(f.error is None for f in filas)


def test_csv_errores_por_fila():
    filas = cm.leer_csv(b"carrera,opinion\nc999,Carrera inexistente\nc001,top\n", CARRERAS)
    assert "desconocida" in filas[0].error
    assert filas[1].error is not None


def test_csv_columnas_faltantes():
    with pytest.raises(cm.CSVInvalidoError):
        cm.leer_csv(b"nombre,texto\na,b\n", CARRERAS)


def test_csv_ids_deterministas():
    contenido = b"carrera,opinion\nc001,Gran carrera nocturna\n"
    assert cm.leer_csv(contenido, CARRERAS)[0].registro_id == cm.leer_csv(contenido, CARRERAS)[0].registro_id
    otro = b"carrera,opinion\nc001,Otra opinion distinta\n"
    assert cm.leer_csv(contenido, CARRERAS)[0].registro_id != cm.leer_csv(otro, CARRERAS)[0].registro_id


class CadenaFalsa:
    def __init__(self):
        self.llamadas = 0

    def invoke(self, datos):
        self.llamadas += 1
        pertinente = "capital" not in datos["opinion"]
        return {"raw": None, "parsing_error": None, "parsed": analisis("positivo" if pertinente else None,
                                                                       pert=pertinente)}


def test_procesar_lote_idempotente(tmp_path):
    ruta = tmp_path / "opiniones.json"
    contenido = ("carrera,opinion\nc001,Gran carrera nocturna\nc001,La capital de Francia es París\n"
                 "c999,No existe\n").encode()
    filas = cm.leer_csv(contenido, CARRERAS)
    cadena = CadenaFalsa()
    r1 = cm.procesar_filas(filas, cargar_config(), cadena=cadena, ruta=ruta)
    assert [r.estado for r in r1] == ["guardada", "no_pertinente", "invalida"]
    assert cadena.llamadas == 2
    r2 = cm.procesar_filas(filas, cargar_config(), cadena=cadena, ruta=ruta)
    assert r2[0].estado == "ya_existia"
    assert len(alm.cargar_opiniones(ruta)["opiniones"]) == 1


# --------------------------------------------------------------- evaluación

def test_kappa():
    assert kappa_cohen(["a", "b", "a", "b"], ["a", "b", "a", "b"]) == 1.0
    assert kappa_cohen(["a", "a", "b", "b"], ["a", "b", "a", "b"]) == 0.0


def test_metricas_y_comparacion():
    a = [{"id": "1", "idioma": "es", "texto": "t", "esperado": "positivo", "obtenido": "positivo",
          "idioma_detectado": "es", "segundos": 2.0},
         {"id": "2", "idioma": "en", "texto": "t", "esperado": "mixto", "obtenido": "negativo",
          "idioma_detectado": "en", "segundos": 4.0}]
    b = [{**a[0]}, {**a[1], "obtenido": "mixto"}]
    m = metricas(a)
    assert m["exactitud"] == 50.0 and m["por_idioma"]["en"]["exactitud"] == 0.0
    assert m["idioma_detectado_ok"] == 100.0 and m["segundos_promedio"] == 3.0
    c = comparar(a, b)
    assert c["acuerdo"] == 50.0 and len(c["desacuerdos"]) == 1
