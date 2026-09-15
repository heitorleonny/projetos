# Backend do Portal FEJEPE — FastAPI.
# Imagem única: serve a API e também roda a suíte de testes
# (`docker compose --profile test run test`).

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Dependências primeiro: mudança em código não invalida esta camada.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Código da aplicação, testes e config do pytest.
COPY pyproject.toml .
COPY app/ app/
COPY tests/ tests/

# Usuário sem privilégios.
RUN useradd --create-home --uid 10001 portal && chown -R portal:portal /app
USER portal

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request,sys;sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health',timeout=3).status==200 else 1)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
