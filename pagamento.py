"""
pagamento.py — Integração com Mercado Pago

Fluxo:
  1. criar_link_assinatura()  → gera URL de checkout do MP
  2. Usuário paga (PIX ou cartão)
  3. MP chama o webhook (webhook_server.py)
  4. Webhook atualiza o plano no banco via database.atualizar_plano()
"""

from __future__ import annotations
import hmac
import hashlib
import json

import mercadopago

from config import MP_ACCESS_TOKEN, APP_BASE_URL, MP_WEBHOOK_SECRET, PLANOS


def _sdk() -> mercadopago.SDK:
    if not MP_ACCESS_TOKEN:
        raise RuntimeError(
            "MP_ACCESS_TOKEN não configurado. Verifique o arquivo .env"
        )
    return mercadopago.SDK(MP_ACCESS_TOKEN)


# ─────────────────────────────────────────────────────────
# CRIAR LINK DE ASSINATURA (Preapproval Plan)
# ─────────────────────────────────────────────────────────

def criar_link_assinatura(user_id: str, id_plano: str) -> str:
    """
    Cria uma assinatura recorrente mensal no Mercado Pago e
    retorna a URL de checkout para redirecionar o usuário.

    O campo external_reference carrega user_id|id_plano para
    o webhook identificar quem pagou e qual plano ativar.
    """
    plano = PLANOS[id_plano]
    sdk = _sdk()

    dados = {
        "reason": f"Duto Passa Fácil — Plano {plano.nome}",
        "auto_recurring": {
            "frequency": 1,
            "frequency_type": "months",
            "transaction_amount": plano.preco_brl,
            "currency_id": "BRL",
        },
        "back_url": f"{APP_BASE_URL}?pagamento=sucesso&plano={id_plano}",
        "external_reference": f"{user_id}|{id_plano}",
        "status": "pending",
    }

    resp = sdk.preapproval().create(dados)

    if resp["status"] not in (200, 201):
        raise RuntimeError(
            f"Erro ao criar assinatura no Mercado Pago: {resp['response']}"
        )

    return resp["response"]["init_point"]


# ─────────────────────────────────────────────────────────
# CRIAR PLANOS NO MP (rodar uma vez no setup)
# ─────────────────────────────────────────────────────────

def criar_planos_mp() -> dict[str, str]:
    """
    Cria os planos Profissional e Empresarial no Mercado Pago
    e retorna {id_plano: mp_plan_id}.

    Execute este script UMA VEZ durante o setup:
        python -c "from pagamento import criar_planos_mp; print(criar_planos_mp())"

    Cole os IDs retornados no .env como MP_PLAN_ID_PROF e MP_PLAN_ID_EMP.
    """
    sdk = _sdk()
    resultado = {}

    for id_plano in ("profissional", "empresarial"):
        plano = PLANOS[id_plano]
        dados = {
            "reason": f"Duto Passa Fácil — {plano.nome}",
            "auto_recurring": {
                "frequency": 1,
                "frequency_type": "months",
                "transaction_amount": plano.preco_brl,
                "currency_id": "BRL",
            },
            "back_url": APP_BASE_URL,
        }
        resp = sdk.plan().create(dados)
        if resp["status"] in (200, 201):
            resultado[id_plano] = resp["response"]["id"]
            print(f"✅ Plano '{id_plano}' criado: {resp['response']['id']}")
        else:
            print(f"❌ Erro ao criar plano '{id_plano}': {resp['response']}")

    return resultado


# ─────────────────────────────────────────────────────────
# CANCELAR ASSINATURA
# ─────────────────────────────────────────────────────────

def cancelar_assinatura(mp_subscription_id: str) -> bool:
    """Cancela assinatura ativa no Mercado Pago."""
    sdk = _sdk()
    resp = sdk.preapproval().update(
        mp_subscription_id, {"status": "cancelled"}
    )
    return resp["status"] in (200, 201)


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
# EXTRAIR DADOS DO WEBHOOK
# ─────────────────────────────────────────────────────────

def processar_evento_mp(payload: dict) -> tuple[str, str, str] | None:
    """
    Lê o payload do webhook e retorna (user_id, id_plano, mp_subscription_id)
    ou None se o evento não for relevante.

    Eventos tratados:
      • payment approved  → ativa plano
      • subscription cancelled/paused → rebaixa para free (tratado no webhook_server)
    """
    tipo = payload.get("type")
    acao = payload.get("action")

    if tipo == "payment" and acao == "payment.updated":
        sdk = _sdk()
        payment_id = payload["data"]["id"]
        payment = sdk.payment().get(payment_id)["response"]

        if payment.get("status") != "approved":
            return None

        referencia = payment.get("external_reference", "")
        if "|" not in referencia:
            return None

        user_id, id_plano = referencia.split("|", 1)
        subscription_id = payment.get("order", {}).get("id", payment_id)
        return user_id, id_plano, str(subscription_id)

    return None
