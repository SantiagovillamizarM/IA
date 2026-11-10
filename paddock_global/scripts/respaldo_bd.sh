#!/bin/sh
# Respaldo diario de PostgreSQL con pg_dump comprimido y retención de 14 días.
# Programarlo en Plesk → Herramientas y configuración → Tareas programadas (o en el cron del dominio):
#   0 3 * * *  /var/www/vhosts/midominio.com/paddock_global/scripts/respaldo_bd.sh
# Restaurar (ver DESPLIEGUE.md):
#   gunzip -c respaldos/paddock-AAAAMMDD-HHMMSS.sql.gz | docker compose -p paddock -f despliegue/docker-compose.yml \
#     --env-file .env exec -T db psql -U paddock -d paddock
set -eu

RAIZ="$(cd "$(dirname "$0")/.." && pwd)"
DESTINO="${RESPALDOS_DIR:-$RAIZ/respaldos}"
RETENCION_DIAS="${RETENCION_DIAS:-14}"
FECHA="$(date +%Y%m%d-%H%M%S)"
ARCHIVO="$DESTINO/paddock-$FECHA.sql.gz"

mkdir -p "$DESTINO"
chmod 700 "$DESTINO"
cd "$RAIZ"
docker compose -p paddock -f despliegue/docker-compose.yml --env-file .env exec -T db \
  pg_dump -U paddock -d paddock --no-owner --clean --if-exists | gzip -9 > "$ARCHIVO.tmp"
mv "$ARCHIVO.tmp" "$ARCHIVO"
chmod 600 "$ARCHIVO"
find "$DESTINO" -name 'paddock-*.sql.gz' -type f -mtime +"$RETENCION_DIAS" -delete
echo "Respaldo creado: $ARCHIVO ($(du -h "$ARCHIVO" | cut -f1))"
