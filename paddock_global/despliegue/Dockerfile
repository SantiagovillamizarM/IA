# Paddock Global · imagen multietapa (Python 3.12 slim, usuario sin privilegios)
# Construir desde la raíz del proyecto:  docker build -f despliegue/Dockerfile -t paddock-global .

# ---------- etapa 1: dependencias en un venv aislado
FROM python:3.12-slim AS constructor
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /build
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY requirements.txt requirements-db.txt ./
RUN pip install -r requirements.txt -r requirements-db.txt

# ---------- etapa 2: imagen final (sin compiladores ni caché de pip)
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH=/app/src:/app PADDOCK_RAIZ=/app STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
RUN groupadd --system paddock && useradd --system --gid paddock --home /app --shell /usr/sbin/nologin paddock
WORKDIR /app
COPY --from=constructor /opt/venv /opt/venv
COPY --chown=paddock:paddock src ./src
COPY --chown=paddock:paddock datos/catalogo.json datos/jerga.json datos/contrasenas_comunes.txt ./datos/
COPY --chown=paddock:paddock migraciones ./migraciones
COPY --chown=paddock:paddock alembic.ini pyproject.toml ./
COPY --chown=paddock:paddock scripts ./scripts
COPY --chown=paddock:paddock despliegue/.streamlit ./.streamlit
COPY --chown=paddock:paddock despliegue/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod 0755 /usr/local/bin/entrypoint.sh && mkdir -p /app/datos && chown -R paddock:paddock /app/datos
USER paddock
EXPOSE 8501
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8501/_stcore/health', timeout=4).read()==b'ok' else 1)"
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["app"]
