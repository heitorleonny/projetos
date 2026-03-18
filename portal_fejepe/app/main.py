"""
Portal FEJEPE — Backend API.

Aplicação FastAPI que centraliza dados e cálculos estratégicos
das Empresas Juniores da FEJEPE.

Endpoints disponíveis:
    /api/v1/empresas     — Consulta, filtro e comparação de EJs
    /api/v1/rede         — Indicadores consolidados e ranking
    /docs                — Swagger UI (documentação interativa)
    /redoc               — ReDoc (documentação alternativa)
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import empresas, rede


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle da aplicação: setup e teardown."""
    # Startup — nada necessário por enquanto (Supabase é lazy-loaded)
    yield
    # Shutdown — cleanup se necessário


app = FastAPI(
    title="Portal FEJEPE API",
    description=(
        "API do Portal FEJEPE — centraliza dados e cálculos estratégicos "
        "das Empresas Juniores da rede. Permite consultar EJs, comparar "
        "indicadores, visualizar KPIs da rede e gerar rankings."
    ),
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ──────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────
app.include_router(empresas.router)
app.include_router(rede.router)


# ── Health check ──────────────────────────────────────────────
@app.get(
    "/health",
    tags=["Sistema"],
    summary="Health check",
    description="Verifica se a API está rodando.",
)
def health():
    """Retorna status da API."""
    return {"status": "ok", "version": "0.1.0"}
