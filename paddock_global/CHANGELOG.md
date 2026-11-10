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

## v2.0.0 · 2026-11-10 · Producto

- Persistencia SQL con SQLAlchemy 2 y Alembic (SQLite en desarrollo, PostgreSQL 16 en producción con `pg8000`). Tablas: catálogo, jerga, usuarios, opiniones (con la última revisión desnormalizada), revisiones, denuncias, trabajos de lote, resúmenes, auditoría, límites de uso, métricas del LLM y tokens de API. Tests de contrato idénticos para JSON y SQL.
- Scripts `sembrar_catalogo.py`, `migrar_json_a_bd.py` (idempotente) y `crear_admin.py` (contraseña con `getpass`).
- Cuentas con argon2id, política de contraseñas, mensaje genérico, bloqueo tras 5 intentos, caducidad de sesión y roles aficionado/moderador/admin comprobados en los casos de uso. «Mi cuenta» con exportación y baja (anonimiza) y «Privacidad» (Ley 1581 de 2012).
- Seguridad: neutralización de los delimitadores `<opinion>` (cierra la inyección hallada en v1), limitador persistente con tope diario global, auditoría con IP en hash y `SEGURIDAD.md` con la tabla riesgo → control → código → prueba. `enableCORS=true` con `allowedHosts`/`corsAllowedOrigins` por dominio (desviación documentada: en Streamlit 1.67 `enableCORS=false` abre CORS).
- Prompt 2.0 con `AnalisisDetallado` (aspectos, ironía, intensidad y entidades literales filtradas en código) y comparación real con el 1.0.
- Dashboard, comparador y administración con Plotly.
- Docker multietapa con usuario sin privilegios y `HEALTHCHECK`; `docker-compose.yml` (app, PostgreSQL y Ollama opcional, solo en 127.0.0.1) y `docker-compose.dev.yml`; configuración de nginx para Plesk; CI con ruff, mypy, cobertura ≥ 80 %, pip-audit y construcción de la imagen.

## v3.0.0 · 2026-11-10 · Plataforma

- Moderación con revisión humana: cola priorizada, confirmar o corregir con nota (historial completo, la etiqueta del modelo intacta), denuncias y ocultación sin borrado.
- Calidad del modelo: exactitud, precisión, recall, F1, matriz de confusión, latencia media y p95, errores por tipo, tokens, exportación del conjunto de evaluación y `scripts/evaluar.py` (reclasifica sin guardar).
- Lotes: validación completa del CSV, cola en `trabajos_lote`, worker en un contenedor aparte, ids `uuid5`, pausa ante el tope diario y progreso en vivo.
- Resúmenes de comunidad con map-reduce, caché y límite de regeneración.
- Mapa mundial con Plotly; informes PDF con fpdf2 y DejaVu Sans (barras vectoriales, sin kaleido).
- API REST FastAPI con tokens personales revocables, errores uniformes y documentación desactivable.
- `docker-compose.yml` con `api` y `worker`; `scripts/respaldo_bd.sh` (respaldo y restauración probados); `DESPLIEGUE.md`.
- Navegación expandida (`expanded=True`): con más de 10 páginas Streamlit ocultaba la sección «Gestión» tras «N more».
