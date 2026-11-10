# Siembra de datos ficticios

Modelo: `ollama/qwen2.5:3b` · prompt v1.1 · 2026-11-09 21:27

| Carrera | Opinión | Esperado | Obtenido | Razón del modelo | ¿Coincide? |
|---|---|---|---|---|---|
| 24 Horas de Le Mans | Ver amanecer en la Sarthe con los coches todavía a fondo me puso la piel de gallina | positivo | positivo | El aficionado describe emocionadamente el espectáculo del amanecer en la Sarthe, lo que valora positivamente la carrera. | ✅ |
| 24 Horas de Le Mans | La entrada era carísima y desde la tribuna casi no se veía la pista | negativo | negativo | El aficionado critica la entrada carísima y la mala visibilidad desde la tribuna, lo que indica un sentimiento negativo sobre la experiencia del evento. | ✅ |
| 24 Horas de Le Mans | Este año la largada fue a las cuatro de la tarde, hora local | neutro | neutro | El aficionado solo describe la hora de la largada sin valorar positivamente o negativamente la carrera. | ✅ |
| 24 Horas de Le Mans | La pelea por la victoria fue apasionante, pero los cortes de la transmisión fueron constantes | mixto | mixto | El aficionado menciona que la pelea por la victoria fue apasionante, pero también critica constantes cortes de la transmisión. | ✅ |
| 24 Horas de Nürburgring | Los aficionados acampando en el bosque crean un ambiente único en el mundo | positivo | neutro | El aficionado describe un hecho sin valorar, los aficionados acampando en el bosque crean un ambiente único en el mundo. | ❌ |
| 24 Horas de Nürburgring | La organización fue un desastre: horas de bandera roja sin información para el público | negativo | negativo | La opinión expresa críticas específicas sobre la organización, utilizando palabras como 'desastre' y 'horas de bandera roja sin información para el público'. | ✅ |
| 24 Horas de Nürburgring | La vuelta combina el trazado de Gran Premio con el Nordschleife | neutro | neutro | El aficionado describe la combinación de trazados sin valorar positivamente ni negativamente la carrera. | ✅ |
| 24 Horas de Nürburgring | El Nordschleife es una maravilla, aunque la niebla dejó la carrera detenida casi toda la noche | mixto | neutro | El aficionado describe la maravilla del Nordschleife, pero menciona que la niebla detuvo la carrera, lo que es un hecho desfavorable. | ❌ |
| 24 Horas de Daytona | Los peraltes de noche con los prototipos a toda velocidad son un espectáculo increíble | positivo | positivo | El aficionado valora el espectáculo increíble causado por los peraltes de noche con prototipos a toda velocidad. | ✅ |
| 24 Horas de Daytona | Me aburrí muchísimo, fue una procesión con demasiadas neutralizaciones | negativo | negativo | El aficionado describe aburrimiento y muchas neutralizaciones, lo que indica una crítica a la carrera. | ✅ |
| 24 Horas de Daytona | La carrera se disputa a finales de enero y abre la temporada | neutro | no pertinente | El aficionado solo describe la fecha de la carrera sin valorarla, lo que no implica ni crítica ni elogio. | ❌ |
| 24 Horas de Daytona | Me encantó la variedad de categorías, pero el tráfico en pista causó accidentes absurdos | mixto | mixto | El aficionado menciona la variedad de categorías como un elogio, pero critica el tráfico en pista como una crítica. | ✅ |
| 24 Horas de Spa | Ver a los GT3 subir Eau Rouge bajo la lluvia es lo más emocionante que he visto | positivo | positivo | El aficionado valora emocionantemente ver a los GT3 subir Eau Rouge bajo la lluvia. | ✅ |
| 24 Horas de Spa | El BoP arruinó la competencia, ganó el que mejor negoció con los comisarios | negativo | negativo | El aficionado critica el BoP y dice que arruinó la competencia, lo que indica una crítica negativa. | ✅ |
| 24 Horas de Spa | La carrera reúne a más de cincuenta coches de la categoría GT3 | neutro | neutro | El aficionado solo describe la cantidad de coches participantes sin valorar positivamente o negativamente la carrera. | ✅ |
| 24 Horas de Spa | El circuito es precioso, lástima que los atascos para salir del parking duraron horas | mixto | negativo | El aficionado critica los atascos para salir del parking, lo que es negativo. | ❌ |

**Aciertos:** 12/16. Los registros se guardaron con la clasificación del modelo, sin corregirla a mano.

**Archivo final:** 15 registros, 4 carreras, conteo {'positivo': 3, 'negativo': 5, 'neutro': 5, 'mixto': 2}.
