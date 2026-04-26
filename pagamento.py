"""
pagamento.py — Integração com Mercado Pago
Modelo: Pagamento único (preference) — sem assinatura recorrente.

Fluxo:
  1. criar_link_pagamento()  → gera URL de checkout do MP
  2. Usuário paga (PIX, cartão ou boleto)
  3. MP chama o webhook (webhook_server.py)
  4. Webhook atualiza o plano no banco via database.ativar_profissional()
"""

from __future__ import annotations
import hmac
import hashlib
import mercadopago
from config import MP_ACCESS_TOKEN, APP_BASE_URL, MP_WEBHOOK_SECRET


def _sdk() -> mercadopago.SDK:
    if not MP_ACCESS_TOKEN:
        raise RuntimeError(
            "MP_ACCESS_TOKEN não configurado. Verifique o arquivo .env"
        )
    return mercadopago.SDK(MP_ACCESS_TOKEN)


# ─────────────────────────────────────────────────────────
# CRIAR LINK DE PAGAMENTO ÚNICO (Preference)
# ─────────────────────────────────────────────────────────

def criar_link_pagamento(user_id: str, user_email: str) -> str:
    """
    Cria uma preferência de pagamento único no Mercado Pago e
    retorna a URL de checkout.

    O external_reference carrega o user_id para o webhook
    identificar quem pagou e ativar o plano Profissional.
    """
    sdk = _sdk()

    back_url = (
        APP_BASE_URL
        if APP_BASE_URL.startswith("https://")
        else "https://www.mercadopago.com.br"
    )

    dados = {
        "items": [
            {
                "title": "Duto Passa Fácil — Licença Profissional Vitalícia",
                "quantity": 1,
                "unit_price": 9.99,
                "currency_id": "BRL",
                "description": "Acesso ilimitado e vitalício ao dimensionador NBR 5410",
            }
        ],
        "payer": {
            "email": user_email,
        },
        "back_urls": {
            "success": f"{back_url}?pagamento=sucesso",
            "failure": f"{back_url}?pagamento=falha",
            "pending": f"{back_url}?pagamento=pendente",
        },
        "auto_return": "approved",
        "external_reference": user_id,
        "statement_descriptor": "DUTO PASSA FACIL",
        "payment_methods": {
            "excluded_payment_types": [],
            "installments": 1,  # à vista — sem parcelamento para R$ 9,99
        },
    }

    resp = sdk.preference().create(dados)

    if resp["status"] not in (200, 201):
        raise RuntimeError(
            f"Erro ao criar pagamento no Mercado Pago: {resp['response']}"
        )

    # Usa sempre init_point — sandbox_init_point causa loop de redirect
    url = resp["response"].get("init_point", "")

    if not url:
        raise RuntimeError("URL de checkout não retornada pelo Mercado Pago.")

    return url


# ─────────────────────────────────────────────────────────
# VALIDAR ASSINATURA DO WEBHOOK
# ─────────────────────────────────────────────────────────

def validar_assinatura_webhook(payload: bytes, assinatura_recebida: str) -> bool:
    """
    Verifica a assinatura HMAC-SHA256 enviada pelo Mercado Pago
    no header x-signature para garantir autenticidade do webhook.
    """
    if not MP_WEBHOOK_SECRET:
        return True  # em desenvolvimento sem secret configurado

    esperado = hmac.new(
        MP_WEBHOOK_SECRET.encode(),
        payload,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(esperado, assinatura_recebida)


# ─────────────────────────────────────────────────────────
# PROCESSAR EVENTO DO WEBHOOK
# ─────────────────────────────────────────────────────────

def processar_evento_mp(payload: dict) -> str | None:
    """
    Lê o payload do webhook e retorna o user_id se o pagamento
    foi aprovado, ou None caso contrário.
    """
    tipo = payload.get("type")
    acao = payload.get("action")

    if tipo == "payment" and acao == "payment.updated":
        sdk = _sdk()
        payment_id = payload["data"]["id"]
        payment = sdk.payment().get(payment_id)["response"]

        if payment.get("status") != "approved":
            return None

        user_id = payment.get("external_reference", "")
        return user_id if user_id else None

    return None
