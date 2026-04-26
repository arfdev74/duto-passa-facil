"""
database.py — Operações com o Supabase (PostgreSQL)

Tabelas:
  • profiles  — dados do usuário e plano
  • consultas — histórico de dimensionamentos
"""

from __future__ import annotations
import json
from datetime import datetime
from typing import Optional

from supabase import create_client, Client
from config import SUPABASE_URL, SUPABASE_KEY, SUPABASE_SERVICE_KEY


def get_client() -> Client:
    """
    Retorna cliente Supabase com service key.
    Streamlit roda server-side — a service key nunca é exposta ao usuário.
    """
    key = SUPABASE_SERVICE_KEY or SUPABASE_KEY
    if not SUPABASE_URL or not key:
        raise RuntimeError(
            "Variáveis SUPABASE_URL e SUPABASE_SERVICE_KEY não configuradas."
        )
    return create_client(SUPABASE_URL, key)


# ─────────────────────────────────────────────────────────
# PERFIL
# ─────────────────────────────────────────────────────────

def buscar_perfil(user_id: str) -> Optional[dict]:
    """Retorna o perfil do usuário ou None se não existir."""
    try:
        sb = get_client()
        resp = sb.table("profiles").select("*").eq("id", user_id).single().execute()
        return resp.data
    except Exception:
        return None


def garantir_perfil(user_id: str, email: str) -> dict:
    """Busca ou cria perfil — chamado após login."""
    perfil = buscar_perfil(user_id)
    if not perfil:
        sb = get_client()
        perfil = {
            "id": user_id,
            "email": email,
            "nome": email.split("@")[0],
            "plano": "free",
            "consultas_mes": 0,
            "mes_referencia": _mes_atual(),
        }
        resp = sb.table("profiles").insert(perfil).execute()
        return resp.data[0] if resp.data else perfil
    return perfil


# ─────────────────────────────────────────────────────────
# COTA MENSAL
# ─────────────────────────────────────────────────────────

def verificar_cota(perfil: dict, limite: int) -> tuple[bool, int, int]:
    """
    Verifica se o usuário tem cota disponível.
    Returns: (tem_cota, usadas, limite) — limite -1 = ilimitado
    """
    if limite == -1:
        return True, perfil.get("consultas_mes", 0), -1

    # Reseta se mudou o mês
    if perfil.get("mes_referencia") != _mes_atual():
        _resetar_contador(perfil["id"])
        return True, 0, limite

    usadas = perfil.get("consultas_mes", 0)
    return usadas < limite, usadas, limite


def incrementar_consulta(user_id: str) -> None:
    """Incrementa o contador de consultas do mês."""
    sb = get_client()
    perfil = buscar_perfil(user_id)
    if not perfil:
        return

    mes = _mes_atual()
    if perfil.get("mes_referencia") != mes:
        sb.table("profiles").update({
            "consultas_mes": 1,
            "mes_referencia": mes,
        }).eq("id", user_id).execute()
    else:
        novo = (perfil.get("consultas_mes") or 0) + 1
        sb.table("profiles").update({
            "consultas_mes": novo,
        }).eq("id", user_id).execute()


def _resetar_contador(user_id: str) -> None:
    sb = get_client()
    sb.table("profiles").update({
        "consultas_mes": 0,
        "mes_referencia": _mes_atual(),
    }).eq("id", user_id).execute()


# ─────────────────────────────────────────────────────────
# ATIVAR LICENÇA PROFISSIONAL
# ─────────────────────────────────────────────────────────

def ativar_profissional(user_id: str, payment_id: str) -> None:
    """
    Ativa o plano Profissional vitalício após pagamento confirmado.
    Uma vez ativado, nunca volta para Free automaticamente.
    """
    sb = get_client()
    sb.table("profiles").update({
        "plano": "profissional",
        "mp_payment_id": payment_id,
    }).eq("id", user_id).execute()


# ─────────────────────────────────────────────────────────
# HISTÓRICO
# ─────────────────────────────────────────────────────────

def salvar_consulta(user_id: str, entrada: dict, resultado: dict) -> None:
    """Persiste um dimensionamento no histórico (plano Profissional)."""
    sb = get_client()
    sb.table("consultas").insert({
        "user_id": user_id,
        "dados_entrada": json.dumps(entrada, ensure_ascii=False),
        "resultado": json.dumps(resultado, ensure_ascii=False),
    }).execute()


def buscar_historico(user_id: str, limite: int = 20) -> list[dict]:
    """Retorna os últimos dimensionamentos do usuário."""
    sb = get_client()
    resp = (
        sb.table("consultas")
        .select("*")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .limit(limite)
        .execute()
    )
    return resp.data or []


# ─────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────

def _mes_atual() -> str:
    return datetime.now().strftime("%Y-%m")
