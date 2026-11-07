// Mesmos nomes e destinos no menu e no guia de primeiro acesso.
export const abasDoPortal = [
    { id: 'visao', to: '/dashboard', label: 'Visão geral', grupo: 'principal', descricao: 'Encontre as empresas juniores da sua rede e acompanhe seus resultados.', acao: 'Confira o período, experimente a busca e clique em uma EJ para abrir seu perfil.' },
    { id: 'indicadores', to: '/indicadores', label: 'Indicadores', grupo: 'principal', descricao: 'Veja o panorama consolidado da federação, com indicadores e gráficos.', acao: 'Confira o ano selecionado e explore os indicadores da rede.' },
    { id: 'eventos', to: '/eventos', label: 'Eventos', grupo: 'principal', descricao: 'Acompanhe os eventos e suas metas. A lista depende dos eventos disponíveis para sua federação.', acao: 'Selecione um evento para conhecer suas metas. Se a lista estiver vazia, sua rede ainda não tem um evento disponível.' },
    { id: 'cluster', to: '/cluster-track', label: 'Evolução de cluster', grupo: 'analises', descricao: 'Acompanhe o cluster oficial, o tracking e a evolução das empresas juniores.', acao: 'Busque uma EJ e compare o cluster oficial com os cenários apresentados.' },
    { id: 'comparacao', to: '/comparacao', label: 'Comparação', grupo: 'analises', descricao: 'Compare indicadores das empresas juniores entre anos.', acao: 'Selecione os anos e um indicador. Períodos sem dados são identificados na tela.' },
    { id: 'simulacao', to: '/simulacao', label: 'Simulação', grupo: 'analises', descricao: 'Explore cenários de desenvolvimento da rede sem alterar os dados cadastrados.', acao: 'Experimente os controles de subida e descida para observar um cenário hipotético.' },
    { id: 'admin', to: '/admin', label: 'Administração', grupo: 'conta', descricao: 'Gerencie usuários, importações e a aparência da sua federação conforme suas permissões.', acao: 'Conheça as abas do painel. Para importar dados, comece pela simulação e confira os avisos antes de gravar.' },
] as const;
