# Siembra de datos ficticios

Modelo: `ollama/qwen2.5:3b` · prompt v2.1 · 2026-11-10 07:04

| Carrera | Opinión | Esperado | Obtenido | Razón del modelo | ¿Coincide? |
|---|---|---|---|---|---|
| 24 Horas de Le Mans | Ver amanecer en la Sarthe con los coches todavía a fondo me puso la piel de gallina | positivo | positivo | El aficionado expresa una valoración favorable al ver el amanecer en la Sarthe con los coches todavía a fondo, lo que lo puso la piel de gallina. | ✅ |
| 24 Horas de Le Mans | La entrada era carísima y desde la tribuna casi no se veía la pista | negativo | negativo | El aficionado critica la calidad de la transmisión desde la tribuna debido a la elevada entrada, lo que indica una percepción negativa de la experiencia en general. | ✅ |
| 24 Horas de Le Mans | Este año la largada fue a las cuatro de la tarde, hora local | neutro | no pertinente | La hora de la largada no tiene impacto sobre el sentimiento general de la carrera y solo proporciona información factual. | ❌ |
| 24 Horas de Le Mans | La pelea por la victoria fue apasionante, pero los cortes de la transmisión fueron constantes | mixto | mixto | El aficionado valora positivamente la pelea por la victoria, pero critica constantemente los cortes de la transmisión. | ✅ |
| 24 Horas de Nürburgring | Los aficionados acampando en el bosque crean un ambiente único en el mundo | positivo | neutro | El aficionado describe el ambiente creado por los aficionados acampando, pero no valora positivamente ni negativamente la carrera en sí. | ❌ |
| 24 Horas de Nürburgring | La organización fue un desastre: horas de bandera roja sin información para el público | negativo | negativo | La opinión expresa críticas específicas sobre la organización, señalando que hubo bandera roja sin información para el público, lo que indica un desastre en la organización. | ✅ |
| 24 Horas de Nürburgring | La vuelta combina el trazado de Gran Premio con el Nordschleife | neutro | neutro | El aficionado solo describe la combinación de trazados sin valorar ni elogiar ni criticar la carrera en sí. | ✅ |
| 24 Horas de Nürburgring | El Nordschleife es una maravilla, aunque la niebla dejó la carrera detenida casi toda la noche | mixto | mixto | El aficionado valora positivamente el Nordschleife pero critica negativamente la niebla que detuvo la carrera casi toda la noche. | ✅ |
| 24 Horas de Daytona | Los peraltes de noche con los prototipos a toda velocidad son un espectáculo increíble | positivo | positivo | El aficionado valora positivamente la velocidad y espectacularidad de los prototipos en los peraltes de noche. | ✅ |
| 24 Horas de Daytona | Me aburrí muchísimo, fue una procesión con demasiadas neutralizaciones | negativo | negativo | El aficionado describe aburrimiento y muchas neutralizaciones, lo que indica una opinión negativa sobre la carrera. | ✅ |
| 24 Horas de Daytona | La carrera se disputa a finales de enero y abre la temporada | neutro | no pertinente | La opinión no habla sobre la carrera seleccionada ni expresa valoraciones sobre ella. Se limita a informar sobre la fecha de la carrera. | ❌ |
| 24 Horas de Daytona | Me encantó la variedad de categorías, pero el tráfico en pista causó accidentes absurdos | mixto | mixto | El aficionado valoró positivamente la variedad de categorías pero criticó el tráfico en pista, que causó accidentes absurdos. | ✅ |
| 24 Horas de Spa | Ver a los GT3 subir Eau Rouge bajo la lluvia es lo más emocionante que he visto | positivo | positivo | El aficionado valora emocionantemente ver a los GT3 subir Eau Rouge bajo la lluvia. | ✅ |
| 24 Horas de Spa | El BoP arruinó la competencia, ganó el que mejor negoció con los comisarios | negativo | negativo | El aficionado critica el BoP y la gestión de los comisarios, lo que arruinó la competencia. | ✅ |
| 24 Horas de Spa | La carrera reúne a más de cincuenta coches de la categoría GT3 | neutro | neutro | La opinión solo menciona la cantidad de coches participantes sin valorar la carrera en sí. | ✅ |
| 24 Horas de Spa | El circuito es precioso, lástima que los atascos para salir del parking duraron horas | mixto | negativo | El aficionado critica los atascos para salir del parking, lo que le resta positividad a la carrera. | ❌ |
| 24 Horas de Le Mans | The atmosphere at Le Mans during the night is something every fan should experience | positivo | neutro | El aficionado describe la atmósfera durante la noche en Le Mans sin valorarla positivamente o negativamente. | ❌ |
| 24 Horas de Daytona | La course était interminable, trop de drapeaux jaunes et aucun suspense | negativo | negativo | El aficionado describe la carrera como interminable y sin suspense debido a demasiadas banderas amarillas, lo que indica una crítica desfavorable. | ✅ |
| 24 Horas de Nürburgring | Das Rennen führt über die Nordschleife und die Grand-Prix-Strecke | neutro | no pertinente | La opinión solo menciona las trazas utilizadas en la carrera, sin valorarlas ni dar opinión sobre la carrera en sí. | ❌ |
| 24 Horas de Spa | A subida da Eau Rouge é sensacional, mas a chuva atrapalhou demais a corrida | mixto | negativo | El aficionado valoró positivamente la subida de Eau Rouge pero criticó la lluvia que afectó significativamente a la carrera. | ❌ |

**Aciertos:** 13/20. Los registros se guardaron con la clasificación del modelo, sin corregirla a mano.

**Archivo final:** 17 registros, 4 carreras, conteo {'positivo': 3, 'negativo': 7, 'neutro': 4, 'mixto': 3}.
