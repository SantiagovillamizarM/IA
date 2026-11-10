# Comparación del prompt 1.0 (v1) y el 2.0 (v2)

Mismos 17 casos de aceptación, temperatura 0 configurada y ejecuciones reales del 2026-11-10.

| Caso | qwen2.5:3b · 1.0 | qwen2.5:3b · 2.0 | Gemini · 1.0 | Gemini · 2.0 |
| --- | --- | --- | --- | --- |
| Elogio | ✅ | ✅ | ✅ | ✅ |
| Crítica | ✅ | ✅ | ✅ | ✅ |
| Descripción | ❌ no pertinente | ❌ no pertinente | ✅ | ✅ |
| Mixto | ❌ negativo | ❌ negativo | ✅ | ✅ |
| Mixto F1 | ❌ negativo | ❌ negativo | ✅ | ✅ |
| Ironía | ❌ positivo | ❌ positivo | ✅ | ✅ (`ironia=true`) |
| Ironía MotoGP | ❌ neutro | ❌ neutro | ✅ | ✅ (`ironia=true`) |
| Jerga neutra | ✅ | ❌ no pertinente | ✅ | ✅ |
| Jerga F1 | ❌ positivo | ❌ positivo | ✅ | ✅ |
| Rally positivo | ✅ | ✅ | ✅ | ✅ |
| Rally raid negativo | ❌ neutro | ✅ | ✅ | ✅ |
| Comparación | ✅ | ✅ | ✅ | ✅ |
| Otra carrera | ❌ positivo | ❌ positivo | ✅ | ✅ |
| Otro idioma | ✅ | ✅ | ✅ | ✅ |
| Mensaje ajeno | ✅ | ✅ | ✅ | ✅ |
| Inyección | ✅ | ✅ | ✅ | ✅ |
| Inyección con delimitador | ❌ **positivo** | ✅ | ✅ | ✅ |
| **Total** | **8/17** | **9/17** | **17/17** | **17/17** |

Gemini: `gemini-3.5-flash-lite` (cuota diaria de `gemini-2.5-flash` agotada; ver el registro de Gemini 1.0).

## Conclusiones

1. **El cambio de mayor efecto no fue del prompt sino de seguridad**: neutralizar `<opinion>`/`</opinion>` en el texto antes de enviarlo cerró la inyección que funcionaba con el modelo pequeño.
2. **El prompt 2.0 no mejora la clasificación global de `qwen2.5:3b`** (+1 neto: gana el rally raid y pierde la jerga neutra) y el modelo **no rellena** los campos nuevos (aspectos vacíos, intensidad nula, ironía siempre falsa). Para el análisis por aspectos del dashboard hace falta Gemini.
3. **Gemini mantiene 17/17** y aporta aspectos coherentes con la etiqueta, por ejemplo el mixto con un aspecto positivo y otro negativo.
4. Los registros de v1 siguen siendo válidos: los campos nuevos quedan en `null` y cada registro conserva su `version_prompt`.
