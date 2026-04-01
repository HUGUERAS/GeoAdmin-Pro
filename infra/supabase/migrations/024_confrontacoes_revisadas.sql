-- =================================================================
-- GeoAdmin Pro — Migration 024: Revisão operacional de confrontações
-- Permite confirmar, descartar e anotar confrontações antes da carta final.
-- =================================================================

CREATE TABLE IF NOT EXISTS confrontacoes_revisadas (
    id                  UUID        DEFAULT gen_random_uuid() PRIMARY KEY,
    projeto_id          UUID        NOT NULL REFERENCES projetos(id) ON DELETE CASCADE,
    confronto_id        TEXT        NOT NULL,
    tipo_relacao        TEXT        NOT NULL DEFAULT 'interna'
                        CHECK (tipo_relacao IN ('interna', 'externa')),
    status_revisao      TEXT        NOT NULL DEFAULT 'detectada'
                        CHECK (status_revisao IN ('detectada', 'confirmada', 'descartada')),
    observacao          TEXT,
    autor               TEXT,
    criado_em           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    atualizado_em       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at          TIMESTAMPTZ,
    UNIQUE (projeto_id, confronto_id)
);

CREATE INDEX IF NOT EXISTS idx_confrontacoes_revisadas_projeto
    ON confrontacoes_revisadas (projeto_id, atualizado_em DESC)
    WHERE deleted_at IS NULL;

CREATE OR REPLACE FUNCTION public.set_confrontacoes_revisadas_atualizado_em()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN NEW.atualizado_em = NOW(); RETURN NEW; END; $$;

DROP TRIGGER IF EXISTS trg_confrontacoes_revisadas_atualizado_em ON confrontacoes_revisadas;
CREATE TRIGGER trg_confrontacoes_revisadas_atualizado_em
    BEFORE UPDATE ON confrontacoes_revisadas
    FOR EACH ROW
    EXECUTE FUNCTION public.set_confrontacoes_revisadas_atualizado_em();

ALTER TABLE confrontacoes_revisadas ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "topografo_acesso_total_confrontacoes_revisadas" ON confrontacoes_revisadas;
CREATE POLICY "topografo_acesso_total_confrontacoes_revisadas" ON confrontacoes_revisadas
    FOR ALL TO authenticated USING (true);
