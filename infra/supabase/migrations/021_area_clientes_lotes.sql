-- =================================================================
-- GeoAdmin Pro — Migration 021: Estrutura condominial por lote
-- Cria participantes por area e status operacionais/documentais do lote.
-- =================================================================

ALTER TABLE areas_projeto
    ADD COLUMN IF NOT EXISTS codigo_lote TEXT,
    ADD COLUMN IF NOT EXISTS quadra TEXT,
    ADD COLUMN IF NOT EXISTS setor TEXT,
    ADD COLUMN IF NOT EXISTS status_operacional TEXT DEFAULT 'aguardando_cliente',
    ADD COLUMN IF NOT EXISTS status_documental TEXT DEFAULT 'pendente';

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'areas_projeto_status_operacional_check'
    ) THEN
        ALTER TABLE areas_projeto
            ADD CONSTRAINT areas_projeto_status_operacional_check
            CHECK (status_operacional IN (
                'aguardando_cliente',
                'cliente_vinculado',
                'croqui_recebido',
                'geometria_final',
                'peca_pronta'
            ));
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'areas_projeto_status_documental_check'
    ) THEN
        ALTER TABLE areas_projeto
            ADD CONSTRAINT areas_projeto_status_documental_check
            CHECK (status_documental IN (
                'pendente',
                'formulario_ok',
                'confrontantes_ok',
                'documentacao_ok',
                'peca_pronta'
            ));
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_areas_projeto_codigo_lote
    ON areas_projeto (projeto_id, codigo_lote)
    WHERE deleted_at IS NULL;

CREATE TABLE IF NOT EXISTS area_clientes (
    id                 UUID        DEFAULT gen_random_uuid() PRIMARY KEY,
    area_id            UUID        NOT NULL REFERENCES areas_projeto(id) ON DELETE CASCADE,
    cliente_id         UUID        NOT NULL REFERENCES clientes(id) ON DELETE CASCADE,
    papel              TEXT        NOT NULL DEFAULT 'outro'
                       CHECK (papel IN (
                           'principal','coproprietario','possuidor',
                           'herdeiro','representante','outro'
                       )),
    principal          BOOLEAN     NOT NULL DEFAULT FALSE,
    recebe_magic_link  BOOLEAN     NOT NULL DEFAULT FALSE,
    ordem              INTEGER     NOT NULL DEFAULT 0,
    criado_em          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    atualizado_em      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at         TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_area_clientes_area
    ON area_clientes (area_id, ordem)
    WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_area_clientes_cliente
    ON area_clientes (cliente_id)
    WHERE deleted_at IS NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uq_area_clientes_ativo
    ON area_clientes (area_id, cliente_id)
    WHERE deleted_at IS NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uq_area_clientes_principal
    ON area_clientes (area_id)
    WHERE deleted_at IS NULL AND principal = TRUE;

CREATE OR REPLACE FUNCTION public.set_area_clientes_atualizado_em()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    NEW.atualizado_em = NOW();
    RETURN NEW;
END; $$;

DROP TRIGGER IF EXISTS trg_area_clientes_atualizado_em ON area_clientes;
CREATE TRIGGER trg_area_clientes_atualizado_em
    BEFORE UPDATE ON area_clientes
    FOR EACH ROW
    EXECUTE FUNCTION public.set_area_clientes_atualizado_em();

ALTER TABLE area_clientes ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "topografo_acesso_total_area_clientes" ON area_clientes;
CREATE POLICY "topografo_acesso_total_area_clientes" ON area_clientes
    FOR ALL TO authenticated USING (true);
