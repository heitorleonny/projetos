# Preparação VPS — 13/10/2026

Heitor escolheu VPS + Supabase gerenciado, considerando Hostinger ou AWS.
Preparação local concluída; nenhum provedor, conta, plano ou domínio provisionado.

## Resultado

Criado `infra/deploy/VPS.md` com pré-requisitos Ubuntu/Docker/Compose, mapa
Hostinger/EC2, DNS A/AAAA, regras de firewall, espaço em disco, configuração privada,
subida, aceite externo, backups de certificados e Supabase e rollback de imagens.
`infra/deploy/README.md` aponta esse caminho como próxima opção de implantação.
Manifesto `compose.aws.yml` conserva seu nome histórico e já era portátil.
`check-env.py --mode vps` é alias explícito da mesma configuração AWS existente.

Corrigida propagação de protocolo externo: Caddy encaminha `/api/*` diretamente
à API, mas Uvicorn por padrão só confia no proxy loopback; o Caddy tem IP de
container. `FORWARDED_ALLOW_IPS=*` no backend habilita leitura desses headers.
A confiança fica limitada operacionalmente à rede Docker: API sem porta no host;
não expor 8000 ou adicionar serviços não confiáveis nessa rede.

## Fontes e decisões

[Hostinger](https://www.hostinger.com/support/8306612-how-to-use-the-docker-vps-template-at-hostinger/)
documenta template Ubuntu 24.04 com Docker. O guia local exige plugin Compose v2;
colagem isolada do manifesto no Docker Manager não basta para contextos de build
do monorepo. [Docker Ubuntu](https://docs.docker.com/engine/install/ubuntu/) e
[firewalls](https://docs.docker.com/engine/network/packet-filtering-firewalls/)
orientam instalação e a limitação do UFW diante de portas publicadas.
Os [headers de proxy Caddy](https://caddyserver.com/docs/caddyfile/directives/reverse_proxy)
e Uvicorn instalado foram inspecionados para a correção de protocolo.
[Backups Supabase](https://supabase.com/docs/guides/platform/backups) sustentam
o procedimento separado de backup do banco/Storage/roles. Nenhuma retenção
contratada foi presumida. Dimensionamento no guia é hipótese para piloto,
não capacidade medida ou garantia de desempenho.

## Validação local

- Compose AWS/VPS validou com `config --quiet` usando exemplo sintético.
- Config Uvicorn na imagem runtime confirmou que a variável é respeitada.
- Sete testes do preflight passaram, zero falhas/pulados.
- Caddyfile previamente validado nesta sessão; smoke das imagens finais passou,
  conforme [preparação integrada](preparacao-deploy-2026-10-13.md).

Não foi emitido certificado público nem simulado firewall/DNS do provedor.
A confirmação de HTTPS, certificado, SMTP, Auth, RLS e ingestão pelo domínio
real permanece no aceite operacional do destino. Não houve alteração de banco,
recurso remoto, commit, push ou chamada de IA paga nesta frente.
