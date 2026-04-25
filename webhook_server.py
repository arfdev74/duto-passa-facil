"""
webhook_server.py — Servidor FastAPI para receber callbacks do Mercado Pago

Deploy separado do Streamlit (ex: Railway.app — plano gratuito):
    uvicorn webhook_server:app --host 0.0.0.0 --port 8000

URL a configurar no painel do Mercado Pago:
    https://SEU-DOMINIO-RAILWAY.app/webhook/mercadopago

O Mercado Pago envia POST nessa URL sempre que:
  • Um pagamento é aprovado   → ativa o plano do usuário
  • Uma assinatura é cancelada → rebaixa para Free
"""

from fastapi import FastAPI, Request, HTTPException, Header
from supabase import create_client

from config import SUPABASE_URL, SUPABASE_SERVICE_KEY
from pagamento import validar_assinatura_webhook, processar_evento_mp
from database import atualizar_plano, rebaixar_para_free

app = FastAPI(title="Duto Passa Fácil — Webhook Server")


def _sb_admin():
    """Cliente Supabase com service key (permissão total) — só no servidor."""
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


@app.get("/health")
async def health():
    return {"status": "ok", "app": "Duto Passa Fácil Webhook"}


@app.post("/webhook/mercadopago")
async def webhook_mp(
    request: Request,
    x_signature: str = Header(default=""),
):
    """
    Endpoint chamado pelo Mercado Pago a cada evento de pagamento/assinatura.
    """
    payload_bytes = await request.body()
    payload = await request.json()

    # 1. Validar autenticidade
    if not validar_assinatura_webhook(payload_bytes, x_signature):
        raise HTTPException(status_code=401, detail="Assinatura inválida")

    tipo = payload.get("type", "")
    acao = payload.get("action", "")

    # 2. Pagamento aprovado → ativa plano
    resultado = processar_evento_mp(payload)
    if resultado:
        user_id, id_plano, subscription_id = resultado
        atualizar_plano(user_id, id_plano, subscription_id)
        print(f"✅ Plano '{id_plano}' ativado para usuário {user_id[:8]}...")
        return {"status": "ok", "acao": "plano_ativado"}

    # 3. Assinatura cancelada → rebaixa para Free
    if tipo == "subscription_preapproval" and acao in ("updated",):
        dados = payload.get("data", {})
        sub_id = str(dados.get("id", ""))
        status = dados.get("status", "")

        if status in ("cancelled", "paused"):
            rebaixar_para_free(sub_id)
            print(f"⬇️  Usuário rebaixado para Free (sub: {sub_id[:8]}...)")
            return {"status": "ok", "acao": "rebaixado_free"}

    # Evento ignorado (notificações de tentativas, etc.)
    return {"status": "ok", "acao": "ignorado"}
