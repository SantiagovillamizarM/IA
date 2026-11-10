#!/bin/sh
# Punto de entrada del contenedor. Aplica las migraciones antes de arrancar el servicio pedido.
set -eu

if [ "${STORAGE_BACKEND:-json}" = "sql" ] && [ "${OMITIR_MIGRACIONES:-0}" != "1" ]; then
  echo "Aplicando migraciones (alembic upgrade head)…"
  alembic upgrade head
  python scripts/sembrar_catalogo.py
fi

# Restringe Host y orígenes al dominio real (protección CORS / DNS rebinding de Streamlit).
if [ -n "${DOMINIO:-}" ]; then
  python scripts/configurar_streamlit.py
fi

servicio="${1:-app}"
case "$servicio" in
  app)
    exec streamlit run src/paddock/interfaz/app.py --server.address=0.0.0.0 --server.port=8501
    ;;
  api)
    exec uvicorn paddock.api.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips="${PROXY_CONFIABLE:-127.0.0.1}"
    ;;
  worker)
    exec python -m paddock.worker.procesador_lotes
    ;;
  *)
    exec "$@"
    ;;
esac
