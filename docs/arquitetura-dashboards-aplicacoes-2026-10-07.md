# Dashboards como aplicações de evento — referência CirandaMEJ

> **Histórico — fora do escopo ativo desde 23/10/2026.** Heitor retirou dashboards
> gerados por IA para simplificar o TCC. Este documento preserva o desenho e as
> evidências anteriores; não é uma entrega pendente. Permanecem Nexo e painéis
> convencionais. Consulte o [plano de retomada](retomada-escopo-reduzido-2026-10-23.md).


Data: 07/10/2026. Estado: desenho técnico revisado a partir da correção de Heitor e da inspeção do projeto Ciranda; não implementado nem validado como gerador de aplicações.

## Referência inspecionada

Pasta: `/Users/heitor/Documents/FEJEPE/CirandaMEJ`.

- `site/package.json`: Next.js 16.2.4, React 19.2.4, TypeScript e Tailwind.
- `site/src/app/page.tsx`: navegação, identidade visual, cinco seções e rodapé.
- `site.md`: briefing de propósito, público, identidade visual, metas globais e de comunidades, reconhecimentos individuais e premiações.
- `Design.md`: paleta, fontes e componentes da identidade do evento.
- `site/src/lib/api.ts`: integração com a API do Portal.
- `site/src/lib/transforms.ts`: regras de metas, elegibilidade, contagem, ordenação e pontuação no frontend antigo.

O resultado esperado passa a ser uma aplicação de acompanhamento do evento com composição e comportamento próprios. As regras de `transforms.ts` servem para levantar requisitos; no Portal das Federações, fórmulas e decisões de elegibilidade devem ser implementadas ou reutilizadas no backend. Não copiar automaticamente regras antigas para o código gerado.

## Formulário de criação na aba Eventos

1. Evento associado e título do dashboard.
2. Descrição curta e objetivo: por que existe, quem acompanha e que decisão ajuda a tomar.
3. Briefing longo: seções, identidade visual, interações, organização e exemplos.
4. Métricas selecionadas: identificador do catálogo, recorte temporal, população, agrupamento e meta configurada quando houver suporte no backend.
5. Visibilidade: privado para usuários autorizados da federação ou público por link, sem login. A interface deve deixar claro que um link público pode ser acessado por qualquer pessoa que o obtenha.
6. Prévia gerada e comando de publicação da versão aprovada.

O briefing pode ser extenso. O limite de entrada deve ser escolhido em tokens e custo após medir um pedido equivalente ao Ciranda; o campo de 1.000 caracteres e a saída de 350 tokens do interpretador atual não representam esse escopo.

### Exemplo de briefing

> Título: Evento do Ano 2026. Objetivo: acompanhar a campanha de setembro e outubro e ajudar cada EJ a encontrar sua posição e evolução. Criar uma página responsiva com identidade do evento, apresentação do propósito, navegação por seções e indicação de atualização dos dados. Incluir ranking por faturamento realizado em setembro e outubro, comparação dos dois meses, metas configuradas para o evento e destaque das EJs que atendem aos critérios autorizados. Permitir busca por nome da EJ. Usar somente os resultados do backend; explicar o recorte e sinalizar meses sem dados. Criar uma versão privada para revisão. Ao publicar, divulgar as métricas escolhidas no link público.

Critérios como “EJ elegível à premiação” precisam de contrato no catálogo do backend. Se uma regra não existir, o sistema pede sua definição e implementação; o modelo não inventa a fórmula para completar o site.

## Arquitetura recomendada

### Aplicação React gerada com núcleo de execução fixo

Usar React + TypeScript para gerar o frontend específico, com CSS e uma biblioteca controlada de componentes do Portal. Um runtime cliente com build estático atende rankings, busca e seções; Next.js não é obrigatório para reproduzir essa experiência. A decisão entre SPA e Next deve seguir os requisitos reais de cada aplicação e o custo de operação.

O gerador pode criar estrutura de arquivos, layout, textos e interações e depois revisar esses arquivos. Ele trabalha a partir de um scaffold com dependências fixas, um SDK de visualização e contratos de dados tipados. Isso permite uma aplicação visual própria por evento, com preservação do controle de dados e métricas.

Não incluir um teto arbitrário de seis gráficos como definição do produto. Dimensionar componentes e tamanho do artefato por orçamento e desempenho; o briefing de referência tem cinco seções com vários elementos em cada uma.

### Trabalho assíncrono e versões

Fluxo: briefing → validação de métricas → reserva de orçamento → geração de código → build isolado → verificação com dados sintéticos → prévia → publicação da versão aprovada.

Cada trabalho recebe um identificador e registra estado, uso de modelo, tokens, custo disponível, tempo de build e resultado. Aplicar limite de tentativas de reparo, duração, memória e tamanho de saída. Uma falha mantém a versão anterior publicada. Pedidos de ajuste modificam a versão existente e os arquivos necessários; evitar gerar a aplicação inteira novamente para alterar um título ou uma cor.

Guardar por usuário e tenant: briefing, métricas vinculadas, arquivos fonte, artefato de build, versões, histórico de ajustes, autor e versão publicada. Armazenamento e persistência também ficam sujeitos ao isolamento e às políticas de acesso; nome de pasta ou slug não substitui autorização.

### Código gerado isolado

Código gerado é conteúdo não confiável. Compilar em ambiente descartável, sem chaves, sessões ou arquivos de produção, com dependências já preparadas e sem instalação livre de pacotes ou scripts de instalação do modelo. Dados usados na construção são sintéticos.

Executar a aplicação em uma origem de artefatos separada, incorporada por um shell confiável do Portal. O endereço visível pode continuar sob o domínio principal. Usar sandbox de iframe, política CSP restritiva e uma ponte controlada para entregar somente resultados autorizados. O bundle gerado não recebe JWT do usuário, credenciais de banco ou acesso ao armazenamento da aplicação principal. A ponte valida a janela emissora, a sessão efêmera e o contrato de mensagens; uma origem opaca do iframe não identifica o tenant.

Não combinar scripts e mesma origem em um iframe servido na origem privilegiada do Portal. A [documentação do iframe](https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/iframe#sandbox) e a [documentação de CSP](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Content-Security-Policy) fundamentam as restrições de execução e carregamento. Sandbox não torna o código correto nem garante a precisão dos números apresentados.

### Métricas e RLS

O modelo recebe catálogo e metadados, não linhas reais das EJs. Ele declara os vínculos da apresentação com resultados conhecidos do backend. Os componentes de métricas exibem valores, rankings e gaps já calculados por serviços autorizados; novas fórmulas precisam entrar no backend com verificação independente.

No ambiente privado, o shell consulta a API com a identidade do usuário, que aplica RLS e filtro explícito de tenant. A aplicação gerada recebe apenas os dados correspondentes aos vínculos aprovados, sem parâmetros para escolher outra federação. Impedir acesso livre a URLs, SQL e Supabase no SDK do código gerado.

Inspeção de código, restrição de imports e uso de componentes confiáveis ajudam a controlar a apresentação, mas não comprovam sozinhos que JavaScript arbitrário preserva números. A verificação deve comparar métricas apresentadas com valores esperados fornecidos pelo backend em cenários sintéticos e adversariais. Manter claramente a fronteira de funcionalidades suportadas pelo runtime.

## Publicação e link público

Formato proposto: `/dashboards/{slug-federacao}/{slug-dashboard}`. Exemplo de caminho: `/dashboards/fejepe/ciranda-mej-2026`. O domínio definitivo é o domínio configurado do Portal.

O backend deriva a federação da sessão autorizada e resolve o slug para a versão publicada. O caminho não concede autorização por si. Rascunhos e prévias continuam privados. Uma preferência de visibilidade pode ser marcada no briefing; o link público só fica ativo quando uma versão válida é publicada.

Para o visitante sem login, servir apenas o artefato publicado e uma projeção aprovada dos dados das métricas escolhidas. Não criar leitura pública das tabelas de EJs, fatos ou outras versões. Toda rota de artefato, dados e mídia deve aplicar a mesma condição de publicação. Tornar privado desativa essas rotas públicas; material já obtido enquanto público não pode ser recolhido do dispositivo do visitante.

O primeiro fluxo de atualização de dados pode ser uma ação autenticada “Atualizar dados publicados”, usando o JWT do gestor e sem chamar IA. Mostrar data e hora da atualização. Atualização automática exige um processo com escopo de tenant e políticas próprias, sem introduzir uma chave que ignore RLS. Não prometer acompanhamento em tempo real enquanto a publicação servir uma projeção estática.

## Créditos corrigidos para geração de aplicações

Manter como alvo **duas novas aplicações de dashboard por federação/mês**, com orçamento reservado para revisões. O briefing pode gerar muitos gráficos na mesma aplicação; cada gráfico não é uma criação independente.

A quantidade de 30 ajustes sugerida anteriormente deixa de ser uma franquia garantida. Ajustes de aplicação variam: trocar texto, reorganizar cinco seções e acrescentar uma nova interação têm custos diferentes. É necessário medir uma geração equivalente ao Ciranda e uma sequência de revisões para definir a folga vendável.

O controle precisa combinar limite de projetos, orçamento por geração, orçamento compartilhado de ajustes e teto financeiro da plataforma. Antes de executar um ajuste, indicar seu consumo estimado e recusar pedidos que excedem o orçamento; aplicar um limite de gasto no trabalho de geração. Uma chamada ao modelo não equivale automaticamente a um crédito de produto.

Registrar também chamadas que falharam ou foram usadas para reparar um build: elas têm custo no provedor, mesmo que não consumam a entrega contratada do cliente. Falha sem entrega não reduz a cota de aplicações concluídas, mas ocupa o orçamento interno de tentativas do operador. Créditos de produto e custo efetivo precisam de contabilidade distinta.

Abrir o dashboard, buscar uma EJ, usar filtros já disponíveis, atualizar dados autorizados, publicar e tornar privado não chamam o gerador. Alterar manualmente título, descrição ou visibilidade nos campos do Portal também não consome geração.

As estimativas anteriores de 4.000 tokens de entrada e 1.500 de saída mediam seleção estruturada de componentes, não geração de uma aplicação React com múltiplos arquivos e reparos. Retirar essas estimativas da decisão comercial. Os preços de R$ 99/R$ 149/R$ 249 continuam hipóteses a revalidar depois de medir o novo custo; as [tarifas da API](https://developers.openai.com/api/docs/pricing) cobram uso de tokens e recursos, não “uma aplicação pronta”.

## Próximas entregas de implementação

1. Formulário de briefing e contrato de métricas do evento.
2. Scaffold React, SDK de dados e ambiente de build/execução isolados.
3. Fila de geração, versões, prévia e ajustes por patches.
4. Publicação por slug, projeção pública e revogação de acesso.
5. Contabilidade de tokens/custo, limite de duas entregas e orçamento de revisões.
6. Avaliação com cenário sintético equivalente ao Ciranda, precisão dos indicadores, autorização e alterações adversariais.

Nenhuma geração paga, build do Ciranda ou alteração no projeto Ciranda foi feita nesta revisão. A implementação atual de uma visualização por registro é uma base de catálogo e isolamento; esse gerador de aplicações ainda precisa ser construído.
