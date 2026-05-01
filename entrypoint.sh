#!/usr/bin/env bash

set -e

trap 'echo "Stopping container..."; exit 0' SIGTERM

log() { echo "[entrypoint] $*"; }

prepare_app() {
	log "Collecting static files..."
	python app/manage.py collectstatic --noinput

	log "Applying migrations..."
	python app/manage.py migrate --noinput
}

wait-for-it --service "${POSTGRES_LINK}" -- echo "[entrypoint] PostgreSQL is up"
wait-for-it --service "${REDIS_LINK}" -- echo "[entrypoint] Redis is up"
wait-for-it --service "${RABBITMQ_LINK}" -- echo "[entrypoint] RabbitMQ is up"

if [ "$1" == "backend" ]; then
	prepare_app

	log "Starting Gunicorn (workers=${WEB_WORKERS:-4})..."

	exec gunicorn core.wsgi:application \
		--chdir /app/app \
		--workers "${WEB_WORKERS:-4}" \
		--worker-class gthread \
		--threads 4 \
		--bind 0.0.0.0:8000 \
		--timeout 600 \
		--log-level info \
		--graceful-timeout 600

elif [ "$1" == "celery" ]; then
	log "Starting Celery worker..."

	exec celery \
		-A core worker \
		-l info \
		--concurrency=1 \
		--without-mingle \
		--without-gossip
else
	log "No valid argument provided, defaulting to infinite sleep..."

	exec sleep infinity
fi
