# ===== Stage 1: Build Nuxt Frontend =====
FROM node:22-slim AS frontend-build
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install
COPY frontend/ ./
RUN NUXT_TELEMETRY_DISABLED=1 npm run build

# ===== Stage 2: Build Python Dependencies =====
FROM python:3.12-slim AS python-build

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt \
    && find /install -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null \
    && find /install -type d -name 'tests' -exec rm -rf {} + 2>/dev/null \
    && find /install -type d -name 'test' -exec rm -rf {} + 2>/dev/null \
    && find /install -type f -name '*.pyx' -delete 2>/dev/null \
    && find /install -type f -name '*.c' -delete 2>/dev/null \
    && find /install -type f -name '*.pxd' -delete 2>/dev/null \
    && find /install -type f -name '*.rst' -delete 2>/dev/null \
    && find /install -type f -name '*.md' -delete 2>/dev/null \
    && find /install -type f -name 'LICENSE*' -delete 2>/dev/null \
    && find /install -type f -name 'COPYING*' -delete 2>/dev/null \
    && rm -rf /install/lib/python3.12/site-packages/pip* \
    && rm -rf /install/lib/python3.12/site-packages/pytest* \
    && rm -rf /install/lib/python3.12/site-packages/coverage* \
    && rm -rf /install/lib/python3.12/site-packages/numpy/doc \
    && rm -rf /install/lib/python3.12/site-packages/numpy/tests \
    && rm -rf /install/lib/python3.12/site-packages/scipy/doc \
    && rm -rf /install/lib/python3.12/site-packages/scipy/tests \
    && rm -rf /install/lib/python3.12/site-packages/sklearn/tests \
    && rm -rf /install/lib/python3.12/site-packages/pandas/tests \
    && rm -rf /install/lib/python3.12/site-packages/pandas/stubs \
    && rm -rf /install/lib/python3.12/site-packages/lightgbm/examples \
    && rm -rf /install/lib/python3.12/site-packages/lightgbm/tests \
    && find /install -type d -empty -delete 2>/dev/null

# ===== Stage 3: Release =====
FROM python:3.12-slim AS release

WORKDIR /app

# Only install runtime deps (no build-essential)
RUN apt-get update && apt-get install -y --no-install-recommends \
    nginx-light \
    supervisor \
    curl \
    libgomp1 \
    tzdata \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /var/cache/nginx \
    && mkdir -p /var/log/nginx /run/nginx \
    && touch /var/log/nginx/error.log /var/log/nginx/access.log

# 设置默认时区（可通过 docker-compose 环境变量覆盖）
ENV TZ=Asia/Shanghai

# Copy ONLY the node binary (not npm or node_modules - Nuxt .output is self-contained)
COPY --from=frontend-build /usr/local/bin/node /usr/local/bin/node

# Copy stripped Python packages
COPY --from=python-build /install /usr/local

# Copy application code
COPY bustag/ ./bustag/
COPY data/ ./data/
COPY setup.py .

# Create directories
RUN mkdir -p /app/data /tmp/nginx_img_cache /run/nginx

# Copy Nuxt SSR build output
COPY --from=frontend-build /app/frontend/.output /app/frontend/.output

# Copy configs
COPY docker/nginx.conf /etc/nginx/sites-available/default
RUN rm -f /etc/nginx/sites-enabled/default && \
    ln -s /etc/nginx/sites-available/default /etc/nginx/sites-enabled/default

COPY docker/supervisord.conf /etc/supervisor/conf.d/bustag.conf
COPY docker/entry.sh /app/docker/entry.sh
RUN chmod 755 /app/docker/entry.sh

EXPOSE 80

LABEL maintainer="bustag fork - using javbus-api"

CMD ["/app/docker/entry.sh"]