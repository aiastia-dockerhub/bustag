FROM python:3.11-slim AS base

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

FROM base AS build

COPY requirements.txt .

RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.11-slim AS release

WORKDIR /app

# Copy installed Python packages
COPY --from=build /install /usr/local

# Copy application code
COPY bustag/ ./bustag/
COPY data/ ./data/
COPY setup.py .

# Create data directory with default config
RUN mkdir -p /app/data

# Copy docker entry script
COPY docker/entry.sh /app/docker/entry.sh
RUN chmod 755 /app/docker/entry.sh

EXPOSE 8000

LABEL maintainer="bustag fork - using javbus-api"

CMD ["/app/docker/entry.sh"]