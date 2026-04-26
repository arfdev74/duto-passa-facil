-- ╔══════════════════════════════════════════════════════════╗
-- ║  DUTO — PASSA FÁCIL · Schema v2 (Licença Vitalícia)      ║
-- ║  Execute no Supabase SQL Editor                          ║
-- ╚══════════════════════════════════════════════════════════╝

-- ─────────────────────────────────────────────────────────
-- TABELA: profiles
-- ─────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.profiles (
    id                UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email             TEXT NOT NULL,
    nome              TEXT,
    plano             TEXT NOT NULL DEFAULT 'free'
                          CHECK (plano IN ('free', 'profissional')),
    consultas_mes     INTEGER NOT NULL DEFAULT 0,
    mes_referencia    TEXT NOT NULL DEFAULT TO_CHAR(NOW(), 'YYYY-MM'),
    mp_payment_id     TEXT,        -- ID do pagamento aprovado no MP
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ─────────────────────────────────────────────────────────
-- TABELA: consultas
-- ─────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.consultas (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id       UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    dados_entrada JSONB NOT NULL,
    resultado     JSONB NOT NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ─────────────────────────────────────────────────────────
-- ÍNDICES
-- ─────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_consultas_user_id
    ON public.consultas(user_id);

CREATE INDEX IF NOT EXISTS idx_consultas_created_at
    ON public.consultas(created_at DESC);

-- ─────────────────────────────────────────────────────────
-- PERMISSÕES
-- ─────────────────────────────────────────────────────────
GRANT USAGE ON SCHEMA public TO anon, authenticated, service_role;
GRANT ALL ON public.profiles TO anon, authenticated, service_role;
GRANT ALL ON public.consultas TO anon, authenticated, service_role;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO anon, authenticated, service_role;

-- ─────────────────────────────────────────────────────────
-- ROW LEVEL SECURITY
-- ─────────────────────────────────────────────────────────
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.consultas ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "profiles: próprio perfil" ON public.profiles;
CREATE POLICY "profiles: próprio perfil"
    ON public.profiles FOR ALL
    USING (auth.uid() = id)
    WITH CHECK (auth.uid() = id);

DROP POLICY IF EXISTS "consultas: próprias consultas" ON public.consultas;
CREATE POLICY "consultas: próprias consultas"
    ON public.consultas FOR ALL
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- ─────────────────────────────────────────────────────────
-- TRIGGER: cria perfil automaticamente após cadastro
-- ─────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.profiles (id, email, nome, plano, consultas_mes, mes_referencia)
    VALUES (
        NEW.id,
        NEW.email,
        COALESCE(NEW.raw_user_meta_data->>'nome', split_part(NEW.email, '@', 1)),
        'free',
        0,
        TO_CHAR(NOW(), 'YYYY-MM')
    )
    ON CONFLICT (id) DO NOTHING;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- ─────────────────────────────────────────────────────────
-- TRIGGER: updated_at automático
-- ─────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION public.set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_profiles_updated_at ON public.profiles;
CREATE TRIGGER trg_profiles_updated_at
    BEFORE UPDATE ON public.profiles
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
