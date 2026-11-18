#!/usr/bin/env bash
# Backup diário do banco de produção (pg_dump -Fc), com retenção de 14 dias.
#
#   /opt/portal-federacoes/atual/infra/deploy/vps-fejepe/backup.sh
#
# Grava em $PF_BACKUPS (padrão /var/backups/portal-federacoes) com umask 077.
# Só apaga arquivos `portal-*.dump` dessa pasta com mais de 14 dias. Não toca em
# volumes nem em outros projetos.
set -euo pipefail
umask 077
source "$(dirname "$0")/comum.sh"

RETENCAO_DIAS="${RETENCAO_DIAS:-14}"
mkdir -p "$PF_BACKUPS"
destino="$PF_BACKUPS/portal-$(date '+%Y%m%d-%H%M%S').dump"
parcial="$destino.parcial"

pf_log "backup iniciado: $destino"
if ! pf_compose exec -T postgres sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' > "$parcial"; then
    rm -f "$parcial"
    pf_log "ERRO: pg_dump falhou; nenhum backup antigo foi removido"
    exit 1
fi
# Um dump custom válido começa com "PGDMP"; arquivo vazio ou truncado é recusado.
if [[ "$(head -c 5 "$parcial")" != "PGDMP" ]]; then
    rm -f "$parcial"
    pf_log "ERRO: saída do pg_dump não é um dump válido; nenhum backup antigo foi removido"
    exit 1
fi
mv "$parcial" "$destino"
pf_log "backup concluído: $(du -h "$destino" | cut -f1)"

find "$PF_BACKUPS" -maxdepth 1 -type f -name 'portal-*.dump' -mtime +"$RETENCAO_DIAS" -print -delete \
    | while read -r antigo; do pf_log "removido por retenção: $antigo"; done
