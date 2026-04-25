# 🔌 Duto — Passa Fácil
### Dimensionamento Inteligente NBR 5410

---

## Estrutura do projeto

```
duto_passa_facil/
├── app.py              # Streamlit — entry point principal
├── auth.py             # Login, cadastro e sessão (Supabase Auth)
├── database.py         # Operações no banco (perfil, cota, histórico)
├── planos.py           # Cards de planos e gate de cota
├── pagamento.py        # Integração Mercado Pago
├── config.py           # Env vars e definição dos planos
├── webhook_server.py   # FastAPI — recebe callbacks do MP
├── schema.sql          # SQL para criar as tabelas no Supabase
├── requirements.txt
└── .env.example        # Template das variáveis de ambiente
```

---

## Setup completo (passo a passo)

### ETAPA 1 — Supabase (banco + auth)

1. Acesse https://supabase.com e crie uma conta gratuita
2. Clique em **New Project** → dê um nome (ex: `duto-passa-facil`)
3. Anote a **senha do banco** que você criará
4. Vá em **Settings → API** e copie:
   - `URL` → `SUPABASE_URL`
   - `anon public` → `SUPABASE_ANON_KEY`
   - `service_role` → `SUPABASE_SERVICE_KEY` ⚠️ mantenha em segredo
5. Vá em **SQL Editor → New Query**, cole o conteúdo de `schema.sql` e execute
6. Vá em **Authentication → Providers** e ative **Email** (já vem ativado)
7. Opcional: ative **Google OAuth** para login social

### ETAPA 2 — Mercado Pago

1. Acesse https://www.mercadopago.com.br/developers/
2. Crie uma aplicação em **Minhas aplicações → Criar aplicação**
3. Vá em **Credenciais de produção** e copie o `Access Token` → `MP_ACCESS_TOKEN`
4. Com o token configurado, rode UMA VEZ para criar os planos:
   ```bash
   python -c "from pagamento import criar_planos_mp; criar_planos_mp()"
   ```
   Copie os IDs retornados para `MP_PLAN_ID_PROF` e `MP_PLAN_ID_EMP` no `.env`

### ETAPA 3 — Configurar o .env

```bash
cp .env.example .env
# Abra .env e preencha todos os valores copiados nas etapas anteriores
```

### ETAPA 4 — Rodar localmente

```bash
pip install -r requirements.txt

# Terminal 1: Streamlit (interface principal)
streamlit run app.py

# Terminal 2: Webhook (recebe confirmações do MP)
uvicorn webhook_server:app --reload --port 8000
```

### ETAPA 5 — Configurar webhook no Mercado Pago

1. No painel do MP, vá em **Webhooks → Adicionar**
2. URL: `https://SEU-DOMINIO/webhook/mercadopago`
   - Em desenvolvimento, use ngrok: `ngrok http 8000`
3. Selecione os eventos: `payment` e `subscription_preapproval`
4. Copie o **secret gerado** para `MP_WEBHOOK_SECRET` no `.env`

---

## Deploy em produção (gratuito)

### Streamlit (interface)
1. Suba o projeto para o GitHub (sem o `.env`!)
2. Acesse https://streamlit.io/cloud → **New app**
3. Conecte o repositório e defina `app.py` como entry point
4. Em **Advanced settings → Secrets**, adicione as variáveis do `.env`
5. Deploy → URL pública gerada automaticamente

### Webhook FastAPI (Railway.app — gratuito)
1. Acesse https://railway.app e conecte o GitHub
2. **New Project → Deploy from GitHub repo**
3. Defina o start command: `uvicorn webhook_server:app --host 0.0.0.0 --port $PORT`
4. Adicione as variáveis de ambiente no painel do Railway
5. Copie a URL gerada e configure no painel do Mercado Pago

---

## Planos e preços

| Plano | Preço | Consultas | Histórico | PDF |
|---|---|---|---|---|
| Free | Grátis | 1/mês | ❌ | ❌ |
| Profissional | R$ 29,90/mês | 50/mês | ✅ | ✅ |
| Empresarial | R$ 89,90/mês | Ilimitado | ✅ | ✅ |

Para alterar preços e limites, edite o dicionário `PLANOS` em `config.py`.

---

## Normas de referência

- **NBR 5410:2004** — Instalações elétricas de baixa tensão
- **NBR 5597** — Eletrodutos de aço-carbono
- **NBR 6150** — Eletrodutos rígidos de PVC
- **NBR 14565** — Cabeamento estruturado para edifícios
