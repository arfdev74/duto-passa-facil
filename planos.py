"""
planos.py — Tela de planos, gate de cota e lógica de upgrade

Responsável por:
  • Mostrar os 3 planos com preços e benefícios
  • Bloquear o acesso ao calculador quando a cota está esgotada
  • Gerar o link de pagamento do Mercado Pago
"""

from __future__ import annotations
import streamlit as st
from config import PLANOS, Plano
from database import verificar_cota
from pagamento import criar_link_assinatura


# ─────────────────────────────────────────────────────────
# VERIFICAÇÃO DE COTA (gate antes do cálculo)
# ─────────────────────────────────────────────────────────

def gate_cota(perfil: dict) -> bool:
    """
    Retorna True se o usuário pode fazer uma consulta.
    Se não pode, renderiza a tela de upgrade e retorna False.
    """
    from config import PLANOS
    plano_obj: Plano = PLANOS[perfil.get("plano", "free")]
    tem_cota, usadas, limite = verificar_cota(perfil, plano_obj.consultas_mes)

    if tem_cota:
        # Mostra badge de cota restante na sidebar
        _badge_cota(usadas, limite, plano_obj.nome)
        return True

    # Sem cota → mostra tela de upgrade
    render_tela_upgrade(perfil, usadas, limite, plano_obj)
    return False


def _badge_cota(usadas: int, limite: int, nome_plano: str) -> None:
    """Badge na sidebar mostrando uso do mês."""
    if limite == -1:
        st.sidebar.caption(f"📊 Plano **{nome_plano}** · Ilimitado")
        return

    restantes = limite - usadas
    cor = "#2ecc71" if restantes > 0 else "#e74c3c"
    st.sidebar.markdown(
        f'<div style="background:#1a1d26; border:1px solid #2a2d3a; '
        f'border-radius:6px; padding:0.6rem 0.8rem; margin-bottom:0.5rem; '
        f'font-size:0.8rem;">'
        f'📊 Plano <strong>{nome_plano}</strong><br>'
        f'<span style="color:{cor}; font-family:\'IBM Plex Mono\',monospace; '
        f'font-size:1rem; font-weight:700">{restantes}</span>'
        f'<span style="color:#888"> de {limite} consultas restantes este mês</span>'
        f'</div>',
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────────────────
# TELA DE UPGRADE
# ─────────────────────────────────────────────────────────

def render_tela_upgrade(
    perfil: dict,
    usadas: int,
    limite: int,
    plano_atual: Plano,
) -> None:
    """Tela completa de upgrade quando a cota esgota."""

    st.markdown("""
    <div style="text-align:center; padding:2rem 0 1rem;">
        <div style="font-size:2.5rem">🔒</div>
        <div style="font-family:'IBM Plex Mono',monospace; font-size:1.4rem;
                    color:#00d4aa; font-weight:700; margin-top:0.5rem">
            Cota do mês esgotada
        </div>
        <div style="color:#888; font-size:0.9rem; margin-top:0.4rem">
            Você usou todas as consultas do plano <strong style="color:#fff">
            {plano}</strong> este mês.<br>Faça upgrade para continuar.
        </div>
    </div>
    """.format(plano=plano_atual.nome), unsafe_allow_html=True)

    render_cards_planos(perfil)


def render_cards_planos(perfil: dict) -> None:
    """Renderiza os 3 cards de plano lado a lado."""
    _css_planos()

    plano_atual_id = perfil.get("plano", "free")
    cols = st.columns(3)

    for col, (id_plano, plano) in zip(cols, PLANOS.items()):
        with col:
            _card_plano(perfil["id"], id_plano, plano, plano_atual_id)


def _card_plano(
    user_id: str,
    id_plano: str,
    plano: Plano,
    plano_atual_id: str,
) -> None:
    destaque = id_plano == "profissional"
    atual = id_plano == plano_atual_id

    # Badge
    if destaque:
        st.markdown("⭐ **Mais popular**")
    elif atual:
        st.markdown("✔️ *Seu plano atual*")
    else:
        st.markdown("&nbsp;", unsafe_allow_html=True)

    # Nome
    st.markdown(f"### {plano.nome}")

    # Preço
    if plano.preco_brl == 0:
        st.markdown(
            '<span style="color:#2ecc71;font-size:1.6rem;font-weight:700;'
            'font-family:monospace">Grátis</span>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f'<span style="color:#00d4aa;font-size:1.5rem;font-weight:700;'
            f'font-family:monospace">R$ {plano.preco_brl:.2f}</span>'
            f'<span style="color:#888;font-size:0.85rem"> /mês</span>',
            unsafe_allow_html=True,
        )

    st.caption(plano.descricao)
    st.divider()

    # Features
    features = [
        (True, f"{'Ilimitadas' if plano.consultas_mes == -1 else plano.consultas_mes} consultas/mês"),
        (plano.historico, "Histórico de projetos"),
        (plano.exportar_pdf, "Exportação em PDF"),
        (plano.multiusuario, "Multi-usuário"),
        (plano.logo_personalizada, "Logo da empresa no PDF"),
    ]
    for ok, txt in features:
        icone = "✅" if ok else "❌"
        cor = "#ddd" if ok else "#555"
        st.markdown(
            f'<div style="color:{cor};font-size:0.85rem;padding:2px 0">{icone} {txt}</div>',
            unsafe_allow_html=True,
        )

    st.write("")

    # ── Botão de ação ──
    if atual:
        st.button("Plano atual", disabled=True, key=f"btn_{id_plano}", use_container_width=True)
    elif id_plano == "free":
        st.info("Aguarde o próximo mês para novas consultas gratuitas.")
    else:
        if st.button(
            f"Assinar por R$ {plano.preco_brl:.2f}/mês",
            key=f"btn_{id_plano}",
            use_container_width=True,
            type="primary",
        ):
            with st.spinner("Gerando link de pagamento..."):
                usuario = st.session_state.get("usuario", {})
                email = usuario.get("email", "")
                _iniciar_checkout(user_id, id_plano, email)


def _iniciar_checkout(user_id: str, id_plano: str, payer_email: str = "") -> None:
    """Gera o link do Mercado Pago e redireciona."""
    try:
        url = criar_link_assinatura(user_id, id_plano, payer_email)
        # Abre em nova aba via JS
        st.markdown(
            f'<meta http-equiv="refresh" content="0; url={url}">',
            unsafe_allow_html=True,
        )
        st.success(
            f"Redirecionando para o pagamento... "
            f"[Clique aqui se não redirecionar automaticamente]({url})"
        )
    except Exception as e:
        st.error(f"Erro ao gerar link de pagamento: {e}")


# ─────────────────────────────────────────────────────────
# CSS DOS CARDS
# ─────────────────────────────────────────────────────────

def _css_planos() -> None:
    st.markdown("""
    <style>
        .card-plano {
            background: #1a1d26;
            border: 1px solid #2a2d3a;
            border-radius: 10px;
            padding: 1.25rem;
            min-height: 360px;
            position: relative;
        }
        .badge-destaque {
            background: #00d4aa;
            color: #0f1117;
            font-size: 0.7rem;
            font-weight: 700;
            padding: 0.2rem 0.6rem;
            border-radius: 20px;
            display: inline-block;
            margin-bottom: 0.75rem;
            font-family: 'IBM Plex Mono', monospace;
        }
        .badge-atual {
            background: #2a3a2a;
            color: #2ecc71;
            font-size: 0.7rem;
            padding: 0.2rem 0.6rem;
            border-radius: 20px;
            display: inline-block;
            margin-bottom: 0.75rem;
        }
        .plano-nome {
            font-family: 'IBM Plex Mono', monospace;
            font-size: 1.1rem;
            font-weight: 700;
            color: #fff;
            margin-bottom: 0.5rem;
        }
        .preco-gratis {
            font-family: 'IBM Plex Mono', monospace;
            font-size: 1.6rem;
            font-weight: 700;
            color: #2ecc71;
        }
        .preco-valor {
            font-family: 'IBM Plex Mono', monospace;
            font-size: 1.6rem;
            font-weight: 700;
            color: #00d4aa;
        }
        .preco-periodo {
            color: #888;
            font-size: 0.85rem;
        }
        .plano-desc {
            color: #888;
            font-size: 0.8rem;
            margin-top: 0.5rem;
            line-height: 1.4;
        }
        .feature {
            font-size: 0.82rem;
            padding: 0.2rem 0;
            color: #ccc;
        }
        .feature.off {
            color: #555;
        }
    </style>
    """, unsafe_allow_html=True)
