"""Informe PDF con ``fpdf2`` (Python puro) y la fuente DejaVu Sans incluida (tildes, «ñ», «ü»; licencia en
``fuentes/LICENSE-DejaVu.txt``).

Los gráficos se dibujan como barras vectoriales directamente en el PDF: ``kaleido`` no está instalado (exige un
navegador y binarios nativos, poco fiables bajo Smart App Control), así que no se exportan imágenes de Plotly.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from fpdf import FPDF

from paddock.aplicacion.generar_informe import DatosInforme
from paddock.dominio.enums import COLOR_SENTIMIENTO, SENTIMIENTOS
from paddock.dominio.reglas import indice_percepcion

FUENTES = Path(__file__).resolve().parent / "fuentes"
NOMBRE = {"positivo": "Positivo", "negativo": "Negativo", "neutro": "Neutro", "mixto": "Mixto"}
ASPECTO = {"trazado": "Trazado", "organizacion": "Organización", "ambiente": "Ambiente", "estrategia": "Estrategia",
           "clima": "Clima", "reglamento": "Reglamento", "pilotos_equipos": "Pilotos y equipos",
           "vehiculos": "Vehículos", "transmision": "Transmisión", "seguridad": "Seguridad", "otro": "Otro"}


def _rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


class _Pdf(FPDF):
    def __init__(self, titulo: str) -> None:
        super().__init__(format="A4")
        self.titulo = titulo
        self.add_font("DejaVu", "", str(FUENTES / "DejaVuSans.ttf"))
        self.add_font("DejaVu", "B", str(FUENTES / "DejaVuSans-Bold.ttf"))
        self.set_auto_page_break(auto=True, margin=18)
        self.set_margins(18, 18, 18)

    def header(self) -> None:
        if self.page_no() == 1:
            return
        self.set_font("DejaVu", "", 8)
        self.set_text_color(120, 120, 120)
        self.cell(0, 6, f"Paddock Global · {self.titulo}", align="L")
        self.ln(8)

    def footer(self) -> None:
        self.set_y(-12)
        self.set_font("DejaVu", "", 8)
        self.set_text_color(120, 120, 120)
        self.cell(0, 6, f"Página {self.page_no()}/{{nb}} · Refleja solo las opiniones registradas en Paddock Global",
                  align="C")

    def subtitulo(self, texto: str) -> None:
        if self.get_y() > self.h - 60:  # evita títulos huérfanos al pie de la página
            self.add_page()
        self.ln(3)
        self.set_font("DejaVu", "B", 13)
        self.set_text_color(30, 30, 30)
        self.cell(0, 8, texto, new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(225, 6, 0)
        self.set_line_width(0.6)
        self.line(self.l_margin, self.get_y(), self.l_margin + 30, self.get_y())
        self.set_draw_color(180, 180, 180)
        self.set_line_width(0.2)
        self.ln(3)

    def parrafo(self, texto: str, tam: float = 10) -> None:
        self.set_font("DejaVu", "", tam)
        self.set_text_color(40, 40, 40)
        self.multi_cell(0, 5.2, texto, new_x="LMARGIN", new_y="NEXT")


def generar_pdf(d: DatosInforme, zona: str = "America/Bogota") -> bytes:
    titulo = d.evento.nombre + (f" · {d.edicion}" if d.edicion else "")
    pdf = _Pdf(titulo)
    pdf.alias_nb_pages()
    e = d.estadisticas

    # ---------------- portada
    pdf.add_page()
    pdf.set_fill_color(21, 23, 28)
    pdf.rect(0, 0, 210, 80, style="F")
    pdf.set_y(22)
    pdf.set_font("DejaVu", "B", 26)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 12, "Paddock Global", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("DejaVu", "", 12)
    pdf.set_text_color(220, 220, 220)
    pdf.cell(0, 7, "Informe de percepción de la comunidad", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("DejaVu", "B", 17)
    pdf.set_text_color(255, 90, 80)
    pdf.cell(0, 10, titulo, new_x="LMARGIN", new_y="NEXT")
    pdf.set_y(90)
    pdf.parrafo(f"{d.disciplina.nombre} · {d.campeonato} · {d.evento.pais} · {d.evento.sede}"
                + (" · prueba histórica" if d.evento.historico else ""), 11)
    try:
        fecha = datetime.fromisoformat(d.generado_utc).astimezone(ZoneInfo(zona)).strftime("%Y-%m-%d %H:%M")
    except (ValueError, KeyError):
        fecha = d.generado_utc
    pdf.parrafo(f"Generado el {fecha} ({zona}).", 9)
    pdf.ln(4)
    pdf.set_fill_color(250, 240, 230)
    pdf.set_font("DejaVu", "", 9)
    pdf.set_text_color(90, 60, 20)
    pdf.multi_cell(0, 5, "Aviso: el catálogo de Paddock Global es una selección didáctica, no un calendario oficial ni "
                         "un ranking. Las cifras reflejan solo las opiniones registradas en la app, no la opinión "
                         "mundial. La clasificación la hizo un modelo de lenguaje y describe lo que expresó cada "
                         "aficionado, no la calidad objetiva de la carrera.", fill=True, new_x="LMARGIN", new_y="NEXT")

    # ---------------- KPIs
    pdf.subtitulo("Indicadores")
    idx = indice_percepcion(e.conteo)
    kpis = [("Opiniones", str(e.total)), ("Índice de percepción", f"{idx:+.2f}" if idx is not None else "—")]
    kpis += [(NOMBRE[s], f"{e.conteo[s]} ({e.porcentajes[s]:.0f} %)") for s in SENTIMIENTOS]
    pdf.set_font("DejaVu", "", 10)
    for etiqueta, valor in kpis:
        pdf.set_text_color(90, 90, 90)
        pdf.cell(60, 6.5, etiqueta)
        pdf.set_text_color(20, 20, 20)
        pdf.set_font("DejaVu", "B", 10)
        pdf.cell(0, 6.5, valor, new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("DejaVu", "", 10)
    pdf.parrafo("Índice = (positivas − negativas) / total, entre −1 y +1.", 8)

    # ---------------- gráfico de barras vectorial
    pdf.subtitulo("Distribución por sentimiento")
    maximo = max(e.conteo.values()) or 1
    ancho_max = 110
    for s in SENTIMIENTOS:
        y = pdf.get_y()
        pdf.set_font("DejaVu", "", 10)
        pdf.set_text_color(40, 40, 40)
        pdf.cell(28, 7, NOMBRE[s])
        pdf.set_fill_color(*_rgb(COLOR_SENTIMIENTO[s]))
        largo = ancho_max * e.conteo[s] / maximo
        if largo > 0:
            pdf.rect(pdf.l_margin + 30, y + 1.2, largo, 4.6, style="F")
        pdf.set_xy(pdf.l_margin + 32 + largo, y)
        pdf.cell(0, 7, str(e.conteo[s]), new_x="LMARGIN", new_y="NEXT")

    # ---------------- aspectos (tabla)
    filas_asp = [(a, c) for a, c in e.aspectos.items() if sum(c.values())]
    if filas_asp:
        pdf.subtitulo("Aspectos valorados")
        pdf.set_font("DejaVu", "B", 9)
        for cab, w in (("Aspecto", 60), ("Positivo", 30), ("Negativo", 30), ("Neutro", 30)):
            pdf.cell(w, 7, cab, border="B")
        pdf.ln()
        pdf.set_font("DejaVu", "", 9)
        for a, c in sorted(filas_asp, key=lambda x: -sum(x[1].values())):
            pdf.cell(60, 6, ASPECTO.get(a, a))
            for s in ("positivo", "negativo", "neutro"):
                pdf.cell(30, 6, str(c[s]))
            pdf.ln()

    # ---------------- resumen de comunidad
    pdf.subtitulo("¿Qué opina la comunidad?")
    if d.resumen is not None:
        pdf.parrafo(d.resumen.texto)
        pdf.parrafo(f"Resumen generado con {d.resumen.modelo} a partir de {d.resumen.n_opiniones} opiniones.", 8)
    else:
        pdf.parrafo("Todavía no se ha generado un resumen para esta carrera.", 9)

    # ---------------- muestra de opiniones
    pdf.subtitulo("Muestra de opiniones por categoría")
    for s in SENTIMIENTOS:
        pdf.set_font("DejaVu", "B", 10)
        pdf.set_text_color(*_rgb(COLOR_SENTIMIENTO[s]))
        pdf.cell(0, 7, NOMBRE[s], new_x="LMARGIN", new_y="NEXT")
        if not d.muestras.get(s):
            pdf.parrafo("Sin opiniones en esta categoría.", 9)
        for o in d.muestras.get(s, []):
            pdf.parrafo(f"«{o.opinion_original}»", 9.5)
            pdf.set_font("DejaVu", "", 8)
            pdf.set_text_color(110, 110, 110)
            pdf.multi_cell(0, 4.5, f"Razón del modelo: {o.razon}", new_x="LMARGIN", new_y="NEXT")
            pdf.ln(1.5)
    return bytes(pdf.output())
