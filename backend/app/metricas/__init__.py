"""Métricas personalizadas: catálogo fechado, expressão segura e avaliação pura.

Nada aqui lê banco nem chama modelo. O service (`app/services/metricas_service.py`)
lê os dados autorizados e chama `avaliacao.calcular`; a IA só propõe uma definição,
que passa pelo mesmo parser antes de qualquer cálculo.
"""
