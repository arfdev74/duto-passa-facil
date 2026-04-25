-- ╔══════════════════════════════════════════════════════════╗
-- ║  DUTO — PASSA FÁCIL · Schema do Banco de Dados           ║
-- ║  Execute este arquivo UMA VEZ no Supabase SQL Editor     ║
-- ║  Dashboard → SQL Editor → New Query → Cole e Execute     ║
-- ╚══════════════════════════════════════════════════════════╝

-- ─────────────────────────────────────────────────────────
-- TABELA: profiles
-- Criada automaticamente após o primeiro login de cada usuário.
-- Espelha auth.users e adiciona dados de plano e cota.
-- ─────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.profiles (
    id                  UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email               TEXT NOT NULL,
    nome                TEXT,
    plano               TEXT NOT NULL DEFAULT 'free'
                            CHECK (plano IN ('free', 'profissional', 'empresarial')),
    consultas_mes       INTEGER NOT NULL DEFAULT 0,
    mes_referencia      TEXT NOT NULL DEFAULT TO_CHAR(NOW(), 'YYYY-MM'),
    mp_subscription_id  TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ─────────────────────────────────────────────────────────
-- TABELA: consultas
-- Histórico de dimensionamentos por usuário.
-- ─────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.consultas (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    dados_entrada   JSONB NOT NULL,
    resultado       JSONB NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ─────────────────────────────────────────────────────────
-- ÍNDICES
-- ─────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_consultas_user_id
    ON public.consultas(user_id);

CREATE INDEX IF NOT EXISTS idx_consultas_created_at
    ON public.consultas(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_profiles_mp_subscription
    ON public.profiles(mp_subscription_id)
    WHERE mp_subscription_id IS NOT NULL;

-- ─────────────────────────────────────────────────────────
-- ROW LEVEL SECURITY (RLS)
-- Cada usuário só vê e edita seus próprios dados.
-- ─────────────────────────────────────────────────────────
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.consultas ENABLE ROW LEVEL SECURITY;

-- Profiles: usuário vê e edita apenas o próprio perfil
CREATE POLICY "profiles: próprio perfil"
    ON public.profiles
    FOR ALL
    USING (auth.uid() = id)
    WITH CHECK (auth.uid() = id);

-- Consultas: usuário vê e insere apenas as próprias consultas
CREATE POLICY "consultas: próprias consultas"
    ON public.consultas
    FOR ALL
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- Service role bypassa RLS (usado no webhook_server para atualizar planos)
-- Isso é automático no Supabase com a service key — sem necessidade de policy extra.

-- ─────────────────────────────────────────────────────────
-- TRIGGER: atualiza updated_at automaticamente
-- ─────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION public.set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_profiles_updated_at
    BEFORE UPDATE ON public.profiles
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
