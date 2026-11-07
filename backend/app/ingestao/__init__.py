"""
Ingestão das exportações do Portal BJ.

Três etapas com responsabilidade separada, para que a CLI e a futura porta HTTP
usem o mesmo núcleo sem duplicar regra:

    leitor.py     .xlsx → DataFrame validado contra o contrato. Não conhece o banco.
    transform.py  linha → entidades do portal. Não escreve.
    carga.py      upsert idempotente sob RLS. Só escreve.

`importacao.py` costura as três (escopo, recorte por federação, simulação e
registro de falha), e é o ponto de entrada de quem chama.
"""
