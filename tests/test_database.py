"""
tests/test_database.py
Testes de integração do banco — usa mocks para não depender do Supabase real.
Execute com:  pytest tests/test_database.py -v
"""

import sys
import os
import pytest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


# ─────────────────────────────────────────────────────────
# MOCK DO SUPABASE
# ─────────────────────────────────────────────────────────

def make_supabase_mock(retorno_perfil=None, retorno_consultas=None):
    """Fábrica de mocks do cliente Supabase."""
    mock = MagicMock()

    # Simula o encadeamento fluente do Supabase:
    # sb.table("x").select("*").eq("id", y).single().execute()
    tabela = mock.table.return_value
    tabela.select.return_value = tabela
    tabela.insert.return_value = tabela
    tabela.update.return_value = tabela
    tabela.eq.return_value = tabela
    tabela.order.return_value = tabela
    tabela.limit.return_value = tabela
    tabela.single.return_value = tabela

    # Configura respostas
    tabela.execute.return_value = MagicMock(
        data=retorno_perfil or [],
    )

    return mock


# ─────────────────────────────────────────────────────────
# PERFIL
# ─────────────────────────────────────────────────────────

class TestBuscarPerfil:
    @patch("database.get_client")
    def test_retorna_perfil_existente(self, mock_get_client):
        perfil_fake = {
            "id": "uuid-123",
            "email": "eng@teste.com",
            "plano": "free",
            "consultas_mes": 0,
            "mes_referencia": "2026-04",
        }
        mock_get_client.return_value = make_supabase_mock(retorno_perfil=perfil_fake)

        from database import buscar_perfil
        resultado = buscar_perfil("uuid-123")
        assert resultado == perfil_fake

    @patch("database.get_client")
    def test_retorna_none_quando_nao_existe(self, mock_get_client):
        mock_sb = make_supabase_mock(retorno_perfil=None)
        mock_get_client.return_value = mock_sb

        from database import buscar_perfil
        resultado = buscar_perfil("uuid-inexistente")
        assert resultado is None


class TestCriarPerfil:
    @patch("database.get_client")
    def test_cria_com_plano_free(self, mock_get_client):
        perfil_criado = {
            "id": "novo-uuid",
            "email": "novo@eng.com",
            "plano": "free",
            "consultas_mes": 0,
        }
        mock_sb = MagicMock()
        mock_sb.table.return_value.insert.return_value.execute.return_value = MagicMock(
            data=[perfil_criado]
        )
        mock_get_client.return_value = mock_sb

        from database import criar_perfil
        resultado = criar_perfil("novo-uuid", "novo@eng.com", "Eng Novo")
        assert resultado["plano"] == "free"
        assert resultado["consultas_mes"] == 0


# ─────────────────────────────────────────────────────────
# COTA MENSAL
# ─────────────────────────────────────────────────────────

class TestVerificarCota:
    def test_free_com_zero_consultas_tem_cota(self):
        from database import verificar_cota
        import datetime

        perfil = {
            "consultas_mes": 0,
            "mes_referencia": datetime.datetime.now().strftime("%Y-%m"),
        }
        tem, usadas, limite = verificar_cota(perfil, limite=1)
        assert tem is True
        assert usadas == 0

    def test_free_com_uma_consulta_sem_cota(self):
        from database import verificar_cota
        import datetime

        perfil = {
            "consultas_mes": 1,
            "mes_referencia": datetime.datetime.now().strftime("%Y-%m"),
        }
        tem, usadas, limite = verificar_cota(perfil, limite=1)
        assert tem is False
        assert usadas == 1

    def test_ilimitado_sempre_tem_cota(self):
        from database import verificar_cota

        perfil = {"consultas_mes": 9999, "mes_referencia": "2026-04"}
        tem, _, limite = verificar_cota(perfil, limite=-1)
        assert tem is True
        assert limite == -1

    def test_novo_mes_reseta_cota(self):
        from database import verificar_cota

        # Perfil com mes_referencia do mês passado
        perfil = {
            "consultas_mes": 1,
            "mes_referencia": "2020-01",  # mês antigo
        }
        with patch("database._resetar_contador"):
            tem, usadas, limite = verificar_cota(perfil, limite=1)
        assert tem is True   # novo mês → cota resetada
        assert usadas == 0


# ─────────────────────────────────────────────────────────
# HISTÓRICO
# ─────────────────────────────────────────────────────────

class TestSalvarHistorico:
    @patch("database.get_client")
    def test_salva_json_corretamente(self, mock_get_client):
        mock_sb = MagicMock()
        mock_sb.table.return_value.insert.return_value.execute.return_value = MagicMock()
        mock_get_client.return_value = mock_sb

        from database import salvar_consulta
        entrada = {"cabos": [{"tipo": "Cabo 750V", "secao": 6}]}
        resultado = {"eletroduto_recomendado": '25mm (1")'}

        # Não deve levantar exceção
        salvar_consulta("uuid-123", entrada, resultado)

        # Verifica que insert foi chamado
        mock_sb.table.assert_called_with("consultas")
        mock_sb.table.return_value.insert.assert_called_once()


# ─────────────────────────────────────────────────────────
# ATUALIZAÇÃO DE PLANO
# ─────────────────────────────────────────────────────────

class TestAtualizarPlano:
    @patch("database.get_client")
    def test_atualiza_para_profissional(self, mock_get_client):
        mock_sb = MagicMock()
        mock_sb.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()
        mock_get_client.return_value = mock_sb

        from database import atualizar_plano
        atualizar_plano("uuid-123", "profissional", "sub-mp-456")

        update_call = mock_sb.table.return_value.update.call_args[0][0]
        assert update_call["plano"] == "profissional"
        assert update_call["mp_subscription_id"] == "sub-mp-456"

    @patch("database.get_client")
    def test_rebaixa_para_free(self, mock_get_client):
        mock_sb = MagicMock()
        tabela = mock_sb.table.return_value
        tabela.update.return_value = tabela
        tabela.eq.return_value = tabela
        tabela.execute.return_value = MagicMock()
        mock_get_client.return_value = mock_sb

        from database import rebaixar_para_free
        rebaixar_para_free("sub-mp-456")

        update_call = mock_sb.table.return_value.update.call_args[0][0]
        assert update_call["plano"] == "free"
        assert update_call["mp_subscription_id"] is None
