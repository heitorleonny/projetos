-- A exportação acumulada de monitoramento informa contratos colaborativos por
-- EJ e mês. O portal já expõe projetos_colab_totais e o filtro correspondente.
ALTER TABLE monitoramento ADD COLUMN IF NOT EXISTS projetos_colab_mes INTEGER;

GRANT INSERT (projetos_colab_mes) ON monitoramento TO ingestao;
GRANT UPDATE (projetos_colab_mes) ON monitoramento TO ingestao;

COMMENT ON COLUMN monitoramento.projetos_colab_mes IS
    'Contratos do mês com ação colaborativa, coluna NUMERO_DE_CONTRATOS_QUE_REALIZOU_ACAO_COLABORATIVA da exportação acumulada do Portal BJ.';
