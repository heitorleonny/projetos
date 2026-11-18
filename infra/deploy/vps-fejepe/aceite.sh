#!/usr/bin/env bash
# Aceite no próprio servidor, SEM tocar em produção.
#
#   cd /opt/portal-federacoes/releases/<versão> && infra/deploy/vps-fejepe/aceite.sh [pasta-do-relatório]
#
# Tudo roda no projeto Compose `portal-federacoes-aceite`, com volume próprio e
# porta 127.0.0.1:8090, removido no fim (`down -v` é permitido SOMENTE nesse
# projeto; o nome é fixo e o script recusa qualquer outro).
#
# Parte A — roteiro mínimo (docs/entrega-tcc-2026-11-05.md, itens 2 a 6) pela
#   suíte do backend contra PostgreSQL descartável com toda a cadeia de migrações:
#   duas federações sintéticas, acesso cruzado negado também sem o filtro Python
#   (RLS), importação idempotente com fixture sintética, membro não importa,
#   desativação/troca de papel derruba privilégio, Nexo com provedor falso.
#   Exige 0 falhas e 0 testes pulados (--require-lab).
# Parte B — itens 1 e 7 na stack de produção (mesmo override), volume vazio:
#   migrações, operador sem senha padrão, login/logout, rota protegida sem sessão
#   = 401, migração repetida sem reaplicar, reinício preservando conta e sessão.
#
# Gera um relatório datado em texto, sem senhas, tokens ou dados reais.
set -euo pipefail
umask 077

PROJETO="portal-federacoes-aceite"
PORTA=8090
raiz="$(cd "$(dirname "$0")/../../.." && pwd)"
relatorios="${1:-$PWD}"
mkdir -p "$relatorios"
relatorio="$relatorios/aceite-$(date '+%Y%m%d-%H%M%S').txt"
tmp="$(mktemp -d)"
falhas=0

[[ "$PROJETO" == "portal-federacoes-aceite" ]] || { echo "Projeto de aceite inválido." >&2; exit 1; }
if [[ ! -f "$raiz/docker-compose.yml" ]]; then
    echo "Rode a partir de um pacote do portal (docker-compose.yml não encontrado em $raiz)." >&2
    exit 1
fi
if ss -ltn 2>/dev/null | grep -q "127.0.0.1:$PORTA "; then
    echo "A porta 127.0.0.1:$PORTA já está em uso; o aceite não sobe." >&2
    exit 1
fi

aceite_compose() {
    docker compose -p "$PROJETO" -f "$raiz/docker-compose.yml" \
        -f "$raiz/infra/deploy/vps-fejepe/compose.prod.yml" --env-file "$tmp/.env.aceite" "$@"
}
aceite_teste() {
    docker compose -p "$PROJETO" -f "$raiz/docker-compose.yml" --profile test "$@"
}
limpar() {
    aceite_compose down -v --remove-orphans >/dev/null 2>&1 || true
    aceite_teste rm -sf db-test >/dev/null 2>&1 || true
    rm -rf "$tmp"
}
trap limpar EXIT

registrar() { printf '%s\n' "$*" | tee -a "$relatorio"; }
conferir() {  # $1 descrição, $2 esperado, $3 obtido
    if [[ "$2" == "$3" ]]; then registrar "PASSOU  $1"; else registrar "FALHOU  $1 (esperado $2, obtido $3)"; falhas=$((falhas + 1)); fi
}
http() {  # método caminho [token] -> código HTTP; corpo em $tmp/corpo
    local auth=()
    [[ -n "${3:-}" ]] && auth=(-H "Authorization: Bearer $3")
    curl -s -o "$tmp/corpo" -w '%{http_code}' -X "$1" ${auth[@]+"${auth[@]}"} "http://127.0.0.1:$PORTA$2" || echo 000
}
login() {
    curl -s -o "$tmp/corpo" -w '%{http_code}' -X POST -H 'Content-Type: application/json' \
        --data @"$tmp/login.json" "http://127.0.0.1:$PORTA/api/v1/auth/login" || echo 000
}
token() { python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["access_token"])' "$tmp/corpo"; }

registrar "Aceite do Portal das Federações — $(date '+%Y-%m-%d %H:%M:%S %z')"
registrar "Pacote: $(basename "$raiz")  |  host: $(hostname)  |  $(docker compose version --short 2>/dev/null | sed 's/^/compose /')"
registrar "Projeto Compose isolado: $PROJETO (porta 127.0.0.1:$PORTA, volume próprio, removido no fim)"
registrar ""

# ── Parte A ───────────────────────────────────────────────────
registrar "== Parte A: suíte do backend contra PostgreSQL descartável =="
aceite_teste rm -sf db-test >/dev/null 2>&1 || true
aceite_teste up -d --wait db-test >/dev/null 2>&1
if aceite_teste logs --no-color db-test | grep -E ' (ERROR|FATAL):' >"$tmp/erros-db"; then
    registrar "FALHOU  migrações no banco de teste: $(wc -l <"$tmp/erros-db") linha(s) de ERROR/FATAL"
    falhas=$((falhas + 1))
fi
set +e
aceite_teste run --build --rm test >"$tmp/pytest.log" 2>&1
codigo=$?
set -e
resumo="$(grep -E '^[0-9]+ (passed|failed)|[0-9]+ passed' "$tmp/pytest.log" | tail -n1)"
registrar "pytest: ${resumo:-sem resumo}"
conferir "suíte do backend (0 falhas, 0 pulados)" 0 "$codigo"
aceite_teste rm -sf db-test >/dev/null 2>&1 || true
registrar ""

# ── Parte B ───────────────────────────────────────────────────
registrar "== Parte B: stack de produção com volume vazio =="
python3 "$raiz/scripts/configurar_docker.py" --producao --dominio aceite.invalid --destino "$tmp/.env.aceite" >/dev/null
sed -i.bak -e "s/^FRONTEND_PORT=.*/FRONTEND_PORT=$PORTA/" \
    -e "s#^CORS_ORIGINS=.*#CORS_ORIGINS=http://127.0.0.1:$PORTA#" "$tmp/.env.aceite" && rm -f "$tmp/.env.aceite.bak"

if aceite_compose up -d --build --wait >"$tmp/up.log" 2>&1; then
    registrar "PASSOU  stack sobe (postgres, migrate, backend, frontend)"
else
    registrar "FALHOU  stack não subiu"; falhas=$((falhas + 1))
fi
servicos="$(aceite_compose ps --services --status running | sort | tr '\n' ' ')"
conferir "só sobem backend, frontend e postgres (migrate termina)" "backend frontend postgres " "$servicos"

conferir "frontend responde /healthz" 200 "$(http GET /healthz)"
conferir "rota protegida sem sessão = 401" 401 "$(http GET /api/v1/auth/me)"
conferir "administração sem sessão = 401" 401 "$(http GET /api/v1/admin/sessao)"

export PORTAL_BOOTSTRAP_PASSWORD
PORTAL_BOOTSTRAP_PASSWORD="$(head -c 24 /dev/urandom | od -An -tx1 | tr -d ' \n')"
if aceite_compose run --rm -T -e PORTAL_BOOTSTRAP_PASSWORD migrate \
    python -m scripts.criar_operador_postgres --email aceite@example.invalid --nome Aceite --federacao 12 >/dev/null 2>&1; then
    registrar "PASSOU  operador criado pelo comando documentado (senha aleatória, não registrada)"
else
    registrar "FALHOU  criação do operador"; falhas=$((falhas + 1))
fi
python3 -c 'import json,os,sys;json.dump({"email":"aceite@example.invalid","password":os.environ["PORTAL_BOOTSTRAP_PASSWORD"]},open(sys.argv[1],"w"))' "$tmp/login.json"
unset PORTAL_BOOTSTRAP_PASSWORD

conferir "login do operador" 200 "$(login)"
t1="$(token 2>/dev/null || true)"
conferir "sessão válida em /auth/me" 200 "$(http GET /api/v1/auth/me "$t1")"
conferir "análise do mês com sessão (banco vazio)" 200 "$(http GET '/api/v1/analise?ano=2026' "$t1")"
conferir "logout" 204 "$(http POST /api/v1/auth/logout "$t1")"
conferir "sessão revogada após logout" 401 "$(http GET /api/v1/auth/me "$t1")"

login >/dev/null; t2="$(token 2>/dev/null || true)"
if aceite_compose run --rm -T migrate >"$tmp/migrate2.log" 2>&1; then
    registrar "PASSOU  migração repetida termina sem erro"
else
    registrar "FALHOU  migração repetida"; falhas=$((falhas + 1))
fi
aceite_compose restart >/dev/null 2>&1
aceite_compose up -d --wait >/dev/null 2>&1
conferir "após reinício, sessão e conta persistem" 200 "$(http GET /api/v1/auth/me "$t2")"
conferir "após reinício, login continua funcionando" 200 "$(login)"
rm -f "$tmp/login.json"

registrar ""
if (( falhas == 0 )); then
    registrar "RESULTADO: APROVADO (0 falhas)"
else
    registrar "RESULTADO: REPROVADO ($falhas falha(s)). Logs do aceite foram descartados junto do projeto; repita com calma."
fi
registrar "Fora do escopo deste aceite: HTTPS/nginx do host, sessões com pessoas, modelo de IA real, dados reais."
registrar "Relatório: $relatorio"
exit $(( falhas > 0 ))
