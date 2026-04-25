"""
tests/test_pagamento.py
Testes do fluxo de pagamento — usa mocks do SDK do Mercado Pago.
Execute com:  pytest tests/test_pagamento.py -v
"""

import sys
import os
import json
import hmac
import hashlib
import pytest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


# ─────────────────────────────────────────────────────────
# CRIAÇÃO DE LINK DE ASSINATURA
# ─────────────────────────────────────────────────────────

class TestCriarLinkAssinatura:
    @patch("pagamento.mercadopago.SDK")
    @patch("pagamento.MP_ACCESS_TOKEN", "TEST-fake-token")
    def test_retorna_url_de_checkout(self, mock_sdk_class):
        mock_sdk = MagicMock()
        mock_sdk_class.return_value = mock_sdk
        mock_sdk.preapproval.return_value.create.return_value = {
            "status": 201,
            "response": {"init_point": "https://www.mercadopago.com.br/subscriptions/checkout?preapproval_plan_id=abc123"},
        }

        from pagamento import criar_link_assinatura
        url = criar_link_assinatura("uuid-user-123", "profissional")

        assert url.startswith("https://")
        assert "mercadopago" in url

    @patch("pagamento.mercadopago.SDK")
    @patch("pagamento.MP_ACCESS_TOKEN", "TEST-fake-token")
    def test_external_reference_contem_user_e_plano(self, mock_sdk_class):
        mock_sdk = MagicMock()
        mock_sdk_class.return_value = mock_sdk
        mock_sdk.preapproval.return_value.create.return_value = {
            "status": 201,
            "response": {"init_point": "https://mp.com/checkout"},
        }

        from pagamento import criar_link_assinatura
        criar_link_assinatura("uuid-abc", "empresarial")

        chamada = mock_sdk.preapproval.return_value.create.call_args[0][0]
        assert chamada["external_reference"] == "uuid-abc|empresarial"

    @patch("pagamento.mercadopago.SDK")
    @patch("pagamento.MP_ACCESS_TOKEN", "TEST-fake-token")
    def test_erro_mp_lanca_exception(self, mock_sdk_class):
        mock_sdk = MagicMock()
        mock_sdk_class.return_value = mock_sdk
        mock_sdk.preapproval.return_value.create.return_value = {
            "status": 400,
            "response": {"message": "Bad request"},
        }

        from pagamento import criar_link_assinatura
        with pytest.raises(RuntimeError, match="Erro ao criar assinatura"):
            criar_link_assinatura("uuid-abc", "profissional")

    def test_sem_token_lanca_exception(self):
        with patch("pagamento.MP_ACCESS_TOKEN", ""):
            from pagamento import criar_link_assinatura
            with pytest.raises(RuntimeError, match="MP_ACCESS_TOKEN"):
                criar_link_assinatura("uuid-abc", "profissional")


# ─────────────────────────────────────────────────────────
# VALIDAÇÃO DO WEBHOOK
# ─────────────────────────────────────────────────────────

class TestValidarWebhook:
    def test_assinatura_valida(self):
        secret = "meu-secret-teste"
        payload = b'{"type":"payment","action":"payment.updated"}'
        assinatura = hmac.new(
            secret.encode(), payload, hashlib.sha256
        ).hexdigest()

        with patch("pagamento.MP_WEBHOOK_SECRET", secret):
            from pagamento import validar_assinatura_webhook
            assert validar_assinatura_webhook(payload, assinatura) is True

    def test_assinatura_invalida(self):
        with patch("pagamento.MP_WEBHOOK_SECRET", "secret-correto"):
            from pagamento import validar_assinatura_webhook
            assert validar_assinatura_webhook(b"payload", "assinatura-errada") is False

    def test_sem_secret_configurado_aceita_tudo(self):
        with patch("pagamento.MP_WEBHOOK_SECRET", ""):
            from pagamento import validar_assinatura_webhook
            assert validar_assinatura_webhook(b"qualquer", "coisa") is True


# ─────────────────────────────────────────────────────────
# PROCESSAMENTO DO EVENTO
# ─────────────────────────────────────────────────────────

class TestProcessarEventoMP:
    @patch("pagamento.mercadopago.SDK")
    @patch("pagamento.MP_ACCESS_TOKEN", "TEST-token")
    def test_payment_approved_extrai_dados(self, mock_sdk_class):
        mock_sdk = MagicMock()
        mock_sdk_class.return_value = mock_sdk
        mock_sdk.payment.return_value.get.return_value = {
            "response": {
                "status": "approved",
                "external_reference": "uuid-user|profissional",
                "order": {"id": "sub-mp-789"},
            }
        }

        from pagamento import processar_evento_mp
        payload = {
            "type": "payment",
            "action": "payment.updated",
            "data": {"id": "pay-123"},
        }
        resultado = processar_evento_mp(payload)

        assert resultado is not None
        user_id, plano, sub_id = resultado
        assert user_id == "uuid-user"
        assert plano == "profissional"
        assert "789" in sub_id

    @patch("pagamento.mercadopago.SDK")
    @patch("pagamento.MP_ACCESS_TOKEN", "TEST-token")
    def test_payment_pending_retorna_none(self, mock_sdk_class):
        mock_sdk = MagicMock()
        mock_sdk_class.return_value = mock_sdk
        mock_sdk.payment.return_value.get.return_value = {
            "response": {"status": "pending", "external_reference": "uuid|profissional"}
        }

        from pagamento import processar_evento_mp
        payload = {"type": "payment", "action": "payment.updated", "data": {"id": "1"}}
        assert processar_evento_mp(payload) is None

    def test_tipo_irrelevante_retorna_none(self):
        from pagamento import processar_evento_mp
        payload = {"type": "plan", "action": "plan.created", "data": {}}
        assert processar_evento_mp(payload) is None
