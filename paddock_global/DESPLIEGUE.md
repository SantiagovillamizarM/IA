# Despliegue de Paddock Global en Plesk (VPS + Docker)

Guía paso a paso para publicar Paddock Global en un servidor con **Plesk Obsidian** y la extensión **Docker**. Todos los dominios, IP y claves son marcadores: sustitúyelos por los tuyos (`paddock.midominio.com`, `midominio.com`, `<IP_DEL_SERVIDOR>`).

> **Hosting compartido: no sirve.** Streamlit necesita un proceso persistente y WebSockets, y un hosting compartido de Plesk no mantiene procesos de larga duración. Si solo tienes hosting compartido, las alternativas son un VPS con Plesk o cualquier VPS con Docker al que apunte tu dominio. No hace falta reescribir la app.

## 1. Requisitos del servidor

| Recurso | Mínimo |
| --- | --- |
| Panel | Plesk Obsidian con acceso SSH y la extensión **Docker** (Plesk → Extensiones → Docker) |
| CPU y RAM | 2 vCPU y 4 GB de RAM con Gemini. Con el perfil `ollama`, **8 GB adicionales libres** (en CPU, cada opinión tardará varios segundos) |
| Disco | 10 GB libres (imagen de ~1 GB, PostgreSQL, respaldos) |
| DNS | Registro **A** de `paddock.midominio.com` → `<IP_DEL_SERVIDOR>` |
| Software | Docker Engine con el plugin `docker compose` v2 (lo instala la extensión) y `git` |

## 2. Pasos

### 2.1 Dominio y certificado

1. Plesk → **Sitios web y dominios** → *Añadir dominio* o *Añadir subdominio* → `paddock.midominio.com`.
2. En el dominio → **SSL/TLS** → *Let's Encrypt* (**SSL It!**): emite el certificado y activa la **redirección permanente 301 de HTTP a HTTPS**.

### 2.2 Código fuera de `httpdocs`

```bash
ssh usuario@<IP_DEL_SERVIDOR>
cd /var/www/vhosts/midominio.com
git clone <URL_DEL_REPOSITORIO> paddock_repo
cd paddock_repo/paddock_global          # aquí están despliegue/, src/, .env.example…
```

También puedes usar la extensión **Git** de Plesk, siempre que el destino quede **fuera** de `httpdocs`.

### 2.3 Archivo `.env` (secretos solo en el servidor)

```bash
cp .env.example .env
chmod 600 .env
python3 -c "import secrets; print(secrets.token_urlsafe(32))"   # ejecútalo dos veces: POSTGRES_PASSWORD y SAL_HASH_IP
nano .env
```

Valores mínimos de producción:

```dotenv
LLM_PROVIDER=gemini
GOOGLE_API_KEY=<tu clave de Google AI Studio>
GEMINI_MODEL=gemini-2.5-flash
STORAGE_BACKEND=sql
POSTGRES_PASSWORD=<aleatoria y larga>
SAL_HASH_IP=<aleatoria y larga>
DOMINIO=paddock.midominio.com
PERMITIR_ANONIMOS=true
REGISTRO_ABIERTO=true
LIMITE_LLM_DIARIO=20        # ajústalo a la cuota REAL de tu plan de Gemini (gratuito: 20/día por modelo)
API_DOCS=false
```

`DATABASE_URL` y `OLLAMA_BASE_URL` los fija `docker-compose.yml` (no hace falta tocarlos).

### 2.4 Arranque

```bash
docker compose -p paddock -f despliegue/docker-compose.yml --env-file .env up -d --build
docker compose -p paddock -f despliegue/docker-compose.yml --env-file .env ps
curl -s http://127.0.0.1:8501/_stcore/health        # → ok
curl -s http://127.0.0.1:8000/api/salud             # → {"estado":"ok",…}
```

Si tu versión de Plesk lo permite, también puedes levantarlo desde **Docker → Stacks** con el mismo archivo. El *entrypoint* aplica `alembic upgrade head` y siembra el catálogo antes de arrancar Streamlit.

### 2.5 Administrador y catálogo

```bash
docker compose -p paddock -f despliegue/docker-compose.yml --env-file .env exec app \
  python scripts/crear_admin.py --email admin@midominio.com --nombre "Administración"   # pide la contraseña
docker compose -p paddock -f despliegue/docker-compose.yml --env-file .env exec app \
  python scripts/sembrar_catalogo.py      # idempotente (el entrypoint ya lo ejecuta)
```

Para migrar las opiniones del modo taller: copia `datos/opiniones.json` al contenedor (`docker compose cp`) y ejecuta `python scripts/migrar_json_a_bd.py --json /app/datos/opiniones.json`.

### 2.6 Proxy inverso de Plesk (nginx)

Plesk → dominio → **Configuración de Apache y nginx** → **Directivas adicionales de nginx**: pega el contenido de [`despliegue/plesk-nginx.conf`](despliegue/plesk-nginx.conf).

- Streamlit **no funciona** sin las cabeceras `Upgrade`/`Connection` de WebSocket: sin ellas la app se queda en «Connecting…».
- Si Plesk rechaza la directiva por un `location /` duplicado, **desactiva el modo proxy de Apache** para ese dominio (en la misma pantalla, desmarca *Modo proxy*) o mantén `location ~ ^/` como está en el archivo. Comprueba la documentación de tu versión de Plesk.
- `/api/` se publica hacia el contenedor `api` (`127.0.0.1:8000`).

### 2.7 Ollama en el servidor (opcional)

Solo si tienes ≥ 8 GB de RAM libres:

```bash
docker compose -p paddock -f despliegue/docker-compose.yml --env-file .env --profile ollama up -d
docker compose -p paddock -f despliegue/docker-compose.yml --env-file .env exec ollama ollama pull qwen2.5:3b
# y en .env: LLM_PROVIDER=ollama ; luego: docker compose … up -d
```

## 3. Red y firewall

- Todos los puertos de los contenedores se publican **solo en `127.0.0.1`** (`8501` app, `8000` api). PostgreSQL y Ollama **no** se publican. Docker se salta las reglas de `ufw` para los puertos publicados en `0.0.0.0`; por eso es obligatorio enlazarlos a `127.0.0.1` (ya lo hace `docker-compose.yml`).
- Puertos abiertos al exterior: **80, 443, SSH** y el panel de Plesk (**8443**), idealmente restringido por IP (Plesk → Herramientas y configuración → Firewall).
- La app toma la IP real de `X-Forwarded-For` **solo** si la conexión viene del proxy de confianza (`PROXY_CONFIABLE`, por defecto la red de Docker `172.16.0.0/12` y `127.0.0.1`). La IP solo se guarda como hash con sal.
- Streamlit acepta solo el host `DOMINIO` y el origen `https://DOMINIO` (`allowedHosts`/`corsAllowedOrigins`, escritos al arrancar por `scripts/configurar_streamlit.py`).

## 4. Operación

### Respaldos

`scripts/respaldo_bd.sh` hace un `pg_dump` comprimido en `respaldos/` (permisos 700/600) y borra los de más de 14 días.

- Prográmalo en Plesk → **Tareas programadas** → *Ejecutar un comando*: `/var/www/vhosts/midominio.com/paddock_repo/paddock_global/scripts/respaldo_bd.sh`, a diario a las 03:00.
- **Restaurar:**
  ```bash
  gunzip -c respaldos/paddock-AAAAMMDD-HHMMSS.sql.gz | \
    docker compose -p paddock -f despliegue/docker-compose.yml --env-file .env exec -T db psql -U paddock -d paddock
  ```
- **Probado** en el equipo de desarrollo (Docker Desktop, PostgreSQL 16): respaldo de 15 tablas y restauración con los datos intactos. Pruébalo una vez en el servidor tras el primer despliegue.

### Actualizaciones

```bash
scripts/respaldo_bd.sh                          # SIEMPRE antes de una migración
git pull
docker compose -p paddock -f despliegue/docker-compose.yml --env-file .env up -d --build   # las migraciones corren solas
```

### Logs y monitoreo

- Driver `json-file` con rotación (`max-size: 10m`, `max-file: 3`). Los logs no contienen textos de opiniones ni secretos: `docker compose … logs -f app worker api`.
- `HEALTHCHECK` de Docker en `app` y `api`, y `restart: unless-stopped` en todos los servicios.
- Opcional: un monitor externo de disponibilidad contra `https://paddock.midominio.com/_stcore/health` y `/api/salud`.

## 5. Verificación posterior al despliegue

- [ ] `https://paddock.midominio.com` con certificado válido, y `http://` redirige a `https://`.
- [ ] La app carga sin quedarse en «Connecting…» (WebSocket correcto).
- [ ] Registro, inicio de sesión y bloqueo tras 5 contraseñas erróneas (15 minutos).
- [ ] Emitir una opinión con Gemini y verla en «Consultar».
- [ ] `docker compose -p paddock -f despliegue/docker-compose.yml --env-file .env restart` y la opinión sigue ahí (volumen `pgdatos`).
- [ ] Desde **otra máquina**, los puertos 5432, 8501, 8000 y 11434 están cerrados: `nmap -p 5432,8501,8000,11434 <IP_DEL_SERVIDOR>`.
- [ ] Cabeceras de seguridad presentes: `curl -sI https://paddock.midominio.com | grep -Ei "strict-transport|x-content-type|referrer-policy|content-security"`.
- [ ] `curl -s https://paddock.midominio.com/api/salud` responde y `https://paddock.midominio.com/api/docs` devuelve 404 (`API_DOCS=false`).
- [ ] Lote de prueba de 2–3 filas en «📥 Lotes»: el worker lo deja en «terminado».
- [ ] Respaldo manual con `scripts/respaldo_bd.sh` y restauración probada una vez.

## 6. Qué se probó en local y qué no

| Prueba | Resultado |
| --- | --- |
| `docker build` de la imagen multietapa | ✅ Docker Desktop 29.8 (Windows 11) |
| Stack `app` + `db` (PostgreSQL 16) + `api` + `worker` | ✅ Migraciones al arrancar, todos sanos, puertos solo en 127.0.0.1 |
| Persistencia tras `docker compose restart` | ✅ |
| Opinión clasificada desde el contenedor y guardada en PostgreSQL | ✅ (Ollama del equipo vía `host.docker.internal`) |
| API: 401 sin token, 201 con token, listado | ✅ |
| Lote procesado por el contenedor `worker` | ✅ 3 filas: 2 guardadas, 1 no pertinente |
| Respaldo y restauración | ✅ |
| `allowedHosts`/`corsAllowedOrigins` aplicados desde `DOMINIO` | ✅ |
| Plesk, Let's Encrypt, nginx, firewall y `nmap` externo | ⏳ No hay acceso al servidor: los ejecuta quien despliegue, con la lista de arriba |
