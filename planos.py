"""
planos.py — Tela de upgrade e gate de cota
Modelo: Free (3/mês) + Profissional (R$ 9,99 vitalício)
"""

from __future__ import annotations
import streamlit as st
from config import PLANOS, Plano
from database import verificar_cota
from pagamento import criar_link_pagamento


# ─────────────────────────────────────────────────────────
# GATE DE COTA
# ─────────────────────────────────────────────────────────

def gate_cota(perfil: dict) -> bool:
    """
    Retorna True se o usuário pode fazer uma consulta.
    Se não pode, mostra a tela de upgrade e retorna False.
    """
    plano_obj: Plano = PLANOS[perfil.get("plano", "free")]
    tem_cota, usadas, limite = verificar_cota(perfil, plano_obj.consultas_mes)

    if tem_cota:
        _badge_cota(usadas, limite, plano_obj)
        return True

    render_tela_upgrade(perfil)
    return False


def _badge_cota(usadas: int, limite: int, plano: Plano) -> None:
    """Badge na sidebar mostrando uso do mês."""
    if limite == -1:
        st.sidebar.markdown(
            f'<div style="background:#152d1f;border:1px solid #27ae60;border-radius:6px;'
            f'padding:0.6rem 0.8rem;margin-bottom:0.5rem;font-size:0.8rem;">'
            f'🏆 Plano <strong style="color:#2ecc71">{plano.nome}</strong><br>'
            f'<span style="color:#2ecc71;font-family:monospace;font-size:0.9rem">Ilimitado ∞</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
        return

    restantes = limite - usadas
    cor = "#2ecc71" if restantes > 0 else "#e74c3c"
    st.sidebar.markdown(
        f'<div style="background:#1a1d26;border:1px solid #2a2d3a;border-radius:6px;'
        f'padding:0.6rem 0.8rem;margin-bottom:0.5rem;font-size:0.8rem;">'
        f'📊 Plano <strong>{plano.nome}</strong><br>'
        f'<span style="color:{cor};font-family:monospace;font-size:1rem;font-weight:700">'
        f'{restantes}</span>'
        f'<span style="color:#888"> de {limite} consultas restantes</span>'
        f'</div>',
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────────────────
# TELA DE UPGRADE
# ─────────────────────────────────────────────────────────

def render_tela_upgrade(perfil: dict) -> None:
    """Tela mostrada quando a cota Free esgota."""
    st.markdown("""
    <div style="text-align:center;padding:2rem 0 1.5rem">
        <div style="font-size:2.5rem">🔒</div>
        <div style="font-family:'IBM Plex Mono',monospace;font-size:1.4rem;
                    color:#00d4aa;font-weight:700;margin-top:0.5rem">
            Cota do mês esgotada
        </div>
        <div style="color:#888;font-size:0.9rem;margin-top:0.4rem">
            Você usou os 3 dimensionamentos gratuitos deste mês.<br>
            Desbloqueie o acesso ilimitado por apenas <strong style="color:#fff">R$ 9,99</strong> — para sempre.
        </div>
    </div>
    """, unsafe_allow_html=True)

    render_cards_planos(perfil)


def render_cards_planos(perfil: dict) -> None:
    """Renderiza os 2 cards de plano lado a lado."""
    plano_atual_id = perfil.get("plano", "free")

    col1, col2 = st.columns(2)

    with col1:
        _card_free(plano_atual_id)

    with col2:
        _card_profissional(perfil, plano_atual_id)


def _card_free(plano_atual_id: str) -> None:
    atual = plano_atual_id == "free"

    if atual:
        st.markdown("✔️ *Seu plano atual*")
    else:
        st.markdown("&nbsp;", unsafe_allow_html=True)

    st.markdown("### Free")
    st.markdown(
        '<span style="color:#2ecc71;font-size:1.5rem;font-weight:700;'
        'font-family:monospace">Grátis</span>',
        unsafe_allow_html=True,
    )
    st.caption("3 dimensionamentos por mês. Ideal para conhecer a ferramenta.")
    st.divider()

    features = [
        (True,  "3 consultas por mês"),
        (False, "Histórico de projetos"),
        (False, "Acesso ilimitado"),
    ]
    for ok, txt in features:
        cor = "#ddd" if ok else "#555"
        icone = "✅" if ok else "❌"
        st.markdown(
            f'<div style="color:{cor};font-size:0.85rem;padding:2px 0">{icone} {txt}</div>',
            unsafe_allow_html=True,
        )

    st.write("")
    st.button("Plano atual", disabled=True, key="btn_free", use_container_width=True)


def _card_profissional(perfil: dict, plano_atual_id: str) -> None:
    atual = plano_atual_id == "profissional"

    st.markdown("⭐ **Recomendado**")
    st.markdown("### Profissional")
    st.markdown(
        '<span style="color:#00d4aa;font-size:1.5rem;font-weight:700;'
        'font-family:monospace">R$ 9,99</span>'
        '<span style="color:#888;font-size:0.85rem"> único · vitalício</span>',
        unsafe_allow_html=True,
    )
    st.caption("Pague uma vez, use para sempre. Sem mensalidade.")
    st.divider()

    features = [
        (True, "Consultas ilimitadas"),
        (True, "Histórico de projetos"),
        (True, "Acesso vitalício"),
    ]
    for ok, txt in features:
        st.markdown(
            f'<div style="color:#ddd;font-size:0.85rem;padding:2px 0">✅ {txt}</div>',
            unsafe_allow_html=True,
        )

    st.write("")

    if atual:
        st.button(
            "✅ Licença ativa",
            disabled=True,
            key="btn_prof",
            use_container_width=True,
        )
    else:
        if st.button(
            "Comprar por R$ 9,99",
            key="btn_prof",
            use_container_width=True,
            type="primary",
        ):
            with st.spinner("Gerando link de pagamento..."):
                _iniciar_checkout(perfil)


def _iniciar_checkout(perfil: dict) -> None:
    """Gera o link do Mercado Pago e redireciona."""
    try:
        url = criar_link_pagamento(
            user_id=perfil["id"],
            user_email=perfil["email"],
        )
        st.markdown(
            f'<meta http-equiv="refresh" content="0; url={url}">',
            unsafe_allow_html=True,
        )
        st.success(
            f"Redirecionando para o pagamento... "
            f"[Clique aqui se não redirecionar]({url})"
        )
    except Exception as e:
        st.error(f"Erro ao gerar link de pagamento: {e}")
