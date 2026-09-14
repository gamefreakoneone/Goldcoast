FROM python:3.12-slim-bookworm AS app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PLAYWRIGHT_BROWSERS_PATH=/opt/browsers
WORKDIR /app
RUN sed -i 's|http://deb.debian.org|https://deb.debian.org|g' /etc/apt/sources.list.d/debian.sources && apt-get -o Acquire::Retries=3 update && apt-get -o Acquire::Retries=3 install -y --no-install-recommends ffmpeg ca-certificates fonts-dejavu-core && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir . && python -m playwright install --with-deps chromium && chmod -R a+rX /opt/browsers && rm -rf /var/lib/apt/lists/*
COPY alembic.ini ./
COPY migrations ./migrations
COPY data/studio_demo ./data/studio_demo
COPY infra/lightsail/smoke.py ./infra/lightsail/smoke.py
RUN useradd --uid 10001 --create-home goldcoast && mkdir -p /app/output/studio/assets /app/output/studio/runs && chown -R goldcoast:goldcoast /app/output
USER goldcoast
CMD ["uvicorn", "goldcoast.api.studio_app:app", "--host", "0.0.0.0", "--port", "8001", "--no-access-log"]

FROM node:22-bookworm-slim AS frontend
WORKDIR /web
RUN npm install --global pnpm@10.17.1
COPY web/package.json web/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY web ./
RUN pnpm build

FROM caddy:2-alpine AS gateway
COPY --from=frontend /web/dist /srv
COPY infra/lightsail/Caddyfile /etc/caddy/Caddyfile
