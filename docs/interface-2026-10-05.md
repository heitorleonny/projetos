# Ajustes de interface — 05/10/2026

Objetivo: aproximar o portal de uma ferramenta institucional de acompanhamento, com menos efeitos decorativos e maior legibilidade. Mudanças visuais não alteram fórmulas, filtros ou respostas da API.

- Superfícies opacas substituem vidro, desfoque, brilho e grelha de fundo. As classes existentes continuam válidas, evitando reescrever componentes e seus comportamentos.
- Cabeçalhos usam títulos simples, sem gradiente, faixa luminosa ou texto em itálico. As páginas mantêm indicadores, tabelas e controles existentes.
- Navegação destaca a seção atual por fundo discreto. “Visão geral”, “Evolução de cluster” e “Administração” explicam melhor os destinos; as rotas permanecem compatíveis.
- Formulário de entrada tem rótulos legíveis e campos com contraste definido. Foco visível e redução de movimento são tratados no CSS compartilhado.
- O evento Ciranda conserva nome e informações próprios, com apresentação uniforme ao restante do portal, sem emojis grandes ou iluminação decorativa.
- A identidade da federação permanece aplicada pelos tokens runtime. A paleta e as fotos das EJs foram tratadas em paralelo por outros agentes. Nexo e mascote permanecem presentes de forma discreta.

Verificação: build e lint do frontend; navegação visual integrada coordenada pelo agente principal. Sem mudanças de regras de negócio, persistência ou implantação.

Integração da paleta: séries genéricas de faturamento e ícones de KPI passam a usar os tokens primário/secundário. Exportação Canvas lê as cores HEX do branding runtime; SVG usa variáveis CSS. Cores que representam ritmo, cluster, erro ou alerta mantêm sua semântica.
