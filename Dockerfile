FROM python:3.12-alpine

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies
RUN apk add --no-cache \
    build-base \
    mariadb-dev \
    pkgconfig \
    ffmpeg \
    && rm -rf /var/cache/apk/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# # Copy project
# COPY . .

# # Make entrypoint executable
# RUN chmod +x /app/entrypoint.sh

# # Create directories for static and media files
# RUN mkdir -p /app/assets_served /app/media && \
# chmod -R 755 /app/assets_served /app/media

# Set entrypoint
# ENTRYPOINT ["/app/entrypoint.sh"]

# Start Gunicorn
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
