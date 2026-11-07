# Política de créditos de IA e cobrança em produção

Pesquisa consultada em 05/10/2026. Valores de planos e preços de provedores mudam; esta política separa a quota de produto do gasto financeiro real.

## Revisão comercial de 06/10/2026

**Correção em 07/10/2026:** a referência do produto é o CirandaMEJ, uma aplicação de evento em React com briefing longo, identidade visual e várias seções. O [desenho revisado](arquitetura-dashboards-aplicacoes-2026-10-07.md) substitui a interpretação anterior de composição de gráficos. Manter duas novas aplicações por federação/mês como alvo; a capacidade de ajustes e as mensalidades exigem medição de geração e revisão de código. A sugestão anterior de 30 ajustes não é franquia garantida. O contador atual de uma visualização por criação continua sendo uma configuração do piloto, sem adoção desses novos limites.

A [pesquisa e proposta revisada de planos](proposta-planos-2026-10-06.md) mantém R$ 99, R$ 149 e R$ 249 por federação como hipóteses a revalidar. Duas aplicações de dashboard e orçamento para revisão de código precisam de contabilidade própria. Os valores não foram aplicados ao catálogo ou a tenants.

A proposta também prevê franquias mensais separadas para o Nexo. Elas ainda não estão implementadas: o limite atual por minuto não estabelece orçamento mensal. A oferta pública precisa desse ajuste e da medição monetária antes de prometer a franquia. O default de 100 dashboards permanece como configuração do piloto enquanto o catálogo comercial não for adotado.

O código atual cria uma visualização por registro e não gera nem revisa uma aplicação React. A nova oferta exige fila de trabalhos, build isolado, versionamento, publicação e orçamento financeiro. Reduzir o contador atual para dois permitiria apenas duas criações de visualização. Visualizar, publicar e alterar controles manuais disponíveis deve continuar gratuito; somente uma alteração que chama o gerador utiliza o orçamento de revisão.

## Decisões

- **Unidade de produto:** 1 crédito equivale a uma geração de dashboard concluída e persistida. Cada chamada começa com uma reserva; falha na geração ou na persistência estorna a reserva. Leituras e visualizações de dashboards existentes são gratuitas. Hoje o escopo da quota cobre o recurso `dashboard`; o Nexo permanece sob seu limite operacional de chamadas por minuto.
- **Quem compartilha a quota:** a federação é o titular da quota mensal, compartilhada por seus usuários autorizados. O usuário que iniciou a geração fica no registro para auditoria, mas não recebe uma franquia independente. Assim, várias contas da mesma federação não multiplicam a capacidade contratada.
- **Quantidade inicial:** 100 créditos de dashboard por federação/mês é somente um **default de piloto**, configurável e sujeito a revisão após instrumentar uso e custo real. O limite efetivo segue esta ordem: override administrativo por federação; `plano.limite_creditos_ia_mes` quando preenchido; default piloto. Um limite de plano igual a `NULL` usa o default, não significa uso ilimitado. Os valores semeados na tabela `plano` já estão documentados como placeholders comerciais e não devem ser tratados como uma oferta aprovada.
- **Contabilidade:** o mês é UTC e a cota é congelada no primeiro uso daquele mês. Uma alteração de configuração passa a valer no próximo período já inicializado. Reservas, consumos e estornos são serializados por federação no banco; o modelo nunca escolhe o tenant nem altera a cota.
- **Pagamento do provedor:** em produção, o backend usa uma credencial de API do portal, guardada como segredo do servidor. A organização responsável pelo portal paga a fatura ou compra créditos de API; a federação consome sua quota comercial interna. Não foi criado BYOK por federação nesta fase. Nenhuma chave de IA pode ir ao navegador.
- **Teto financeiro separado:** definir alertas e um limite de gasto no provedor, monitorar consumo/token/preço por modelo, limitar tokens de entrada e saída, e interromper gerações se o saldo/cap da plataforma estiver esgotado. Créditos internos não são reais, não têm conversão cambial nem garantem custo constante: uma geração longa ou um modelo mais caro ainda custa mais ao operador que outra geração.

## Por que a assinatura Codex não alimenta o backend

A documentação oficial informa que ChatGPT e API Platform têm faturamentos separados, e que créditos de uso de funcionalidades Codex são distintos de créditos de API. Portanto, não existe um endpoint de produção que permita ao Portal enviar requisições em nome da assinatura Codex desta sessão. A fase de desenvolvimento pode usar a API já configurada no servidor; isso continua sendo uso pago da API, separado da assinatura Codex. Não conecte cookies, sessão local ou credenciais pessoais do Codex a um serviço multi-tenant.

## Por que a quota é da federação

O dashboard é um artefato de gestão da federação, pode ser compartilhado com a equipe e eventualmente publicado. Uma quota por usuário daria ao mesmo tenant franquias multiplicadas pelo número de contas, dificultando o orçamento e a comparação entre federações. O serviço salva o usuário solicitante para auditoria, porém desconta do contador mensal único do tenant.

Uma unidade por geração oferece orçamento previsível de produto, mas **não prevê dólares**. Após observar chamadas reais, o portal deve revisar o default de 100, a composição da quota e o gasto por geração. Para custo mais uniforme, mantenha um modelo econômico, limite de tokens e uma API financeira da plataforma com hard cap próprio. Não prometa que 100 créditos custam um valor fixo antes dessa medição.

## Separação do Nexo

A migração 18 aplica ao Nexo um limite operacional de janela: 6 chamadas por usuário e 30 por federação por minuto, independente da assinatura do plano. Isso reduz abuso e picos; não é franquia mensal nem medição de gasto. A migração 19 adiciona apenas a quota mensal de criação de dashboards. As duas políticas têm contadores e propósitos diferentes.

## Fontes

- OpenAI Help Center, [Managing billing for ChatGPT and the API platform](https://help.openai.com/en/articles/9039756-managing-billing-settings-on-chatgpt-web-and-platform): contas e cobranças separadas; uso de API cobrado à parte por tokens e recursos.
- OpenAI Help Center, [Using Credits for Flexible Usage in ChatGPT (Personal plans)](https://help.openai.com/en/articles/12642688): os créditos de uso compatível com Codex não são créditos de API.
- OpenAI Help Center, [Setting up and managing prepaid API billing](https://help.openai.com/en/articles/8264644-how): saldo pré-pago, expiração e atraso de processamento; o saldo zerado não deve ser tratado como corte instantâneo.
- OpenAI Help Center, [Troubleshooting API usage and spend limits](https://help.openai.com/en/articles/6614457-why-am-i-getting-an-error-message-stating-that-i-ve-reached-my-usage-limit): limites de gasto/alertas e possibilidade de pequeno excedente por atraso de enforcement.
- OpenRouter, [API keys](https://openrouter.ai/docs/api/api-reference/api-keys/create-keys): limites de gasto por chave e período de reinício.
- OpenRouter, [Usage and billing support](https://openrouter.ai/support): custo calculado pelo uso do provedor/tokens e retorno de informações de uso; preços variam por modelo.
- OpenRouter, [Get request and usage metadata for a generation](https://openrouter.ai/docs/api/api-reference/generations/get-generation): registro de tokens e custo total por geração.

## Operação e limites atuais

1. A migração `infra/db/init/19-creditos-ia-tenant.sql` cria um default de piloto de 100, overrides por federação, contadores mensais e primitivas internas de reserva. Elas não são executáveis pelo cliente autenticado. A migração `20-dashboards-evento-ia.sql` persiste o dashboard e consome a unidade na mesma transação; o cliente não escreve diretamente na tabela. A atualização direta das tabelas de configuração deve ser feita pelo administrador do banco, não por payload da API.
2. No Postgres local existente, os scripts `init/` não rodam novamente sem recriar o volume. Aplicar a migração 19 individualmente conforme `infra/db/README.md`; conferir logs por `ERROR`, `FATAL` e `WARNING`. Em Supabase hospedado, aplicar a migração depois da 18 e confirmar o papel `ia_limitador` e as permissões/RLS no projeto.
3. Não foi feita chamada de modelo nesta tarefa. A verificação de consumo fica determinística: as RPCs reservam sob JWT, fazem estorno idempotente somente enquanto pendente, e confirmam consumo uma vez. Testes concorrentes e integração com o projeto Supabase devem ocorrer quando o ambiente de banco da migração estiver disponível.
4. O contador grava unidade de produto, tenant, usuário, recurso, período e estado; não grava prompt ou resposta. O custo monetário real ainda depende de capturar os dados `usage`/`total_cost` do adaptador de modelo e conciliá-los com o painel do provedor. Isso não faz parte da unidade do piloto.
