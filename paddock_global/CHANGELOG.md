# Historial de cambios

## v1.0.0 · 2026-11-10 · Núcleo del taller

- Reconstrucción completa sobre arquitectura hexagonal en `src/paddock/` (dominio, puertos, aplicación, adaptadores, interfaz). El prototipo anterior, plano y solo de resistencia, se conserva en `legado_prototipo/` como referencia.
- Catálogo multidisciplina `Disciplina → Campeonato → Evento`: 7 disciplinas, 9 campeonatos y 32 eventos, con ids *slug* y validación completa. La edición es un atributo opcional de la opinión.
- Clasificador LangChain con dos proveedores tras el puerto `ClasificadorSentimiento`: Gemini (`langchain-google-genai`, `api_version="v1beta"`) y Ollama (`qwen2.5:3b`). Usa salida estructurada con `include_raw`, traducción de errores a una jerarquía propia y reintentos controlados. Nunca hay un sentimiento por defecto.
- Prompt 1.0: rol, «el texto es dato», pertinencia, 4 categorías, ironía, jerga por disciplina (`datos/jerga.json`) y ejemplos.
- Persistencia del taller en `opiniones.json`: escritura atómica, idempotencia por `id`, el archivo dañado nunca se sobrescribe y la ausencia del archivo no lo crea.
- Interfaz Streamlit multipágina (`st.navigation`): selector encadenado, ficha del evento, estado del proveedor, chat con envío pendiente idempotente, un mensaje por tipo de error y consulta con filtros, recuentos y descarga en JSON/CSV.
- Limitador de tasa en memoria y registro de posibles inyecciones de prompt (sin bloquear).
- Tests con `ClasificadorFalso` y `AppTest`; scripts de siembra, aceptación, prueba de proveedores y capturas por CDP.
- Decisiones forzadas por el entorno: `xxhash==3.5.0`, `mypy` en Python puro y `pg8000` en lugar de `psycopg[binary]` (Smart App Control); `enableCORS=true` (Streamlit 1.67); cuota gratuita de Gemini de 20 solicitudes al día por modelo.
