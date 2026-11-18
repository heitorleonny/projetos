#!/usr/bin/env bash
# Restaura o backup mais recente num PostgreSQL DESCARTÁVEL e compara contagens
# com o banco de produção. Nunca toca no volume de produção.
#
#   /opt/portal-federacoes/atual/infra/deploy/vps-fejepe/restaurar-teste.sh [arquivo.dump]
#
# O container de teste tem nome fixo, sem porta e sem volume; é removido no fim
# (e só ele). Erros de GRANT/POLICY para papéis que não existem no container de
# teste são esperados e contados à parte: os dados das tabelas são o que importa.
set -euo pipefail
umask 077
source "$(dirname "$0")/comum.sh"

CONTAINER="portal-federacoes-restauracao-teste"
TABELAS=(public.federacao public.empresa_junior public.monitoramento public.metas
         public.cluster_historico public.usuario auth.users public.metrica_personalizada)

dump="${1:-$(ls -1t "$PF_BACKUPS"/portal-*.dump 2>/dev/null | head -n1 || true)}"
if [[ -z "$dump" || ! -f "$dump" ]]; then
    echo "Nenhum backup encontrado em $PF_BACKUPS." >&2
    exit 1
fi

limpar() { docker rm -f "$CONTAINER" >/dev/null 2>&1 || true; }
if docker ps -a --format '{{.Names}}' | grep -qx "$CONTAINER"; then
    echo "Já existe um container '$CONTAINER' (teste anterior interrompido). Removendo só ele."
    limpar
fi
trap limpar EXIT

senha="$(head -c 24 /dev/urandom | od -An -tx1 | tr -d ' \n')"
pf_log "restaurando $(basename "$dump") em container descartável"
docker run -d --name "$CONTAINER" --network none -e POSTGRES_PASSWORD="$senha" \
    -e POSTGRES_DB=restauracao postgres:16-alpine >/dev/null
for _ in $(seq 1 60); do
    if docker exec "$CONTAINER" sh -c '[ "$(cat /proc/1/comm)" = postgres ] && pg_isready -U postgres -d restauracao' >/dev/null 2>&1; then
        break
    fi
    sleep 1
done

docker cp "$dump" "$CONTAINER:/tmp/portal.dump" >/dev/null
set +e
erros="$(docker exec "$CONTAINER" pg_restore -U postgres -d restauracao --no-owner --no-acl /tmp/portal.dump 2>&1 | grep -c 'error:')"
set -e

contar() {  # $1 = comando psql (array em string), $2 = tabela
    local sql="SELECT CASE WHEN to_regclass('$2') IS NULL THEN 'ausente' ELSE (SELECT count(*)::text FROM $2) END"
    eval "$1 -tAc \"$sql\"" 2>/dev/null | tr -d '[:space:]'
}

falhas=0
printf '%-32s %12s %12s\n' "tabela" "produção" "restaurado"
for t in "${TABELAS[@]}"; do
    p="$(contar "pf_compose exec -T postgres sh -c 'psql -U \"\$POSTGRES_USER\" -d \"\$POSTGRES_DB\" \"\$@\"' --" "$t")"
    r="$(contar "docker exec $CONTAINER psql -U postgres -d restauracao" "$t")"
    marca=""
    if [[ "$p" != "$r" ]]; then marca="  <- diferente"; falhas=$((falhas + 1)); fi
    printf '%-32s %12s %12s%s\n' "$t" "${p:-?}" "${r:-?}" "$marca"
done
pf_log "erros do pg_restore (papéis/ACL ausentes no teste): $erros"

if (( falhas > 0 )); then
    pf_log "RESTAURAÇÃO COM DIFERENÇAS: $falhas tabela(s). Se houve escrita depois do backup, rode o backup e repita."
    exit 1
fi
pf_log "restauração conferida: contagens iguais às de produção"
