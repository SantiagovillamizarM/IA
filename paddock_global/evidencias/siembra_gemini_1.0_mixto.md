# Siembra de datos · gemini/gemini-2.5-flash · prompt 1.0

Ejecutado el 2026-11-10 09:41 con `scripts/sembrar_datos.py`. Cada opinión pasó por el clasificador real; las discrepancias **no** se corrigieron en los registros.

| Fase | Carrera | Opinión | Esperado | Obtenido | ¿Coincide? | Estado | Razón del modelo | Tiempo |
|---|---|---|---|---|---|---|---|---|
| categoría mixto | 24 Horas de Le Mans | La pelea por la victoria fue apasionante, aunque las entradas estaban carísimas | mixto | mixto | ✅ | guardada | El aficionado valora positivamente la pelea por la victoria, pero critica el alto precio de las entradas al evento. | 3.2 s |
| categoría mixto | Gran Premio de Mónaco | El escenario del puerto es una joya, lástima que todo se decidiera con la estrategia en boxes | mixto | mixto | ✅ | guardada | El aficionado elogia el escenario del puerto, pero lamenta que la estrategia en boxes haya sido el factor decisivo de la carrera. | 2.0 s |
| categoría mixto | Rally de Finlandia | Los saltos fueron brutales, pero la señal de la transmisión se perdía cada dos minutos | mixto | mixto | ✅ | guardada | El aficionado elogia los saltos de la carrera, pero critica la mala calidad de la transmisión, lo que indica una valoración mixta. | 2.3 s |
| categoría mixto | Daytona 500 | La emoción del rebufo es increíble, aunque el Big One acabó con medio pelotón | mixto | mixto | ✅ | guardada | El aficionado valora positivamente la emoción del rebufo, pero también señala el impacto negativo de 'the Big One' en la carrera. | 2.1 s |
| categoría mixto | Rally Dakar | Los paisajes son impresionantes, pero los resúmenes de televisión duraban apenas cinco minutos | mixto | mixto | ✅ | guardada | El aficionado elogia los impresionantes paisajes de la carrera, pero critica la corta duración de los resúmenes televisivos. | 2.0 s |
| categoría mixto | Gran Premio de Italia (MotoGP) | El adelantamiento de la última vuelta fue de película, pero la long lap penalty fue injusta | mixto | mixto | ✅ | guardada | El aficionado elogia el adelantamiento de la última vuelta como 'de película', pero critica la long lap penalty, considerándola injusta. | 2.8 s |
| categoría mixto | Gran Premio de Italia | El público de Monza es único, pero la salida de los aficionados fue un caos | mixto | mixto | ✅ | guardada | El aficionado elogia al público de Monza, pero critica la organización de la salida de los aficionados, calificándola de caos. | 32.3 s |
| categoría mixto | 12 Horas de Bathurst | La bajada de la montaña es impresionante, aunque hubo demasiados coches de seguridad | mixto | mixto | ✅ | guardada | El aficionado elogia la bajada de la montaña, pero critica la cantidad de coches de seguridad durante la carrera. | 32.4 s |

**Coinciden:** 8/8.

## Comprobación de mínimos (registros con origen «semilla»)

- Registros guardados: **33** (mínimo 12)
- Eventos distintos: **8** (mínimo 4)
- Por categoría: {'mixto': 8, 'positivo': 9, 'negativo': 9, 'neutro': 7}
- Resultado: ✅ cumple
