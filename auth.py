"""
auth.py — Telas de login, cadastro e sessão via Supabase Auth

Gerencia st.session_state["usuario"] com os dados do usuário logado.
"""

from __future__ import annotations
import streamlit as st
from supabase import create_client, Client
from config import SUPABASE_URL, SUPABASE_KEY
from database import garantir_perfil


def _sb() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)


# ─────────────────────────────────────────────────────────
# SESSÃO
# ─────────────────────────────────────────────────────────

def usuario_logado() -> dict | None:
    """Retorna o dict do usuário na sessão ou None."""
    return st.session_state.get("usuario")


def carregar_sessao_do_query() -> None:
    """
    Tenta recuperar sessão via token na URL (retorno do OAuth / email link).
    Streamlit não lida com fragments (#) então usamos query params.
    """
    params = st.query_params
    access_token = params.get("access_token")
    refresh_token = params.get("refresh_token")

    if access_token and not usuario_logado():
        try:
            sb = _sb()
            sessao = sb.auth.set_session(access_token, refresh_token or "")
            _salvar_usuario_na_sessao(sessao.user)
            # Limpa params da URL
            st.query_params.clear()
        except Exception:
            pass


def _salvar_usuario_na_sessao(user) -> dict:
    """Salva dados do usuário no session_state e garante perfil no banco."""
    perfil = garantir_perfil(user.id, user.email)
    st.session_state["usuario"] = {
        "id": user.id,
        "email": user.email,
        **perfil,
    }
    return st.session_state["usuario"]


def logout() -> None:
    """Encerra a sessão."""
    try:
        _sb().auth.sign_out()
    except Exception:
        pass
    st.session_state.pop("usuario", None)
    st.rerun()


# ─────────────────────────────────────────────────────────
# TELA DE AUTENTICAÇÃO
# ─────────────────────────────────────────────────────────

def render_tela_auth() -> None:
    """
    Renderiza as abas de Login e Cadastro.
    Quando bem-sucedido, salva o usuário na sessão e chama st.rerun().
    """
    _css_auth()

    st.markdown("""
        <div class="auth-header">
            <div class="auth-logo">🔌</div>
            <div class="auth-titulo">Duto — Passa Fácil</div>
            <div class="auth-sub">Dimensionamento Inteligente NBR 5410</div>
        </div>
    """, unsafe_allow_html=True)

    aba_login, aba_cadastro = st.tabs(["Entrar", "Criar conta"])

    with aba_login:
        _form_login()

    with aba_cadastro:
        _form_cadastro()


def _form_login() -> None:
    st.markdown('<div class="auth-card">', unsafe_allow_html=True)

    email = st.text_input("E-mail", placeholder="seu@email.com", key="login_email")
    senha = st.text_input("Senha", type="password", placeholder="••••••••", key="login_senha")

    col1, col2 = st.columns([2, 1])
    with col1:
        entrar = st.button("Entrar", use_container_width=True, key="btn_login")
    with col2:
        if st.button("Esqueci a senha", use_container_width=True, key="btn_esqueci"):
            if email:
                _enviar_reset_senha(email)
            else:
                st.warning("Digite seu e-mail primeiro.")

    if entrar:
        if not email or not senha:
            st.error("Preencha e-mail e senha.")
        else:
            _fazer_login(email, senha)

    st.markdown('</div>', unsafe_allow_html=True)


def _form_cadastro() -> None:
    st.markdown('<div class="auth-card">', unsafe_allow_html=True)

    nome = st.text_input("Nome completo", placeholder="Engenheiro Silva", key="cad_nome")
    email = st.text_input("E-mail", placeholder="seu@email.com", key="cad_email")
    senha = st.text_input("Senha", type="password", placeholder="Mínimo 8 caracteres", key="cad_senha")
    senha2 = st.text_input("Confirmar senha", type="password", placeholder="••••••••", key="cad_senha2")

    if st.button("Criar conta gratuita", use_container_width=True, key="btn_cadastro"):
        if not all([nome, email, senha, senha2]):
            st.error("Preencha todos os campos.")
        elif len(senha) < 8:
            st.error("A senha deve ter pelo menos 8 caracteres.")
        elif senha != senha2:
            st.error("As senhas não coincidem.")
        else:
            _fazer_cadastro(nome, email, senha)

    st.caption("Ao criar conta você concorda com os Termos de Uso. Plano gratuito: 1 consulta/mês.")
    st.markdown('</div>', unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────
# LÓGICA DE AUTH
# ─────────────────────────────────────────────────────────

def _fazer_login(email: str, senha: str) -> None:
    try:
        sb = _sb()
        resp = sb.auth.sign_in_with_password({"email": email, "password": senha})
        _salvar_usuario_na_sessao(resp.user)
        st.rerun()
    except Exception as e:
        msg = str(e).lower()
        if "invalid" in msg or "credentials" in msg:
            st.error("E-mail ou senha incorretos.")
        elif "email not confirmed" in msg:
            st.warning("Confirme seu e-mail antes de entrar. Verifique sua caixa de entrada.")
        else:
            st.error(f"Erro ao entrar: {e}")


def _fazer_cadastro(nome: str, email: str, senha: str) -> None:
    try:
        sb = _sb()
        resp = sb.auth.sign_up({
            "email": email,
            "password": senha,
            "options": {"data": {"nome": nome}},
        })

        if resp.user:
            # Supabase pode exigir confirmação de e-mail
            if resp.session:
                _salvar_usuario_na_sessao(resp.user)
                st.rerun()
            else:
                st.success(
                    "✅ Conta criada! Verifique seu e-mail para confirmar o cadastro "
                    "e depois faça login."
                )
    except Exception as e:
        msg = str(e).lower()
        if "already registered" in msg or "already exists" in msg:
            st.error("Este e-mail já está cadastrado. Tente entrar.")
        else:
            st.error(f"Erro ao criar conta: {e}")


def _enviar_reset_senha(email: str) -> None:
    try:
        _sb().auth.reset_password_email(email)
        st.success(f"Link de redefinição enviado para {email}.")
    except Exception as e:
        st.error(f"Erro: {e}")


# ─────────────────────────────────────────────────────────
# CSS DA TELA DE AUTH
# ─────────────────────────────────────────────────────────

def _css_auth() -> None:
    st.markdown("""
    <style>
        .auth-header {
            text-align: center;
            padding: 2.5rem 1rem 1.5rem;
        }
        .auth-logo {
            font-size: 3rem;
            margin-bottom: 0.5rem;
        }
        .auth-titulo {
            font-family: 'IBM Plex Mono', monospace;
            font-size: 1.6rem;
            font-weight: 700;
            color: #00d4aa;
            letter-spacing: -0.02em;
        }
        .auth-sub {
            font-size: 0.85rem;
            color: #888;
            margin-top: 0.25rem;
            font-family: 'IBM Plex Mono', monospace;
        }
        .auth-card {
            background: #1a1d26;
            border: 1px solid #2a2d3a;
            border-radius: 10px;
            padding: 1.5rem;
            max-width: 420px;
            margin: 1rem auto;
        }
    </style>
    """, unsafe_allow_html=True)
