"""
pwa.py — Injeta o manifesto PWA e service worker no Streamlit
Chame inject_pwa() no início do app.py, antes de qualquer st.*
"""

import streamlit as st


def inject_pwa():
    """
    Injeta as tags PWA no <head> do Streamlit via st.markdown.
    Inclui: manifest.json, meta tags, service worker registration.
    """
    APP_URL = "https://duto-passa-facil.streamlit.app"

    st.markdown(f"""
    <link rel="manifest" href="{APP_URL}/assets/manifest.json">
    <meta name="theme-color" content="#f57c20">
    <meta name="mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <meta name="apple-mobile-web-app-title" content="Duto">
    <link rel="apple-touch-icon" href="{APP_URL}/assets/icon-192.png">
    <meta name="description" content="Dimensionamento Inteligente de Eletrodutos — NBR 5410">

    <script>
    if ('serviceWorker' in navigator) {{
        window.addEventListener('load', function() {{
            navigator.serviceWorker.register('/assets/sw.js')
                .then(reg => console.log('SW registrado:', reg.scope))
                .catch(err => console.log('SW erro:', err));
        }});
    }}
    </script>
    """, unsafe_allow_html=True)
