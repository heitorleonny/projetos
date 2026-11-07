"""Baseline sintético: fixa comportamento observado, não correção das regras.

Não atualizar o JSON automaticamente no pytest. Mudança intencional de regra
deve explicar o antes/depois e revisar os valores literais em separado.
"""
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.services.empresa_service import buscar_empresa, listar_empresas
from app.services.evento_service import calcular_evento
from app.services.rede_service import calcular_indicadores_rede, calcular_sde_cenarios

BASELINE = Path(__file__).parent / "fixtures/caracterizacao/baseline-2026-10-13.json"


class ConsultaSintetica:
    """Simula filtros/ordem/contagem do PostgREST; não simula nem prova RLS."""
    def __init__(self, rows):
        self.rows = list(rows)
        self.slice = None

    def select(self, *args, **kwargs):
        return self

    def eq(self, column, value):
        self.rows = [row for row in self.rows if row.get(column) == value]
        return self

    def in_(self, column, values):
        self.rows = [row for row in self.rows if row.get(column) in values]
        return self

    def lte(self, column, value):
        self.rows = [row for row in self.rows if row.get(column, 0) <= value]
        return self

    def order(self, column, desc=False):
        self.rows.sort(key=lambda row: row.get(column, 0), reverse=desc)
        return self

    def range(self, start, end):
        self.slice = (start, end + 1)
        return self

    def limit(self, size):
        self.slice = (0, size)
        return self

    def execute(self):
        rows = self.rows if self.slice is None else self.rows[slice(*self.slice)]
        return SimpleNamespace(data=rows, count=len(self.rows))


class BancoSintetico:
    def __init__(self):
        self.tables = dados_de_borda()

    def table(self, name):
        return ConsultaSintetica(self.tables[name])


def dados_de_borda():
    # IDs reservados a fixtures; sem CNPJ, fotos, nomes ou dados de EJs reais.
    specs = [
        (900001, "A Zerada", 1, 0, 0, None, "ativa"),  # 9.7: zero legítimo
        (900002, "B Sem cluster", None, 6000, 0, 4, "ativa"),  # 9.14
        (900003, "C Parou reporte", 2, 10000, 0, 4, "ativa"),  # 9.7/9.22
        (900004, "D CSAT zero", 1, 10000, 0, 0, "ativa"),  # 9.8: zero coletado
        (900005, "E Acima meta", 4, 200000, 20000, 5, "ativa"),  # 9.18/9.2
        (900006, "F Abaixo verde", 1, 9996, 1000, 4, "ativa"),  # 9.5: 41,65%
        (900007, "G Inativa", 3, 10000, 0, 4, "inativa"),  # 9.20
        (900008, "H Sem dados", 2, 0, 0, None, "ativa"),  # 9.11/9.12
        (900099, "Z Outro tenant", 5, 9999999, 999999, 5, "ativa"),
    ]
    tables = {name: [] for name in ["empresa_junior", "monitoramento", "metas", "cluster_historico", "federacao"]}
    tables["federacao"] = [{"id": 991, "nome": "Federação Sintética A"}, {"id": 992, "nome": "Federação Sintética B"}]
    for eid, name, cluster, fat, colab, csat, status in specs:
        tables["empresa_junior"].append({"id": eid, "id_ej": eid, "nome": name, "federacao_id": 992 if eid == 900099 else 991, "status": status})
        if cluster is not None:
            for year in [2025, 2026]:
                tables["cluster_historico"].append({"id_ej": eid, "ano": year, "cluster": cluster})
        tables["metas"].append({"id": eid, "id_ej": eid, "ano": 2026, "meta_faturamento": 120000, "meta_csat": 4.5, "meta_engajamento_mej": 50, "meta_taxa_colaboracao": 0.2})
        if eid == 900008:
            continue
        for month in ([1, 3] if eid == 900003 else [1, 3, 5]):
            tables["monitoramento"].append({
                "id": eid * 100 + month, "id_ej": eid, "ano": 2026, "mes": month,
                "faturamento_mes": fat, "faturamento_acumulado": fat * month,
                # 9.2/9.23: acumulado não é a soma das três linhas esparsas.
                "faturamento_colab_mes": colab, "faturamento_colab_acumulado": colab * month,
                "projetos_vendidos_mes": 1 if fat else 0, "projetos_colab_mes": 1 if colab else 0,
                "csat": csat, "numero_membros": 10,
                # 9.9: max 15 / último 10 = 1,5; não normalizar nesta tarefa.
                "membros_engajados_mes": 15 if month == 1 else 2,
            })
        tables["monitoramento"].append({"id": eid * 100 + 90, "id_ej": eid, "ano": 2025, "mes": 5, "faturamento_acumulado": 10000, "faturamento_mes": 10000})
    return tables


def capturar(funcao):
    sb = BancoSintetico()
    scope = {"ano": 2026, "mes": 5, "federacao_id": 991}
    if funcao == "listar_empresas":
        value = listar_empresas(sb, **scope, page_size=100)
    elif funcao == "buscar_empresa":
        return {str(eid): buscar_empresa(sb, eid, **scope).model_dump(mode="json") for eid in range(900001, 900009)}
    elif funcao == "calcular_indicadores_rede":
        value = calcular_indicadores_rede(sb, **scope)
    elif funcao == "calcular_sde_cenarios":
        value = calcular_sde_cenarios(sb, **scope)
    else:
        value = calcular_evento(sb, "ciranda-mej-26", **scope)
    return value.model_dump(mode="json")


@pytest.mark.parametrize("funcao", ["listar_empresas", "buscar_empresa", "calcular_indicadores_rede", "calcular_sde_cenarios", "calcular_evento"])
def test_baseline_campo_a_campo_das_cinco_funcoes(funcao):
    expected = json.loads(BASELINE.read_text())[funcao]
    assert capturar(funcao) == expected


def test_ej_de_outro_tenant_nao_entra_no_perfil():
    assert buscar_empresa(BancoSintetico(), 900099, ano=2026, mes=5, federacao_id=991) is None


def test_ej_sem_cluster_conta_como_c1_e_engajamento_excede_cem_por_cento():
    # 9.14 permanece aberta; 9.9 não foi normalizada. Não são regras aprovadas.
    rede = capturar("calcular_indicadores_rede")
    assert rede["distribuicao_clusters"]["1"] == 4
    empresas = capturar("listar_empresas")["data"]
    assert empresas[1]["cluster"] is None
    assert empresas[1]["engajamento_mej"] == 1.5
    assert empresas[2]["faturamento_mes"] == 10000
    assert empresas[3]["csat_medio"] == 0
    assert empresas[5]["percentual_meta"] == 41.65
