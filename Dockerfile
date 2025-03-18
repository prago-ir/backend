FROM python:3.12.7-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    python3-dev \
    libffi-dev \
    libpq-dev \
    default-libmysqlclient-dev \
    libxml2-dev \
    libxslt1-dev \
    liblapack-dev \
    libblas-dev \
    gfortran \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Add this line to your existing Dockerfile
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Set the entrypoint script
ENTRYPOINT ["/entrypoint.sh"]

# Your existing CMD should remain as is
CMD ["gunicorn", "core.wsgi:application", "--bind", "0.0.0.0:8000"]
