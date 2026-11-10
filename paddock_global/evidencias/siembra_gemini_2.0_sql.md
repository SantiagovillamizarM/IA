# Siembra de datos · gemini/gemini-3.5-flash-lite · prompt 2.0

Ejecutado el 2026-11-10 10:53 con `scripts/sembrar_datos.py`. Cada opinión pasó por el clasificador real; las discrepancias **no** se corrigieron en los registros.

| Fase | Carrera | Opinión | Esperado | Obtenido | ¿Coincide? | Estado | Razón del modelo | Tiempo |
|---|---|---|---|---|---|---|---|---|
| principal | 24 Horas de Le Mans | El ambiente del camping y los fuegos artificiales del sábado me encantaron | positivo | positivo | ✅ | guardada | El aficionado expresa su agrado y entusiasmo hacia el ambiente del camping y los fuegos artificiales de la carrera. | 2.9 s |
| principal | 24 Horas de Le Mans | Las colas para salir del aparcamiento duraron tres horas, una organización pésima | negativo | negativo | ✅ | guardada | El aficionado critica duramente la organización debido al tiempo excesivo de espera en el aparcamiento. | 8.2 s |
| principal | 24 Horas de Le Mans | Vi la carrera completa desde la curva de Arnage con dos amigos | neutro | neutro | ✅ | guardada | El aficionado describe objetivamente su experiencia de ver la carrera completa en una ubicación específica sin emitir juicios de valor. | 6.9 s |
| principal | 24 Horas de Le Mans | La pelea por la victoria fue apasionante, aunque las entradas estaban carísimas | mixto | mixto | ✅ | guardada | El aficionado elogia la lucha por la victoria, pero critica el precio elevado de las entradas. | 4.7 s |
| principal | Gran Premio de Mónaco | Ver los coches rozar los muros en la Piscina es un espectáculo único | positivo | positivo | ✅ | guardada | El aficionado elogia el espectáculo único de los coches rozando los muros en una zona emblemática del circuito. | 1.6 s |
| principal | Gran Premio de Mónaco | Una carrera soporífera, nadie pudo adelantar en toda la tarde | negativo | negativo | ✅ | guardada | El aficionado califica la carrera como soporífera y critica la falta de adelantamientos durante toda la tarde. | 10.6 s |
| principal | Gran Premio de Mónaco | El circuito pasa por el túnel y luego baja hacia la chicane del puerto | neutro | neutro | ✅ | guardada | El aficionado describe de forma objetiva partes del circuito sin emitir ninguna valoración positiva o negativa. | 1.3 s |
| principal | Gran Premio de Mónaco | El escenario del puerto es una joya, lástima que todo se decidiera con la estrategia en boxes | mixto | error (ProveedorNoDisponibleError) | ❌ | no guardada | Gemini no responde. Intenta más tarde. | 4.3 s |
| principal | Rally de Finlandia | Los bosques y los saltos hacen de este rally el más espectacular del calendario | positivo | positivo | ✅ | guardada | El aficionado elogia el trazado del rally destacando los bosques y los saltos como elementos muy espectaculares. | 1.1 s |
| principal | Rally de Finlandia | Pasé horas en el barro esperando y cancelaron la especial sin avisar, qué desastre | negativo | negativo | ✅ | guardada | El aficionado expresa su enojo y decepción porque pasó horas esperando en el barro y cancelaron la especial sin previo aviso. | 1.9 s |
| principal | Rally de Finlandia | Los tramos son de tierra rápida y atraviesan zonas de lagos | neutro | neutro | ✅ | guardada | El aficionado describe de forma puramente informativa las características del trazado sin emitir ninguna valoración positiva o negativa. | 3.2 s |
| principal | Rally de Finlandia | Los saltos fueron brutales, pero la señal de la transmisión se perdía cada dos minutos | mixto | mixto | ✅ | guardada | El aficionado elogia los saltos del tramo pero critica fuertemente las fallas en la señal de la transmisión. | 8.0 s |
| principal | Daytona 500 | El final con tres coches lado a lado en el banking me dejó sin aliento | positivo | positivo | ✅ | guardada | El aficionado expresa una gran emoción y admiración por el final de la carrera utilizando expresiones positivas sobre el banking y la lucha en pista. | 2.5 s |
| principal | Daytona 500 | Demasiadas cautions, la carrera se hizo eterna y aburrida | negativo | negativo | ✅ | guardada | El aficionado critica la cantidad de neutralizaciones y califica la carrera como eterna y aburrida. | 1.8 s |
| principal | Daytona 500 | La carrera se divide en stages y al final puede haber un green-white-checkered | neutro | neutro | ✅ | guardada | El aficionado describe de forma informativa y sin emitir juicios de valor aspectos del formato de competencia. | 10.9 s |
| principal | Daytona 500 | La emoción del rebufo es increíble, aunque el Big One acabó con medio pelotón | mixto | mixto | ✅ | guardada | El aficionado destaca positivamente la emoción del rebufo, pero expresa una crítica por el impacto del Big One sobre el pelotón. | 7.2 s |
| principal | Rally Dakar | Las imágenes de las dunas al amanecer son lo más bonito que he visto en un rally | positivo | positivo | ✅ | guardada | El aficionado elogia de forma clara y directa la belleza visual de las dunas durante el amanecer en la carrera. | 2.1 s |
| principal | Rally Dakar | La navegación fue un caos y la organización nunca explicó las penalizaciones | negativo | error (ProveedorNoDisponibleError) | ❌ | no guardada | Gemini no responde. Intenta más tarde. | 6.0 s |
| principal | Rally Dakar | Cada etapa termina en un bivac donde los equipos reparan los vehículos | neutro | neutro | ✅ | guardada | El aficionado describe una característica general sobre cómo terminan las etapas y el trabajo en el bivac sin emitir ninguna valoración. | 8.3 s |
| principal | Rally Dakar | Los paisajes son impresionantes, pero los resúmenes de televisión duraban apenas cinco minutos | mixto | mixto | ✅ | guardada | El aficionado elogia los paisajes de la carrera, pero critica la escasa duración de los resúmenes televisivos. | 1.5 s |
| principal | Gran Premio de Italia (MotoGP) | Mugello lleno de banderas amarillas y la afición cantando es algo que todo motero debe vivir | positivo | error (ProveedorNoDisponibleError) | ❌ | no guardada | Gemini no responde. Intenta más tarde. | 5.2 s |
| principal | Gran Premio de Italia (MotoGP) | Una caída en la primera curva arruinó la carrera y el resto no tuvo ninguna emoción | negativo | negativo | ✅ | guardada | El aficionado critica duramente la carrera al mencionar que una caída inicial la arruinó y que careció de emoción. | 19.6 s |
| principal | Gran Premio de Italia (MotoGP) | La recta principal es larga y termina en una frenada fuerte antes de la primera curva | neutro | neutro | ✅ | guardada | El aficionado describe de forma objetiva las características del trazado sin emitir una valoración positiva o negativa. | 9.9 s |
| principal | Gran Premio de Italia (MotoGP) | El adelantamiento de la última vuelta fue de película, pero la long lap penalty fue injusta | mixto | mixto | ✅ | guardada | El aficionado elogia el adelantamiento final, pero critica la sanción de long lap penalty como injusta. | 8.2 s |

**Coinciden:** 21/24.

## Comprobación de mínimos (registros con origen «semilla»)

- Registros guardados: **54** (mínimo 12)
- Eventos distintos: **8** (mínimo 4)
- Por categoría: {'mixto': 13, 'neutro': 13, 'negativo': 14, 'positivo': 14}
- Resultado: ✅ cumple
