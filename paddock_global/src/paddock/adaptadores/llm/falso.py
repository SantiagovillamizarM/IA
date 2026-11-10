"""``ClasificadorFalso``: determinista, sin red. Lo usan los tests y la CI (nunca llaman a Gemini ni a Ollama)."""

from __future__ import annotations

from collections.abc import Sequence

from paddock.dominio.analisis import AnalisisDetallado, AnalisisOpinion, AspectoValorado, ResultadoClasificacion
from paddock.dominio.reglas import validar_coherencia

_POSITIVAS = ("magia", "espectacular", "increíble", "brillante", "me encant", "inolvidable", "mejor",
              "maravill", "precioso", "piel de gallina", "amazing", "best", "emocionante")
_NEGATIVAS = ("decepcion", "aburrid", "arruin", "horrible", "desastre", "imposible", "procesión",
              "eterna", "mataron", "peor", "sin imágenes", "cortó")
_AJENAS = ("capital de francia", "cocinar", "ignora las reglas", "</opinion>", "receta")
_IRONIA = ("qué emoción:", "qué maravilla de", "bravo por")


class ClasificadorFalso:
    """Clasificación por palabras clave, o respuestas/errores programados para un test."""

    def __init__(
        self,
        *,
        detallado: bool = True,
        respuestas: dict[str, AnalisisOpinion] | None = None,
        error: Exception | None = None,
        errores: Sequence[Exception] | None = None,
        validar: bool = True,
    ) -> None:
        self.detallado = detallado
        self.respuestas = respuestas or {}
        self.error = error
        self._errores = list(errores or [])
        self.validar = validar
        self.llamadas: list[str] = []

    @property
    def proveedor(self) -> str:
        return "falso"

    @property
    def modelo(self) -> str:
        return "falso/determinista"

    @property
    def version_prompt(self) -> str:
        return "2.0" if self.detallado else "1.0"

    def clasificar(
        self, *, texto: str, carrera: str, disciplina: str, disciplina_id: str, edicion: int | None
    ) -> ResultadoClasificacion:
        if not texto or not texto.strip():
            raise ValueError("El clasificador nunca se llama con texto vacío.")
        self.llamadas.append(texto)
        if self._errores:
            raise self._errores.pop(0)
        if self.error is not None:
            raise self.error
        analisis = self.respuestas.get(texto) or self._heuristica(texto)
        if self.validar:
            validar_coherencia(analisis)
        return ResultadoClasificacion(analisis=analisis, modelo=self.modelo, version_prompt=self.version_prompt,
                                      latencia_ms=1)

    def _heuristica(self, texto: str) -> AnalisisOpinion:
        t = texto.casefold()
        if any(a in t for a in _AJENAS):
            return self._crear(False, None, "El texto no es una opinión sobre la carrera.")
        ironia = any(i in t for i in _IRONIA)
        pos = any(p in t for p in _POSITIVAS) and not ironia
        neg = any(n in t for n in _NEGATIVAS) or ironia
        if pos and neg:
            s = "mixto"
        elif pos:
            s = "positivo"
        elif neg:
            s = "negativo"
        else:
            s = "neutro"
        razon = f"El aficionado expresa una valoración {s}." + (" Usa ironía." if ironia else "")
        return self._crear(True, s, razon, ironia=ironia)

    def _crear(self, pertinente: bool, s: str | None, razon: str, ironia: bool = False) -> AnalisisOpinion:
        if not self.detallado:
            return AnalisisOpinion(es_pertinente=pertinente, sentimiento=s, razon=razon)  # type: ignore[arg-type]
        aspectos: list[AspectoValorado] = []
        if s == "mixto":
            aspectos = [AspectoValorado(aspecto="trazado", sentimiento="positivo"),
                        AspectoValorado(aspecto="clima", sentimiento="negativo")]
        elif s in ("positivo", "negativo"):
            aspectos = [AspectoValorado(aspecto="ambiente", sentimiento=s)]  # type: ignore[arg-type]
        return AnalisisDetallado(
            es_pertinente=pertinente, sentimiento=s, razon=razon, aspectos=aspectos,  # type: ignore[arg-type]
            ironia=ironia, intensidad=3 if pertinente else None, entidades=[],
        )
