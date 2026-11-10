# Registro de pruebas · resumen

Índice de todas las ejecuciones reales. Los detalles (entrada, salida, razón del modelo y explicación de cada discrepancia) están en cada archivo.

## v1 · prompt 1.0 · 2026-11-10

### Pruebas automáticas

`pytest` (sin LLM real): ver la salida en el [README](../README.md#9-pruebas).

### Aceptación de clasificación (17 casos, §10.2)

| Proveedor y modelo | Coinciden | Discrepancias principales | Evidencia |
| --- | --- | --- | --- |
| Ollama · `qwen2.5:3b` | **8/17** | Mixto (×2) → negativo; ironía (×2) → positivo/neutro; descripción → no pertinente; jerga F1 → positivo; rally raid → neutro; otra carrera → positivo; **inyección con delimitador → positivo** | [registro_pruebas_ollama_1.0.md](registro_pruebas_ollama_1.0.md) |
| Gemini · `gemini-3.5-flash-lite`¹ | **17/17** (×3 ejecuciones) | Ninguna | [registro_pruebas_gemini_1.0.md](registro_pruebas_gemini_1.0.md) |
| Gemini · `gemini-2.5-flash-lite`¹ | 12/13 respondidos (+1 parcial) | Ironía sin mencionarla en la razón; 4 casos sin respuesta por cuota o tiempo de espera | Anotado en el registro de Gemini |

¹ La cuota gratuita de `gemini-2.5-flash` (20 solicitudes al día por modelo) se agotó con la siembra; ver las salvedades en el registro de Gemini.

### Operación (automatizada con adaptadores reales, en copias temporales)

12/12: entrada vacía y corta sin llamar al modelo; Ollama apagado; modelo ausente (con `ollama pull`); clave de Gemini inválida (sin mostrar la clave); cuota simulada; persistencia; conservación; cambio de carrera; reejecución sin duplicar; archivo dañado conservado byte a byte; archivo de solo lectura sin confirmación y sin `.tmp` huérfanos. Detalle en [registro_pruebas_ollama_1.0.md](registro_pruebas_ollama_1.0.md#operación-automatizada-con-adaptadores-reales-y-copias-temporales).

### Interfaz (AppTest de Streamlit y capturas)

`tests/aceptacion/test_interfaz.py` comprueba con la app real (y `ClasificadorFalso`): selector por defecto y sin selectores de personalidad/modelo/temperatura, entrada vacía y corta, confirmación solo tras guardar, persistencia tras «reinicio», cambio de carrera, no pertinente sin guardar, «Nueva conversación» con el archivo intacto, archivo dañado, XSS mostrado como texto, filtros y recuentos coherentes, y que reejecutar no duplica.

Capturas reales (app con `qwen2.5:3b`):

- [Opinión emitida y guardada desde la interfaz](capturas/v1_emitir_guardada.png)
- [Consulta tras reiniciar Streamlit: el registro sigue ahí](capturas/v1_persistencia_tras_reinicio.png)
- [Consulta filtrada por 24 Horas de Le Mans](capturas/v1_consulta_filtrada_lemans.png)

### Siembra de datos

| Ejecución | Coinciden con lo esperado | Notas | Evidencia |
| --- | --- | --- | --- |
| `qwen2.5:3b`, 24 opiniones + 2 de reserva | 17/26 | **0/10 mixtas** (4 negativo, 4 positivo, 2 neutro); 1 neutra → no pertinente (no se guardó) | [siembra_ollama_1.0.md](siembra_ollama_1.0.md) |
| Gemini `gemini-2.5-flash`, solo mixtas (`--categoria mixto`) | 8/8 | Se añadieron porque faltaba la categoría; los registros de qwen **no** se editaron | [siembra_gemini_1.0_mixto.md](siembra_gemini_1.0_mixto.md) |

**Resultado en `datos/opiniones.json`:** 33 registros de siembra + 1 emitido desde la interfaz, en 8 eventos y 6 disciplinas: positivo 10, negativo 9, neutro 7 y mixto 8. Cumple los mínimos (≥12 registros, ≥4 eventos, las 4 categorías). Algunas opiniones mixtas aparecen dos veces con etiquetas distintas (qwen: positivo/neutro/negativo; Gemini: mixto). Es deliberado y sirve como comparación: cada registro guarda su `modelo`.

### Discrepancias de la siembra (no se corrigieron en los registros)

- «Vi la carrera completa desde la curva de Arnage con dos amigos» (esperado neutro) → no pertinente: no se guardó.
- Mixtas de qwen: Le Mans, Daytona 500 y Bathurst → positivo; Finlandia, MotoGP Italia y Monza → negativo; Mónaco y Dakar → neutro (con una razón que menciona el elogio y la crítica).
- Análisis completo en la [reflexión](reflexion.md).

## v2 · prompt 2.0 · 2026-11-10

### Aceptación de clasificación

| Proveedor y modelo | Coinciden | Notas | Evidencia |
| --- | --- | --- | --- |
| Ollama · `qwen2.5:3b` | **9/17** | La inyección con delimitador ya **no** funciona (neutralización de `<opinion>`); los campos de v2 quedan vacíos | [registro_pruebas_ollama_2.0.md](registro_pruebas_ollama_2.0.md) |
| Gemini · `gemini-3.5-flash-lite` | **17/17** | Aspectos coherentes; `ironia=true` en los dos casos irónicos | [registro_pruebas_gemini_2.0.md](registro_pruebas_gemini_2.0.md) |

Comparación caso por caso: [comparacion_prompt_1.0_vs_2.0.md](comparacion_prompt_1.0_vs_2.0.md).

### Base de datos y Docker

- `alembic upgrade head` / `downgrade base` / `upgrade head` y `alembic check` sin diferencias (SQLite).
- Migración JSON → BD: 34 importadas; repetida: 0 importadas, 34 omitidas.
- Siembra en SQL con Gemini y el prompt 2.0: 21/24 coinciden; 3 `ProveedorNoDisponibleError` (tiempos de espera de Gemini) **no** se guardaron ([siembra_gemini_2.0_sql.md](siembra_gemini_2.0_sql.md)).
- Docker Desktop 29.8: imagen construida; PostgreSQL 16 con `pg8000`; migraciones al arrancar; app sana en `127.0.0.1`; PostgreSQL sin puerto publicado; un usuario que persiste tras `docker compose restart`; clasificación desde el contenedor con el Ollama del equipo guardada en PostgreSQL. **Fallo encontrado y corregido:** con el paquete instalado en el venv de la imagen, la raíz del proyecto se calculaba desde `site-packages` y no encontraba `datos/` (ahora `PADDOCK_RAIZ=/app` y `PYTHONPATH`).

### Interfaz (AppTest, modo SQL)

Anónimo consulta pero no emite; inicio de sesión y opinión guardada con `usuario_id` y aspectos; mensaje genérico y bloqueo tras 5 intentos; un aficionado no ve «Administración» y la página la deniega igualmente; el admin ve sus 4 pestañas; el dashboard y el comparador cargan; cerrar sesión limpia el estado. Capturas: [dashboard](capturas/v2_dashboard.png), [administración tras un inicio de sesión real](capturas/v2_administracion.png).

## v3 · 2026-11-10

- Tests automáticos: moderación, calidad, lotes (reprocesar no duplica; una fila con error no detiene el lote; pausa por el tope diario), resúmenes (mínimo, caché, límite y map-reduce en grupos de 30), PDF con tildes, API (401 sin token o revocado, 422, 429, filtros, paginación y error 500 sin traza) y páginas de v3 con AppTest.
- Resumen real con `gemini-3.5-flash-lite` (Le Mans, 8 opiniones) e [informe PDF de ejemplo](informe_ejemplo_lemans.pdf).
- Docker: API (401/201), lote procesado por el `worker` (2 guardadas, 1 no pertinente; la fila 1, positiva, salió *neutro* con `qwen2.5:3b`), respaldo y restauración de PostgreSQL.
- `scripts/evaluar.py`: sin revisiones humanas todavía, termina avisando que hacen falta. **No se inventaron etiquetas humanas.**
- Capturas: [mapa](capturas/v3_mapa.png), [moderación](capturas/v3_moderacion.png).
