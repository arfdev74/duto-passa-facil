"""
scripts/verificar_ambiente.py
Verifica se todas as dependências e credenciais estão configuradas corretamente.
Execute antes de rodar o app pela primeira vez:
    python scripts/verificar_ambiente.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

OK = "✅"
ERRO = "❌"
AVISO = "⚠️ "

erros = []

print("\n" + "="*55)
print("  DUTO — PASSA FÁCIL · Verificação de Ambiente")
print("="*55 + "\n")


# ─── 1. Variáveis de ambiente ───────────────────────────

print("📋 Variáveis de ambiente")
vars_obrigatorias = {
    "SUPABASE_URL": "URL do projeto Supabase",
    "SUPABASE_ANON_KEY": "Chave pública do Supabase",
    "MP_ACCESS_TOKEN": "Token de acesso do Mercado Pago",
}
vars_opcionais = {
    "SUPABASE_SERVICE_KEY": "Chave service_role (só no webhook)",
    "MP_WEBHOOK_SECRET": "Secret HMAC do webhook MP",
    "MP_PLAN_ID_PROF": "ID do plano Profissional no MP",
    "MP_PLAN_ID_EMP": "ID do plano Empresarial no MP",
    "APP_BASE_URL": "URL pública do app",
}

from dotenv import load_dotenv
load_dotenv()

for var, descricao in vars_obrigatorias.items():
    valor = os.getenv(var, "")
    if valor:
        print(f"  {OK} {var}")
    else:
        print(f"  {ERRO} {var} — {descricao}")
        erros.append(var)

for var, descricao in vars_opcionais.items():
    valor = os.getenv(var, "")
    status = OK if valor else AVISO
    print(f"  {status} {var}{' (não configurado)' if not valor else ''}")

print()


# ─── 2. Dependências Python ─────────────────────────────

print("📦 Dependências Python")
pacotes = {
    "streamlit": "Interface",
    "pandas": "Dados",
    "supabase": "Banco de dados",
    "mercadopago": "Pagamento",
    "fastapi": "Webhook server",
    "uvicorn": "Servidor ASGI",
    "dotenv": "Variáveis de ambiente",
}

for pacote, descricao in pacotes.items():
    try:
        __import__(pacote if pacote != "dotenv" else "dotenv")
        print(f"  {OK} {pacote}")
    except ImportError:
        print(f"  {ERRO} {pacote} — {descricao} — rode: pip install {pacote}")
        erros.append(f"pip:{pacote}")

print()


# ─── 3. Conexão com Supabase ────────────────────────────

print("🗄️  Conexão com Supabase")
url = os.getenv("SUPABASE_URL", "")
key = os.getenv("SUPABASE_ANON_KEY", "")

if url and key and not url.startswith("https://PROJETO"):
    try:
        from supabase import create_client
        sb = create_client(url, key)
        # Tenta uma query simples
        sb.table("profiles").select("id").limit(1).execute()
        print(f"  {OK} Conexão estabelecida")
        print(f"  {OK} Tabela 'profiles' acessível")
    except Exception as e:
        msg = str(e)
        if "relation" in msg.lower() or "does not exist" in msg.lower():
            print(f"  {AVISO} Conectado, mas tabelas não criadas — rode o schema.sql no Supabase")
        elif "Invalid API key" in msg:
            print(f"  {ERRO} Chave do Supabase inválida — verifique SUPABASE_ANON_KEY")
            erros.append("supabase:key")
        else:
            print(f"  {ERRO} Erro: {msg[:80]}")
            erros.append("supabase:conn")
else:
    print(f"  {AVISO} Variáveis não configuradas — pulando verificação")

print()


# ─── 4. Conexão com Mercado Pago ────────────────────────

print("💳 Mercado Pago")
token = os.getenv("MP_ACCESS_TOKEN", "")

if token and not token.startswith("APP_USR-000"):
    try:
        import mercadopago
        sdk = mercadopago.SDK(token)

        # Verifica se é token de teste ou produção
        modo = "SANDBOX (TEST-)" if token.startswith("TEST-") else "PRODUÇÃO"
        print(f"  {OK} Token configurado — modo: {modo}")

        if token.startswith("TEST-"):
            print(f"  {OK} Ambiente de sandbox ativo — pagamentos não cobram de verdade")
        else:
            print(f"  {AVISO} Token de PRODUÇÃO — pagamentos são reais!")

    except Exception as e:
        print(f"  {ERRO} Erro ao inicializar SDK: {e}")
        erros.append("mp:sdk")
else:
    print(f"  {AVISO} Token não configurado — pulando verificação")

print()


# ─── 5. Resumo ───────────────────────────────────────────

print("="*55)
if not erros:
    print(f"  {OK} Ambiente pronto! Execute: streamlit run app.py")
else:
    print(f"  {ERRO} {len(erros)} problema(s) encontrado(s):")
    for e in erros:
        print(f"     • {e}")
    print("\n  Corrija os erros acima e rode este script novamente.")
print("="*55 + "\n")
