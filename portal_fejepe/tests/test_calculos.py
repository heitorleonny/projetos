"""
Testes unitários para app.services.calculo_service.

Valida cada fórmula estratégica conforme documentado em calculos.md.
"""

import pytest

from app.services.calculo_service import (
    calcular_crescimento,
    calcular_media_csat,
    calcular_percentual_meta,
    calcular_pontos_cluster,
    calcular_pontos_cluster_adaptativo,
    calcular_ritmo_necessario,
    calcular_sde,
    calcular_taxa_colaboracao,
    calcular_tendencia_cluster,
    classificar_cluster,
    classificar_ritmo,
    projetar_faturamento_anual,
)
from app.models.empresa import Ritmo, TendenciaCluster


# ── 1. Percentual de Meta ────────────────────────────────────


class TestPercentualMeta:
    def test_meta_atingida_50_porcento(self):
        assert calcular_percentual_meta(60_000, 120_000) == 50.0

    def test_meta_atingida_100_porcento(self):
        assert calcular_percentual_meta(120_000, 120_000) == 100.0

    def test_meta_superada(self):
        assert calcular_percentual_meta(150_000, 120_000) == 125.0

    def test_meta_none(self):
        assert calcular_percentual_meta(50_000, None) is None

    def test_meta_zero(self):
        assert calcular_percentual_meta(50_000, 0) is None


# ── 2. Classificação de Ritmo ────────────────────────────────


class TestClassificarRitmo:
    def test_sem_vendas(self):
        assert classificar_ritmo(0, 120_000) == Ritmo.sem_vendas

    def test_ritmo_minimo(self):
        """Vendeu algo, mas abaixo da meta mensal (120k/12 = 10k)."""
        assert classificar_ritmo(5_000, 120_000) == Ritmo.minimo

    def test_ritmo_significativo(self):
        """Vendeu >= meta mensal."""
        assert classificar_ritmo(10_000, 120_000) == Ritmo.significativo

    def test_ritmo_significativo_acima_meta(self):
        assert classificar_ritmo(15_000, 120_000) == Ritmo.significativo

    def test_sem_meta_vendeu(self):
        """Se não tem meta mas vendeu, é mínimo."""
        assert classificar_ritmo(5_000, None) == Ritmo.minimo

    def test_faturamento_negativo(self):
        assert classificar_ritmo(-100, 120_000) == Ritmo.sem_vendas


# ── 3. Taxa de Colaboração ───────────────────────────────────


class TestTaxaColaboracao:
    def test_taxa_25_porcento(self):
        assert calcular_taxa_colaboracao(30_000, 120_000) == 0.25

    def test_sem_faturamento(self):
        assert calcular_taxa_colaboracao(0, 0) is None

    def test_taxa_zero(self):
        assert calcular_taxa_colaboracao(0, 100_000) == 0.0


# ── 4. Pontuação de Cluster ──────────────────────────────────


class TestPontosCluster:
    def test_formula_basica(self):
        """
        Faturamento=100_000, CSAT=4.5, Engaj=0.25, Colab=0.10
        Pontos = 100_000 * 4.5 * (1+0.25) * (1+0.10) * 100
               = 100_000 * 4.5 * 1.25 * 1.10 * 100
               = 61_875_000_000
        """
        resultado = calcular_pontos_cluster(100_000, 4.5, 0.25, 0.10)
        assert resultado == pytest.approx(61_875_000.0, rel=1e-2)

    def test_sem_engajamento_nem_colab(self):
        """
        Faturamento=50_000, CSAT=4.0, Engaj=0, Colab=0
        Pontos = 50_000 * 4.0 * 1 * 1 * 100 = 20_000_000
        """
        resultado = calcular_pontos_cluster(50_000, 4.0, 0, 0)
        assert resultado == pytest.approx(20_000_000.0, rel=1e-2)


# ── 4b. Pontuação de Cluster Adaptativa ──────────────────────


class TestPontosClusterAdaptativo:
    """
    Testa as 3 fases da fórmula adaptativa:
    - Fase 1 (mês 1-3): meta_csat + meta_engajamento
    - Fase 2 (mês 4-6): meta_csat + engajamento condicional
    - Fase 3 (mês 7-12): csat_real + engajamento_real
    """

    # ── Fase 1 (Q1: meses 1-3) ──

    def test_fase1_basico(self):
        """
        Mês 3: usa meta_csat e meta_engajamento.
        fat_acum=30_000, mes=3 → fat_anual = 120_000
        meta_csat=4.5, meta_engaj=0.25, colab=0.10
        Pontos = 120_000 * 4.5 * 1.25 * 1.10 * 100 = 74_250_000
        """
        pontos = calcular_pontos_cluster_adaptativo(
            faturamento_acumulado=30_000,
            mes_atual=3,
            meta_csat=4.5,
            csat_real=3.0,  # Ignorado na fase 1
            meta_engajamento_mej=0.25,
            engajamento_real=0.05,  # Ignorado na fase 1
            taxa_colaboracao=0.10,
        )
        assert pontos is not None
        assert pontos == pytest.approx(74_250_000.0, rel=1e-2)

    def test_fase1_mes_1(self):
        """
        Mês 1: fat_anual = 10_000 * 12 = 120_000
        meta_csat=4.0, meta_engaj=0, colab=0
        Pontos = 120_000 * 4.0 * 1.0 * 1.0 * 100 = 48_000_000
        """
        pontos = calcular_pontos_cluster_adaptativo(10_000, 1, 4.0, None, 0, None, 0)
        assert pontos == pytest.approx(48_000_000.0, rel=1e-2)

    def test_fase1_ignora_csat_real(self):
        """Na fase 1, CSAT real é ignorado — usa meta."""
        p1 = calcular_pontos_cluster_adaptativo(30_000, 2, 4.5, 2.0, 0.25, 0.1, 0.10)
        p2 = calcular_pontos_cluster_adaptativo(30_000, 2, 4.5, 5.0, 0.25, 0.1, 0.10)
        assert p1 == p2  # csat_real diferente, resultado igual

    # ── Fase 2 (Q2: meses 4-6) ──

    def test_fase2_engajamento_no_caminho(self):
        """
        Mês 5: engaj_real=0.10 >= meta*0.25 (0.40*0.25=0.10) → usa meta (0.40)
        fat_acum=50_000, mes=5 → fat_anual = 120_000
        meta_csat=4.5, engaj=0.40, colab=0.10
        Pontos = 120_000 * 4.5 * 1.40 * 1.10 * 100 = 83_160_000
        """
        pontos = calcular_pontos_cluster_adaptativo(
            faturamento_acumulado=50_000,
            mes_atual=5,
            meta_csat=4.5,
            csat_real=4.0,  # Ignorado na fase 2
            meta_engajamento_mej=0.40,
            engajamento_real=0.10,  # >= 0.40*0.25=0.10 → usa meta
            taxa_colaboracao=0.10,
        )
        assert pontos is not None
        assert pontos == pytest.approx(83_160_000.0, rel=1e-2)

    def test_fase2_engajamento_penalizado(self):
        """
        Mês 5: engaj_real=0.05 < meta*0.25 (0.40*0.25=0.10) → usa 0.05/0.25=0.20
        fat_anual = 120_000
        Pontos = 120_000 * 4.5 * 1.20 * 1.10 * 100 = 71_280_000
        """
        pontos = calcular_pontos_cluster_adaptativo(
            faturamento_acumulado=50_000,
            mes_atual=5,
            meta_csat=4.5,
            csat_real=4.0,
            meta_engajamento_mej=0.40,
            engajamento_real=0.05,  # < 0.10 → usa 0.05/0.25 = 0.20
            taxa_colaboracao=0.10,
        )
        assert pontos is not None
        assert pontos == pytest.approx(71_280_000.0, rel=1e-2)

    # ── Fase 3 (Q3/Q4: meses 7-12) ──

    def test_fase3_usa_valores_reais(self):
        """
        Mês 9: usa csat_real e engajamento_real.
        fat_acum=90_000, mes=9 → fat_anual = 120_000
        csat_real=4.8, engaj_real=0.30, colab=0.10
        Pontos = 120_000 * 4.8 * 1.30 * 1.10 * 100 = 82_368_000
        """
        pontos = calcular_pontos_cluster_adaptativo(
            faturamento_acumulado=90_000,
            mes_atual=9,
            meta_csat=4.5,  # Ignorado na fase 3
            csat_real=4.8,
            meta_engajamento_mej=0.25,  # Ignorado na fase 3
            engajamento_real=0.30,
            taxa_colaboracao=0.10,
        )
        assert pontos is not None
        assert pontos == pytest.approx(82_368_000.0, rel=1e-2)

    def test_fase3_sem_csat_real(self):
        """Na fase 3, se CSAT real é None → None (não pode calcular)."""
        pontos = calcular_pontos_cluster_adaptativo(
            90_000, 9, 4.5, None, 0.25, 0.30, 0.10
        )
        assert pontos is None

    def test_fase3_mes_12_converge(self):
        """No mês 12, faturamento anualizado = faturamento real."""
        fat_anual = 120_000
        pontos_adaptativo = calcular_pontos_cluster_adaptativo(
            fat_anual, 12, 4.5, 4.8, 0.25, 0.30, 0.10
        )
        # Fase 3: usa csat_real=4.8 e engaj_real=0.30
        pontos_oficial = calcular_pontos_cluster(fat_anual, 4.8, 0.30, 0.10)
        assert pontos_adaptativo == pytest.approx(pontos_oficial, rel=1e-6)

    # ── Edge cases ──

    def test_sem_faturamento(self):
        assert calcular_pontos_cluster_adaptativo(0, 3, 4.5, 4.0, 0.25, 0.1, 0.10) is None

    def test_mes_zero(self):
        assert calcular_pontos_cluster_adaptativo(30_000, 0, 4.5, 4.0, 0.25, 0.1, 0.10) is None

    def test_fase1_sem_meta_csat(self):
        assert calcular_pontos_cluster_adaptativo(30_000, 3, None, 4.0, 0.25, 0.1, 0.10) is None


# ── 5. Classificação de Cluster ──────────────────────────────


class TestClassificarCluster:
    def test_cluster_1(self):
        assert classificar_cluster(5_000_000) == 1

    def test_cluster_2(self):
        assert classificar_cluster(15_000_000) == 2

    def test_cluster_3(self):
        assert classificar_cluster(40_000_000) == 3

    def test_cluster_4(self):
        assert classificar_cluster(100_000_000) == 4

    def test_cluster_5(self):
        assert classificar_cluster(200_000_000) == 5

    def test_cluster_limites(self):
        """Valores exatos nos limites."""
        assert classificar_cluster(0) == 1
        assert classificar_cluster(12_000_000) == 1
        assert classificar_cluster(12_000_000.01) == 2
        assert classificar_cluster(24_000_000) == 2
        assert classificar_cluster(24_000_000.01) == 3


# ── 6. Tendência de Cluster ──────────────────────────────────


class TestTendenciaCluster:
    def test_sobe(self):
        assert calcular_tendencia_cluster(3, 2) == TendenciaCluster.sobe

    def test_desce(self):
        assert calcular_tendencia_cluster(1, 3) == TendenciaCluster.desce

    def test_mantem(self):
        assert calcular_tendencia_cluster(2, 2) == TendenciaCluster.mantem

    def test_dados_insuficientes(self):
        assert calcular_tendencia_cluster(None, 2) is None
        assert calcular_tendencia_cluster(3, None) is None


# ── 7. SDE ───────────────────────────────────────────────────


class TestSDE:
    def test_sde_positivo(self):
        """Mais EJs subindo que descendo."""
        sde = calcular_sde(
            subidas_por_cluster=[3, 2, 1, 1, 0],
            descidas_por_cluster=[1, 1, 0, 0, 0],
        )
        # 0.30*(3-1) + 0.25*(2-1) + 0.15*(1-0) + 0.15*(1-0) + 0.15*(0-0)
        # = 0.60 + 0.25 + 0.15 + 0.15 + 0
        # = 1.15
        assert sde == pytest.approx(1.15, rel=1e-4)

    def test_sde_negativo(self):
        """Mais EJs descendo que subindo."""
        sde = calcular_sde(
            subidas_por_cluster=[0, 0, 0, 0, 0],
            descidas_por_cluster=[2, 3, 1, 0, 0],
        )
        # 0.30*(0-2) + 0.25*(0-3) + 0.15*(0-1) + 0 + 0
        # = -0.60 + -0.75 + -0.15
        # = -1.50
        assert sde == pytest.approx(-1.50, rel=1e-4)

    def test_sde_neutro(self):
        sde = calcular_sde(
            subidas_por_cluster=[1, 1, 1, 1, 1],
            descidas_por_cluster=[1, 1, 1, 1, 1],
        )
        assert sde == pytest.approx(0.0, abs=1e-10)

    def test_sde_tamanho_invalido(self):
        with pytest.raises(ValueError):
            calcular_sde([1, 2], [1, 2, 3, 4, 5])


# ── 8. Crescimento Percentual ────────────────────────────────


class TestCrescimento:
    def test_crescimento_positivo(self):
        assert calcular_crescimento(115, 100) == 15.0

    def test_crescimento_negativo(self):
        assert calcular_crescimento(80, 100) == -20.0

    def test_sem_anterior(self):
        assert calcular_crescimento(100, 0) is None


# ── 9. Projeção Anual ────────────────────────────────────────


class TestProjecaoAnual:
    def test_tendencia_constante(self):
        """Se fatura 10k todo mês, projeção ≈ 120k."""
        serie = [10_000] * 6  # 6 meses iguais
        projecao = projetar_faturamento_anual(serie)
        assert projecao is not None
        assert projecao == pytest.approx(120_000, rel=0.01)

    def test_tendencia_crescente(self):
        """Faturamento crescente: projeção > acumulado simples."""
        serie = [10_000, 12_000, 14_000, 16_000]
        projecao = projetar_faturamento_anual(serie)
        assert projecao is not None
        assert projecao > sum(serie)

    def test_dados_insuficientes(self):
        assert projetar_faturamento_anual([10_000]) is None
        assert projetar_faturamento_anual([]) is None


# ── 10. Ritmo Necessário ─────────────────────────────────────


class TestRitmoNecessario:
    def test_ritmo_basico(self):
        """Meta 120k, acumulou 60k, faltam 6 meses → 10k/mês."""
        assert calcular_ritmo_necessario(120_000, 60_000, 6) == 10_000.0

    def test_meta_ja_atingida(self):
        assert calcular_ritmo_necessario(120_000, 130_000, 6) == 0.0

    def test_sem_meta(self):
        assert calcular_ritmo_necessario(None, 50_000, 6) is None

    def test_sem_meses_restantes(self):
        assert calcular_ritmo_necessario(120_000, 50_000, 0) is None


# ── 11. Média CSAT ───────────────────────────────────────────


class TestMediaCSAT:
    def test_media_simples(self):
        assert calcular_media_csat([4.0, 4.5, 5.0]) == 4.5

    def test_ignora_none(self):
        assert calcular_media_csat([4.0, None, 5.0]) == 4.5

    def test_todos_none(self):
        assert calcular_media_csat([None, None]) is None

    def test_lista_vazia(self):
        assert calcular_media_csat([]) is None
