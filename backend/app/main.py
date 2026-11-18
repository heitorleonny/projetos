"""
Portal das Federações — Backend API.

Aplicação FastAPI que centraliza dados e cálculos estratégicos
das Empresas Juniores da FEJEPE.

Endpoints disponíveis:
    /api/v1/empresas     — Consulta, filtro e comparação de EJs
    /api/v1/rede         — Indicadores consolidados e ranking
    /api/v1/eventos      — Monitoramento de metas de eventos
    /api/v1/federacao    — Branding da federação (PÚBLICO, sem autenticação)
    /api/v1/admin        — Painel: federações, usuários e importação de planilha
    /api/v1/metricas     — Painel de métricas personalizadas (todos leem; admin cria)
    /docs                — Swagger UI (documentação interativa)
    /redoc               — ReDoc (documentação alternativa)

As rotas de documentação só existem quando `settings.DOCS_ENABLED` é
verdadeiro — em produção o schema da API não precisa ser público.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import auth, admin, analise, empresas, eventos, federacao, ia, metricas, rede


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle da aplicação: setup e teardown."""
    # Startup — nada necessário por enquanto (Supabase é lazy-loaded)
    yield
    # Shutdown — cleanup se necessário


def criar_app() -> FastAPI:
    """
    Monta a aplicação FastAPI.

    É uma factory, e não um módulo de efeito colateral, para que as
    configurações sejam lidas no momento da chamada — assim os testes
    conseguem construir variantes da app (por exemplo com a documentação
    desligada) sem recarregar o módulo.
    """
    app = FastAPI(
        title="Portal das Federações API",
        description=(
            "API do Portal das Federações — centraliza dados e cálculos estratégicos "
            "das Empresas Juniores da rede. Permite consultar EJs, comparar "
            "indicadores, visualizar KPIs da rede e gerar rankings."
        ),
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs" if settings.DOCS_ENABLED else None,
        redoc_url="/redoc" if settings.DOCS_ENABLED else None,
        openapi_url="/openapi.json" if settings.DOCS_ENABLED else None,
    )

    # ── CORS ──────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Routers ───────────────────────────────────────────────────
    app.include_router(auth.router)
    app.include_router(empresas.router)
    app.include_router(eventos.router)
    app.include_router(rede.router)
    app.include_router(analise.router)
    app.include_router(admin.router)
    app.include_router(ia.router)
    app.include_router(metricas.router)
    # Único router sem `Depends(get_current_user)`: é consumido antes do login.
    # O motivo está no cabeçalho de app/routers/federacao.py.
    app.include_router(federacao.router)

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

    return app


app = criar_app()
