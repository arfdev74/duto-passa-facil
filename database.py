"""
database.py — Operações com o Supabase (PostgreSQL)

Tabelas utilizadas:
  • profiles   — dados do usuário, plano e cota mensal
  • consultas  — histórico de dimensionamentos
"""

from __future__ import annotations
import json
from datetime import datetime
from typing import Optional

from supabase import create_client, Client
from config import SUPABASE_URL, SUPABASE_KEY


def get_client() -> Client:
    """Retorna cliente Supabase autenticado com chave anônima."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise RuntimeError(
            "Variáveis SUPABASE_URL e SUPABASE_ANON_KEY não configuradas. "
            "Verifique o arquivo .env"
        )
    return create_client(SUPABASE_URL, SUPABASE_KEY)


# ─────────────────────────────────────────────────────────
# PERFIL DO USUÁRIO
# ─────────────────────────────────────────────────────────

def buscar_perfil(user_id: str) -> Optional[dict]:
    """Retorna o perfil do usuário ou None se não existir."""
    sb = get_client()
    resp = sb.table("profiles").select("*").eq("id", user_id).single().execute()
    return resp.data


def criar_perfil(user_id: str, email: str, nome: str = "") -> dict:
    """Cria perfil inicial com plano Free."""
    sb = get_client()
    perfil = {
        "id": user_id,
        "email": email,
        "nome": nome or email.split("@")[0],
        "plano": "free",
        "consultas_mes": 0,
        "mes_referencia": _mes_atual(),
        "mp_subscription_id": None,
    }
    resp = sb.table("profiles").insert(perfil).execute()
    return resp.data[0]


def garantir_perfil(user_id: str, email: str) -> dict:
    """Busca ou cria perfil — use após login."""
    perfil = buscar_perfil(user_id)
    if not perfil:
        perfil = criar_perfil(user_id, email)
    return perfil


# ─────────────────────────────────────────────────────────
# COTA MENSAL
# ─────────────────────────────────────────────────────────

def verificar_cota(perfil: dict, limite: int) -> tuple[bool, int, int]:
    """
    Verifica se o usuário ainda tem cota disponível.

    Returns:
        (tem_cota, consultas_usadas, limite)
        limite == -1 significa ilimitado
    """
    if limite == -1:
        return True, perfil["consultas_mes"], -1

    # Reseta contador se mudou o mês
    if perfil.get("mes_referencia") != _mes_atual():
        _resetar_contador(perfil["id"])
        return True, 0, limite

    usadas = perfil.get("consultas_mes", 0)
    return usadas < limite, usadas, limite


def incrementar_consulta(user_id: str) -> None:
    """Incrementa o contador de consultas do mês."""
    sb = get_client()
    # Busca valor atual para incrementar
    perfil = buscar_perfil(user_id)
    mes = _mes_atual()

    if perfil.get("mes_referencia") != mes:
        # Novo mês — zera e começa em 1
        sb.table("profiles").update({
            "consultas_mes": 1,
            "mes_referencia": mes,
        }).eq("id", user_id).execute()
    else:
        novo_valor = (perfil.get("consultas_mes") or 0) + 1
        sb.table("profiles").update({
            "consultas_mes": novo_valor,
        }).eq("id", user_id).execute()


def _resetar_contador(user_id: str) -> None:
    sb = get_client()
    sb.table("profiles").update({
        "consultas_mes": 0,
        "mes_referencia": _mes_atual(),
    }).eq("id", user_id).execute()


# ─────────────────────────────────────────────────────────
# HISTÓRICO DE CONSULTAS
# ─────────────────────────────────────────────────────────

def salvar_consulta(user_id: str, entrada: dict, resultado: dict) -> None:
    """Persiste um dimensionamento no histórico."""
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
# ATUALIZAÇÃO DE PLANO (chamado pelo webhook do MP)
# ─────────────────────────────────────────────────────────

def atualizar_plano(user_id: str, novo_plano: str, mp_subscription_id: str) -> None:
    """Eleva o plano do usuário após pagamento confirmado."""
    sb = get_client()
    sb.table("profiles").update({
        "plano": novo_plano,
        "mp_subscription_id": mp_subscription_id,
    }).eq("id", user_id).execute()


def rebaixar_para_free(mp_subscription_id: str) -> None:
    """Volta para Free quando assinatura é cancelada/expirada."""
    sb = get_client()
    sb.table("profiles").update({
        "plano": "free",
        "mp_subscription_id": None,
    }).eq("mp_subscription_id", mp_subscription_id).execute()


# ─────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────

def _mes_atual() -> str:
    """Retorna 'YYYY-MM' do mês corrente."""
    return datetime.now().strftime("%Y-%m")
