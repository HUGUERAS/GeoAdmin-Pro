-- =================================================================
-- GeoAdmin Pro — Migration 020: Arquivos cartograficos do projeto
-- Bandeja cartografica com classificacao e origem controladas.
-- =================================================================

CREATE TABLE IF NOT EXISTS arquivos_projeto (
    id               UUID        DEFAULT gen_random_uuid() PRIMARY KEY,
    projeto_id       UUID        NOT NULL REFERENCES projetos(id) ON DELETE CASCADE,
    area_id          UUID        REFERENCES areas_projeto(id) ON DELETE SET NULL,
    cliente_id       UUID        REFERENCES clientes(id) ON DELETE SET NULL,
    nome_arquivo     TEXT        NOT NULL,
    nome_original    TEXT,
    formato          TEXT        NOT NULL,
    mime_type        TEXT,
    tamanho_bytes    BIGINT,
    origem           TEXT        NOT NULL DEFAULT 'topografo'
                     CHECK (origem IN ('topografo', 'cliente', 'escritorio', 'sistema')),
    classificacao    TEXT        NOT NULL DEFAULT 'referencia_visual'
                     CHECK (classificacao IN (
                         'referencia_visual',
                         'esboco_area',
                         'perimetro_tecnico',
                         'camada_auxiliar',
                         'documento_croqui',
                         'exportacao'
                     )),
    storage_path     TEXT        NOT NULL,
    hash_arquivo     TEXT,
    metadados_json   JSONB       NOT NULL DEFAULT '{}'::jsonb,
    criado_em        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    atualizado_em    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at       TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_arquivos_projeto_projeto
    ON arquivos_projeto (projeto_id, criado_em DESC)
    WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_arquivos_projeto_area
    ON arquivos_projeto (area_id)
    WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_arquivos_projeto_cliente
    ON arquivos_projeto (cliente_id)
    WHERE deleted_at IS NULL;

CREATE OR REPLACE FUNCTION public.set_arquivos_projeto_atualizado_em()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    NEW.atualizado_em = NOW();
    RETURN NEW;
END; $$;

DROP TRIGGER IF EXISTS trg_arquivos_projeto_atualizado_em ON arquivos_projeto;
CREATE TRIGGER trg_arquivos_projeto_atualizado_em
    BEFORE UPDATE ON arquivos_projeto
    FOR EACH ROW
    EXECUTE FUNCTION public.set_arquivos_projeto_atualizado_em();

ALTER TABLE arquivos_projeto ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "topografo_acesso_total_arquivos_projeto" ON arquivos_projeto;
CREATE POLICY "topografo_acesso_total_arquivos_projeto" ON arquivos_projeto
    FOR ALL TO authenticated USING (true);
