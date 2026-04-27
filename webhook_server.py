"""
webhook_server.py — Servidor FastAPI para callbacks do Mercado Pago
"""

from fastapi import FastAPI, Request, Header
from config import SUPABASE_URL, SUPABASE_SERVICE_KEY
from pagamento import validar_assinatura_webhook
from database import ativar_profissional
import mercadopago
import os

app = FastAPI(title="Duto Passa Fácil — Webhook")


def _sdk():
    from config import MP_ACCESS_TOKEN
    return mercadopago.SDK(MP_ACCESS_TOKEN)


@app.get("/health")
async def health():
    return {"status": "ok", "app": "Duto Passa Fácil Webhook", "modelo": "licença vitalícia"}


@app.post("/webhook/mercadopago")
async def webhook_mp(
    request: Request,
    x_signature: str = Header(default=""),
):
    """
    Recebe notificações do Mercado Pago.
    O MP envia o payment_id como query param: ?data.id=XXX&type=payment
    """
    # Pega query params
    params = dict(request.query_params)
    payment_id = params.get("data.id", "")
    tipo = params.get("type", "")

    # Também tenta ler do body JSON (simulação e outros formatos)
    try:
        body = await request.json()
        if not payment_id:
            payment_id = str(body.get("data", {}).get("id", ""))
        if not tipo:
            tipo = body.get("type", "")
    except Exception:
        pass

    print(f"Webhook recebido — tipo: {tipo}, payment_id: {payment_id}")

    if tipo != "payment" or not payment_id:
        print(f"Evento ignorado — tipo: {tipo}, payment_id: {payment_id}")
        return {"status": "ok", "acao": "ignorado"}

    # Busca dados do pagamento no MP
    try:
        sdk = _sdk()
        payment = sdk.payment().get(payment_id)["response"]
        status = payment.get("status", "")
        user_id = payment.get("external_reference", "")

        print(f"Pagamento {payment_id} — status: {status}, user_id: {user_id}")

        if status == "approved" and user_id:
            ativar_profissional(user_id, payment_id)
            print(f"✅ Licença Profissional ativada — usuário {user_id[:8]}...")
            return {"status": "ok", "acao": "licenca_ativada"}
        else:
            print(f"Pagamento não aprovado ou sem user_id — status: {status}")
            return {"status": "ok", "acao": "ignorado"}

    except Exception as e:
        print(f"Erro ao processar pagamento {payment_id}: {e}")
        return {"status": "ok", "acao": "erro", "detail": str(e)}
