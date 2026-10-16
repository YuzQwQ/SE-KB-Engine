# Base updates are deliberate: Python 3.13.2 is inside the supported 3.11-3.13 range.
FROM python:3.13.2-slim-bookworm AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1
WORKDIR /build
COPY requirements-prod.txt ./
RUN python -m pip wheel --require-hashes --wheel-dir /wheels -r requirements-prod.txt

FROM python:3.13.2-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    DATA_ROOT=/app/data \
    CACHE_ROOT=/app/cache \
    OUTPUT_ROOT=/app/output

RUN groupadd --gid 10001 app && useradd --uid 10001 --gid app --no-create-home --shell /usr/sbin/nologin app
WORKDIR /app
COPY --from=builder /wheels /wheels
COPY requirements-prod.txt ./
# Builder inputs were verified with --require-hashes above. Wheels built from an
# sdist have a new local hash, so the runtime installs only from that isolated
# wheelhouse. Install every verified build output directly, without an index or
# dependency resolution; requirements-prod.txt remains in the image as the lock record.
RUN python -m pip install --no-index --no-deps /wheels/*.whl \
    && rm -rf /wheels

COPY --chown=10001:10001 api ./api
COPY --chown=10001:10001 config ./config
COPY --chown=10001:10001 se_kb_app ./se_kb_app
COPY --chown=10001:10001 service_boundary ./service_boundary
COPY --chown=10001:10001 utils ./utils
COPY --chown=10001:10001 vectorizer ./vectorizer
RUN mkdir -p /app/data /app/cache /app/output /app/logs /app/se_kb && chown -R 10001:10001 /app

USER 10001:10001
EXPOSE 8000
STOPSIGNAL SIGTERM
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/ready', timeout=3).read()"]

CMD ["sh", "-c", "exec gunicorn --workers ${GUNICORN_WORKERS:-2} --threads ${GUNICORN_THREADS:-4} --bind 0.0.0.0:8000 --timeout ${GUNICORN_TIMEOUT:-60} --graceful-timeout ${GUNICORN_GRACEFUL_TIMEOUT:-30} --keep-alive 5 --max-requests 1000 --max-requests-jitter 100 --access-logfile - --error-logfile - api.app:app"]
