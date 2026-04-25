"""
╔══════════════════════════════════════════════════════════╗
║          DUTO — PASSA FÁCIL                              ║
║          Dimensionamento Inteligente NBR 5410            ║
║                                                          ║
║     NBR 5410 · NBR 5597 · NBR 6150 · NBR 14565          ║
╚══════════════════════════════════════════════════════════╝
"""

import streamlit as st
import math
import pandas as pd

from auth import usuario_logado, render_tela_auth, logout, carregar_sessao_do_query
from planos import gate_cota, render_cards_planos
from database import (
    incrementar_consulta,
    salvar_consulta,
    buscar_historico,
    buscar_perfil,
)
from config import PLANOS


# ─────────────────────────────────────────────────────────
# 1. DADOS DE REFERÊNCIA (NBR / fabricantes)
# ─────────────────────────────────────────────────────────

DIAMETROS_CABOS = {
    "Cabo 750V (flexível)": {
        1.5: 3.09, 2.5: 3.75, 4: 4.28, 6: 4.83,
        10: 6.05, 16: 7.13, 25: 8.80, 35: 9.96,
        50: 11.65, 70: 13.65, 95: 15.80, 120: 17.40,
        150: 19.50, 185: 21.64, 300: 27.12,
    },
    "Cabo 0,6/1kV (flexível)": {
        1.5: 5.17, 2.5: 5.62, 4: 6.56, 6: 7.14,
        10: 8.25, 16: 9.33, 25: 11.20, 35: 12.40,
        50: 14.60, 70: 16.30, 95: 18.60, 120: 20.14,
        150: 22.08, 185: 24.16, 240: 30.00, 300: 30.72,
    },
    "Cabo 0,6/1kV (rígido)": {
        1.5: 4.90, 2.5: 5.30, 4: 6.40, 6: 7.00,
        10: 7.90, 16: 9.50, 25: 10.80, 35: 12.80,
        50: 15.10, 70: 16.90, 95: 19.20, 120: 21.10,
        150: 23.60, 185: 25.80, 240: 29.40,
    },
    "Cabo Blindado 1mm² (controle)": {
        2: 9.60, 3: 9.90, 4: 10.50, 5: 11.10, 6: 11.70,
        7: 11.70, 8: 12.40, 9: 13.00, 10: 13.90, 12: 14.20,
        14: 14.70, 16: 15.30, 20: 16.60, 24: 18.10, 25: 18.10,
    },
    "Cabo Blindado 1,5mm² (controle)": {
        2: 10.00, 3: 10.40, 4: 11.00, 5: 11.70, 6: 12.40,
        7: 12.40, 8: 13.10, 9: 13.80, 10: 14.70, 12: 15.00,
        14: 15.70, 16: 16.30, 20: 17.70, 24: 19.40,
    },
    "Cabo Blindado 2,5mm² (controle)": {
        2: 12.70, 3: 13.30, 4: 15.20, 5: 15.30, 6: 16.40,
        7: 16.40, 8: 17.50, 9: 18.60, 10: 20.10, 12: 20.60,
    },
    "Cabo UTP Cat.6 (dados)": {6.0: 6.00},
    "Cabo Coaxial RG-58 (sinal)": {5.0: 5.00},
    "Cabo Coaxial RG-6 (CFTV)": {6.9: 6.90},
}

TIPO_SINAL = {
    "Cabo 750V (flexível)": "potência",
    "Cabo 0,6/1kV (flexível)": "potência",
    "Cabo 0,6/1kV (rígido)": "potência",
    "Cabo Blindado 1mm² (controle)": "sinal",
    "Cabo Blindado 1,5mm² (controle)": "sinal",
    "Cabo Blindado 2,5mm² (controle)": "sinal",
    "Cabo UTP Cat.6 (dados)": "dados",
    "Cabo Coaxial RG-58 (sinal)": "sinal",
    "Cabo Coaxial RG-6 (CFTV)": "sinal",
}

ELETRODUTOS_METALICOS = {
    '15mm (1/2")':   {"area_util": 199.03},
    '20mm (3/4")':   {"area_util": 346.31},
    '25mm (1")':     {"area_util": 554.59},
    '32mm (1.1/4")': {"area_util": 958.80},
    '40mm (1.1/2")': {"area_util": 1321.31},
    '50mm (2")':     {"area_util": 2170.60},
    '65mm (2.1/2")': {"area_util": 3089.85},
    '80mm (3")':     {"area_util": 4745.47},
    '90mm (3.1/2")': {"area_util": 6326.40},
    '100mm (4")':    {"area_util": 8102.29},
    '125mm (5")':    {"area_util": 12826.92},
    '150mm (6")':    {"area_util": 18245.54},
}

ELETRODUTOS_PVC = {
    '20mm (3/4")':   {"area_util": 125.66},
    '25mm (1")':     {"area_util": 196.34},
    '32mm (1.1/4")': {"area_util": 321.69},
    '40mm (1.1/2")': {"area_util": 502.64},
    '50mm (2")':     {"area_util": 785.38},
    '60mm (2.1/2")': {"area_util": 1130.94},
    '75mm (3")':     {"area_util": 1767.09},
    '85mm (3.1/2")': {"area_util": 2269.73},
    '102mm (4")':    {"area_util": 3268.42},
}

FATORES_AGRUPAMENTO = {
    1: 1.00, 2: 0.80, 3: 0.70, 4: 0.65,
    5: 0.60, 6: 0.57, 7: 0.54, 8: 0.52,
    9: 0.50, 10: 0.50, 11: 0.50, 12: 0.45,
}


# ─────────────────────────────────────────────────────────
# 2. MOTOR DE CÁLCULO
# ─────────────────────────────────────────────────────────

def taxa_ocupacao(total_cabos: int) -> float:
    if total_cabos == 1:
        return 0.53
    elif total_cabos == 2:
        return 0.31
    return 0.40


def calcular_area_cabo(d: float) -> float:
    return math.pi * (d / 2) ** 2


def area_total_cabos(cabos: list[dict]) -> float:
    return sum(calcular_area_cabo(c["diametro"]) * c["quantidade"] for c in cabos)


def recomendar_eletrodutos(area_minima: float, tipo: str) -> list[dict]:
    tabela = ELETRODUTOS_METALICOS if tipo == "Metálico (NBR 5597)" else ELETRODUTOS_PVC
    return [
        {"eletroduto": nome, "area_util": d["area_util"]}
        for nome, d in tabela.items()
        if d["area_util"] >= area_minima
    ]


def verificar_emi(cabos: list[dict]) -> tuple[bool, list[str]]:
    tipos = {TIPO_SINAL.get(c["tipo_cabo"], "potência") for c in cabos}
    conflito = "potência" in tipos and ("sinal" in tipos or "dados" in tipos)
    return conflito, list(tipos)


def verificar_trecho(num_curvas: int, comprimento: float) -> tuple[bool, list[str]]:
    msgs = []
    if num_curvas > 3:
        msgs.append(f"🔄 {num_curvas} curvas de 90° (limite: 3)")
    if comprimento > 15:
        msgs.append(f"📏 {comprimento:.1f}m de comprimento (limite: 15m sem caixa de passagem)")
    return bool(msgs), msgs


def fator_agrupamento_valor(n: int) -> float:
    return FATORES_AGRUPAMENTO.get(min(n, 12), 0.45)


# ─────────────────────────────────────────────────────────
# 3. CONFIGURAÇÃO DA PÁGINA
# ─────────────────────────────────────────────────────────

def configurar_pagina() -> None:
    st.set_page_config(
        page_title="Duto - Passa Fácil",
        page_icon="🔌",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@300;400;600;700&display=swap');
        html, body, [class*="css"] { font-family: 'IBM Plex Sans', sans-serif; }
        .stApp { background: #0f1117; color: #e0e0e0; }
        .titulo-principal {
            font-family: 'IBM Plex Mono', monospace;
            font-size: 1.8rem; font-weight: 700;
            color: #00d4aa; letter-spacing: -0.02em;
            border-left: 4px solid #00d4aa;
            padding-left: 1rem; margin-bottom: 0.25rem;
        }
        .subtitulo {
            font-size: 0.82rem; color: #888;
            padding-left: 1.25rem; margin-bottom: 2rem;
            font-family: 'IBM Plex Mono', monospace;
        }
        .card {
            background: #1a1d26; border: 1px solid #2a2d3a;
            border-radius: 8px; padding: 1.25rem 1.5rem; margin-bottom: 1rem;
        }
        .card-titulo {
            font-size: 0.72rem; font-weight: 700; letter-spacing: 0.12em;
            text-transform: uppercase; color: #00d4aa;
            margin-bottom: 0.75rem; font-family: 'IBM Plex Mono', monospace;
        }
        .metrica-valor {
            font-family: 'IBM Plex Mono', monospace;
            font-size: 2rem; font-weight: 700; color: #fff;
        }
        .metrica-label { font-size: 0.75rem; color: #888; margin-top: 0.25rem; }
        .alerta-erro {
            background: #2d1515; border: 1px solid #c0392b;
            border-radius: 6px; padding: 1rem 1.25rem; color: #e74c3c; margin: 0.5rem 0;
        }
        .alerta-aviso {
            background: #2d2515; border: 1px solid #e67e22;
            border-radius: 6px; padding: 1rem 1.25rem; color: #f39c12; margin: 0.5rem 0;
        }
        .alerta-ok {
            background: #152d1f; border: 1px solid #27ae60;
            border-radius: 6px; padding: 1rem 1.25rem; color: #2ecc71; margin: 0.5rem 0;
        }
        .eletroduto-top {
            background: #0d2436; border: 2px solid #00d4aa;
            border-radius: 8px; padding: 1rem 1.25rem; margin: 0.5rem 0;
        }
        .eletroduto-alt {
            background: #1a1d26; border: 1px solid #2a2d3a;
            border-radius: 6px; padding: 0.6rem 1rem; margin: 0.25rem 0; color: #aaa;
        }
        .stButton > button {
            background: #00d4aa; color: #0f1117; border: none;
            font-weight: 700; font-family: 'IBM Plex Mono', monospace;
            border-radius: 6px;
        }
        .stButton > button:hover { background: #00b894; }
        .user-bar {
            background: #1a1d26; border-bottom: 1px solid #2a2d3a;
            padding: 0.4rem 1rem; font-size: 0.78rem; color: #888;
            display: flex; justify-content: space-between; align-items: center;
            margin-bottom: 1rem;
        }
    </style>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────
# 4. COMPONENTES DA CALCULADORA
# ─────────────────────────────────────────────────────────

def render_cabos_input() -> list[dict]:
    st.sidebar.markdown("### ⚡ Cabos no Eletroduto")
    if "cabos" not in st.session_state:
        st.session_state.cabos = [{"id": 0}]

    if st.sidebar.button("➕ Adicionar cabo"):
        novo_id = max(c["id"] for c in st.session_state.cabos) + 1
        st.session_state.cabos.append({"id": novo_id})

    cabos_resultado = []
    for i, entry in enumerate(st.session_state.cabos):
        cid = entry["id"]
        with st.sidebar.expander(f"Cabo #{i+1}", expanded=True):
            tipo = st.selectbox(
                "Tipo", options=list(DIAMETROS_CABOS.keys()), key=f"tipo_{cid}"
            )
            secoes = sorted(DIAMETROS_CABOS[tipo].keys())
            secao = st.selectbox(
                "Seção (mm²)", options=secoes, key=f"sec_{cid}",
                format_func=lambda x: f"{x} mm²" if x == int(x) else f"{x} mm",
            )
            d_ext = DIAMETROS_CABOS[tipo][secao]
            st.caption(f"Ø externo: **{d_ext} mm**")
            qtd = st.number_input("Qtd", 1, 200, 1, key=f"qtd_{cid}")
            cabos_resultado.append({
                "id": cid, "tipo_cabo": tipo, "secao": secao,
                "diametro": d_ext, "quantidade": qtd,
                "sinal": TIPO_SINAL.get(tipo, "potência"),
            })
            if len(st.session_state.cabos) > 1:
                if st.button("🗑 Remover", key=f"rm_{cid}"):
                    st.session_state.cabos = [
                        c for c in st.session_state.cabos if c["id"] != cid
                    ]
                    st.rerun()
    return cabos_resultado


def render_parametros_trecho():
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🏗️ Parâmetros do Trecho")
    tipo = st.sidebar.radio(
        "Tipo de eletroduto",
        ["Metálico (NBR 5597)", "PVC (NBR 6150)"], horizontal=True,
    )
    curvas = st.sidebar.slider("Curvas de 90°", 0, 10, 0)
    comp = st.sidebar.number_input("Comprimento do trecho (m)", 0.0, 500.0, 10.0, 0.5)
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🌡️ Agrupamento")
    circ = st.sidebar.number_input("Circuitos no eletroduto", 1, 12, 1)
    return tipo, curvas, comp, circ


def render_resultado(area_cabos, total_fios, area_min, taxa):
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="card-titulo">📐 Dimensionamento por Área</div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f'<div class="metrica-valor">{area_cabos:.1f}</div>', unsafe_allow_html=True)
        st.markdown('<div class="metrica-label">Área total dos cabos (mm²)</div>', unsafe_allow_html=True)
    with c2:
        label = "1 cabo" if total_fios == 1 else "2 cabos" if total_fios == 2 else "3+ cabos"
        st.markdown(f'<div class="metrica-valor">{taxa*100:.0f}%</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="metrica-label">Taxa de ocupação ({label})</div>', unsafe_allow_html=True)
    with c3:
        st.markdown(f'<div class="metrica-valor">{area_min:.1f}</div>', unsafe_allow_html=True)
        st.markdown('<div class="metrica-label">Área útil mínima exigida (mm²)</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)


def render_recomendacoes(adequados):
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="card-titulo">✅ Eletrodutos Indicados</div>', unsafe_allow_html=True)
    if not adequados:
        st.error("Nenhum eletroduto da tabela comporta essa instalação. Considere eletrocalha.")
    else:
        for i, item in enumerate(adequados):
            if i == 0:
                st.markdown(
                    f'<div class="eletroduto-top"><strong style="color:#00d4aa;'
                    f'font-family:\'IBM Plex Mono\',monospace">⭐ {item["eletroduto"]}'
                    f'</strong><br><span style="color:#aaa;font-size:0.85rem">'
                    f'Área útil: {item["area_util"]:.1f} mm²</span></div>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f'<div class="eletroduto-alt">{item["eletroduto"]} '
                    f'— {item["area_util"]:.1f} mm²</div>',
                    unsafe_allow_html=True,
                )
    st.markdown('</div>', unsafe_allow_html=True)


def render_alerta_emi(cabos):
    conflito, tipos = verificar_emi(cabos)
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="card-titulo">📡 Segregação de Sinais — EMI</div>', unsafe_allow_html=True)
    if conflito:
        st.markdown(
            '<div class="alerta-erro"><strong>⛔ VIOLAÇÃO — NBR 5410 / NBR 14565</strong><br>'
            'Mistura de cabos de <strong>POTÊNCIA</strong> com <strong>DADOS/SINAL</strong>.<br>'
            '🔧 Use eletrodutos separados ou eletrocalha com divisória metálica.</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f'<div class="alerta-ok">✅ Sem conflito de sinais '
            f'<span style="opacity:0.6;font-size:0.8rem">({", ".join(tipos)})</span></div>',
            unsafe_allow_html=True,
        )
    st.markdown('</div>', unsafe_allow_html=True)


def render_alerta_trecho(curvas, comp):
    alerta, msgs = verificar_trecho(curvas, comp)
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="card-titulo">🔧 Curvas e Comprimento</div>', unsafe_allow_html=True)
    if alerta:
        corpo = "<br>".join(msgs)
        st.markdown(
            f'<div class="alerta-aviso"><strong>⚠️ Risco de dano à isolação</strong><br>'
            f'{corpo}<br>🔧 Aumente o diâmetro ou insira caixa de passagem.</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f'<div class="alerta-ok">✅ Trecho OK '
            f'<span style="opacity:0.6;font-size:0.8rem">({curvas} curva(s) · {comp:.1f}m)</span></div>',
            unsafe_allow_html=True,
        )
    st.markdown('</div>', unsafe_allow_html=True)


def render_fator_agrupamento(num_circ):
    fator = fator_agrupamento_valor(num_circ)
    cor = "#2ecc71" if fator >= 0.80 else "#f39c12" if fator >= 0.60 else "#e74c3c"
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="card-titulo">🌡️ Fator de Agrupamento — Tabela 42 NBR 5410</div>', unsafe_allow_html=True)
    c1, c2 = st.columns([1, 2])
    with c1:
        st.markdown(
            f'<div style="font-family:\'IBM Plex Mono\',monospace;font-size:2rem;'
            f'font-weight:700;color:{cor}">{fator:.2f}</div>',
            unsafe_allow_html=True,
        )
        st.caption(f"para {num_circ} circuito(s)")
    with c2:
        st.markdown(
            f"Corrente corrigida = nominal × **{fator:.2f}**<br>"
            f'<span style="color:#aaa;font-size:0.85rem">Exemplo: cabo de 40A → '
            f"capacidade real no agrupamento: **{40*fator:.1f}A**</span>",
            unsafe_allow_html=True,
        )
        if fator < 0.60:
            st.markdown(
                '<div class="alerta-erro" style="font-size:0.82rem;margin-top:0.5rem">'
                '⚠️ Fator crítico. Redistribua circuitos ou aumente a seção.</div>',
                unsafe_allow_html=True,
            )
    with st.expander("Tabela completa de fatores"):
        df = pd.DataFrame({
            "Circuitos": list(FATORES_AGRUPAMENTO.keys()),
            "Fator": list(FATORES_AGRUPAMENTO.values()),
            "Redução": [f"{(1-v)*100:.0f}%" for v in FATORES_AGRUPAMENTO.values()],
        }).set_index("Circuitos")
        st.dataframe(df, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)


def render_tabela_cabos(cabos):
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="card-titulo">📋 Resumo dos Cabos</div>', unsafe_allow_html=True)
    linhas = []
    for c in cabos:
        a = calcular_area_cabo(c["diametro"])
        linhas.append({
            "Tipo": c["tipo_cabo"],
            "Seção": f"{c['secao']} mm²",
            "Ø ext (mm)": c["diametro"],
            "Qtd": c["quantidade"],
            "Área/cabo (mm²)": f"{a:.2f}",
            "Área total (mm²)": f"{a * c['quantidade']:.2f}",
            "Sinal": c["sinal"],
        })
    st.dataframe(pd.DataFrame(linhas), use_container_width=True, hide_index=True)
    st.markdown('</div>', unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────
# 5. TELA DE HISTÓRICO (planos pagos)
# ─────────────────────────────────────────────────────────

def render_historico(user_id: str) -> None:
    import json
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="card-titulo">📁 Histórico de Projetos</div>', unsafe_allow_html=True)
    registros = buscar_historico(user_id)
    if not registros:
        st.caption("Nenhum dimensionamento salvo ainda.")
    else:
        for r in registros:
            entrada = json.loads(r["dados_entrada"])
            resultado = json.loads(r["resultado"])
            data = r["created_at"][:16].replace("T", " ")
            with st.expander(f"📄 {data} — {resultado.get('eletroduto_recomendado', 'N/A')}"):
                col1, col2 = st.columns(2)
                with col1:
                    st.write("**Entrada:**")
                    st.json(entrada)
                with col2:
                    st.write("**Resultado:**")
                    st.json(resultado)
    st.markdown('</div>', unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────
# 6. MAIN
# ─────────────────────────────────────────────────────────

def main():
    configurar_pagina()

    # Tenta recuperar sessão de OAuth/magic link na URL
    carregar_sessao_do_query()

    usuario = usuario_logado()

    # ── Não logado → tela de auth ──
    if not usuario:
        render_tela_auth()
        return

    # ── Logado: atualiza perfil do banco (plano pode ter mudado via webhook) ──
    perfil_atualizado = buscar_perfil(usuario["id"]) or usuario
    st.session_state["usuario"].update(perfil_atualizado)
    usuario = st.session_state["usuario"]

    # ── Sidebar: info do usuário e navegação ──
    plano_obj = PLANOS[usuario.get("plano", "free")]

    with st.sidebar:
        st.markdown(
            f'<div style="background:#1a1d26;border:1px solid #2a2d3a;border-radius:8px;'
            f'padding:0.8rem;margin-bottom:1rem;">'
            f'<div style="font-size:0.7rem;color:#888;font-family:\'IBM Plex Mono\',monospace">'
            f'CONTA</div>'
            f'<div style="color:#fff;font-size:0.9rem;margin-top:0.2rem">{usuario["email"]}</div>'
            f'<div style="color:#00d4aa;font-size:0.75rem;font-family:\'IBM Plex Mono\',monospace;'
            f'margin-top:0.2rem">Plano {plano_obj.nome}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        pagina = st.radio(
            "Navegação",
            ["🔌 Dimensionar", "📁 Histórico", "📦 Planos"],
            label_visibility="collapsed",
        )

        st.markdown("---")
        if st.button("Sair", use_container_width=True):
            logout()

    # ── Cabeçalho ──
    st.markdown('<div class="titulo-principal">🔌 Duto — Passa Fácil</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="subtitulo">Dimensionamento Inteligente NBR 5410 · NBR 5597 · NBR 6150</div>',
        unsafe_allow_html=True,
    )

    # ──────────── PÁGINA: DIMENSIONAR ────────────
    if "Dimensionar" in pagina:

        # Gate de cota — bloqueia se esgotada
        if not gate_cota(usuario):
            return

        cabos = render_cabos_input()
        tipo_eltr, num_curvas, comprimento, num_circ = render_parametros_trecho()

        total_fios = sum(c["quantidade"] for c in cabos)
        area_cab = area_total_cabos(cabos)
        taxa = taxa_ocupacao(total_fios)
        area_min = area_cab / taxa
        adequados = recomendar_eletrodutos(area_min, tipo_eltr)

        # Botão de cálculo
        st.sidebar.markdown("---")
        calcular = st.sidebar.button("⚡ CALCULAR", use_container_width=True)

        col_esq, col_dir = st.columns([3, 2])

        with col_esq:
            render_tabela_cabos(cabos)
            render_resultado(area_cab, total_fios, area_min, taxa)
            render_recomendacoes(adequados)

        with col_dir:
            render_alerta_emi(cabos)
            render_alerta_trecho(num_curvas, comprimento)
            render_fator_agrupamento(num_circ)

        # Salva no banco e incrementa cota ao clicar em calcular
        if calcular:
            eletroduto_rec = adequados[0]["eletroduto"] if adequados else "Nenhum"
            conflito_emi, _ = verificar_emi(cabos)
            alerta_trecho, msgs_trecho = verificar_trecho(num_curvas, comprimento)

            entrada_json = {
                "cabos": [
                    {"tipo": c["tipo_cabo"], "secao": c["secao"], "qtd": c["quantidade"]}
                    for c in cabos
                ],
                "tipo_eletroduto": tipo_eltr,
                "num_curvas": num_curvas,
                "comprimento_m": comprimento,
                "num_circuitos": num_circ,
            }
            resultado_json = {
                "area_cabos_mm2": round(area_cab, 2),
                "taxa_ocupacao_pct": round(taxa * 100, 1),
                "area_minima_mm2": round(area_min, 2),
                "eletroduto_recomendado": eletroduto_rec,
                "conflito_emi": conflito_emi,
                "alerta_trecho": alerta_trecho,
                "fator_agrupamento": fator_agrupamento_valor(num_circ),
            }

            incrementar_consulta(usuario["id"])

            # Salva histórico apenas para planos pagos
            if plano_obj.historico:
                salvar_consulta(usuario["id"], entrada_json, resultado_json)

            st.sidebar.success("✅ Cálculo registrado!")

    # ──────────── PÁGINA: HISTÓRICO ────────────
    elif "Histórico" in pagina:
        if not plano_obj.historico:
            st.info(
                "📁 O histórico de projetos está disponível nos planos **Profissional** e **Empresarial**."
            )
            render_cards_planos(usuario)
        else:
            render_historico(usuario["id"])

    # ──────────── PÁGINA: PLANOS ────────────
    elif "Planos" in pagina:
        st.markdown("## 📦 Planos e Preços")
        render_cards_planos(usuario)

    # Rodapé
    st.markdown("---")
    st.markdown(
        '<span style="color:#333;font-size:0.72rem;font-family:\'IBM Plex Mono\',monospace">'
        "Duto — Passa Fácil · Dimensionamento Inteligente NBR 5410 · "
        "NBR 5597 · NBR 6150 · NBR 14565</span>",
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
