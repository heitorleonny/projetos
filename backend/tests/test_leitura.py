"""
Testes de app/services/leitura.py — a leitura sem o corte de `max_rows`.

O defeito que motivou o módulo (29/09/2026): o PostgREST corta a resposta em
1000 linhas sem avisar, e a FEJEMG, com 2.619 linhas de monitoramento em 2026,
aparecia com 139 EJs em R$ 0. O servidor falso daqui reproduz esse corte.
"""

import pytest

from app.services.leitura import TAMANHO_PAGINA, LeituraIncompleta, ler_todas


class _Resposta:
    def __init__(self, data, count):
        self.data = data
        self.count = count


class _ConsultaFalsa:
    """Consulta que corta em `max_rows`, como o PostgREST, e respeita offset/limit."""

    def __init__(self, servidor):
        self._servidor = servidor
        self._filtro_ano = None
        self._range = None
        self.ranges_aplicados = 0

    def select(self, colunas, count=None):
        self._servidor.counts_pedidos.append(count)
        return self

    def eq(self, campo, valor):
        if campo == "ano":
            self._filtro_ano = valor
        return self

    def order(self, coluna):
        self._servidor.ordens.append(coluna)
        return self

    def range(self, inicio, fim):
        # O builder real ACUMULA offset/limit se reusado; aqui isso vira erro.
        self.ranges_aplicados += 1
        assert self.ranges_aplicados == 1, "consulta reaproveitada entre páginas"
        self._range = (inicio, fim)
        return self

    def execute(self):
        linhas = [l for l in self._servidor.linhas if self._filtro_ano in (None, l["ano"])]
        inicio, fim = self._range
        pedidas = linhas[inicio : fim + 1]
        contagem = len(linhas) + self._servidor.mentir_contagem
        return _Resposta(pedidas[: self._servidor.max_rows], contagem)


class _ServidorFalso:
    def __init__(self, n_linhas, max_rows=1000, mentir_contagem=0):
        self.linhas = [{"id": i, "ano": 2026} for i in range(n_linhas)]
        self.max_rows = max_rows
        self.mentir_contagem = mentir_contagem
        self.consultas: list[_ConsultaFalsa] = []
        self.counts_pedidos: list = []
        self.ordens: list = []

    def table(self, nome):
        consulta = _ConsultaFalsa(self)
        self.consultas.append(consulta)
        return consulta


def test_le_alem_do_teto_do_servidor():
    """2.619 linhas, teto de 1000: chegam as 2.619, em 3 páginas."""
    servidor = _ServidorFalso(2619)
    linhas = ler_todas(servidor, "monitoramento", filtros=lambda q: q.eq("ano", 2026))
    assert len(linhas) == 2619
    assert [l["id"] for l in linhas] == list(range(2619))
    assert len(servidor.consultas) == 3


def test_teto_do_servidor_menor_que_a_pagina():
    """Servidor com teto de 300 (menor que TAMANHO_PAGINA): avança pelo lote recebido."""
    servidor = _ServidorFalso(1000, max_rows=300)
    linhas = ler_todas(servidor, "monitoramento")
    assert len(linhas) == 1000
    assert len(servidor.consultas) == 4


def test_uma_consulta_nova_por_pagina():
    """O builder do postgrest-py é mutável: reaproveitar acumularia offset/limit."""
    servidor = _ServidorFalso(2500)
    ler_todas(servidor, "monitoramento")
    assert all(c.ranges_aplicados == 1 for c in servidor.consultas)


def test_pede_contagem_exata_e_ordem_estavel():
    servidor = _ServidorFalso(10)
    ler_todas(servidor, "cluster_historico", ordem=("id_ej", "ano"))
    assert servidor.counts_pedidos == ["exact"]
    assert servidor.ordens == ["id_ej", "ano"]


def test_resultado_pequeno_numa_ida_so():
    servidor = _ServidorFalso(387)
    assert len(ler_todas(servidor, "monitoramento")) == 387
    assert len(servidor.consultas) == 1


def test_vazio():
    assert ler_todas(_ServidorFalso(0), "monitoramento") == []


def test_contagem_que_nao_fecha_e_erro_e_nao_numero_errado():
    """Se o banco diz 1.500 e a leitura acaba em 1.200, a tela não pode seguir calculando."""
    servidor = _ServidorFalso(1200, mentir_contagem=300)
    with pytest.raises(LeituraIncompleta):
        ler_todas(servidor, "monitoramento")


def test_tamanho_da_pagina_igual_ao_max_rows_padrao():
    assert TAMANHO_PAGINA == 1000
