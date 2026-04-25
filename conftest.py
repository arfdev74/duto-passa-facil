"""
conftest.py — Fixtures compartilhadas entre todos os testes
O pytest carrega este arquivo automaticamente.
"""

import pytest
import os
import sys

# Garante que o diretório raiz do projeto está no path
sys.path.insert(0, os.path.dirname(__file__))

# Bloqueia chamadas reais ao Supabase e Mercado Pago durante testes unitários
os.environ.setdefault("SUPABASE_URL", "https://fake.supabase.co")
os.environ.setdefault("SUPABASE_ANON_KEY", "fake-anon-key")
os.environ.setdefault("SUPABASE_SERVICE_KEY", "fake-service-key")
os.environ.setdefault("MP_ACCESS_TOKEN", "TEST-fake-mp-token")
os.environ.setdefault("MP_WEBHOOK_SECRET", "fake-secret")
os.environ.setdefault("APP_BASE_URL", "http://localhost:8501")


# ─────────────────────────────────────────────────────────
# FIXTURES REUTILIZÁVEIS
# ─────────────────────────────────────────────────────────

@pytest.fixture
def perfil_free():
    """Perfil de usuário no plano gratuito com cota disponível."""
    from datetime import datetime
    return {
        "id": "uuid-free-user",
        "email": "free@teste.com",
        "nome": "Eng Free",
        "plano": "free",
        "consultas_mes": 0,
        "mes_referencia": datetime.now().strftime("%Y-%m"),
        "mp_subscription_id": None,
    }


@pytest.fixture
def perfil_profissional():
    """Perfil de usuário no plano Profissional."""
    from datetime import datetime
    return {
        "id": "uuid-prof-user",
        "email": "prof@teste.com",
        "nome": "Eng Profissional",
        "plano": "profissional",
        "consultas_mes": 5,
        "mes_referencia": datetime.now().strftime("%Y-%m"),
        "mp_subscription_id": "sub-mp-profissional-123",
    }


@pytest.fixture
def perfil_free_esgotado():
    """Perfil Free que já usou a cota do mês."""
    from datetime import datetime
    return {
        "id": "uuid-free-esgotado",
        "email": "esgotado@teste.com",
        "plano": "free",
        "consultas_mes": 1,
        "mes_referencia": datetime.now().strftime("%Y-%m"),
        "mp_subscription_id": None,
    }


@pytest.fixture
def cabos_simples():
    """Lista de cabos para um circuito básico de iluminação."""
    return [
        {"tipo_cabo": "Cabo 750V (flexível)", "secao": 2.5,
         "diametro": 3.75, "quantidade": 3, "sinal": "potência"},
    ]


@pytest.fixture
def cabos_com_emi():
    """Lista de cabos que viola a segregação de sinais."""
    return [
        {"tipo_cabo": "Cabo 0,6/1kV (rígido)", "secao": 6,
         "diametro": 7.00, "quantidade": 2, "sinal": "potência"},
        {"tipo_cabo": "Cabo UTP Cat.6 (dados)", "secao": 6.0,
         "diametro": 6.00, "quantidade": 1, "sinal": "dados"},
    ]


@pytest.fixture
def payload_webhook_aprovado():
    """Payload simulando pagamento aprovado do Mercado Pago."""
    return {
        "type": "payment",
        "action": "payment.updated",
        "data": {"id": "pay-teste-123"},
    }


@pytest.fixture
def payload_webhook_cancelado():
    """Payload simulando cancelamento de assinatura."""
    return {
        "type": "subscription_preapproval",
        "action": "updated",
        "data": {"id": "sub-teste-456", "status": "cancelled"},
    }
