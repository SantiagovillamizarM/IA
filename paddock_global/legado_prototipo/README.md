# 🏁 Paddock Global — Análisis de sentimientos LangChain

Chatbot de Streamlit que registra opiniones de aficionados sobre **carreras de resistencia** (24 Horas de Le Mans, Nürburgring, Daytona y otras), clasifica su sentimiento con **LangChain** usando **modelos locales en Ollama o Gemini en la nube** (se eligen desde la app) y guarda los registros en JSON para consultarlos después de reiniciar.

Es una adaptación del taller «Percepción de futbolistas mediante un chatbot»: se cambia el tema (futbolistas → carreras) y el proveedor (OpenAI → Ollama local, sin API key).

> El catálogo es una **selección didáctica**, no un calendario oficial ni un ranking. La clasificación describe lo que expresó cada aficionado, no la calidad objetiva de la carrera, y las cifras solo representan las opiniones registradas en esta app.

## Requisitos

- Windows 10/11, Python 3.12
- [Ollama](https://ollama.com) con el modelo `qwen2.5:3b` (1,9 GB; cabe en GPUs de 3 GB y funciona también en CPU)
- Opcional: `llama3.2:3b` (2,0 GB), segundo modelo local
- Opcional: una clave de [Google AI Studio](https://aistudio.google.com/apikey) para usar Gemini (`GOOGLE_API_KEY` en `.env`)

## Instalación y ejecución

```powershell
cd C:\Users\Santiago\Desktop\IA\paddock_global
python -m venv .venv
.\.venv\Scripts\Activate.ps1   # si falla por ExecutionPolicy: Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
pip install -r requirements.txt
copy .env.example .env
ollama pull qwen2.5:3b
ollama pull llama3.2:3b        # opcional: segundo modelo para comparar
streamlit run app.py
```

La app abre en http://localhost:8501. La **primera** clasificación tarda alrededor de **1 minuto** porque Ollama carga el modelo en memoria; las siguientes, unos 5 segundos.

Otros comandos:

```powershell
python -m pytest -q                 # pruebas sin modelo (55)
python pruebas_aceptacion.py        # casos de clasificación contra Ollama → evidencias/
python prueba_interfaz.py           # pruebas de la interfaz (respalda y restaura opiniones.json)
python sembrar_datos.py             # añade opiniones ficticias usando el clasificador real
python sembrar_datos.py --reiniciar # hace copia de seguridad y empieza vacío
python comparar_modelos.py ollama:qwen2.5:3b gemini:gemini-3.5-flash   # compara 2 o más modelos → evidencias/
python pruebas_aceptacion.py gemini:gemini-3.5-flash   # casos del taller con otro modelo
python experimento_temperatura.py   # estabilidad de las etiquetas a temperatura 0, 0.5 y 1
```

## Configuración (`.env`)

```dotenv
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:3b
OLLAMA_TEMPERATURE=0
OLLAMA_MODEL_COMPARACION=llama3.2:3b
GOOGLE_API_KEY=tu_clave_de_google_ai_studio   # opcional, para Gemini
```

`OLLAMA_MODEL` y `OLLAMA_TEMPERATURE` son solo los valores **iniciales**: desde la barra lateral se cambian el modelo y la temperatura sin reiniciar. `OLLAMA_MODEL` acepta `qwen2.5:3b`, `ollama:qwen2.5:3b` o `gemini:gemini-3.5-flash`. **Nunca subas `.env` a un repositorio**: contiene tu clave de Google.

Para cambiar de modelo (por ejemplo `llama3.2:3b` o `qwen2.5:7b`), descárgalo con `ollama pull` y cambia `OLLAMA_MODEL`. El modelo debe soportar salida estructurada (JSON schema). La temperatura 0 reduce la variación, pero **no garantiza** resultados idénticos ni exactos.

## Versiones utilizadas

| Componente | Versión |
|---|---|
| Python | 3.12.10 |
| Ollama | 0.40.15 |
| Modelo principal | qwen2.5:3b |
| Modelo de comparación | llama3.2:3b |
| Modelos en la nube | gemini-3.5-flash, gemini-3.5-flash-lite |
| langchain-google-genai | 4.4.3 |
| google-genai | 3.0.0 |
| altair (gráficas, viene con Streamlit) | incluida |
| streamlit | 1.67.0 |
| langchain-core | 1.7.6 |
| langchain-ollama | 1.1.0 |
| ollama (cliente) | 0.6.3 |
| pydantic | 2.14.3 |
| python-dotenv | 1.2.4 |
| pandas | 3.1.1 |
| xxhash | 3.5.0 (fijada, ver «Problemas conocidos») |
| pytest | 9.2.0 |

La lista completa está en `versiones_instaladas.txt`.

## Arquitectura

| Archivo | Responsabilidad |
|---|---|
| `config.py` | Rutas absolutas (desde `Path(__file__)`) y lectura de `.env`. |
| `analisis.py` | `ChatPromptTemplate` (system + human), `ChatOllama`, esquema `AnalisisOpinion`, `validar_texto`, `validar_coherencia`, `analizar_opinion`, `verificar_ollama`. |
| `almacenamiento.py` | `cargar_carreras`, `cargar_opiniones`, `crear_registro`, `guardar_opinion` (escritura atómica e idempotente), `consultar_opiniones`, `contar_por_sentimiento`. |
| `app.py` | Barra lateral (carrera, sección, estado de Ollama) y enrutado a las secciones. |
| `ui/` | Una sección por archivo: `emitir.py`, `consultar.py`, `estadisticas.py`, `carga.py`, `comparar.py`; `comun.py` con colores, caché y gráficas. |
| `estadisticas.py` | Conteos para gráficas, ranking y aspectos (sin modelo). |
| `carga_masiva.py` | Lectura y validación de CSV, y procesamiento idempotente por lotes. |
| `evaluacion.py` | Métricas por idioma y categoría, kappa de Cohen y comparación de modelos. |
| `comparar_modelos.py` | Script que evalúa los dos modelos y escribe el informe. |
| `datos/carreras.json` | Catálogo de 20 carreras con `id` estable. |
| `datos/opiniones.json` | Registros persistentes. |
| `datos/conjunto_evaluacion.json` | 26 opiniones ficticias etiquetadas a mano en 5 idiomas (solo para evaluar). |
| `datos/ejemplo_carga.csv` | CSV de ejemplo para la carga masiva. |

```mermaid
flowchart LR
    U[Usuario escribe opinión] --> V{validar_texto<br/>5–1000 caracteres}
    V -- no --> E1[Aviso: entrada no válida<br/>sin LLM, sin guardar]
    V -- sí --> L[prompt | ChatOllama<br/>.with_structured_output]
    L -- error de conexión/modelo --> E2[Error visible, sin registro]
    L --> P{¿parsea y es coherente?}
    P -- no, tras 1 reintento --> E3[Error visible, sin registro]
    P -- no pertinente --> N[Aviso: no se guarda]
    P -- pertinente --> R[crear_registro<br/>UUID, fecha, carrera, metadatos]
    R --> G[guardar_opinion<br/>tmp + os.replace]
    G -- ok --> OK[✅ Opinión guardada]
    G -- error --> E4[❌ No se guardó]
```

**Puntos clave del diseño**

- El modelo solo produce `es_pertinente`, `sentimiento` y `razon`. El programa genera el `id` (UUID4), `fecha_utc`, la carrera y los metadatos (`modelo`, `version_prompt`).
- La carrera se **captura en el momento del envío** (copia del diccionario): cambiar el selector después no altera registros anteriores.
- El clasificador recibe **solo la opinión actual**, sin el historial del chat.
- Un fallo de conexión, de parseo, de validación o de escritura **nunca** se registra como «neutro».
- El `registro_id` se genera una vez por envío y `guardar_opinion` ignora un `id` repetido, así que los *reruns* de Streamlit no duplican registros.
- Escritura atómica: archivo temporal en el mismo directorio, `fsync` y `os.replace`. Si `opiniones.json` está dañado, se muestra un error y **no se sobrescribe**.
- Limitación: se supone **un único escritor local**. El reemplazo atómico evita archivos incompletos, pero no resuelve escrituras concurrentes; para varios usuarios habría que migrar a SQLite o PostgreSQL.

## Ampliaciones (además del taller)

| Ampliación | Dónde | Cómo funciona |
|---|---|---|
| 📊 **Gráfica por carrera** | «Estadísticas» | Barras apiladas por sentimiento (cantidad o %), con tooltip y vista de tabla. Solo usa registros de la app. Colores fijos por sentimiento, validados para daltonismo. |
| 🏆 **Ranking de carreras** | «Estadísticas» | Índice de percepción = (positivas − negativas) ÷ total × 100, de −100 a +100. Las carreras con menos opiniones que el mínimo elegido van al final. |
| 🔍 **Sentimiento por aspecto** | Análisis y «Estadísticas» | El modelo indica los aspectos que menciona la opinión (trazado, organización, clima, reglamento, ambiente, transmisión, competencia, logística) y cómo valora cada uno. |
| ⚠️ **Alerta de revisión** | «Emitir» y «Consultar» | Si los aspectos contradicen la categoría global (por ejemplo, un aspecto positivo y otro negativo, pero la categoría no es mixto), la opinión se marca para revisión. **No** cambia la etiqueta. |
| ✏️ **Corrección manual** | «Consultar» | Se guarda `sentimiento_corregido` + nota + fecha. `sentimiento` (lo que dijo el modelo) **nunca** se sobrescribe. Filtros, recuentos, gráficas y ranking usan la etiqueta vigente. Elegir de nuevo la etiqueta del modelo deshace la corrección. |
| 🌍 **Multilingüe** | Análisis, «Consultar» y «Comparar» | Acepta opiniones en cualquier idioma; la razón siempre sale en español. Se guarda el `idioma` detectado y se puede filtrar por él. La evaluación por idioma está en «Comparar modelos». |
| 🤖 **Switch de IAs** | Barra lateral | Elige entre Qwen 2.5 3B y Llama 3.2 3B (locales, Ollama) o Gemini 3.5 Flash y Flash-Lite (nube, `langchain-google-genai`). Muestra 🟢/🔴 según la disponibilidad real del modelo. Con Gemini, las opiniones **se envían a Google**. |
| 🌡️ **Control de temperatura** | Barra lateral | Deslizador de 0 a 1 (0 por defecto). Con valores mayores que 0 avisa de que la etiqueta puede variar. Cada registro guarda `modelo` y `temperatura`, y la tabla de «Consultar» los muestra. |
| ⚖️ **Comparar modelos** | «Comparar modelos» + `comparar_modelos.py` | Exactitud global, por idioma y por categoría, detección de idioma, tiempo, acuerdo y kappa de Cohen sobre 26 casos, para 2 o más modelos. También permite comparar en vivo una opinión con 2 o 3 modelos (sin guardar). |
| 📁 **Carga masiva CSV** | «Carga masiva» | Valida cada fila, muestra una vista previa y clasifica con barra de progreso. El id de cada registro se deriva del contenido del archivo y del número de fila (uuid5), así que volver a subir el mismo archivo no duplica nada. Si Ollama se cae, se detiene y conserva lo ya guardado. |

**Compatibilidad:** los campos nuevos (`temperatura`, `idioma`, `aspectos`, `alerta_revision`, `sentimiento_corregido`, `nota_correccion`, `fecha_correccion_utc`) son opcionales. Los registros antiguos siguen cargando y `version` sigue siendo 1.

## Historial de sesión vs. persistencia

- `st.session_state.historial`: lo que se ve en el chat. Vive en la memoria del navegador y del servidor, y se pierde al cerrar la pestaña o al pulsar «Nueva conversación».
- `datos/opiniones.json`: los registros guardados. Sobreviven al reinicio; «Nueva conversación» no los toca.

## Diferencias con `streamlit_chatbot2.py` (código base del curso)

| Original | Paddock Global |
|---|---|
| `ChatOpenAI` + `OPENAI_API_KEY` | `ChatOllama` local, sin clave |
| Selectores de modelo, temperatura y personalidad | Eliminados: el clasificador mantiene criterios estables |
| `{historial}` dentro del prompt | Sin historial: cada opinión se analiza sola |
| `cadena.stream(...)` y `chunk.content` | `cadena.invoke(...)` → objeto Pydantic (`analisis.sentimiento`) |
| Historial como `HumanMessage`/`AIMessage` | Diccionarios con la carrera y el estado de cada opinión |
| Sin persistencia | `opiniones.json` + sección de consultas |

**Antiejemplo del zip:** `analisis_sentimientos_parte1.py` devuelve `{"sentimiento": "neutro", "razon": "Error en análisis"}` cuando falla `json.loads`. Eso convierte un error en un dato falso. Aquí un fallo siempre se reporta como error y no se guarda.

## Problemas conocidos en Windows

- **Gemini:** el plan gratuito tiene un límite de peticiones por minuto. Si se supera, la app muestra «Se alcanzó el límite de uso gratuito de Gemini» y no guarda nada; la carga masiva se detiene y conserva lo ya guardado. `gemini-2.5-flash` no funciona con la versión instalada de `langchain-google-genai` (error de versión de API), por eso no aparece en el selector.
- **Smart App Control** (Windows 11) bloquea DLLs de algunos paquetes pip sin reputación: `ImportError: DLL load failed ... Una directiva de Control de aplicaciones bloqueó este archivo`. En este equipo bloqueó `xxhash 4.1.0` (dependencia de `langsmith` → `langchain-core`). Solución: fijar `xxhash==3.5.0`. **No desactives Smart App Control**: en Windows 11 no se puede volver a activar sin reinstalar el sistema. Crea el venv dentro del proyecto, no en `%TEMP%`.
- **Primera llamada lenta** (~1 min): es la carga del modelo. `keep_alive="30m"` lo mantiene cargado entre opiniones.
- Si `ollama` no se reconoce en la terminal, ábrela de nuevo o usa `%LOCALAPPDATA%\Programs\Ollama\ollama.exe`.

## Pruebas y evidencias

```text
> python -m pytest -q
.......................................................                  [100%]
55 passed in 2.10s
```

- [evidencias/registro_pruebas.md](evidencias/registro_pruebas.md): todos los casos, con lo esperado, lo observado y las discrepancias explicadas. Clasificación: 9/11 (v1.0), 10/11 (v1.1) y 10/11 (v2.1) con qwen2.5:3b, y 11/11 con Gemini 3.5 Flash. Interfaz: 16/16. Carga masiva idempotente.
- [evidencias/comparacion_modelos_3modelos_v2.1.md](evidencias/comparacion_modelos_3modelos_v2.1.md): qwen2.5:3b 73,1 %, llama3.2:3b 76,9 % y Gemini 3.5 Flash-Lite 96,2 % en 26 casos de 5 idiomas.
- [evidencias/experimento_temperatura_qwen2.5_3b.md](evidencias/experimento_temperatura_qwen2.5_3b.md): con T=0 la etiqueta es 100 % estable; con T=1 una opinión recibió 3 etiquetas distintas en 4 intentos.
- [evidencias/reflexion.md](evidencias/reflexion.md): análisis de los errores y ambigüedades.
- `evidencias/capturas/`: capturas de persistencia tras reinicio y de la consulta filtrada.

## Historial del prompt

| Versión | Cambio |
|---|---|
| 1.0 | Roles, criterios de las 4 categorías, pertinencia, ironía, jerga y ejemplos. |
| 1.1 | Procedimiento de decisión paso a paso (elogios / críticas → categoría). Corrigió las descripciones neutras clasificadas como positivas; volvió al modelo más conservador con los elogios implícitos (ver reflexión). |
| 2.0 | Multilingüe (mismos criterios en todos los idiomas, razón siempre en español), campos `idioma` y `aspectos` antes de la categoría, elogios implícitos explícitamente reconocidos y «un dato sobre la carrera es pertinente y neutro». `num_ctx` 2048 → 4096. |
| 2.1 | La descripción de `es_pertinente` dice «trata sobre la carrera (valoración o dato)» en vez de «constituye una opinión». Sin efecto medible (ver reflexión, caso 5), pero es coherente con el prompt. **Versión actual.** |
