-- =================================================================
-- GeoAdmin Pro — Migration 025: Ownership por topógrafo
-- Adiciona topografo_id a projetos e restringe RLS por proprietário.
-- Não quebra dados existentes (coluna nullable + policy permissiva
-- quando topografo_id é NULL, para compatibilidade com registros antigos).
-- =================================================================

-- -----------------------------------------------------------------
-- 1. Coluna topografo_id em projetos
-- -----------------------------------------------------------------
ALTER TABLE projetos
    ADD COLUMN IF NOT EXISTS topografo_id UUID REFERENCES auth.users(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_projetos_topografo
    ON projetos (topografo_id)
    WHERE deleted_at IS NULL;

-- -----------------------------------------------------------------
-- 2. RLS em projetos: scope por topografo_id quando preenchido
--    Regra: service_role bypassa tudo; auth.uid() === topografo_id;
--           registros legados sem topografo_id ficam acessíveis a
--           qualquer usuário autenticado (backward-compat).
-- -----------------------------------------------------------------
ALTER TABLE projetos ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "topografo_acesso_total" ON projetos;
DROP POLICY IF EXISTS "projetos_por_topografo" ON projetos;

CREATE POLICY "projetos_por_topografo" ON projetos
    FOR ALL TO authenticated
    USING (
        topografo_id IS NULL
        OR topografo_id = auth.uid()
    )
    WITH CHECK (
        topografo_id IS NULL
        OR topografo_id = auth.uid()
    );

-- -----------------------------------------------------------------
-- 3. Índice de performance para consultas frequentes
-- -----------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_projetos_topografo_status
    ON projetos (topografo_id, status, criado_em DESC)
    WHERE deleted_at IS NULL;

-- -----------------------------------------------------------------
-- 4. Tabelas filhas: mantêm USING (true) para auth.
--    A proteção real vem da cascata: o backend/service_role acessa
--    apenas dados de projetos que pertençam ao topógrafo autenticado.
--    Registrar política explícita de leitura para clareza.
-- -----------------------------------------------------------------

-- areas_projeto: herda segurança via projeto_id
DROP POLICY IF EXISTS "topografo_acesso_total" ON areas_projeto;
CREATE POLICY "areas_por_topografo" ON areas_projeto
    FOR ALL TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM projetos p
            WHERE p.id = areas_projeto.projeto_id
              AND (p.topografo_id IS NULL OR p.topografo_id = auth.uid())
              AND p.deleted_at IS NULL
        )
    );

-- area_clientes: herda via area_id → areas_projeto → projetos
DROP POLICY IF EXISTS "topografo_acesso_total_area_clientes" ON area_clientes;
CREATE POLICY "area_clientes_por_topografo" ON area_clientes
    FOR ALL TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM areas_projeto a
            JOIN projetos p ON p.id = a.projeto_id
            WHERE a.id = area_clientes.area_id
              AND (p.topografo_id IS NULL OR p.topografo_id = auth.uid())
              AND a.deleted_at IS NULL
              AND p.deleted_at IS NULL
        )
    );

-- projeto_clientes
DROP POLICY IF EXISTS "topografo_acesso_total_projeto_clientes" ON projeto_clientes;
CREATE POLICY "projeto_clientes_por_topografo" ON projeto_clientes
    FOR ALL TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM projetos p
            WHERE p.id = projeto_clientes.projeto_id
              AND (p.topografo_id IS NULL OR p.topografo_id = auth.uid())
              AND p.deleted_at IS NULL
        )
    );

-- eventos_magic_link
DROP POLICY IF EXISTS "topografo_acesso_total_eventos_magic_link" ON eventos_magic_link;
CREATE POLICY "eventos_magic_link_por_topografo" ON eventos_magic_link
    FOR ALL TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM projetos p
            WHERE p.id = eventos_magic_link.projeto_id
              AND (p.topografo_id IS NULL OR p.topografo_id = auth.uid())
              AND p.deleted_at IS NULL
        )
    );

-- eventos_cartograficos
DROP POLICY IF EXISTS "topografo_acesso_total_eventos_cartograficos" ON eventos_cartograficos;
CREATE POLICY "eventos_cartograficos_por_topografo" ON eventos_cartograficos
    FOR ALL TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM projetos p
            WHERE p.id = eventos_cartograficos.projeto_id
              AND (p.topografo_id IS NULL OR p.topografo_id = auth.uid())
              AND p.deleted_at IS NULL
        )
    );

-- confrontacoes_revisadas
DROP POLICY IF EXISTS "topografo_acesso_total_confrontacoes_revisadas" ON confrontacoes_revisadas;
CREATE POLICY "confrontacoes_por_topografo" ON confrontacoes_revisadas
    FOR ALL TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM projetos p
            WHERE p.id = confrontacoes_revisadas.projeto_id
              AND (p.topografo_id IS NULL OR p.topografo_id = auth.uid())
              AND p.deleted_at IS NULL
        )
    );

-- arquivos_projeto
DROP POLICY IF EXISTS "topografo_acesso_total_arquivos_projeto" ON arquivos_projeto;
CREATE POLICY "arquivos_por_topografo" ON arquivos_projeto
    FOR ALL TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM projetos p
            WHERE p.id = arquivos_projeto.projeto_id
              AND (p.topografo_id IS NULL OR p.topografo_id = auth.uid())
              AND p.deleted_at IS NULL
        )
    );

-- -----------------------------------------------------------------
-- 5. Funções auxiliares para registrar topografo_id automaticamente
--    em novos projetos quando criados via Supabase client (não backend)
-- -----------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.set_projeto_topografo_id()
RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER AS $$
BEGIN
    IF NEW.topografo_id IS NULL AND auth.uid() IS NOT NULL THEN
        NEW.topografo_id = auth.uid();
    END IF;
    RETURN NEW;
END; $$;

DROP TRIGGER IF EXISTS trg_set_projeto_topografo_id ON projetos;
CREATE TRIGGER trg_set_projeto_topografo_id
    BEFORE INSERT ON projetos
    FOR EACH ROW
    EXECUTE FUNCTION public.set_projeto_topografo_id();
