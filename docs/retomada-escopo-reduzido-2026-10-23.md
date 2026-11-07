# Retomada do TCC com escopo reduzido

Data: 23/10/2026. Decisão de Heitor: retirar a parte dos dashboards de IA para
facilitar a conclusão. Este plano substitui a frente de geração de dashboards dos
planos anteriores; não modifica objetivos acadêmicos nem registra aceite do orientador.

## O que entregar

O objeto continua sendo a transformação do Portal FEJEPE em uma plataforma
multi-tenant para federações de empresas juniores. A pergunta central segue ligada
às decisões arquiteturais e ao isolamento quando cada cliente alimenta sua base.

| Permanece no recorte | Critério verificável |
|---|---|
| Autenticação, papéis e isolamento por federação | testes de autorização e RLS, incluindo segundo tenant, com resultados e ambiente registrados |
| Branding e administração das federações | demonstração de configuração por tenant e limites de cada papel |
| Ingestão e regras de indicadores existentes | contrato de entrada, erros compreensíveis, testes de cálculo e explicação de divergências |
| Painéis convencionais, comparação, indicadores e eventos | navegação e números coerentes com os services; nenhuma geração de código exigida |
| Nexo | perguntas sobre dados autorizados, catálogo validado, limites e evidência de avaliação do assistente |
| Avaliação e monografia | rastrear objetivos para artefato, testes e evidências humanas efetivamente coletadas |

Saem do escopo ativo: geração/edição de aplicações React por IA, briefing para
criação de dashboards, publicação por slug de aplicações geradas, fila e sandbox
de geração e franquia comercial de dashboards. Não são requisitos de conclusão.
Migrações e relatórios já existentes são histórico; removê-los poderia quebrar a
cadeia SQL e não é necessário para reduzir o produto.

Nexo permanece uma frente de IA distinta. Mantê-lo no produto não equivale a
confirmar objetivo específico próprio ou aprovação acadêmica: o enquadramento e o
peso da avaliação do assistente ainda precisam ser alinhados com o orientador.

## Retomada por prioridades

| Ordem | Trabalho | Evidência necessária para fechar |
|---|---|---|
| 1 | Consolidar a retirada dos dashboards de IA da experiência e do contrato ativo | ausência de atalhos/formulários ativos de geração; painéis convencionais e Nexo preservados; verificações locais aprovadas |
| 2 | Verificar a base atual e tratar apenas falhas que impedem a demonstração | execução de `make check`, resultados completos sem omitir skips e registro de limitações; não rodar verificações de banco concorrentes |
| 3 | Preparar roteiro curto de demonstração de dois tenants | login, branding, consulta, ingestão e tentativa de acesso cruzado, com dados autorizados ou sintéticos |
| 4 | Fechar lacunas de regras e evidências já identificadas | registrar a decisão de cada divergência relevante; separar caracterização técnica de validação humana |
| 5 | Executar avaliação com participantes e orientador | consentimento, sessões efetivas, registros anonimizados e análise; agendamento não conta como avaliação |
| 6 | Escrever e revisar a monografia pelo escopo reduzido | objetivos, implementação, resultados e limitações coerentes; não alegar que a geração de dashboards foi concluída |

As etapas 3–6 podem avançar com documentação e preparação enquanto falhas da base
são corrigidas. Evitar novas funcionalidades que não resolvam impedimento concreto
da demonstração ou da pergunta de pesquisa. Não impor cronograma de desenvolvimento
de IA como pré-requisito para iniciar a escrita.

## Pendências que não somem com o corte

Os relatórios de 13/10 registram lacunas de ingestão de núcleo/federação/histórico,
regras de negócio, regressão em produção, homologação hospedada e sessões P1–P3.
Reconfirmar a necessidade de cada uma contra os objetivos e o roteiro; não tratar
checkbox antigo como evidência de execução. Se uma frente adicional não for
necessária ao recorte, documentar a limitação em vez de inventar sua conclusão.

VPS + Supabase consta como direção de homologação em 13/10, sem prova de publicação
remota neste documento. Hospedagem, acessos, regressão em produção e avaliação real
de modelo exigem sua própria execução autorizada e evidência; verificações locais
não as substituem. A retirada dos dashboards não autoriza gastos ou deploy.

A data de entrega registrada no contexto é 30/11/2026 e precisa de confirmação
institucional pelo autor. Usar a ordem acima como plano de trabalho; reservar as
semanas finais à avaliação, escrita, revisão com o orientador e ensaio. O calendário
anterior de 13/10 é histórico e não foi revalidado em fonte externa nesta retomada.

## Como usar as evidências existentes

- [Estado consolidado](../ESTADO-PORTAL-PARA-TCC.md): conferir ambiente, data e limites antes de citar um resultado.
- [Cronograma de 13/10](cronograma-conferido-2026-10-13.md): referência histórica, sem a frente de dashboards no plano atual.
- [Caracterização de 13/10](caracterizacao-2026-10-13.md): evidência técnica, sem substituir sessões com usuários.
- [Preparação da VPS](preparacao-vps-2026-10-13.md): preparação não prova implantação.
- [Arquitetura dos dashboards](arquitetura-dashboards-aplicacoes-2026-10-07.md): desenho histórico retirado; conservar para explicar o corte de escopo.

Este documento é um plano de retomada, não relatório de testes nem aprovação
acadêmica. A revisão da monografia deve preservar a cronologia e distinguir o que
foi projetado, implementado, verificado localmente e validado por pessoas.
