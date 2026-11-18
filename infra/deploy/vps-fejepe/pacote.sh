#!/usr/bin/env bash
# Gera o pacote de fontes de uma tag Git, para enviar à VPS.
#
#   infra/deploy/vps-fejepe/pacote.sh v2026.11.17 [pasta-de-saída]
#
# Usa `git archive`: só entram arquivos versionados na tag. Ficam de fora, por
# construção, .env*, dados reais (../dados fica fora do repositório),
# node_modules, dist e caches, que não são versionados. O script confere isso no
# pacote gerado e imprime o SHA-256 para conferir no servidor.
set -euo pipefail

tag="${1:-}"
saida="${2:-.}"
if [[ -z "$tag" ]]; then
    echo "Uso: $0 <tag> [pasta-de-saída]" >&2
    exit 2
fi
if ! git rev-parse -q --verify "refs/tags/$tag" >/dev/null; then
    echo "Tag '$tag' não existe. Crie com: git tag -a $tag -m 'Release $tag'" >&2
    exit 1
fi

raiz="$(git rev-parse --show-toplevel)"
mkdir -p "$saida"
arquivo="$(cd "$saida" && pwd)/portal-federacoes-$tag.tar.gz"
git -C "$raiz" archive --format=tar.gz --prefix="portal-federacoes-$tag/" -o "$arquivo" "refs/tags/$tag"

# Defesa extra: recusa o pacote se algo sensível tiver sido versionado por engano.
proibidos="$(tar -tzf "$arquivo" | grep -E '(^|/)\.env($|\.)|(^|/)node_modules/|(^|/)dist/|__pycache__|\.dump$|\.xlsx$' \
    | grep -vE '\.env\.example$|env\.prod\.example$|(aws|render|vercel)\.env\.example$|/tests/fixtures/' || true)"
if [[ -n "$proibidos" ]]; then
    rm -f "$arquivo"
    echo "Pacote recusado: arquivos que não deveriam ir ao servidor:" >&2
    echo "$proibidos" >&2
    exit 1
fi

if command -v sha256sum >/dev/null; then
    hash="$(sha256sum "$arquivo" | cut -d' ' -f1)"
else
    hash="$(shasum -a 256 "$arquivo" | cut -d' ' -f1)"
fi
echo "Pacote: $arquivo"
echo "Commit: $(git rev-parse "refs/tags/$tag^{commit}")"
echo "SHA-256: $hash"
