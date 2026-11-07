# Dependências travadas; a imagem publicada não contém ferramentas de testes.
FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
COPY requirements.lock ./
RUN pip install --no-cache-dir --require-hashes -r requirements.lock
RUN useradd --create-home --uid 10001 portal
COPY --chown=portal:portal app/ app/
COPY --chown=portal:portal scripts/ scripts/

FROM base AS test
COPY requirements-dev.lock ./
RUN pip install --no-cache-dir --require-hashes -r requirements-dev.lock
COPY --chown=portal:portal pyproject.toml ./
COPY --chown=portal:portal tests/ tests/
COPY --chown=portal:portal scripts/ scripts/
USER portal
CMD ["python", "-m", "pytest", "-q", "-rs", "--require-lab"]

FROM base AS runtime
USER portal
ENV PORT=8000
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import os,urllib.request;urllib.request.urlopen('http://127.0.0.1:'+os.environ.get('PORT','8000')+'/health',timeout=3)"
# Render fornece PORT. exec conserva o tratamento de SIGTERM pelo servidor.
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
