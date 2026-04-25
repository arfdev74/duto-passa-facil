"""
tests/test_webhook.py
Testa os endpoints do webhook FastAPI sem precisar do Mercado Pago real.
Execute com:  pytest tests/test_webhook.py -v
"""

import sys
import os
import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# FastAPI test client
from fastapi.testclient import TestClient


# Mocka as dependências externas antes de importar o webhook
with patch("database.get_client"), \
     patch("pagamento.MP_ACCESS_TOKEN", "TEST-token"):
    from webhook_server import app

client = TestClient(app)


class TestHealthCheck:
    def test_health_retorna_ok(self):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


class TestWebhookMP:
    def test_assinatura_invalida_retorna_401(self):
        with patch("webhook_server.validar_assinatura_webhook", return_value=False):
            resp = client.post(
                "/webhook/mercadopago",
                json={"type": "payment", "action": "payment.updated", "data": {"id": "1"}},
                headers={"x-signature": "invalida"},
            )
        assert resp.status_code == 401

    def test_pagamento_aprovado_ativa_plano(self):
        with patch("webhook_server.validar_assinatura_webhook", return_value=True), \
             patch("webhook_server.processar_evento_mp",
                   return_value=("uuid-user", "profissional", "sub-789")), \
             patch("webhook_server.atualizar_plano") as mock_atualizar:

            resp = client.post(
                "/webhook/mercadopago",
                json={"type": "payment", "action": "payment.updated", "data": {"id": "1"}},
            )

        assert resp.status_code == 200
        assert resp.json()["acao"] == "plano_ativado"
        mock_atualizar.assert_called_once_with("uuid-user", "profissional", "sub-789")

    def test_assinatura_cancelada_rebaixa_para_free(self):
        with patch("webhook_server.validar_assinatura_webhook", return_value=True), \
             patch("webhook_server.processar_evento_mp", return_value=None), \
             patch("webhook_server.rebaixar_para_free") as mock_rebaixar:

            resp = client.post(
                "/webhook/mercadopago",
                json={
                    "type": "subscription_preapproval",
                    "action": "updated",
                    "data": {"id": "sub-789", "status": "cancelled"},
                },
            )

        assert resp.status_code == 200
        assert resp.json()["acao"] == "rebaixado_free"
        mock_rebaixar.assert_called_once_with("sub-789")

    def test_evento_irrelevante_retorna_ignorado(self):
        with patch("webhook_server.validar_assinatura_webhook", return_value=True), \
             patch("webhook_server.processar_evento_mp", return_value=None):

            resp = client.post(
                "/webhook/mercadopago",
                json={"type": "plan", "action": "plan.updated", "data": {}},
            )

        assert resp.status_code == 200
        assert resp.json()["acao"] == "ignorado"
