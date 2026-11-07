# Portal das Federações — estado consolidado para a escrita do TCC

**Atualizado em:** 23/10/2026, America/Recife (redução de escopo; consolidações anteriores preservadas como histórico).  
**Finalidade:** arquivo de referência para anexar ao projeto de escrita no Claude e atualizar os capítulos conforme o portal evolui.  
**Base:** código local e documentos de implementação/verificação identificados abaixo.  
**Checkout inspecionado:** `feat/painel-admin`, HEAD `e84fa5b`, com numerosas alterações e arquivos novos ainda não commitados.

Este documento substitui as descrições de **estado de implementação** de 03/10 presentes em `CONTEXTO-TCC.md`. O contexto continua sendo referência para pergunta de pesquisa, objetivos, método e invariantes. O conteúdo antigo de `CLAUDE.md` sobre previsão de risco é histórico abandonado.

Os resultados de testes abaixo foram **registrados nas tarefas anteriores**. Na consolidação documental de 05/10, foram lidos os relatórios e inspecionado o código; não foram repetidas as suítes, as cargas nem chamadas ao modelo. O código está em evolução: um relatório aprovado comprova a versão que ele verificou, não toda alteração posterior.

## Decisão vigente — retomada em 23/10/2026

Por pedido direto de Heitor, **dashboards gerados por IA foram retirados do escopo
ativo do produto e do TCC**. Permanecem painéis convencionais, indicadores,
comparação, eventos, ingestão, arquitetura multi-tenant e assistente Nexo.
Referências posteriores neste arquivo a geração, publicação e créditos de
dashboards descrevem o histórico, não requisitos atuais de conclusão.

Mudanças locais: seção de geração e rota pública removidas do frontend; API de
dashboards desregistrada; administração sem oferta/edição dessas cotas; contrato
OpenAPI atualizado. Módulos internos inativos, migrações e testes históricos de
banco foram preservados para não apagar dados nem reescrever migrações aplicadas.
Isso não revoga interfaces SQL de um Supabase já existente nem modifica um destino
remoto: qualquer revisão dessas permissões é uma atividade separada.

A monografia teve introdução, metodologia, desenvolvimento e conclusão alinhados
ao corte. O plano de retomada está em
[retomada com escopo reduzido](docs/retomada-escopo-reduzido-2026-10-23.md).
Não houve commit, publicação, chamada de modelo pago ou avaliação humana.

Verificações desta alteração: frontend com **20 testes aprovados, 0 falhas e 0
pulos**, lint e build aprovados; backend isolado com **25 testes aprovados, 0
pulos**, incluindo ausência das cinco rotas retiradas e preservação das rotas de
Nexo/eventos/indicadores. Dois avisos de depreciação no teste isolado.
Verificação estática da monografia: 14 arquivos, 44 citações/chaves válidas,
nenhuma referência/estrutura ausente e **16 marcadores pendentes**.
A compilação PDF pelo editor foi iniciada e interrompida durante a preparação/
download das dependências LaTeX; nenhum PDF foi validado nesta retomada.
A suíte completa de banco foi tentada, mas o Docker não respondeu nem à consulta
de versão; a execução bloqueada foi interrompida. Não há novo resultado de RLS
nem de integração completa nesta retomada. Resultados de 13/10 abaixo são históricos.

## 1. Orientação para o Claude responsável pela escrita

Use este arquivo para revisar e acrescentar conteúdo ao texto existente, preservando a estrutura e o estilo adotados por Heitor. Não presuma quais capítulos já estão escritos: consulte o texto efetivamente fornecido. Para cada acréscimo, diferencie **decisão de arquitetura**, **implementação**, **resultado medido** e **limitação**.

- A contribuição central é transformar um portal de uma federação em uma plataforma multi-tenant com isolamento de dados. IA e ingestão fazem parte dessa arquitetura; previsão de risco não é o objeto atual.
- “Implementado localmente” não significa publicado, homologado, validado por usuário real ou pronto para produção.
- Não converta uma demonstração técnica em avaliação de usabilidade, aceite institucional ou prova de melhoria de gestão.
- Um número precisa de data, ambiente, procedimento e fonte. Não misture a exportação de setembro com a de outubro ou resultados de versões diferentes do modelo.
- Não publique nomes de EJs associados a desempenho individual, CNPJ, credenciais ou capturas de dados reais sem a autorização apropriada. Use exemplos sintéticos e resultados agregados/anônimos.
- Não invente referências bibliográficas. Os ADRs e relatórios locais são evidências do artefato; as fontes teóricas devem ser conferidas separadamente. Se faltar referência, use `[CITAR: assunto]`.
- Marque `[CONFIRMAR]` para fatos sem evidência e `[DECIDIR]` para escolhas acadêmicas ainda abertas. A inclusão de IA no título ou em um objetivo específico depende de Heitor e do orientador.

## 2. Escopo acadêmico vigente

Conforme `CONTEXTO-TCC.md`, trata-se do TCC de Bacharelado em Sistemas de Informação da UFRPE, trilha Graduação-Tecnologia, orientado pelo professor Lucas Cambuim, com entrega indicada para **30/11/2026**. Esses dados vêm do contexto do projeto; esta revisão não os confirmou com a instituição.

Título de referência no contexto: **Portal das Federações: uma arquitetura multi-tenant para gestão de desempenho em redes de empresas juniores**. Não tratar sugestões posteriores de título como aprovação definitiva.

Pergunta de pesquisa registrada: **quais decisões de arquitetura multi-tenant são necessárias para transformar um sistema single-tenant em SaaS, e como garantir isolamento de dados quando é o próprio cliente quem alimenta a base?** Uma questão adicional trata do que quebra quando o segundo tenant tem outra ordem de grandeza.

O método declarado é Design Science Research. Os objetivos abrangem comparar estratégias de isolamento, distinguir regras universais de configurações de federação, implementar multi-tenancy, externalizar configurações, verificar isolamento e validar o artefato com outra federação. Sessões com P1–P3 e orientador são planejamento de validação; não há, nas fontes desta consolidação, resultado final dessas sessões.

## 3. Visão do produto e arquitetura

O portal centraliza cadastro de empresas juniores, metas anuais e monitoramento mensal para acompanhamento estratégico da rede. O tenant é a **federação**. Núcleos são agrupamentos internos; regras nacionais de cluster, ritmo e SDE não são customizadas por tenant.

| Camada | Implementação |
|---|---|
| Interface | React 19, TypeScript, Vite, React Router, Tailwind, TanStack Query, Axios e Recharts |
| Autenticação | Supabase Auth; JWT validado pelo backend |
| API | FastAPI, Pydantic; routers, services e utilitários separados |
| Persistência | PostgreSQL/Supabase, schema compartilhado, `federacao_id`, RLS e índices por tenant |
| Ingestão | Python, contrato versionado, leitura/transformação/carga, psycopg e staging com proveniência |
| IA | Intérprete de planos tipados, catálogo fechado, adaptador HTTP de provedor compatível e execução no backend |
| Ambientes | Laboratório PostgreSQL, demo Supabase completa e banco descartável de testes |

O cliente de leitura de cada requisição utiliza chave pública e JWT do usuário. O backend aplica filtro explícito e o PostgreSQL aplica RLS como camadas independentes. O modelo de IA não escolhe federação, identidade ou papel. A exceção da chave de serviço permanece restrita ao serviço de convites, após a escrita autorizada pela RLS.

### Papéis

| Papel | Alcance |
|---|---|
| `membro` | Leitura dos dados estratégicos da própria federação |
| `admin` | Leitura e administração autorizada da própria federação, usuários, importação e aparência |
| `plataforma` | Administração de federações/usuários/cargas conforme ADR-003; dados estratégicos continuam limitados ao tenant vinculado |

Nas escritas administrativas, papel, vínculo e situação ativa devem ser conferidos no banco, em vez de confiar exclusivamente em um claim antigo do token.

## 4. Funcionalidades existentes

| Área | O que já existe | Evidência principal |
|---|---|---|
| Visão geral | Lista de EJs, busca, filtros, paginação, resumos do recorte completo e exportação | `src/features/dashboard/`; auditoria de métricas |
| Perfil da EJ | Metas, indicadores, séries mensais, ritmo, índices e projeções | `src/features/empresa/`; services de empresa/cálculo |
| Evolução de cluster | Cluster oficial, índices calculados, tracking e acompanhamento de metas | `src/features/cluster-track/` |
| Comparação | Indicadores das EJs entre anos, filtros e exportação; anos sem monitoramento identificados | `src/features/comparacao/` |
| Indicadores | Panorama da federação, distribuição de cluster, ritmo, ranking e cenários SDE | `src/features/indicadores/`; `rede_service.py` |
| Simulação | Cenários hipotéticos de subidas/descidas com totais vindos da API | `src/features/simulacao/`; ainda há regra local, ver pendências |
| Eventos | Metas e acompanhamento dos eventos disponíveis para o tenant; Ciranda específica da FEJEPE | `src/features/eventos/`; `evento_service.py` |
| Administração | Usuários, convites, importação com simulação e histórico; federações para operador; aparência da própria federação | `src/features/admin/`; ADR-003 e ADR-006 |
| Primeiro acesso | Guia em três etapas, adiamento e conclusão por conta/navegador; reabertura pelo menu; fluxo de senha do convite | `src/features/onboarding/`; relatório de onboarding |
| Nexo | Perguntas em linguagem natural, continuidade limitada, esclarecimentos, fontes e contexto visível | `app/ia/`; `src/features/assistente/`; ADR-004/005 |

Os caminhos de frontend da tabela são relativos a `frontend/`; os arquivos de backend estão em `backend/app/`.

### Branding, paleta e interface

Nome, slogan, logo, ano de referência e cores são configuração de federação. A marca após login segue a federação do usuário; a configuração do deploy vale para o acesso sem sessão. A migração 17 acrescenta cores secundária e de acento. Administração → Aparência permite prévia, salvamento e restauração de até três cores, compartilhadas com a equipe. Sessões abertas atualizam metadados ao ganhar foco ou periodicamente.

A escrita da paleta usa operação limitada à própria federação e às colunas de cor, evitando uma política de UPDATE ampla que permitiria alterar nome ou status. A troca de tenant remove rampas anteriores. Há testes de contraste de controles e links; isso **não equivale a auditoria WCAG completa**.

A revisão de 05/10 adotou superfícies sólidas, títulos simples, cartões compactos, menos efeitos decorativos, foco visível e tratamento de movimento reduzido. Os rótulos de navegação passaram a explicar a função das páginas, mantendo as rotas compatíveis.

### Fotos e logos de EJs

O campo `foto_url` já existia no banco e era propagado pela API. A investigação documentada de nove XLSX e onze abas não encontrou fonte de fotos/logos. Não houve backfill nem invenção de coluna no contrato. A ingestão preserva fotos existentes. O componente valida URLs e assets locais seguros, mantém iniciais como fallback e trata falha da imagem. A obtenção de uma fonte confiável de imagens permanece pendente.

### Onboarding

Atualização de 06/10: a visita abre cada aba real, com explicações e avanço/retorno.
Ao terminar, oferece personalização opcional com seletor e hexadecimal `#RRGGBB`,
prévia e salvamento explícito da paleta compartilhada, restrito a administradores.
Visão geral, Indicadores e Eventos ficam visíveis; outras análises foram agrupadas
em **Análises**, e administração/ajuda/saída em **Minha conta**. A troca de abas
internas da Administração preserva o guia. Build/lint e 11 testes Node passaram;
as sete páginas foram percorridas na demo FEJEPAR, e hexadecimal inválido, prévia,
menus e layout móvel foram conferidos. Não houve nova suíte backend nem gravação
da paleta. Evidência: [visita guiada de 06/10](docs/onboarding-visita-guiada-2026-10-06.md).

Primeira versão (04/10):

O primeiro acesso a rota protegida apresenta sua rede, os recursos e primeiras ações. A conclusão fica em armazenamento local por ID da conta; adiar vale na sessão da aba. Não há sincronização entre dispositivos. Armazenamento bloqueado tem fallback em memória, e o retorno preserva rota, filtros e âncora. O guia não concede permissões. Foram corrigidos o aviso repetido a cada login, a preferência global entre contas, textos desatualizados e tratamento de exceções dos formulários. O fluxo completo de convite/alteração de senha não foi executado manualmente nessa tarefa.

## 5. Ingestão e dados

A exportação do Portal BJ é nacional e acumulada. A carga suporta modo nacional explícito ou recorte obrigatório por federação; não há escolha implícita de escopo. O contrato valida colunas/tipos/domínios, a transformação organiza cadastros, metas, fatos e cluster histórico, e a carga aplica upserts em transação sob RLS. Há simulação com rollback e staging com arquivo, hash, data e proveniência. Ausência de EJ numa exportação não autoriza apagar registros anteriores.

O nível implementado é **EJ**. O schema permite donos EJ/núcleo/federação com FK e restrição de exclusividade, mas isso não prova que as planilhas com fatos próprios de núcleo/federação já sejam ingeridas. Essa ingestão e o despivotamento do histórico `RESULTADO` 2016–2024 permanecem pendentes nas fontes consultadas.

### Recorte medido em 04/10

Fonte: `docs/auditoria-segundo-tenant-2026-10-04.md`. Os números são desse relatório, não nova medição desta revisão.

- Exportação de 04/10: **1.502 EJs**, 10 meses, **15.020 linhas**, 27 federações.
- Demo após upsert: **1.507 EJs e 15.065 fatos de 2026**, porque cinco EJs ausentes na nova exportação e seus fatos anteriores foram preservados.
- FEJEPE: 43 EJs/430 fatos. FEJEPAR: 139 EJs/1.390 fatos, sete núcleos; 22 EJs ligadas ao Núcleo Maringá.
- Verificação autenticada de nove tabelas via Auth/API/PostgREST não encontrou cruzamento de linhas; perfil de EJ alheia retornou 404.
- Reimportação idempotente FEJEPAR em ambiente preparado: **4,39 s**. Bateria Auth/API/PostgREST: **4,43 s**. Soma das duas etapas: **8,82 s**.
- **Zero linhas de lógica de aplicação específicas para FEJEPAR** nessa ativação. Federações e núcleos já estavam configurados em seeds.

Essas medidas não são o tempo de provisionar um tenant do zero, não medem a transformação original, não são teste de carga e não demonstram aceite por representante da FEJEPAR. FEJEMG foi usada anteriormente como segundo tenant de maior volume; FEJEPAR é o recorte técnico mais recente documentado.

## 6. Correções e achados com interesse para o TCC

| Achado | Correção/estado | Implicação para a escrita |
|---|---|---|
| Claim derivado da fatia de dados na carga | Recorte mantém o claim externo fixo | Filtro e RLS precisam ser independentes; derivá-los do mesmo dado enfraquece a defesa |
| Limite de linhas do PostgREST | Leituras multipágina centralizadas em `leitura.py`; frontend percorre todas as páginas necessárias | Isolar corretamente não basta: agregados também precisam ler a população completa |
| Branding do deploy após login | Identidade visual segue o tenant autenticado | Marca e dados precisam ter a mesma origem de identidade |
| Meta de engajamento em escala 0–100 | Cluster adaptativo Q1/Q2 divide por 100, conforme auditoria de 04/10 | Esta correção já ocorreu; não descrevê-la como pendência anterior |
| Crescimento anual com períodos diferentes | Comparação até o mesmo mês; uso da linha mais recente do acumulado | Período e atualização retroativa influenciam a validade do indicador |
| Acumulado colaborativo diferente da soma mensal | Coluna acumulada oficial do BJ adotada como fonte | A fonte precisa ser declarada; a auditoria registrou divergência em 570/1.502 EJs |
| Resumo/CSV dependentes da página carregada | Totais e exportação usam o recorte completo; filtros locais antes da paginação | Paginação de apresentação não pode mudar o agregado |
| Privilégios do schema `auth` na demo | Helpers privados mínimos para identidade do limitador | Laboratório simplificado não reproduz todos os privilégios do Supabase real |
| Cidade interpretada como busca por nome no Nexo | Intenção literal validada no backend e prompt ajustado | Isolamento e fidelidade semântica são propriedades diferentes |

O achado de paginação foi revisado: a interpretação antiga de um viés que escondia precisamente EJs em risco **não se sustentou**. A causa incluía truncamento de fatos pelo teto do servidor; não reproduzir a conclusão invalidada. Consulte a atualização de 29/09 em `docs/achado-9.17-limites-com-segundo-tenant.md`.

## 7. IA implementada: Nexo

Nexo é o nome atual do assistente, com descritor “Pergunte à sua rede” e mascote vaga-lume em SVG. “Lamps” era o placeholder anterior. O modelo funciona como intérprete, não como executor autônomo de SQL.

Fluxo: pergunta → guardas locais quando aplicáveis → interpretação estruturada → validação do plano → ferramenta autorizada → services sob JWT/RLS → resposta factual composta pelo backend. Não há segunda chamada para redigir a resposta a partir das linhas do banco.

O catálogo evoluiu para EJs fora do zero, indicadores da rede, ranking, SDE e ritmo mensal, com cluster oficial e busca literal por nome nos casos suportados; esclarecimento e recusa também fazem parte do contrato. Continuidade usa somente o último plano tipado, revalidado, sem resultados, JWT ou identidade de tenant. O histórico da interface é efêmero e é descartado na mudança de identidade/tenant/papel.

O período omitido é resolvido pelos dados autorizados/configuração. Período sem cobertura suficiente não deve virar uma resposta preenchida com zeros. As respostas mostram fonte, período e filtros; perguntas ambíguas recebem opções, e filtros devem ser preservados nas sugestões e continuações. Nome/slug da própria federação são lidos sob autenticação; menção a outra federação não escolhe o tenant.

O adaptador permite trocar provedor/modelo por configuração do servidor. O modelo usado na avaliação registrada em 05/10 foi `nvidia/nemotron-3-super-120b-a12b:free` via OpenRouter. Isso é identificação de um experimento, não compromisso de fornecedor nem confirmação de disponibilidade futura. Cada troca exige nova avaliação.

Pergunta e contexto limitado podem ser enviados ao provedor; resultados do banco não são enviados para geração textual. Isso não impede o usuário de digitar informação sensível nem define sozinho a política de retenção do fornecedor. Não afirmar ausência total de exposição ou retenção sem verificar a operação real.

### Controle operacional

A migração 18 implementa reserva compartilhada no PostgreSQL antes de interpretar: defaults de **6 chamadas por usuário e 30 por federação por minuto**, janela fixa. A identidade vem de `auth.uid()`/tenant e vínculo ativo atual; chamadas concorrentes compartilham a reserva. Respostas locais não consomem chamada ao modelo. Tentativas aceitas contam mesmo se o fornecedor falhar. HTTP 429 do portal é distinto da indisponibilidade/quota do fornecedor.

Esses limites não são créditos mensais, preço de plano ou teto monetário. A janela fixa admite rajadas próximas à virada do minuto. O controle usa papel restrito e helpers privados, sem acesso a fatos estratégicos nem chave de serviço no request.

### Avaliação real mais recente documentada

Fonte: `docs/verificacao-portal-2026-10-05.md` e `docs/ia-avaliacao-nexo-2026-10-05.json`.

| Medida | Resultado registrado |
|---|---:|
| Perguntas do corpus | 21 |
| Erros de transporte | 0 |
| Ferramenta correta | 21/21 |
| Plano exatamente igual ao gabarito | 17/21 |
| Resposta do catálogo exatamente igual ao gabarito | 20/21 |
| Status do fluxo com guardas correto | 21/21 |
| Valores/linhas do fluxo completo corretos | 21/21 |
| IDs retornados autorizados | 21/21 |
| Recusas esperadas | 7/7 |

O runner terminou com **código 1**, pois também exige igualdade integral de plano e catálogo. Não apresentar a execução como aprovação integral nem converter o 21/21 do fluxo em 100% de interpretação. O corpus foi usado no desenvolvimento, não é holdout; recusas/esclarecimentos sem linhas não medem acerto numérico. O runner não testa autenticação HTTP. Limite operacional e preservação de acentos foram verificados posteriormente por testes/rota real, sem nova rodada integral do corpus.

Em 04/10 havia corpus de 19 perguntas e uma reavaliação bloqueada por quota do fornecedor. O relatório de 05/10 é a evolução posterior; não confundir a falha de fornecedor antiga com o resultado sem erros de transporte mais recente.

## 8. Frente em desenvolvimento: dashboards de eventos e créditos

**Revisão de escopo em 07/10/2026 — planejada:** Heitor definiu a geração de aplicações de evento em React, com briefing longo, título, descrição, propósito, métricas específicas e publicação opcional no caminho do Portal. O projeto `/Users/heitor/Documents/FEJEPE/CirandaMEJ` foi inspecionado como referência de composição, navegação e identidade visual. O alvo comercial é duas aplicações por federação/mês com orçamento para revisões; a sugestão anterior de 30 ajustes e os custos estimados de interpretação curta foram retirados como fundamento da oferta. Geração de arquivos, build isolado, versões, revisão de código e contabilidade monetária ainda não foram implementados nem avaliados. Fonte: [desenho de aplicações de dashboard](docs/arquitetura-dashboards-aplicacoes-2026-10-07.md). Esta revisão documental não verifica a integração existente descrita abaixo.

**Estado nesta consolidação: há código, interface, migrações 19/20 e documentação; a integração ainda não pode ser declarada concluída.** Não aplicar a esta frente a aprovação de 513 testes de uma etapa anterior.

O desenho propõe pedido em linguagem natural convertido em `PlanoDashboard`: métricas mensais armazenadas (`faturamento_mes`, `projetos_vendidos_mes`, `csat`), soma/média, dimensão EJ/mês, ranking/barras/linha/cartão, um ano e ranking limitado a 50 EJs. CSAT só admite média. O modelo escolhe parâmetros de catálogo; agregação e acesso permanecem no backend.

Há tabela de dashboards com tenant, criador, evento, plano e publicação. A interface inclui geração/visualização em Eventos e rota `/eventos/dashboard/:id`. O desenho da divulgação pública entrega somente snapshot previamente publicado; privado não deve ser servido anonimamente. Publicar um ranking pode divulgar nomes e valores individuais: é uma fronteira de divulgação intencional que precisa de consentimento, testes e revisão próprios.

A política de produto documentada define **1 crédito por dashboard concluído e persistido**, quota compartilhada da federação, mês UTC e **100 créditos/mês como default de piloto**, não plano comercial aprovado. Override administrativo precede limite do plano, que precede default. Consumo de dashboard é distinto do limitador por minuto do Nexo e do custo monetário do fornecedor. Leitura de dashboards existentes não deve consumir geração.

**Inconsistência encontrada por inspeção estática:** `routers/dashboards.py` importa funções de reserva/confirmação/estorno e `LimiteCreditosIA` que não estavam definidas em `app/ia/creditos.py` no recorte inspecionado. O service de persistência usa INSERT/UPDATE direto, enquanto a migração 20 concede escrita ao papel `ia_limitador`, não ao cliente `authenticated`. O texto da política menciona consumo atômico na persistência, mas esse caminho completo não foi localizado na migração 20 lida. Portanto, a documentação de intenção não comprova o funcionamento. Esses pontos exigem reconciliação do código/SQL e verificação integrada; não foram corrigidos nesta tarefa documental.

Antes de registrar como resultado do TCC: validar importação da aplicação, geração, autorização, RLS, quota concorrente, estorno/atomicidade, publicação/revogação e ausência de leitura pública dos fatos. Confirmar aplicação de 19/20 no ambiente de teste/demo e avaliar o modelo nesse catálogo específico. As 21 perguntas do Nexo não validam geração de dashboards.

Fontes: `docs/dashboards-ia-eventos.md`, `docs/politica-creditos-ia.md`, `app/models/dashboard_ia.py`, `app/routers/dashboards.py`, `app/services/dashboard_ia_service.py`, `app/ia/creditos.py`, migrações 19 e 20.

## 9. Migrações e operação

`infra/db/init/` é a fonte única do schema. Os nomes abaixo identificam os arquivos existentes, não comprovam aplicação em todos os ambientes.

| Faixa | Conteúdo |
|---|---|
| 00–01 | Shim de auth exclusivo do laboratório e schema inicial |
| 02–07 | Federação/núcleo/plano, associação ao tenant, donos de metas/monitoramento, usuário/hook e RLS |
| 08–12 | Cluster histórico, branding, staging, escrita de ingestão e seed de núcleos |
| 13–15 | Painel administrativo e slogan |
| 16 | `16-projetos-colaborativos.sql`: projetos colaborativos; **não** a revogação ampla de privilégios planejada no contexto antigo |
| 17 | `17-paleta-federacao.sql`: paleta compartilhada; aplicação em lab/demo registrada |
| 18 | `18-controle-consultas-ia.sql`: limitador operacional; aplicação em lab/demo registrada |
| 19 | `19-creditos-ia-tenant.sql`: quota mensal de dashboards; integração pendente neste recorte |
| 20 | `20-dashboards-evento-ia.sql`: dashboards/snapshot público/cota; aplicada na demo em 07/10 na preparação de entrega |
| 21 | `21-privilegios-minimos.sql`: grants de clientes e defaults por criador |
| 22 | `22-administracao-master.sql`: administração master e catálogo por RPC |
| 23 | `23-acl-rpcs-ia.sql`: correção de ACLs sob dono limitado |

Não reutilizar “migração 16” para a antiga tarefa de segurança A2. Escolher o próximo número livre e verificar o disco antes de criar nova migração. Não alterar migrações já aplicadas nem duplicar o schema em outra pasta.

A operação ganhou `make doctor`, `setup`, `test`, `test-local`, `check`, `front-build`, `front-lint`, `demo-smoke` e `ia-eval`. Testes usam banco descartável com migrações e papéis corretos; `--require-lab` impede interpretar skips como aprovação integral. Demo completa verifica Auth/PostgREST; laboratório com shim é complementar. A reexecução em volume existente não aplica automaticamente toda migração nova.

## 10. Evidências de verificação, sem somar execuções

| Relatório/etapa | Resultado registrado | Limite da evidência |
|---|---|---|
| Verificação operacional de 03–04/10 | 377 testes inicialmente; atualização para 383 após auditoria, build/lint e smoke aprovados | Fotografias de etapas anteriores; não são a suíte final atual |
| Evolução Nexo de 04/10 | 453 testes, 0 pulados; 70 específicos IA; build/lint | Modelo real teve limitações separadas |
| Integração de 05/10 | **513 testes, 0 pulados**, 5 avisos de depreciação; build/lint; 8 testes Node de fotos/paleta | Resultado anterior à conclusão de dashboards/créditos; não valida automaticamente 19/20 |
| Controle Nexo | 26 testes de controle e bateria IA/RLS/controle de 113, sem pulos | Subconjuntos das etapas; não somar aos totais globais |
| Onboarding | 6 testes Node, build/lint e navegação local | Convite completo e troca manual de conta não executados |

Na integração de 05/10, houve indisponibilidade do registry na tentativa de `make test`; a alternativa registrada usou imagem de dependências já instalada com código/testes atuais montados e PostgreSQL descartável. O procedimento e os comandos estão no relatório. Preservar essa informação na descrição de reprodutibilidade.

Navegação local registrada: FEJEPE, FEJEMG, operador e, depois, FEJEPAR; paleta em desktop/mobile, consulta Nexo com fonte/contexto/continuação e onboarding. Isso não é estudo com participantes reais, auditoria completa de acessibilidade, teste de carga, avaliação de custo ou verificação do deploy remoto.

## 11. Pendências e afirmações que o texto ainda não pode fazer

1. **Segurança de privilégios:** corrigida localmente em 07/10 pela migração 21, com privilégios mínimos de tabelas/sequências e defaults seguros do dono das migrações. Na demo, 16 concessões de TRUNCATE (oito tabelas, dois papéis) foram removidas; defaults de public de postgres e supabase_admin também foram fechados. Contagens/fingerprints das 12 tabelas preservados, 524 testes passaram sem skips, três testes adversariais passaram também na stack Supabase real local, e demo-smoke passou. Na correção inicial a demo ainda não recebeu 19/20. Na entrega posterior desta data, 19/20 e a corretiva 23 foram aplicadas de forma aditiva, preservando os dados; veja a atualização de entrega abaixo. Ainda é necessário aplicar e verificar no destino remoto, inclusive defaults de qualquer outro criador. Evidência: [verificacao-privilegios-2026-10-07.md](docs/verificacao-privilegios-2026-10-07.md).
2. **Dashboards/créditos:** concluir e testar a integração descrita na seção 8; não afirmar consumo atômico, geração funcional ou publicação segura como resultado já verificado.
3. **Regressão:** falta comparação controlada com produção FEJEPE. Testar demo contra lab alimentados pela mesma fonte não comprova regressão de produção.
4. **Caracterização:** existem testes de cálculos e correções registradas, mas a conclusão integral do pacote A3 com as cinco funções/antes-depois exige evidência específica. Não inferir conclusão pelo total de testes.
5. **Regras de negócio:** auditoria de 04/10 ainda registra tratamento de cluster ausente como C1, descida forçada de C4 em cenário SDE, mês de calendário em Escalonado, meses sem dado apresentados como zero, definições divergentes de colaboração e fallback de Tracking. São pendências registradas, cuja resolução requer evidência posterior.
6. **Frontend:** a auditoria ainda registra variação de cluster/percentuais com apresentação inadequada, resumos de comparação fora da busca e fórmula/pesos de SDE duplicados no simulador. Não declarar toda regra estratégica centralizada enquanto essa exceção existir.
7. **Dados:** ingerir fatos próprios de núcleo/federação e histórico anual; decidir semântica de EJ ausente na exportação e obter fonte confiável de fotos.
8. **Avaliação humana:** concluir sessões autorizadas com participantes e orientador; medir utilidade/usabilidade com instrumento definido. Provisão inicial limpa e tempo completo de onboarding de uma federação ainda não foram medidos.
9. **IA:** planos/catalogo ainda divergiram do gabarito na avaliação real; testar conjunto independente, cada novo modelo e catálogo de dashboards. Instrumentação monetária, retenção/região de fornecedor e teto financeiro continuam separados da quota de produto.
10. **Entrega:** consolidar commits/push, decidir publicação multi-tenant e aplicar/verificar migrações no destino. Foram estudadas opções de homologação em 07/10, sem executar deploy: [opcoes-deploy-beta-2026-10-07.md](docs/opcoes-deploy-beta-2026-10-07.md). Nenhuma publicação remota foi comprovada nesta consolidação.

As pendências da auditoria são o último registro encontrado, não uma nova reprodução de todos os bugs. Uma correção posterior deve atualizar esta lista com evidência antes de ser incorporada ao texto como concluída.

## 12. Onde incorporar as novidades no texto existente

| Parte do texto, conforme estrutura adotada | Material para revisar/adicionar |
|---|---|
| Problema e objetivos | Evolução single-tenant → multi-tenant; ingestão pelo cliente; IA como novo caminho submetido ao isolamento |
| Arquitetura e implementação | Schema/RLS, identidade por requisição, configuração de tenant, papéis, paleta, ETL, catálogo tipado e controles compartilhados |
| Método e avaliação | Ambiente descartável, diferença lab/demo, dados sintéticos, testes adversariais, corpus do modelo e validação humana ainda pendente |
| Resultados | Achados de paginação/identidade/escala, recorte FEJEPAR com limites do tempo medido, métricas separadas de interpretação e fluxo |
| Discussão | Compromisso do catálogo fechado, defesa independente, diferença interpretação/isolamento, exceções de regra no front e limitações de origem |
| Trabalhos futuros | Núcleo/federação/histórico, fotos, regressão, validação humana, produção, custo e conclusão de dashboards/créditos |

Não adicionar a este documento trechos supostamente já escritos sem consultar a monografia. A documentação do artefato orienta a revisão; não substitui a decisão acadêmica do autor e do orientador.

## 13. Índice de fontes locais

- [Contexto acadêmico e invariantes](CONTEXTO-TCC.md).
- [Execução e verificação operacional](docs/verificacao-2026-10-04.md), [guia de execução](docs/como-rodar.md).
- [Auditoria de métricas](docs/auditoria-estatica-metricas-2026-10-04.md), [regras de negócio](docs/regras-de-negocio.md), [fórmulas](backend/calculos.md).
- [Segundo tenant e dados de outubro](docs/auditoria-segundo-tenant-2026-10-04.md), [achado de paginação revisado](docs/achado-9.17-limites-com-segundo-tenant.md).
- [Painel administrativo](docs/adr-003-painel-admin.md), [ETL](docs/etl-planilhas-portal-bj.md).
- [IA inicial](docs/adr-004-pergunte-a-rede.md), [evolução Nexo](docs/adr-005-nexo.md), [verificação Nexo 04/10](docs/verificacao-nexo-2026-10-04.md).
- [Verificação integrada 05/10](docs/verificacao-portal-2026-10-05.md), [avaliação real 05/10](docs/ia-avaliacao-nexo-2026-10-05.json).
- [Ajustes semânticos/contexto](docs/nexo-ajustes-2026-10-05.md), [controle operacional](docs/nexo-controle-operacional-2026-10-05.md).
- [Paleta](docs/adr-006-paleta-por-federacao.md), [interface](docs/interface-2026-10-05.md), [fotos](docs/fotos-ejs-2026-10-05.md), [onboarding](docs/onboarding-primeiro-acesso.md).
- [Dashboards em desenvolvimento](docs/dashboards-ia-eventos.md), [política de créditos](docs/politica-creditos-ia.md).
- [Schema/migrações](infra/db/README.md), [API](backend/docs/API.md).

## 14. Como manter este arquivo atualizado

Ao concluir uma tarefa substantiva no portal, atualizar este mesmo arquivo: data, funcionalidade final, estado (em desenvolvimento/implementado/verificado/publicado), evidência, pendências resolvidas e novas limitações. Vincular o relatório detalhado/ADR; não duplicar credenciais nem dados individuais. Resultados novos entram com ambiente e escopo, preservando os antigos como histórico identificável, sem somar suítes ou ocultar falhas.

Antes de fechar uma sessão de escrita, substituir no projeto Claude a cópia anterior deste arquivo pela versão atual e pedir a revisão das partes afetadas. **Editar o arquivo local não sincroniza automaticamente o projeto Claude.** Este documento é autocontido para servir de anexo; os links relativos levam às evidências quando o repositório também está disponível.

Mensagem reutilizável ao Claude:

> Atualizei o estado do Portal das Federações no arquivo ESTADO-PORTAL-PARA-TCC.md. Leia-o como referência mais recente de implementação e evidências. Compare com os capítulos que já escrevemos e proponha os acréscimos e correções necessários, preservando a estrutura e meu estilo. Distinga o que foi implementado, medido, planejado e ainda não validado. Não declare produção, aceite de usuários ou resultados de dashboards/créditos sem evidência. Aponte conflitos com textos anteriores e referências bibliográficas que precisam ser conferidas.

## Administração master — 07/10/2026

Implementada a área `/admin/master`, restrita ao papel ativo `plataforma`, com
agregados de usuários por federação (incluindo inativos e federações sem cadastro),
catálogo editável de planos e atribuição/remoção do plano por federação. A área
reutiliza gestão de usuários, status/branding e importação existentes. Os totais
são agregados no banco, evitando truncamento pelo PostgREST. A migração 22 verifica
permissão em RPCs nominais sem conceder troca de plano ao admin de tenant. Não
amplia a leitura dos indicadores das EJs. Preços continuam cadastrais; limite de
usuários não é aplicado; créditos seguem a cota mensal congelada da migração 19.

Verificação local: 561 testes aprovados, zero pulados, cinco avisos; build/lint
aprovados; smoke com Auth/PostgREST reais confirmou contagens e recusas. Migração
aplicada somente na demo. API já aberta na porta 8000 requer reinício para carregar
as novas rotas. Sem validação visual autenticada ou produção; conta pessoal master
ainda depende de identificação do login. Fonte: [ADR-007](docs/adr-007-administracao-master.md).


## Entrega organizada e preparação de deploy — 07/10/2026

Heitor autorizou organizar o código e testar o projeto para hospedagem. O repositório
existente e seu histórico foram preservados; não houve commit, push ou novo remoto.
Pastas atuais: `backend/`, `frontend/`, `tools/cluster-calculator/`, `infra/deploy/`.
Scripts, Makefile, workspace, pacotes e documentação operacional usam esses nomes;
relatórios históricos mantêm as referências da época.

Implementado: locks Python de produção/desenvolvimento com hashes; manifestos
Render/Vercel e AWS com frontend/API/proxy HTTPS e Supabase externo; CI com banco
SQL descartável, frontend, ferramenta auxiliar, manifests e smoke de containers;
migrador com ledger/checksum e recusa de banco legado sem inventário; bootstrap de
operador novo com senha privada, confirmação e prova de alinhamento Auth/banco.

Achado operacional: o dono limitado do Supabase não conseguia completar ownership/
ACLs das funções de IA com os SQLs antigos. O executor trata membership temporária
sem alterar arquivos históricos; a migração aditiva 23 fecha ACLs das RPCs existentes.
Demo recebeu 19/20 e 23 com dados preservados. As contas antigas foram mantidas
somente para validar a demo; a implantação nova cria contas próprias.

Verificação da versão final: **567 testes backend passaram, 0 falhas, 0 pulados**
(em PostgreSQL descartável 00–23), com 7 avisos de depreciação/cache. **15 testes
frontend passaram, nenhum pulado**, build/lint passaram; calculadora compilou.
Demo smoke passou Auth/PostgREST reais locais, master e isolamento cruzado.
Imagens runtime finais construídas; smoke passou PORT, UID sem privilégios,
produção sem pytest, SPA, configuração sem cache, proxy 401 e docs 404.

Auditorias consultadas nesta data: frontend e calculadora com **0 vulnerabilidades
conhecidas no npm audit**; **55 dependências Python de produção, 0 vulnerabilidades,
0 pacotes ignorados no pip-audit**. Atualizados locks e FastAPI/Starlette; sem
suprimir advisories ou enfraquecer testes. Isso não é auditoria completa de sistema,
imagem de SO, Supabase externo, regras de negócio ou toda vulnerabilidade futura.

O pacote `make package` inclui o código atual e testes, inclusive arquivos não
commitados. Exclui ambientes, builds, dependências, dados reais e relatórios JSON
brutos. O pacote não inclui histórico Git. O README e guia de deploy explicam
instalação e preparação do ambiente novo. Nenhuma monografia foi alterada.

Limites: CI está configurada, não executada no GitHub nesta tarefa. Não houve
recurso remoto ou endereço público criado, email externo, migração em produção,
avaliação com participantes nem chamada de modelo real/pago. A validação no destino
(hook, SMTP, contas novas, RLS, upload, IA e publicação/revogação) permanece necessária.
As demais pendências acadêmicas/de regra de negócio anteriores não foram encerradas
por esta reorganização ou pelo total de testes.

Fontes: [entrega backend](docs/verificacao-backend-entrega-2026-10-07.md),
[entrega integrada](docs/verificacao-entrega-2026-10-07.md),
[guia de deploy](infra/deploy/README.md), [comparação](docs/opcoes-deploy-beta-2026-10-07.md).

## Revisão integrada e VPS — 13/10/2026

Heitor autorizou trabalho multiagente, revisão da monografia, pesquisa e melhorias
do artefato e preparação para deploy. Escolheu **VPS (Hostinger ou AWS) + Supabase**.
Cronograma online foi lido na sessão autenticada do Brave; sua reconciliação com
evidências locais está em [cronograma conferido](docs/cronograma-conferido-2026-10-13.md).
As marcações do navegador não foram alteradas. O progresso 43/70 da fonte contém
descrições históricas e não é cobertura técnica atual.

Implementações locais verificadas:

- Fronteira de sessão limpa cache antes de trocar identidade/tenant/papel e remonta
  estado privado, inclusive em logout externo; renovação do mesmo escopo preserva
  cache. Resposta tardia não repovoa queries antigas. Claims no navegador delimitam
  cache; autorização permanece na API/RLS.
- Comparação apresenta diferença de cluster em níveis e taxas em pontos
  percentuais; cartões de resumo acompanham a busca. Fórmulas de negócio preservadas.
- A3 tem baseline literal completo das cinco funções, corpus sintético de nove
  EJs/dois tenants, sete testes novos e prova de sensibilidade por mutação em
  memória. Caracteriza a versão atual; não comprova regressão antes/depois.
- Preflight Render e alias VPS, verificações de configuração segura e guia VPS
  com Docker/Caddy/Supabase, DNS, firewall, backup e rollback. Compose mantém nomes
  históricos AWS, compatíveis com Hostinger. Headers HTTPS confiáveis restritos
  pela topologia privada do backend sem porta publicada.
- Comparador GET preparado para indicadores/SDE/ritmo/ranking de faturamento top100,
  com JWTs via ambiente, redirects recusados e relatório sem valores/identidades.
  Sete testes sintéticos aprovados; nenhuma comparação com produção executada.

Evidência final local: **574 testes backend aprovados, 0 falhas, 0 pulos**, sete
avisos; **20 testes frontend aprovados, 0 falhas, 0 pulos**, lint/build aprovados;
calculadora compilada na verificação integrada. Demo smoke passou autenticação,
branding, leitura completa, master e isolamento cruzado, incluindo 27 contas admin
de demonstração. Imagens runtime finais reconstruídas e smoke aprovado (PORT,
UID sem privilégios, sem pytest, SPA, configuração sem cache, proxy 401, docs 404).
`make deploy-check` aprovou sete testes de configuração, sete de regressão e Compose.
Avisos SQL de revogação de membership não concedida foram observados nas migrações
19/20 do banco descartável; sem ERROR/FATAL e sem enfraquecer testes de privilégios.

Monografia revisada por autorização direta: defasagens factuais e generalizações
corrigidas, título/OEs preservados. Verificação estática: 14 arquivos, 44 referências
e nenhuma citação/label/asset/ambiente faltante; 19 marcadores acadêmicos pendentes.
Esse resultado não é compilação nem aprovação visual de PDF. Roteiro/registro
P1–P3 preparado; não houve sessão humana ou parecer do orientador.

Permanecem: geração completa de aplicações React para dashboards e orçamento/modelo
correspondente, ETL núcleo/federação/histórico, divergências de negócio sem decisão,
regressão real de produção, avaliação independente de IA, escolha de IA para
avaliação formal, Portal BJ com evidência autorizada e decisões acadêmicas. VPS,
domínio, projeto Supabase novo, SMTP/hook/contas e auditoria remota ainda precisam
ser configurados/verificados. Nenhum recurso remoto, publicação, convite externo,
modelo pago, commit ou push foi realizado. A preparação local não fecha homologação.

Fontes: [frontend](docs/pendencias-implementacao-2026-10-13.md),
[caracterização](docs/caracterizacao-2026-10-13.md),
[regressão preparada](docs/regressao-producao-preparacao-2026-10-13.md),
[deploy](docs/preparacao-deploy-2026-10-13.md),
[VPS](docs/preparacao-vps-2026-10-13.md).

## Verificação da migração em 05/11/2026

Runtime local substituído por PostgreSQL direto (psycopg), autenticação própria
com PBKDF2, sessões opacas armazenadas por hash, expiração/revogação e convite
local de uso único. SDK Supabase removido do frontend e dependências runtime;
PostgREST permanece somente como biblioteca de tipo de erro compatível, sem
serviço HTTP. API usa login restrito e SET LOCAL ROLE/claims por transação;
credencial de proprietário somente em migração/bootstrap.

`make check`: **582 backend passaram, 0 falhas, 0 pulados**, 3 avisos;
**20 frontend passaram, 0 falhas, 0 pulados**, lint/build e calculadora aprovados.
Inclui integração real de login/logout, expiração, papel atual, desativação,
convite único, troca de senha e RLS sem filtro Python. Stack Docker local subiu;
portal via nginx retornou 200 e rota protegida sem sessão retornou 401.
Não houve navegação autenticada manual, avaliação humana, publicação remota ou
migração de dados/contas antigas. Conta inicial deve ser criada pelo autor pelo
comando documentado em `docs/entrega-tcc-2026-11-05.md`. Monografia preservada.

Pacote: `artifacts/portal-das-federacoes-src.tar.gz`, 351 arquivos de código,
sem configuração privada/dados reais segundo o empacotador. Claude foi tentado,
interrompido sem resultado; implementação e verificação por Codex.

## Ajustes de upload e aparência — 05/11/2026
Banco novo confirmado sem EJs; requer importação explícita. Nginx ajustado para 21 MB (API mantém 20 MB) e timeout 120s. Teste de corpo sintético 2 MB sem sessão retornou 401, ultrapassando o proxy e mantendo autenticação. Aparência ganhou quatro paletas e prévia com cartões/gráficos ilustrativos. Frontend: 20 testes, zero falhas/pulos, lint/build aprovados; imagem reconstruída e container atualizado. Importação autenticada de planilha real ainda não executada nesta alteração.

## Correção de leitura numérica — 05/11/2026
Após upload, consultas falhavam por mistura de float e Decimal retornado por
psycopg. Adaptador agora normaliza Decimal recursivamente ao contrato numérico
JSON anterior, incluindo resultados RPC e mutações. Fórmulas preservadas.
Teste de regressão cobre estruturas aninhadas, ausência, zero e identidade.
Imagem da API reconstruída e container atualizado; dados importados preservados.

## Tema neutro e importação — 05/11/2026
Removido azul dos tokens neutros e fundos fixos principais. Importação master
agora inicia na própria federação e explica o privilégio; admins continuam
restritos no backend. Bootstrap anterior criava papel plataforma/master.
Uploads recusam fórmulas, macros, vínculos externos e expansão acima de 150 MB,
além do contrato existente. Isso não autentica valores: aprovação de hash de
exportação original foi apresentada ao autor como opção, ainda sem decisão.
Backend: 583 passaram, zero falhas/pulos; frontend: 20 passaram, lint/build
aprovados. Não foram apagados dados nacionais importados nem alterado papel da conta.

Correção de escopo: Heitor retirou a ideia de trava de autenticidade. A validação adicional de fórmulas/macros foi removida; contrato e validações anteriores preservados.

Paleta padrão: restaurada rampa secundária institucional original por pedido de Heitor. Tokens neutros de fundo permanecem neutros.

Ajuste solicitado: restaurados também os tokens de superfícies azul-ardósia da aparência padrão; restauração anterior só da paleta secundária não atendia à preferência visual.

## Superfícies por paleta — 05/11/2026
Azul-ardósia restrito à paleta padrão (três cores sem personalização).
Qualquer paleta personalizada aplica tokens neutros às superfícies; restaurar
padrão ou trocar de tenant remove os overrides e recupera o azul original.
Teste de transição acrescentado: 21 testes frontend aprovados, sem falhas/pulos;
lint/build aprovados. Frontend reconstruído para atualização local.

Preferência final de Heitor: superfícies azul-ardósia em todas as paletas, inclusive personalizadas. Cores da marca continuam configuráveis.

## Logos da FEJEPE — 05/11/2026
Coletadas 58 associações nome/URL exibidas na listagem autenticada do Portal BJ, quatro páginas. Cruzamento por nome normalizado exato e único, restrito a federacao_id=12: 43 EJs locais receberam foto_url; 15 registros sem correspondente local não foram alterados; zero EJs locais sem foto após aplicação. Nenhuma credencial foi extraída. Mapa de coleta em Downloads/logos-fejepe-portal-bj.json, fora do repositório. Checagem pública HEAD: 58/58 URLs retornam imagem. URLs externas podem mudar; navegação visual local ainda não conferida nesta etapa.

## Logos nacionais — 05/11/2026
Coleta autorizada pela sessão Chrome do autor, via cliente da própria aplicação
Portal BJ e endpoint de dados da rede. 51 páginas, 1.506 IDs únicos, zero falhas.
Exportado somente mapa ID EJ/nome/federação/URL, sem tokens ou métricas, para
Downloads/logos-nacional-portal-bj.json (fora do repositório).
Cruzamento por id_ej e federacao_id: 1.445 fotos preenchidas, 43 existentes
preservadas, 18 registros sem logo na origem; nenhuma EJ local ausente da coleta
e nenhuma divergência de federação. Total: 1.488/1.506 com imagem, 27 federações.
URLs limitadas a HTTPS no host uploads.brasiljunior.org.br; sem alteração de
indicadores, permissões ou registros de outras tabelas. URLs externas podem mudar.
Checagem HEAD de uma imagem por federação: 27/27 acessíveis; não equivale a verificar todos os arquivos.

## Histórico de cargas — 05/11/2026
Corrigido erro 500 em exportado_em: date/datetime do psycopg normalizados para
ISO na camada de adaptação JSON. Teste de regressão valida o modelo Carga com
data PostgreSQL e ausência. Suíte backend: 584 passaram, zero falhas/pulos.
Imagem reconstruída. Smoke autenticado FEJECE: GET /admin/importacoes retornou
200, uma carga, todas as linhas restritas a federacao_id=15. Sessão de verificação
revogada ao terminar; nenhum conteúdo da planilha foi registrado.
