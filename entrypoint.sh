#!/bin/bash
set -e

# Function to check if MySQL is available
function mysql_ready() {
    python << END
import sys
import MySQLdb
try:
    conn = MySQLdb.connect(
        host="${DB_HOST}",
        port=int("${DB_PORT}"),
        user="${DB_USER}",
        passwd="${DB_PASSWORD}",
        db="${DB_NAME}"
    )
    sys.exit(0)
except Exception as e:
    print(f"Error connecting to MySQL: {e}")
    sys.exit(1)
END
}

# Wait for MySQL database to be ready
echo "Waiting for MySQL database..."
until mysql_ready; do
  echo "MySQL is unavailable - sleeping (5s)"
  sleep 5
done
echo "MySQL database is available!"

# Create necessary directories if they don't exist
echo "Creating necessary directories..."
mkdir -p /app/assets_served
mkdir -p /app/media

# Set permissions
chmod -R 755 /app/assets_served
chmod -R 755 /app/media

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput --clear

# Apply database migrations
echo "Applying database migrations..."
python manage.py migrate

# Start the application
echo "Starting application..."
exec "$@"
