#!/bin/bash
set -e

echo "Starting entrypoint script..."

# Wait for database to be ready
# echo "Waiting for database to be ready..."
# python << END
# import sys
# import time
# import MySQLdb

# for i in range(30):
#     try:
#         MySQLdb.connect(
#             host="${DB_HOST}",
#             user="${DB_USER}",
#             passwd="${DB_PASSWORD}",
#             db="${DB_NAME}"
#         )
#         print("Database is ready!")
#         break
#     except MySQLdb.OperationalError:
#         print("Database not ready yet, waiting...")
#         time.sleep(1)
# else:
#     print("Could not connect to database after 30 attempts")
#     sys.exit(1)
# END

# Apply core migrations first
#echo "Running contenttypes migrations..."
#python manage.py migrate contenttypes
#
#echo "Running auth migrations..."
#python manage.py migrate auth
#
#echo "Running admin migrations..."
#python manage.py migrate admin
#
#echo "Running sessions migrations..."
#python manage.py migrate sessions
#
## Apply migrations
#echo "Running the rest of migrations..."
#python manage.py migrate

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput --clear

echo "Application initialization complete."
echo "Starting application..."
exec "$@"

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput --clear

set -e  # Return to exit on error

echo "Application initialization complete."
echo "Starting application..."
exec "$@"
