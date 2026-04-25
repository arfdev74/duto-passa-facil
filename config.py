"""
config.py — Configurações centrais do Duto Passa Fácil
Todas as variáveis de ambiente e constantes ficam aqui.
"""

import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


# ─────────────────────────────────────────────────────────
# SUPABASE
# ─────────────────────────────────────────────────────────
SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY: str = os.getenv("SUPABASE_ANON_KEY", "")  # chave pública (anon)
SUPABASE_SERVICE_KEY: str = os.getenv("SUPABASE_SERVICE_KEY", "")  # só no webhook


# ─────────────────────────────────────────────────────────
# MERCADO PAGO
# ─────────────────────────────────────────────────────────
MP_ACCESS_TOKEN: str = os.getenv("MP_ACCESS_TOKEN", "")
MP_WEBHOOK_SECRET: str = os.getenv("MP_WEBHOOK_SECRET", "")  # validação HMAC
APP_BASE_URL: str = os.getenv("APP_BASE_URL", "http://localhost:8501")


# ─────────────────────────────────────────────────────────
# PLANOS — edite aqui para ajustar preços e limites
# ─────────────────────────────────────────────────────────
@dataclass
class Plano:
    id: str
    nome: str
    preco_brl: float          # 0 = gratuito
    consultas_mes: int        # -1 = ilimitado
    historico: bool           # acesso ao histórico de projetos
    exportar_pdf: bool        # exportação em PDF
    multiusuario: bool        # conta empresarial com membros
    logo_personalizada: bool  # logo da empresa no PDF
    mp_plan_id: str           # ID do plano no Mercado Pago (preenchido após criação)
    descricao: str


PLANOS: dict[str, Plano] = {
    "free": Plano(
        id="free",
        nome="Free",
        preco_brl=0.0,
        consultas_mes=1,
        historico=False,
        exportar_pdf=False,
        multiusuario=False,
        logo_personalizada=False,
        mp_plan_id="",
        descricao="1 dimensionamento por mês. Ideal para conhecer a ferramenta.",
    ),
    "profissional": Plano(
        id="profissional",
        nome="Profissional",
        preco_brl=29.90,
        consultas_mes=50,
        historico=True,
        exportar_pdf=True,
        multiusuario=False,
        logo_personalizada=False,
        mp_plan_id=os.getenv("MP_PLAN_ID_PROF", ""),
        descricao="50 dimensionamentos/mês, histórico completo e exportação PDF.",
    ),
    "empresarial": Plano(
        id="empresarial",
        nome="Empresarial",
        preco_brl=89.90,
        consultas_mes=-1,       # ilimitado
        historico=True,
        exportar_pdf=True,
        multiusuario=True,
        logo_personalizada=True,
        mp_plan_id=os.getenv("MP_PLAN_ID_EMP", ""),
        descricao="Ilimitado, multi-usuário e logo da empresa nos relatórios.",
    ),
}
