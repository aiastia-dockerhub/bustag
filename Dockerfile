# ===== Stage 1: Build Vue Frontend =====
FROM node:20-slim AS frontend-build
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# ===== Stage 2: Build Python Backend =====
FROM python:3.11-slim AS base

WORKDIR /app

# Install build dependencies + nginx + supervisor
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    nginx \
    supervisor \
    && rm -rf /var/lib/apt/lists/*

FROM base AS build

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ===== Stage 3: Release =====
FROM python:3.11-slim AS release

WORKDIR /app

# Install nginx + supervisor
RUN apt-get update && apt-get install -y --no-install-recommends \
    nginx \
    supervisor \
    && rm -rf /var/lib/apt/lists/*

# Copy installed Python packages
COPY --from=build /install /usr/local

# Copy application code
COPY bustag/ ./bustag/
COPY data/ ./data/
COPY setup.py .

# Create data directory and nginx cache directory
RUN mkdir -p /app/data /tmp/nginx_img_cache

# Copy Vue frontend build output
COPY --from=frontend-build /app/frontend/dist /usr/share/nginx/html

# Copy nginx config
COPY docker/nginx.conf /etc/nginx/sites-available/default
RUN rm -f /etc/nginx/sites-enabled/default && \
    ln -s /etc/nginx/sites-available/default /etc/nginx/sites-enabled/default

# Copy supervisor config
COPY docker/supervisord.conf /etc/supervisor/conf.d/bustag.conf

# Copy entry script
COPY docker/entry.sh /app/docker/entry.sh
RUN chmod 755 /app/docker/entry.sh

EXPOSE 80

LABEL maintainer="bustag fork - using javbus-api"

CMD ["/app/docker/entry.sh"]