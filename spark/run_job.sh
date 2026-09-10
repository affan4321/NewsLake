#!/usr/bin/env bash
# Submit a PySpark job (from ./spark/jobs) to the local standalone cluster, with MinIO
# (s3a://) wired up. Usage: ./spark/run_job.sh bronze_to_silver.py [-- extra spark-submit args]
#
# Also callable from inside the Airflow worker container (Docker-outside-of-Docker): that
# container talks to the HOST's Docker daemon via the mounted socket, so `docker compose`
# must be pointed at the compose file's real HOST path -- a container-internal path like
# /opt/project means nothing to the daemon. Set COMPOSE_FILE to override the default.
set -euo pipefail
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

if [ -f .env ]; then
  set -a
  source .env
  set +a
fi

COMPOSE_FILE="${COMPOSE_FILE:-$PROJECT_ROOT/docker-compose.yml}"

JOB_FILE="$1"
shift || true

# Named volumes are created root-owned; the spark image runs as uid 185, so the
# ivy dependency cache needs its permissions fixed before spark-submit can write to it.
docker compose -f "$COMPOSE_FILE" run --rm --user root --entrypoint sh spark-master \
  -c "mkdir -p /opt/ivy-cache && chown -R 185:185 /opt/ivy-cache" >/dev/null

docker compose -f "$COMPOSE_FILE" run --rm spark-master /opt/spark/bin/spark-submit \
  --master spark://spark-master:7077 \
  --packages org.apache.hadoop:hadoop-aws:3.3.4,com.amazonaws:aws-java-sdk-bundle:1.12.262 \
  --conf spark.jars.ivy=/opt/ivy-cache \
  --conf spark.hadoop.fs.s3a.endpoint="http://minio:9000" \
  --conf spark.hadoop.fs.s3a.access.key="$MINIO_ROOT_USER" \
  --conf spark.hadoop.fs.s3a.secret.key="$MINIO_ROOT_PASSWORD" \
  --conf spark.hadoop.fs.s3a.path.style.access=true \
  --conf spark.hadoop.fs.s3a.impl=org.apache.hadoop.fs.s3a.S3AFileSystem \
  --conf spark.hadoop.fs.s3a.connection.ssl.enabled=false \
  --conf spark.sql.shuffle.partitions=4 \
  "/opt/spark-jobs/$JOB_FILE" "$@"
