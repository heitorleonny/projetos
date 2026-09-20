#!/bin/sh
# Entrypoint do container do frontend.
#
# Gera /usr/share/nginx/html/env-config.js a partir das variáveis de ambiente
# reais do container e só então entrega o controle ao nginx.
#
# POR QUE ISTO EXISTE
#
# O Vite congela `import.meta.env.VITE_*` dentro do bundle em build time. Sem
# este passo, mudar a URL da API ou a federação servida exigiria rebuildar a
# imagem — uma imagem por ambiente e por tenant. Com ele, a mesma imagem sobe
# em qualquer lugar e lê a configuração no start.
#
# As variáveis aqui NÃO têm prefixo `VITE_`: esse prefixo é do build. Em
# runtime elas são variáveis de ambiente comuns.
#
# TUDO QUE ENTRA AQUI É PÚBLICO. O arquivo é servido ao navegador como
# qualquer outro estático. Só cabem valores que já seriam públicos de
# qualquer forma (a URL da API, a chave ANÔNIMA do Supabase, o slug do
# tenant). A SUPABASE_SERVICE_KEY não entra nesta lista em hipótese alguma —
# ela ignora Row Level Security e aqui viraria um segredo publicado.
#
# Valor vazio é escrito mesmo assim, e src/config/env.ts trata vazio como
# ausente — caindo no valor que foi embutido no bundle. É isso que faz o
# build-time continuar valendo como default da imagem.

set -eu

ARQUIVO="/usr/share/nginx/html/env-config.js"

# Escapa o que quebraria a string JavaScript: barra invertida, aspas duplas e
# quebras de linha. Nenhum dos valores esperados tem isso, mas um `env-config.js`
# malformado derruba a aplicação inteira antes do primeiro render — o custo de
# não confiar é uma linha.
escapar() {
    printf '%s' "${1:-}" | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g' | tr -d '\n\r'
}

cat > "$ARQUIVO" <<EOF
// Gerado por docker-entrypoint.sh no start do container. Não editar à mão:
// qualquer alteração aqui é perdida no próximo restart.
window.__ENV__ = {
    API_BASE_URL: "$(escapar "${API_BASE_URL:-}")",
    SUPABASE_URL: "$(escapar "${SUPABASE_URL:-}")",
    SUPABASE_ANON_KEY: "$(escapar "${SUPABASE_ANON_KEY:-}")",
    USE_MOCK: "$(escapar "${USE_MOCK:-}")",
    FEEDBACK_FORM_URL: "$(escapar "${FEEDBACK_FORM_URL:-}")",
    TENANT_SLUG: "$(escapar "${TENANT_SLUG:-}")",
};
EOF

echo "[entrypoint] env-config.js gerado — tenant: '${TENANT_SLUG:-(default do bundle)}', api: '${API_BASE_URL:-(default do bundle)}'"

exec "$@"
