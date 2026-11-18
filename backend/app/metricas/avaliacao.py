"""Cálculo puro de uma métrica sobre linhas já lidas com o tenant (sem banco, sem I/O).

Regras de período (decisões de 12/11/2026):

* a janela é sempre dentro de um único ano;
* uma EJ entra no cálculo só se tiver monitoramento em TODOS os meses da janela
  (quando a fórmula usa variável de monitoramento). As que faltam saem e são
  contadas em `sem_cobertura`; o período nunca é trocado em silêncio;
* uma EJ com cobertura mas sem valor (variável ausente, divisão por zero) sai e
  é contada em `sem_valor`. Ausente não vira zero, salvo `ausente_e_zero`.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.metricas.catalogo import VARIAVEIS
from app.metricas.expressao import No, avaliar, variaveis

MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho",
         "agosto", "setembro", "outubro", "novembro", "dezembro"]


def texto_periodo(ano: int, mes_inicio: int, mes_fim: int | None) -> str:
    if mes_fim is None:
        return f"de {MESES[mes_inicio - 1]} até o último mês com dados de {ano}"
    if mes_inicio == mes_fim:
        return f"{MESES[mes_inicio - 1]} de {ano}"
    return f"de {MESES[mes_inicio - 1]} a {MESES[mes_fim - 1]} de {ano}"


def valor_da_variavel(nome: str, meses: list[dict], meta: dict | None) -> float | None:
    """Valor de uma variável para uma EJ. `meses` vem ordenado por mês, só da janela."""
    var = VARIAVEIS[nome]
    if var.agregacao == "ano":
        bruto = (meta or {}).get(var.coluna)
        return None if bruto is None else float(bruto)
    registrados = [m.get(var.coluna) for m in meses if m.get(var.coluna) is not None]
    if var.agregacao == "soma":
        return float(sum(registrados)) if registrados else None
    if registrados:
        return float(registrados[-1])
    return 0.0 if var.ausente_e_zero and meses else None


@dataclass
class Calculo:
    valores: dict[int, float] = field(default_factory=dict)  # id_ej → valor
    total_ejs: int = 0
    sem_cobertura: int = 0
    sem_valor: int = 0


def calcular_janela(no: No, *, ids_ej: list[int], monitoramento: dict[int, dict[int, dict]],
                    metas: dict[int, dict], mes_inicio: int, mes_fim: int) -> Calculo:
    """`monitoramento` é {id_ej: {mes: linha}}; `metas` é {id_ej: linha do ano}."""
    usadas = variaveis(no)
    exige_mensal = any(VARIAVEIS[n].origem == "monitoramento" for n in usadas)
    janela = range(mes_inicio, mes_fim + 1)
    calculo = Calculo(total_ejs=len(ids_ej))
    for id_ej in ids_ej:
        por_mes = monitoramento.get(id_ej, {})
        if exige_mensal and any(m not in por_mes for m in janela):
            calculo.sem_cobertura += 1
            continue
        meses = [por_mes[m] for m in janela if m in por_mes]
        valor = avaliar(no, {n: valor_da_variavel(n, meses, metas.get(id_ej)) for n in usadas})
        if valor is None:
            calculo.sem_valor += 1
            continue
        calculo.valores[id_ej] = valor
    return calculo


def agregar(valores: list[float], agregacao: str) -> float | None:
    if not valores:
        return None
    total = sum(valores)
    return total if agregacao == "soma" else total / len(valores)


def explicar(no: No, periodo: str) -> list[str]:
    linhas = [f"Período: {periodo}."]
    for nome in sorted(variaveis(no), key=lambda n: VARIAVEIS[n].rotulo):
        var = VARIAVEIS[nome]
        linhas.append(f"{var.rotulo}: {var.descricao}.")
    if any(VARIAVEIS[n].origem == "monitoramento" for n in variaveis(no)):
        linhas.append("Entram só as EJs com monitoramento em todos os meses do período e com valor em "
                      "todas as variáveis. Divisão por zero deixa a EJ sem valor.")
    else:
        linhas.append("Entram só as EJs com valor em todas as variáveis. Divisão por zero deixa a EJ sem valor.")
    linhas.append("Métrica personalizada da federação: não é indicador oficial do MEJ e não altera "
                  "cluster, SDE ou tracking.")
    return linhas
