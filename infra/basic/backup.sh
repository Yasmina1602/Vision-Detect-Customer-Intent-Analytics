#!/usr/bin/env bash
# Kunlik zaxira nusxa (cron: 0 3 * * * /opt/vision-basic/infra/basic/backup.sh)
set -euo pipefail
DIR=/var/backups/vision
mkdir -p "$DIR"
mysqldump --single-transaction --routines -u vision -p"${DB_PASSWORD:?DB_PASSWORD kerak}" vision_basic | gzip > "$DIR/db_$(date +%F).sql.gz"
tar -czf "$DIR/media_$(date +%F).tar.gz" -C /opt/vision-basic/apps/api media 2>/dev/null || true
find "$DIR" -type f -mtime +30 -delete      # 30 kundan eskilari o'chiriladi
