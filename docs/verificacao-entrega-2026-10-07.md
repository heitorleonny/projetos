# Entrega integrada — Portal das Federações

Data: 07/10/2026, America/Recife. Preparação local; sem publicação remota.

## Resultado

Repositório existente preservado. Código organizado em backend, frontend e ferramenta
auxiliar. Referências operacionais, workspace, docs e OpenAPI (28 rotas) atualizados.
Todo o código atual, inclusive arquivos novos, pode ser entregue por `make package`.
O pacote exclui ambientes, builds, dependências, dados reais e relatórios JSON brutos.
Nenhum commit/push/reset/stash ou alteração na monografia foi executado.

## Evidências finais

| Verificação | Resultado | Limite |
|---|---|---|
| `make test` | 567 passaram, 0 falhas, 0 pulados; 7 avisos | SQL descartável, não ambiente remoto |
| `npm run check` em frontend | 15 testes passaram, nenhum pulado; lint/build passaram | Testes Node e compilação; não auditoria integral de usabilidade |
| `npm run build` em tools/cluster-calculator | Passou | Aplicação auxiliar fora do deploy principal |
| `npm audit` em ambos pacotes Node | 0 vulnerabilidades conhecidas | Consulta à base nesta data |
| `pip-audit` do lock de produção | 55 dependências, 0 vulnerabilidades, 0 ignoradas | Não audita SO, Supabase externo ou configuração |
| `make demo-smoke` | Passou Auth, tenant, master, endpoints e recusas cruzadas | Supabase real local com contas existentes |
| `make demo` | Passou, dados preservados | Conferência da estrutura após renomeação |
| Build runtime API/frontend | Passou | Imagens locais; API final FastAPI 0.133.1/Starlette 1.3.1 |
| `python3 infra/deploy/smoke-containers.py` | Passou PORT, UID, ausência pytest, SPA, env sem cache, proxy401 e docs404 | Configuração sintética; não acessa produção |
| Compose/Caddy/Render schema/CI YAML | Configurações validadas | Não provisiona recursos; CI não foi disparada no GitHub |
| `git diff --check` | Passou | Verificação textual |

Foi necessário corrigir dependências Node e Python com advisories conhecidos e
repetir testes/builds após as atualizações. Não usado `npm audit fix --force`.
Sharp atualizado explicitamente para 0.35.5; API atualizada com suporte compatível
a Starlette corrigido. Dependências Python têm locks com hashes; runtime não contém
pytest. Auditorias não foram silenciadas.

Os SQLs históricos não foram editados. A migração aditiva 23 corrige ACLs de RPCs
IA sob dono não superusuário. O migrador mantém membership temporária para concluir
ownership/ACLs e restaura concessões anteriores. A demo recebeu 19/20 e 23, sem
reset ou substituição de usuários. O executor de demo nova usa esse mesmo migrador;
bancos legados sem ledger são recusados em vez de reaplicar a migração04.

Bootstrap de operador novo verificado com banco real e Auth simulado: senha sem
eco/argumentos, destino confirmado, conta existente recusada, prova de alinhamento
Auth/banco e compensação após falha. Nenhuma conta remota foi criada.

## Implantação

[Guia](../infra/deploy/README.md) e manifestos para Vercel/Render/Supabase ou
aplicação em máquina AWS com Supabase gerenciado. Ainda dependem do provedor
escolhido: credenciais, domínio, hook Auth, SMTP e verificação pública com duas
federações. Não foi implementado Supabase self-hosted na AWS sem essa decisão.

Nenhum modelo real ou pago foi chamado; testes determinísticos não comprovam
qualidade universal de interpretação. As pendências de indicadores/regras e de
avaliação humana permanecem separadas desta entrega técnica.

Verificação detalhada: [backend](verificacao-backend-entrega-2026-10-07.md).
