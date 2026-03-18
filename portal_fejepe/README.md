# Portal FEJEPE – Backend API

## 🚀 Quick Start

### Pré-requisitos
- Python 3.11+
- Conta Supabase com as tabelas `empresa_junior`, `metas` e `monitoramento`

### Setup

```bash
# 1. Clonar e entrar no projeto
cd portal_fejepe

# 2. Criar venv
python -m venv .venv
source .venv/bin/activate

# 3. Instalar dependências
pip install -r requirements.txt

# 4. Configurar variáveis de ambiente
cp .env.example .env
# Editar .env com SUPABASE_URL e SUPABASE_KEY

# 5. Rodar o servidor
uvicorn app.main:app --reload --port 8000
```

### Documentação da API

Com o servidor rodando, acesse:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Testes

```bash
pytest
```

## 📁 Estrutura

```
app/
├── main.py              # App FastAPI, CORS, lifespan
├── config.py            # Settings (variáveis de ambiente)
├── dependencies.py      # Injeção de dependência Supabase
├── models/              # Schemas Pydantic (request/response)
│   ├── empresa.py
│   ├── meta.py
│   ├── monitoramento.py
│   └── indicadores.py
├── routers/             # Endpoints agrupados
│   ├── empresas.py
│   ├── metas.py
│   ├── monitoramento.py
│   └── rede.py
├── services/            # Lógica de negócio e cálculos
│   ├── empresa_service.py
│   ├── calculo_service.py
│   └── rede_service.py
└── utils/
    └── constants.py     # Faixas de cluster, pesos SDE
```

## 🔧 Variáveis de ambiente

| Variável | Descrição |
|----------|-----------|
| `SUPABASE_URL` | URL do projeto Supabase |
| `SUPABASE_KEY` | Chave anon/service do Supabase |
| `CORS_ORIGINS` | Origens permitidas (separadas por vírgula) |

## 📐 Cálculos

Todos os cálculos estratégicos estão centralizados em `app/services/calculo_service.py`.
As fórmulas oficiais estão documentadas em `calculos.md`.
