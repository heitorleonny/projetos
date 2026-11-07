# Cronograma conferido com o artefato de Heitor

> **Retrato histórico de 13/10.** Em 23/10, Heitor retirou dashboards gerados
> por IA do escopo. A semana dedicada a eles e a pendência de geração de aplicações
> abaixo deixam de orientar a execução. O [plano de retomada](retomada-escopo-reduzido-2026-10-23.md)
> prevalece para o trabalho atual. Não houve nova leitura nem alteração do artefato externo.


Fonte: [Portal das Federações — plano de execução do TCC](https://claude.ai/artifact/C96RYHq62ty9ZY7fHbx3Gs),
lido em 13/10/2026 na sessão autenticada do Brave. O acesso público do navegador
interno exigiu login. Estado exibido: semana 4 (12–18/10), 43 de 70 tarefas marcadas.
Os checkboxes são salvos no navegador; não foram alterados nesta revisão. Não usar
43/70 como medida de cobertura técnica.

## Calendário da fonte

| Semana | Período de 2026 | Frente prevista |
|---|---|---|
| 4 | 12–18/10 | papéis, personalização, segundo tenant, referencial e metodologia |
| 5 | 19–25/10 | segundo tenant e início do assistente |
| 6 | 26/10–01/11 | IA, medição e agendamento de sessões; definir IA avaliada |
| 7 | 02–08/11 | dashboards, medição e escrita de resultados |
| 8 | 09–15/11 | sessões P1–P3 e consolidação dos resultados |
| 9 | 16–22/11 | monografia completa e revisão final |
| 10 | 23–29/11 | folga, ajustes, logística e ensaio |

Entrega indicada: 30/11/2026, sem nova confirmação institucional. O calendário
do artefato prevalece sobre datas sugeridas no contexto local para esta execução;
as decisões posteriores sobre produto e arquitetura continuam nos ADRs/estado.

## Reconciliação com as evidências locais

| Frente do artefato | Marcação na fonte | Situação conferida |
|---|---|---|
| Fundação de segurança | 4/4 | testes locais e demo repetidos; destino remoto não verificado |
| Modelagem/isolamento/papéis | 20/20 | schema/RLS/papéis implementados; operador plataforma é exceção administrativa documentada |
| Personalização | 5/5 | branding e runtime existentes; comunidade preservada como configuração FEJEPE, diferente do texto do artefato |
| Segundo tenant | 6/6 | demo local existente; ETL núcleo/federação/histórico segue faltando apesar de checkbox ETL marcado |
| Assistente | 0/5 | Nexo já nomeado, integrado e com catálogo/JWT/RLS; avaliação real histórica 17/21 planos exatos, sem reavaliar modelo nesta sessão |
| Dashboards | 0/4 | base de catálogo/persistência existente; geração de aplicações React definida em 07/10 ainda não concluída |
| Avaliação | 0/10 | verificações técnicas locais existentes/repetidas; caracterização e roteiro preparados; sessões, produção e homologação pendentes |
| Escrita | 8/13 | sete capítulos existentes e revisados; dados humanos e decisões acadêmicas ainda não disponíveis |
| Folga/defesa | 0/3 | depende de calendário institucional e ensaio pelo autor |

O texto do artefato sobre corte de 100 EJs esconder especificamente a população
de risco é uma interpretação histórica invalidada pela revisão de 29/09 em
`docs/achado-9.17-limites-com-segundo-tenant.md`. A medição de 8,82 s registrada em
04/10 representa reimportação e bateria técnica em ambiente preparado, não custo
completo de provisionar uma federação. Ambas as distinções precisam acompanhar
qualquer atualização do cronograma.

## Entregas desta execução e próximos critérios

- Revisão de coerência e correção factual do texto: relatório externo
  `../../revisao-tcc-2026-10-13.md`; compilação visual depende de TeX disponível.
- Isolamento do estado frontend e apresentação da Comparação:
  `pendencias-implementacao-2026-10-13.md`.
- Caracterização sintética das cinco funções: `caracterizacao-2026-10-13.md`.
- Preparação de regressão GET: `regressao-producao-preparacao-2026-10-13.md`.
  Para fechar, fornecer acessos de leitura e dados equivalentes e comparar também
  SDE/ritmo/rankings, com explicação privada de toda diferença.
- VPS + Supabase é a escolha de Heitor nesta sessão; preparação operacional em
  `preparacao-vps-2026-10-13.md`. Para fechar homologação, definir VPS/domínio,
  configurar Supabase/SMTP e verificar pelo endereço externo.
- Roteiro e registros P1–P3 em `../../monografia/avaliacao/`; sessão de 60 minutos
  complementar em `../../validacao/protocolo-sessoes-2026-10-13.md`.
  Agendamento, consentimento efetivo e parecer dependem das pessoas responsáveis.

Não executar compras, publicar dados, convidar participantes, escolher resultado
acadêmico ou alterar regras de negócio para preencher uma marcação. O gerador de
aplicações precisa de runtime isolado, fila/versionamento, projeção publicada,
orçamento e avaliação adversarial; um gráfico selecionado por catálogo não fecha
esse escopo. O orçamento/provedor da geração e qual IA entra na avaliação formal
continuam decisões abertas, conforme o próprio cronograma.
