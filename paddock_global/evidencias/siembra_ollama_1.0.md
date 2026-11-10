# Siembra de datos · ollama/qwen2.5:3b · prompt 1.0

Ejecutado el 2026-11-10 09:38 con `scripts/sembrar_datos.py`. Cada opinión pasó por el clasificador real; las discrepancias **no** se corrigieron en los registros.

| Fase | Carrera | Opinión | Esperado | Obtenido | ¿Coincide? | Estado | Razón del modelo | Tiempo |
|---|---|---|---|---|---|---|---|---|
| principal | 24 Horas de Le Mans | El ambiente del camping y los fuegos artificiales del sábado me encantaron | positivo | positivo | ✅ | guardada | El aficionado expresa una opinión positiva sobre el ambiente del camping y los fuegos artificiales del sábado. | 8.2 s |
| principal | 24 Horas de Le Mans | Las colas para salir del aparcamiento duraron tres horas, una organización pésima | negativo | negativo | ✅ | guardada | Expresa críticas a la organización y espera que se mejore, lo que justifica la categoría negativa | 4.4 s |
| principal | 24 Horas de Le Mans | Vi la carrera completa desde la curva de Arnage con dos amigos | neutro | no pertinente | ❌ | no pertinente | El aficionado solo menciona que vio la carrera completa desde una curva, sin expresar opinión sobre la carrera. | 4.5 s |
| principal | 24 Horas de Le Mans | La pelea por la victoria fue apasionante, aunque las entradas estaban carísimas | mixto | positivo | ❌ | guardada | Expresa admiración por la pelea por la victoria, lo que es positivo | 3.5 s |
| principal | Gran Premio de Mónaco | Ver los coches rozar los muros en la Piscina es un espectáculo único | positivo | positivo | ✅ | guardada | El aficionado valoró positivamente la espectacularidad de ver los coches rozar los muros en la Piscina | 4.2 s |
| principal | Gran Premio de Mónaco | Una carrera soporífera, nadie pudo adelantar en toda la tarde | negativo | negativo | ✅ | guardada | Expresa una opinión negativa sobre la carrera, sin mencionar aspectos positivos o neutralizantes. | 4.8 s |
| principal | Gran Premio de Mónaco | El circuito pasa por el túnel y luego baja hacia la chicane del puerto | neutro | neutro | ✅ | guardada | El aficionado describe el trazado del circuito sin valorar positivamente ni negativamente, simplemente describe la existencia del túnel y la chicane del puerto. | 6.0 s |
| principal | Gran Premio de Mónaco | El escenario del puerto es una joya, lástima que todo se decidiera con la estrategia en boxes | mixto | neutro | ❌ | guardada | El aficionado describe positivamente el escenario del puerto como una 'joya', pero termina con una crítica sobre la estrategia en boxes que da un tono neutro a la opinión | 5.6 s |
| principal | Rally de Finlandia | Los bosques y los saltos hacen de este rally el más espectacular del calendario | positivo | positivo | ✅ | guardada | El aficionado valoró positivamente la naturaleza y los saltos del trazado, considerándolo el más espectacular del calendario. | 6.5 s |
| principal | Rally de Finlandia | Pasé horas en el barro esperando y cancelaron la especial sin avisar, qué desastre | negativo | negativo | ✅ | guardada | Expresa decepción por la cancelación sin aviso de la especial y la espera en condiciones adversas. | 5.3 s |
| principal | Rally de Finlandia | Los tramos son de tierra rápida y atraviesan zonas de lagos | neutro | neutro | ✅ | guardada | Expresa que los tramos son de tierra rápida y atraviesan zonas de lagos, describiendo la naturaleza del trazado sin valorar positivamente o negativamente. | 6.9 s |
| principal | Rally de Finlandia | Los saltos fueron brutales, pero la señal de la transmisión se perdía cada dos minutos | mixto | negativo | ❌ | guardada | El aficionado critica la calidad de la señal de la transmisión, lo que reduce su experiencia de la carrera. | 4.8 s |
| principal | Daytona 500 | El final con tres coches lado a lado en el banking me dejó sin aliento | positivo | positivo | ✅ | guardada | El aficionado describe emocionadamente el final de la carrera con tres coches en el banking, lo que sugiere una experiencia emocionante y atractiva. | 5.6 s |
| principal | Daytona 500 | Demasiadas cautions, la carrera se hizo eterna y aburrida | negativo | negativo | ✅ | guardada | Expresa críticas a la cantidad de caution y describe la carrera como aburrida. | 4.4 s |
| principal | Daytona 500 | La carrera se divide en stages y al final puede haber un green-white-checkered | neutro | neutro | ✅ | guardada | Explica que la carrera está dividida en etapas y termina con un checkered, sin emitir opinión sobre el contenido o la calidad de la carrera. | 6.0 s |
| principal | Daytona 500 | La emoción del rebufo es increíble, aunque el Big One acabó con medio pelotón | mixto | positivo | ❌ | guardada | El aficionado valoró positivamente la emoción del rebufo, que consideró increíble. | 5.4 s |
| principal | Rally Dakar | Las imágenes de las dunas al amanecer son lo más bonito que he visto en un rally | positivo | positivo | ✅ | guardada | Expresa admiración por las imágenes de dunas al amanecer | 5.3 s |
| principal | Rally Dakar | La navegación fue un caos y la organización nunca explicó las penalizaciones | negativo | negativo | ✅ | guardada | Expresa críticas sobre la navegación y la falta de explicación de penalizaciones por parte de la organización | 5.1 s |
| principal | Rally Dakar | Cada etapa termina en un bivac donde los equipos reparan los vehículos | neutro | neutro | ✅ | guardada | Expresa una información sobre la carrera sin valorarla positivamente o negativamente. | 4.5 s |
| principal | Rally Dakar | Los paisajes son impresionantes, pero los resúmenes de televisión duraban apenas cinco minutos | mixto | neutro | ❌ | guardada | El aficionado describe los paisajes como impresionantes, pero critica la brevedad de los resúmenes de televisión. | 4.6 s |
| principal | Gran Premio de Italia (MotoGP) | Mugello lleno de banderas amarillas y la afición cantando es algo que todo motero debe vivir | positivo | positivo | ✅ | guardada | El aficionado valoró positivamente la experiencia de Mugello con banderas amarillas y el ambiente de la afición. | 4.6 s |
| principal | Gran Premio de Italia (MotoGP) | Una caída en la primera curva arruinó la carrera y el resto no tuvo ninguna emoción | negativo | negativo | ✅ | guardada | Expresa una caída que arruinó la carrera y no hay ninguna emoción destacada | 4.8 s |
| principal | Gran Premio de Italia (MotoGP) | La recta principal es larga y termina en una frenada fuerte antes de la primera curva | neutro | neutro | ✅ | guardada | El aficionado describe la longitud de la recta principal sin valorarla positivamente o negativamente. | 5.7 s |
| principal | Gran Premio de Italia (MotoGP) | El adelantamiento de la última vuelta fue de película, pero la long lap penalty fue injusta | mixto | negativo | ❌ | guardada | El aficionado critica la long lap penalty injusta, lo que indica una opinión negativa sobre la carrera. | 4.9 s |
| reserva (mixto) | Gran Premio de Italia | El público de Monza es único, pero la salida de los aficionados fue un caos | mixto | negativo | ❌ | guardada | El aficionado critica la salida de los aficionados, lo que es negativo | 3.6 s |
| reserva (mixto) | 12 Horas de Bathurst | La bajada de la montaña es impresionante, aunque hubo demasiados coches de seguridad | mixto | positivo | ❌ | guardada | El aficionado valoró positivamente la bajada de la montaña, lo que clasifica como positivo. | 4.0 s |

**Coinciden:** 17/26.

## Comprobación de mínimos (registros con origen «semilla»)

- Registros guardados: **25** (mínimo 12)
- Eventos distintos: **8** (mínimo 4)
- Por categoría: {'positivo': 9, 'negativo': 9, 'neutro': 7}
- Resultado: ❌ no cumple

## Intentos con opiniones de reserva

- Faltaba «mixto»: «El público de Monza es único, pero la salida de los aficionados fue un caos» → negativo
- Faltaba «mixto»: «La bajada de la montaña es impresionante, aunque hubo demasiados coches de seguridad» → positivo
