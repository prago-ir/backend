#!/bin/sh
set -e

echo "Starting entrypoint script..."

# The docker-compose.prod.yml ensures MariaDB is healthy before starting this container.
# If an additional explicit wait is needed, a loop checking DB connectivity can be added here.
# Example (requires mysql-client in the container, or use the Python script previously in comments):
# echo "Waiting for database to be ready..."
# until mysqladmin ping -h"${DB_HOST}" -u"${DB_USER}" -p"${DB_PASSWORD}" --silent; do
#     echo "Database not ready yet, waiting..."
#     sleep 2
# done
# echo "Database is ready!"

echo "Running database migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput --clear

echo "Application initialization complete."
echo "Starting application with command: $@"
exec "$@"
