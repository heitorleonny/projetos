# Portal das Federações – Backend API

> Execução recomendada: na raiz, `make setup`, `make demo` e
> `make demo-backend`. Testes completos: `make test` (Docker e banco descartável)
> ou `make test-local` (Python do host e lab atualizado).
> Veja [o roteiro completo](../docs/como-rodar.md).

## 🚀 Quick Start

### Pré-requisitos
- Python 3.11+
- Supabase com o schema multi-tenant de `infra/db/init/01..NN` e hook de Auth ativo

### Setup

```bash
# 1. Clonar e entrar no projeto
cd backend

# 2. Criar venv
python -m venv .venv
source .venv/bin/activate

# 3. Instalar dependências
pip install --require-hashes -r requirements-dev.lock

# 4. Configurar variáveis de ambiente
cp .env.example .env
# Editar .env com SUPABASE_URL e SUPABASE_ANON_KEY

# 5. Rodar o servidor
uvicorn app.main:app --reload --port 8000
```

### Documentação da API

Com o servidor rodando, acesse:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Testes

```bash
pytest -q -rs --require-lab  # exige o laboratório disponível e atualizado
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
│   ├── eventos.py
│   ├── federacao.py
│   ├── admin.py
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
| `SUPABASE_ANON_KEY` | Chave anônima; o JWT do usuário mantém a leitura sob RLS |
| `SUPABASE_SERVICE_KEY` | Opcional, usada somente no convite pelo backend |
| `INGESTAO_DSN` | Papel de carga sujeito a RLS, para upload pelo painel |
| `CORS_ORIGINS` | Origens permitidas (separadas por vírgula) |

## 📐 Cálculos

Todos os cálculos estratégicos estão centralizados em `app/services/calculo_service.py`.
As fórmulas oficiais estão documentadas em `calculos.md`.


## Dependências e ferramentas operacionais

Python 3.11+; as imagens de entrega usam Python 3.12. `requirements.txt` contém
somente dependências diretas de produção; `requirements-dev.txt` acrescenta pytest.
`requirements.lock` e `requirements-dev.lock` travam versões transitivas e hashes:

```bash
pip install --require-hashes -r requirements.lock       # produção
pip install --require-hashes -r requirements-dev.lock   # desenvolvimento/testes
```

Atualize ambos conscientemente com `uv pip compile --python-version 3.11
--generate-hashes` a partir dos arquivos `.txt`, revise o diff e rode `make test`.
A imagem runtime exclui pytest, testes e scripts administrativos. Para um banco
novo, use `python -m scripts.migrar_banco`; para o primeiro operador novo,
`python -m scripts.criar_operador`. Ambos revisam sem escrita por padrão e exigem
confirmação explícita com `--apply`. A sequência completa, variáveis privadas,
hook Auth e verificações do destino estão em [infra/db/README.md](../infra/db/README.md).
