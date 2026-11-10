"""v3: moderación, calidad, lotes, resúmenes, informes PDF y API REST (SQLite real, sin LLM real)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from paddock.adaptadores.llm.falso import ClasificadorFalso
from paddock.adaptadores.llm.resumidor import ResumidorFalso
from paddock.adaptadores.persistencia.json_repo import cargar_catalogo, cargar_jerga
from paddock.aplicacion.autorizacion import Actor
from paddock.aplicacion.calidad import evaluar_pares, percentil, rendimiento
from paddock.aplicacion.clasificar_lote import id_fila, validar_csv
from paddock.config import DATOS, Ajustes
from paddock.contenedor import crear_contenedor
from paddock.dominio import errores as err
from paddock.dominio.entidades import FiltrosOpinion, MetricaLlamada
from tests.conftest import opinion_ejemplo

pytestmark = pytest.mark.integracion
CLAVE = "Tres-Palabras-Largas-9"


@pytest.fixture
def c(tmp_path):
    aj = Ajustes(STORAGE_BACKEND="sql", DATABASE_URL=f"sqlite:///{(tmp_path / 'v3.db').as_posix()}",
                 LOTE_PAUSA_S=0, PERMITIR_ANONIMOS=True, API_DOCS=False)
    cont = crear_contenedor(aj, clasificador_forzado=ClasificadorFalso(detallado=True),
                            resumidor_forzado=ResumidorFalso())
    cont.bd.crear_esquema()
    cont.repo_catalogo.sembrar(cargar_catalogo(DATOS / "catalogo.json"), cargar_jerga(DATOS / "jerga.json"))
    return cont


def actores(c):
    mod = c.cuentas.registrar("mod@ejemplo.com", "Mod", CLAVE, rol="moderador", forzar=True)
    adm = c.cuentas.registrar("adm@ejemplo.com", "Adm", CLAVE, rol="admin", forzar=True)
    afi = c.cuentas.registrar("afi@ejemplo.com", "Afi", CLAVE)
    return Actor(mod.id, "moderador"), Actor(adm.id, "admin"), Actor(afi.id, "aficionado")


# ======================================================================= moderación


def test_revision_humana_no_cambia_la_etiqueta_del_modelo(c):
    mod, _, afi = actores(c)
    c.repo_opiniones.guardar(opinion_ejemplo(1, sentimiento="positivo", ironia=True))
    oid = opinion_ejemplo(1).id
    with pytest.raises(err.PermisoDenegadoError):
        c.moderacion.revisar(afi, oid, "negativo")
    c.moderacion.revisar(mod, oid, "negativo", "Es irónico")
    op = c.repo_opiniones.obtener(oid)
    assert op.sentimiento == "positivo" and op.revision.sentimiento == "negativo"
    assert op.revision.revisor_id == mod.usuario_id and op.revision.nota == "Es irónico"
    assert "revision" in [a["accion"] for a in c.repo_auditoria.consultar()]


def test_cola_priorizada_denuncias_y_ocultar(c):
    mod, _, afi = actores(c)
    c.repo_opiniones.guardar(opinion_ejemplo(1, sentimiento="positivo"))
    c.repo_opiniones.guardar(opinion_ejemplo(2, sentimiento="mixto"))
    c.repo_opiniones.guardar(opinion_ejemplo(3, sentimiento="negativo", ironia=True))
    c.repo_opiniones.guardar(opinion_ejemplo(4, sentimiento="positivo", intensidad=1))
    c.moderacion.denunciar(afi, opinion_ejemplo(1).id, "mal_clasificada")
    with pytest.raises(err.EntradaInvalidaError):
        c.moderacion.denunciar(afi, opinion_ejemplo(1).id, "spam")  # una denuncia pendiente por usuario
    with pytest.raises(err.SesionRequeridaError):
        c.moderacion.denunciar(None, opinion_ejemplo(2).id, "spam")
    cola = c.moderacion.cola(mod)
    assert [e.opinion.id[-1] for e in cola] == ["1", "3", "4", "2"]  # denunciada, ironía, intensidad, mixta
    with pytest.raises(err.PermisoDenegadoError):
        c.moderacion.cola(afi)
    c.moderacion.cambiar_visibilidad(mod, opinion_ejemplo(1).id, False)
    assert c.repo_opiniones.contar(FiltrosOpinion()) == 3
    assert c.repo_opiniones.obtener(opinion_ejemplo(1).id) is not None  # nunca se borra
    assert c.repo_denuncias.pendientes() == []


# ======================================================================= calidad


def test_metricas_de_calidad_y_matriz():
    pares = [("positivo", "positivo"), ("positivo", "positivo"), ("negativo", "positivo"),
             ("negativo", "negativo"), ("mixto", "negativo"), ("neutro", "neutro")]
    inf = evaluar_pares(pares)
    assert inf.n == 6 and inf.exactitud == pytest.approx(4 / 6)
    assert inf.matriz["negativo"]["positivo"] == 1 and inf.matriz["mixto"]["negativo"] == 1
    assert inf.por_clase["positivo"].precision == pytest.approx(2 / 3)
    assert inf.por_clase["positivo"].recall == 1.0
    assert inf.por_clase["mixto"].recall == 0.0 and inf.por_clase["mixto"].f1 == 0.0
    assert evaluar_pares([]).exactitud is None


def test_rendimiento_latencia_p95_y_errores():
    ms = [MetricaLlamada("2026-11-10T00:00:00+00:00", "ollama", "q", "2.0", lat, True) for lat in range(100, 1100, 100)]
    ms.append(MetricaLlamada("2026-11-10T00:00:00+00:00", "ollama", "q", "2.0", 50, False, "CuotaExcedidaError"))
    r = rendimiento(ms)[0]
    assert r.llamadas == 11 and r.latencia_media_ms == 550
    assert r.latencia_p95_ms == pytest.approx(percentil(list(range(100, 1100, 100)), 95))
    assert r.errores == {"CuotaExcedidaError": 1} and r.tasa_error == pytest.approx(1 / 11)


def test_calidad_solo_admin_y_solo_revisadas(c):
    mod, adm, _ = actores(c)
    c.repo_opiniones.guardar(opinion_ejemplo(1, sentimiento="positivo"))
    c.repo_opiniones.guardar(opinion_ejemplo(2, sentimiento="positivo"))
    c.moderacion.revisar(mod, opinion_ejemplo(1).id, "negativo")
    with pytest.raises(err.PermisoDenegadoError):
        c.calidad.informe(mod)
    inf = c.calidad.informe(adm)
    assert inf.n == 1 and inf.matriz["negativo"]["positivo"] == 1
    assert c.calidad.informe(adm, proveedor="ollama").n == 0


# ======================================================================= lotes

CSV_OK = ("evento_id,edicion_anio,opinion\n"
          "ev-res-lemans,2025,La salida al amanecer es pura magia\n"
          "ev-f1-monaco,,Una carrera aburrida y decepcionante\n"
          "ev-wrc-finlandia,2024,La capital de Francia es París\n").encode()


def test_validar_csv_errores_por_fila(c):
    cat = c.repo_catalogo.obtener()
    malo = ("evento_id,edicion_anio,opinion\nev-no-existe,,Texto suficiente\nev-f1-monaco,2999,Texto válido aquí\n"
            "ev-f1-monaco,,top\n").encode()
    v = validar_csv(malo, cat, 2026)
    assert not v.valido and [e["fila"] for e in v.errores] == [1, 2, 3]
    assert not validar_csv(b"a,b,c\n1,2,3\n", cat, 2026).valido
    assert not validar_csv(b"x" * 1_000_001, cat, 2026).valido
    filas = "evento_id,edicion_anio,opinion\n" + "ev-f1-monaco,,Una opinión válida\n" * 501
    assert any("500" in e["error"] for e in validar_csv(filas.encode(), cat, 2026).errores)
    assert validar_csv(CSV_OK, cat, 2026).valido


def test_lote_se_procesa_y_reprocesar_no_duplica(c):
    mod, _, afi = actores(c)
    with pytest.raises(err.PermisoDenegadoError):
        c.clasificar_lote.crear(afi, CSV_OK)
    t, val = c.clasificar_lote.crear(mod, CSV_OK)
    assert t is not None and t.total == 3 and t.estado == "pendiente"
    hecho = c.procesador_lotes.procesar(t)
    assert hecho.estado == "terminado" and hecho.procesadas == 3 and hecho.fallidas == 0
    assert [r["estado"] for r in hecho.resultados] == ["guardada", "guardada", "no_pertinente"]
    guardadas = c.repo_opiniones.consultar(FiltrosOpinion())
    assert len(guardadas) == 2 and {o.origen for o in guardadas} == {"lote"}
    assert {o.id for o in guardadas} == {id_fila(t.id, 1), id_fila(t.id, 2)}
    llamadas = len(c.clasificador.llamadas)
    otra = c.procesador_lotes.procesar(c.repo_trabajos.obtener(t.id))  # reprocesar el mismo trabajo
    assert len(c.repo_opiniones.consultar(FiltrosOpinion())) == 2
    assert otra.procesadas == 3
    assert len(c.clasificador.llamadas) == llamadas + 1  # solo la fila no pertinente vuelve al modelo


def test_una_fila_con_error_no_detiene_el_lote(c):
    mod, _, _ = actores(c)
    c.clasificador._errores = [err.ProveedorNoDisponibleError("caído")]
    t, _ = c.clasificar_lote.crear(mod, CSV_OK)
    hecho = c.procesador_lotes.procesar(t)
    assert hecho.estado == "terminado" and hecho.fallidas == 1 and hecho.procesadas == 2
    assert hecho.errores[0]["fila"] == 1 and "ProveedorNoDisponible" in hecho.errores[0]["error"]
    assert c.repo_opiniones.obtener(id_fila(t.id, 1)) is None  # el fallo NO se guarda como neutro


def test_lote_se_pausa_con_el_tope_diario(c):
    mod, _, _ = actores(c)
    c.limitador.global_diario = 1
    t, _ = c.clasificar_lote.crear(mod, CSV_OK)
    pausado = c.procesador_lotes.procesar(t)
    assert pausado.estado == "pendiente" and pausado.procesadas == 1
    assert "reanudará" in pausado.errores[-1]["error"]


# ======================================================================= resúmenes


def test_resumen_minimo_cache_y_regenerar(c):
    _, _, afi = actores(c)
    for i in range(1, 5):
        c.repo_opiniones.guardar(opinion_ejemplo(i))
    with pytest.raises(err.EntradaInvalidaError, match="al menos 5"):
        c.resumir_comunidad.ejecutar("ev-res-lemans", 2026, afi)
    c.repo_opiniones.guardar(opinion_ejemplo(5, sentimiento="negativo"))
    with pytest.raises(err.SesionRequeridaError):
        c.resumir_comunidad.ejecutar("ev-res-lemans", 2026, None)
    r1 = c.resumir_comunidad.ejecutar("ev-res-lemans", 2026, afi)
    assert not r1.reutilizado and "5 opiniones" in r1.resumen.texto and r1.resumen.n_opiniones == 5
    r2 = c.resumir_comunidad.ejecutar("ev-res-lemans", 2026, None)  # caché: no hace falta sesión
    assert r2.reutilizado and c.resumidor.llamadas == 1
    c.resumir_comunidad.ejecutar("ev-res-lemans", 2026, afi, regenerar=True)
    with pytest.raises(err.LimiteExcedidoError):
        c.resumir_comunidad.ejecutar("ev-res-lemans", 2026, afi, regenerar=True)


def test_resumidor_map_reduce_por_grupos_de_30():
    from paddock.adaptadores.llm.resumidor import ResumidorLangChain

    llamadas = []

    class Cadena:
        def __init__(self, nombre):
            self.nombre = nombre

        def invoke(self, entrada):
            llamadas.append((self.nombre, entrada["opiniones"].count("\n- ") + 1 if self.nombre == "parcial" else 0))
            return f"resumen {self.nombre}"

    r = ResumidorLangChain.__new__(ResumidorLangChain)
    r._proveedor, r._nombre = "falso", "x"
    r._final, r._parcial = Cadena("final"), Cadena("parcial")
    ops = [("positivo", f"opinión {i}") for i in range(65)]
    assert r.resumir(carrera="Le Mans", edicion=None, opiniones=ops) == "resumen final"
    assert [n for n, _ in llamadas] == ["parcial", "parcial", "parcial", "final"]
    assert [k for n, k in llamadas if n == "parcial"] == [30, 30, 5]


# ======================================================================= informe PDF


def test_informe_pdf_con_tildes(c):
    c.repo_opiniones.guardar(opinion_ejemplo(1, opinion_original="Nürburgring y São Paulo: ¡qué carrera!"))
    c.repo_opiniones.guardar(opinion_ejemplo(2, sentimiento="mixto", aspectos=[
        {"aspecto": "trazado", "sentimiento": "positivo"}, {"aspecto": "clima", "sentimiento": "negativo"}]))
    pdf = c.informes.pdf("ev-res-lemans", 2026)
    assert pdf.startswith(b"%PDF") and len(pdf) > 5000
    d = c.informes.datos("ev-res-lemans", 2026)
    assert d.estadisticas.total == 2 and len(d.muestras["mixto"]) == 1
    with pytest.raises(err.EventoNoEncontradoError):
        c.informes.pdf("ev-no-existe", None)


# ======================================================================= API REST


@pytest.fixture
def api(c):
    from paddock.api.main import crear_app

    return TestClient(crear_app(c)), c


def test_api_salud_catalogo_y_docs_desactivados(api):
    cli, _ = api
    assert cli.get("/api/salud").json()["estado"] == "ok"
    cat = cli.get("/api/catalogo").json()
    assert len(cat["eventos"]) == 32 and cat["eventos"][0]["id"] == "ev-f1-monaco"
    assert cli.get("/api/docs").status_code == 404
    assert cli.get("/api/openapi.json").status_code == 404


def test_api_post_sin_token_y_con_token_revocado_401(api):
    cli, c = api
    cuerpo = {"evento_id": "ev-res-lemans", "opinion": "La salida al amanecer es pura magia"}
    r = cli.post("/api/opiniones", json=cuerpo)
    assert r.status_code == 401 and r.json()["error"]["codigo"] == "no_autenticado"
    assert cli.post("/api/opiniones", json=cuerpo, headers={"Authorization": "Bearer pg_falso"}).status_code == 401
    _, _, afi = actores(c)
    token = c.tokens_api.crear(afi, "pruebas")
    cab = {"Authorization": f"Bearer {token}"}
    r = cli.post("/api/opiniones", json=cuerpo, headers=cab)
    assert r.status_code == 201 and r.json()["estado"] == "guardada"
    assert r.json()["opinion"]["origen"] == "api" and "usuario_id" not in r.json()["opinion"]
    c.tokens_api.revocar(afi, c.tokens_api.listar(afi)[0].id)
    assert cli.post("/api/opiniones", json=cuerpo, headers=cab).status_code == 401
    assert c.repo_tokens.de_usuario(afi.usuario_id)[0].hash_token != token  # se guarda solo el hash


def test_api_no_pertinente_validacion_y_limite(api):
    cli, c = api
    _, _, afi = actores(c)
    cab = {"Authorization": f"Bearer {c.tokens_api.crear(afi, 'pruebas')}"}
    r = cli.post("/api/opiniones", json={"evento_id": "ev-f1-monaco", "opinion": "La capital de Francia es París"},
                 headers=cab)
    assert r.status_code == 200 and r.json()["estado"] == "no_pertinente"
    r = cli.post("/api/opiniones", json={"evento_id": "ev-f1-monaco", "opinion": "top"}, headers=cab)
    assert r.status_code == 422 and r.json()["error"]["codigo"] == "entrada_invalida"
    r = cli.post("/api/opiniones", json={"evento_id": "ev-f1-monaco"}, headers=cab)
    assert r.status_code == 422 and "opinion" in r.json()["error"]["mensaje"]
    for i in range(9):  # ya hubo 2 llamadas que cuentan (no pertinente + validación sí falla antes)
        cli.post("/api/opiniones", json={"evento_id": "ev-f1-monaco", "opinion": f"Gran carrera número {i}"},
                 headers=cab)
    r = cli.post("/api/opiniones", json={"evento_id": "ev-f1-monaco", "opinion": "Una más, increíble"}, headers=cab)
    assert r.status_code == 429 and r.json()["error"]["codigo"] == "limite_excedido"


def test_api_filtros_paginacion_y_estadisticas(api):
    cli, c = api
    for i in range(1, 8):
        c.repo_opiniones.guardar(opinion_ejemplo(i, sentimiento="positivo" if i % 2 else "negativo"))
    c.repo_opiniones.guardar(opinion_ejemplo(9, evento_id="ev-f1-monaco", evento_nombre="GP Mónaco",
                                             disciplina_id="formula"))
    r = cli.get("/api/opiniones", params={"evento_id": "ev-res-lemans", "limite": 3, "desplazamiento": 2}).json()
    assert r["total"] == 7 and len(r["opiniones"]) == 3 and r["desplazamiento"] == 2
    assert all("usuario_id" not in o for o in r["opiniones"])
    assert cli.get("/api/opiniones", params={"sentimiento": "negativo"}).json()["total"] == 3
    assert cli.get("/api/opiniones", params={"campeonato_id": "f1"}).json()["total"] == 1
    assert cli.get("/api/opiniones", params={"limite": 1000}).status_code == 422
    assert cli.get("/api/opiniones", params={"sentimiento": "feliz"}).status_code == 422
    e = cli.get("/api/estadisticas", params={"disciplina_id": "resistencia"}).json()
    assert e["total"] == 7 and e["por_sentimiento"] == {"positivo": 4, "negativo": 3, "neutro": 0, "mixto": 0}


def test_api_error_interno_sin_traza(api, monkeypatch):
    cli, c = api
    monkeypatch.setattr(c.repo_catalogo, "obtener", lambda: (_ for _ in ()).throw(RuntimeError("secreto interno")))
    r = TestClient(cli.app, raise_server_exceptions=False).get("/api/catalogo")
    assert r.status_code == 500 and "secreto" not in r.text and r.json()["error"]["codigo"] == "error_interno"
