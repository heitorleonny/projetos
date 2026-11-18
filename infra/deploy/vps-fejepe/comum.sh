# Definições comuns dos scripts do servidor. Não executar: é lido com `source`.
#
# Caminhos de produção; as variáveis PF_* podem ser trocadas só para testar os
# scripts numa máquina local (ver DEPLOY-VPS-FEJEPE.md, "Verificação local").
PF_BASE="${PF_BASE:-/opt/portal-federacoes}"
PF_ATUAL="${PF_ATUAL:-$PF_BASE/atual}"
PF_ENV="${PF_ENV:-$PF_BASE/.env.prod}"
PF_PROJETO="${PF_PROJETO:-portal-federacoes}"
PF_BACKUPS="${PF_BACKUPS:-/var/backups/portal-federacoes}"

if [[ "$PF_PROJETO" != "portal-federacoes" ]]; then
    echo "Projeto Compose inesperado: '$PF_PROJETO'. Estes scripts só operam 'portal-federacoes'." >&2
    exit 1
fi

pf_compose() {
    docker compose -p "$PF_PROJETO" \
        -f "$PF_ATUAL/docker-compose.yml" \
        -f "$PF_ATUAL/infra/deploy/vps-fejepe/compose.prod.yml" \
        --env-file "$PF_ENV" "$@"
}

pf_log() {
    printf '%s %s\n' "$(date '+%Y-%m-%dT%H:%M:%S%z')" "$*"
}
