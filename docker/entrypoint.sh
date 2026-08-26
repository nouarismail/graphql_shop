#!/bin/sh
set -eu

if [ "${RUN_MIGRATIONS:-true}" = "true" ]; then
    echo "Applying database migrations..."
    python manage.py migrate --noinput
fi

if [ "${SETUP_ROLES:-true}" = "true" ]; then
    echo "Creating application roles and permissions..."
    python manage.py setup_roles
fi

if [ "${COLLECT_STATIC:-true}" = "true" ]; then
    echo "Collecting static files..."
    python manage.py collectstatic --noinput
fi

exec "$@"
