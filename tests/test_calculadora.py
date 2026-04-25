"""
tests/test_calculadora.py
Testes unitários do motor de cálculo — sem dependência de banco ou pagamento.
Execute com:  pytest tests/ -v
"""

import sys
import os
import math
import pytest

# Garante que o diretório pai está no path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app import (
    taxa_ocupacao,
    calcular_area_cabo,
    area_total_cabos,
    recomendar_eletrodutos,
    verificar_emi,
    verificar_trecho,
    fator_agrupamento_valor,
)


# ─────────────────────────────────────────────────────────
# TAXA DE OCUPAÇÃO
# ─────────────────────────────────────────────────────────

class TestTaxaOcupacao:
    def test_um_cabo(self):
        assert taxa_ocupacao(1) == 0.53

    def test_dois_cabos(self):
        assert taxa_ocupacao(2) == 0.31

    def test_tres_cabos(self):
        assert taxa_ocupacao(3) == 0.40

    def test_muitos_cabos(self):
        assert taxa_ocupacao(10) == 0.40
        assert taxa_ocupacao(50) == 0.40


# ─────────────────────────────────────────────────────────
# ÁREA DO CABO
# ─────────────────────────────────────────────────────────

class TestAreaCabo:
    def test_cabo_6mm_750v(self):
        # Ø externo = 4.83mm → área = π*(4.83/2)² ≈ 18.32 mm²
        resultado = calcular_area_cabo(4.83)
        assert abs(resultado - 18.32) < 0.1

    def test_cabo_50mm_rigido(self):
        # Ø externo = 15.10mm → área ≈ 179.08 mm²
        resultado = calcular_area_cabo(15.10)
        assert abs(resultado - 179.08) < 0.5

    def test_diametro_zero_retorna_zero(self):
        assert calcular_area_cabo(0) == 0.0


# ─────────────────────────────────────────────────────────
# ÁREA TOTAL DOS CABOS
# ─────────────────────────────────────────────────────────

class TestAreaTotalCabos:
    def test_dois_cabos_iguais(self):
        cabos = [{"diametro": 4.83, "quantidade": 2}]
        esperado = calcular_area_cabo(4.83) * 2
        assert abs(area_total_cabos(cabos) - esperado) < 0.01

    def test_mix_de_cabos(self):
        cabos = [
            {"diametro": 4.83, "quantidade": 3},   # 3 cabos 6mm 750V
            {"diametro": 9.33, "quantidade": 1},   # 1 cabo 16mm 0,6/1kV
        ]
        esperado = (calcular_area_cabo(4.83) * 3) + calcular_area_cabo(9.33)
        assert abs(area_total_cabos(cabos) - esperado) < 0.01

    def test_lista_vazia_retorna_zero(self):
        assert area_total_cabos([]) == 0.0


# ─────────────────────────────────────────────────────────
# RECOMENDAÇÃO DE ELETRODUTOS
# ─────────────────────────────────────────────────────────

class TestRecomendarEletrodutos:
    def test_area_pequena_retorna_menor_eletroduto(self):
        # Área de 100 mm² → deve indicar o menor eletroduto metálico (199 mm²)
        resultado = recomendar_eletrodutos(100.0, "Metálico (NBR 5597)")
        assert len(resultado) > 0
        assert resultado[0]["eletroduto"] == '15mm (1/2")'

    def test_area_enorme_retorna_lista_vazia(self):
        # Nenhum eletroduto padrão comporta 50.000 mm²
        resultado = recomendar_eletrodutos(50_000.0, "Metálico (NBR 5597)")
        assert resultado == []

    def test_pvc_retorna_eletrodutos_pvc(self):
        resultado = recomendar_eletrodutos(100.0, "PVC (NBR 6150)")
        assert len(resultado) > 0
        # Menor PVC tem 125.66 mm²
        assert resultado[0]["area_util"] >= 125.0

    def test_recomendacao_ordenada_por_tamanho(self):
        resultado = recomendar_eletrodutos(200.0, "Metálico (NBR 5597)")
        areas = [r["area_util"] for r in resultado]
        assert areas == sorted(areas)  # crescente


# ─────────────────────────────────────────────────────────
# VERIFICAÇÃO DE EMI
# ─────────────────────────────────────────────────────────

class TestVerificarEmi:
    def test_sem_conflito_so_potencia(self):
        cabos = [
            {"tipo_cabo": "Cabo 750V (flexível)"},
            {"tipo_cabo": "Cabo 0,6/1kV (rígido)"},
        ]
        conflito, tipos = verificar_emi(cabos)
        assert conflito is False
        assert "potência" in tipos

    def test_conflito_potencia_e_dados(self):
        cabos = [
            {"tipo_cabo": "Cabo 750V (flexível)"},
            {"tipo_cabo": "Cabo UTP Cat.6 (dados)"},
        ]
        conflito, _ = verificar_emi(cabos)
        assert conflito is True

    def test_conflito_potencia_e_sinal(self):
        cabos = [
            {"tipo_cabo": "Cabo 0,6/1kV (flexível)"},
            {"tipo_cabo": "Cabo Coaxial RG-58 (sinal)"},
        ]
        conflito, _ = verificar_emi(cabos)
        assert conflito is True

    def test_sem_conflito_so_sinal(self):
        cabos = [
            {"tipo_cabo": "Cabo UTP Cat.6 (dados)"},
            {"tipo_cabo": "Cabo Coaxial RG-6 (CFTV)"},
        ]
        conflito, _ = verificar_emi(cabos)
        assert conflito is False


# ─────────────────────────────────────────────────────────
# VERIFICAÇÃO DE TRECHO
# ─────────────────────────────────────────────────────────

class TestVerificarTrecho:
    def test_trecho_ok(self):
        alerta, msgs = verificar_trecho(2, 10.0)
        assert alerta is False
        assert msgs == []

    def test_excesso_de_curvas(self):
        alerta, msgs = verificar_trecho(4, 10.0)
        assert alerta is True
        assert any("curva" in m.lower() for m in msgs)

    def test_comprimento_excedido(self):
        alerta, msgs = verificar_trecho(1, 20.0)
        assert alerta is True
        assert any("20.0" in m for m in msgs)

    def test_ambos_excedidos(self):
        alerta, msgs = verificar_trecho(5, 30.0)
        assert alerta is True
        assert len(msgs) == 2

    def test_limite_exato_curvas_ok(self):
        alerta, _ = verificar_trecho(3, 10.0)
        assert alerta is False

    def test_limite_exato_comprimento_ok(self):
        alerta, _ = verificar_trecho(0, 15.0)
        assert alerta is False


# ─────────────────────────────────────────────────────────
# FATOR DE AGRUPAMENTO
# ─────────────────────────────────────────────────────────

class TestFatorAgrupamento:
    def test_um_circuito_fator_maximo(self):
        assert fator_agrupamento_valor(1) == 1.00

    def test_dois_circuitos(self):
        assert fator_agrupamento_valor(2) == 0.80

    def test_seis_circuitos(self):
        assert fator_agrupamento_valor(6) == 0.57

    def test_acima_do_maximo_usa_12(self):
        # 15 circuitos → usa o fator de 12 (0.45)
        assert fator_agrupamento_valor(15) == 0.45

    def test_fator_sempre_menor_que_1(self):
        for n in range(1, 13):
            assert fator_agrupamento_valor(n) <= 1.0

    def test_fator_sempre_positivo(self):
        for n in range(1, 13):
            assert fator_agrupamento_valor(n) > 0


# ─────────────────────────────────────────────────────────
# CENÁRIOS DE INTEGRAÇÃO (cálculo ponta a ponta)
# ─────────────────────────────────────────────────────────

class TestCenariosReais:
    """
    Casos práticos tirados de projetos reais para validar
    que toda a cadeia de cálculo está correta.
    """

    def test_cenario_quadro_iluminacao(self):
        """
        Quadro de iluminação: 3 cabos 2,5mm² 750V
        Ø ext = 3.75mm → área = 11.04mm² cada → total = 33.13mm²
        Taxa 3+ cabos = 40% → área mínima = 33.13 / 0.40 = 82.82mm²
        Menor PVC disponível: 20mm (125.66mm²) → OK
        """
        cabos = [{"diametro": 3.75, "quantidade": 3}]
        area = area_total_cabos(cabos)
        taxa = taxa_ocupacao(3)
        area_min = area / taxa
        adequados = recomendar_eletrodutos(area_min, "PVC (NBR 6150)")

        assert abs(area - 33.13) < 0.1
        assert abs(area_min - 82.82) < 0.5
        assert adequados[0]["eletroduto"] == '20mm (3/4")'

    def test_cenario_alimentador_50mm2(self):
        """
        Alimentador: 1 cabo 50mm² 0,6/1kV
        Ø ext = 14.60mm → área = 167.42mm²
        Taxa 1 cabo = 53% → área mínima = 315.89mm²
        Menor metálico: 25mm (554.59mm²) → OK
        """
        cabos = [{"diametro": 14.60, "quantidade": 1}]
        area = area_total_cabos(cabos)
        taxa = taxa_ocupacao(1)
        area_min = area / taxa
        adequados = recomendar_eletrodutos(area_min, "Metálico (NBR 5597)")

        assert abs(area - 167.42) < 0.5
        assert abs(area_min - 315.89) < 1.0
        assert adequados[0]["eletroduto"] == '25mm (1")'

    def test_cenario_emi_invalido_aeroporto(self):
        """
        Caso típico do Santos Dumont: engenheiro tentando colocar
        cabo de força junto com UTP de sistema de balizamento.
        Deve gerar alerta de EMI.
        """
        cabos = [
            {"tipo_cabo": "Cabo 0,6/1kV (rígido)"},   # potência
            {"tipo_cabo": "Cabo UTP Cat.6 (dados)"},   # dados
        ]
        conflito, _ = verificar_emi(cabos)
        assert conflito is True
