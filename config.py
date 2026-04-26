"""
config.py — Configurações centrais do Duto Passa Fácil
Modelo: Licença Vitalícia — Free (3/mês) + Profissional (R$ 9,99 único)
"""

import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


def _get(key: str, default: str = "") -> str:
    """
    Lê variável de ambiente com fallback para st.secrets.
    - Localmente: usa o arquivo .env via os.getenv()
    - Streamlit Cloud: usa st.secrets (TOML no painel)
    """
    # Tenta os.getenv primeiro (local / Railway)
    valor = os.getenv(key, "")
    if valor:
        return valor.strip()

    # Fallback para st.secrets (Streamlit Cloud)
    try:
        import streamlit as st
        return str(st.secrets.get(key, default)).strip()
    except Exception:
        return default


# ─────────────────────────────────────────────────────────
# SUPABASE
# ─────────────────────────────────────────────────────────
SUPABASE_URL: str = _get("SUPABASE_URL")
SUPABASE_KEY: str = _get("SUPABASE_ANON_KEY")
SUPABASE_SERVICE_KEY: str = _get("SUPABASE_SERVICE_KEY")

# ─────────────────────────────────────────────────────────
# MERCADO PAGO
# ─────────────────────────────────────────────────────────
MP_ACCESS_TOKEN: str = _get("MP_ACCESS_TOKEN")
MP_WEBHOOK_SECRET: str = _get("MP_WEBHOOK_SECRET")
APP_BASE_URL: str = _get("APP_BASE_URL", "http://localhost:8501")

# ─────────────────────────────────────────────────────────
# PLANOS
# ─────────────────────────────────────────────────────────
@dataclass
class Plano:
    id: str
    nome: str
    preco_brl: float      # 0 = gratuito
    consultas_mes: int    # -1 = ilimitado
    historico: bool
    descricao: str
    vitalicio: bool       # True = pagamento único, False = gratuito


PLANOS: dict[str, Plano] = {
    "free": Plano(
        id="free",
        nome="Free",
        preco_brl=0.0,
        consultas_mes=3,
        historico=False,
        vitalicio=False,
        descricao="3 dimensionamentos por mês. Ideal para conhecer a ferramenta.",
    ),
    "profissional": Plano(
        id="profissional",
        nome="Profissional",
        preco_brl=9.99,
        consultas_mes=-1,
        historico=True,
        vitalicio=True,
        descricao="Licença vitalícia. Ilimitado para sempre, sem mensalidade.",
    ),
}
