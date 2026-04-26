"""
webhook_server.py — Servidor FastAPI para callbacks do Mercado Pago
Modelo: Pagamento único — só trata aprovação, sem cancelamento recorrente.

Deploy separado (Railway.app — gratuito):
    uvicorn webhook_server:app --host 0.0.0.0 --port 8000

URL a configurar no painel do Mercado Pago:
    https://SEU-DOMINIO.railway.app/webhook/mercadopago
"""

from fastapi import FastAPI, Request, HTTPException, Header
from supabase import create_client

from config import SUPABASE_URL, SUPABASE_SERVICE_KEY
from pagamento import validar_assinatura_webhook, processar_evento_mp
from database import ativar_profissional

app = FastAPI(title="Duto Passa Fácil — Webhook")


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
    Quando pagamento é aprovado → ativa licença Profissional vitalícia.
    """
    payload_bytes = await request.body()
    payload = await request.json()

    # 1. Valida autenticidade
    if not validar_assinatura_webhook(payload_bytes, x_signature):
        raise HTTPException(status_code=401, detail="Assinatura inválida")

    # 2. Processa evento — retorna user_id se aprovado
    user_id = processar_evento_mp(payload)

    if user_id:
        payment_id = str(payload.get("data", {}).get("id", ""))
        ativar_profissional(user_id, payment_id)
        print(f"✅ Licença Profissional ativada — usuário {user_id[:8]}...")
        return {"status": "ok", "acao": "licenca_ativada"}

    # Evento irrelevante (tentativas, estornos futuros, etc.)
    return {"status": "ok", "acao": "ignorado"}
