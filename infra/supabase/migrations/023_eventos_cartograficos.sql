-- =================================================================
-- GeoAdmin Pro — Migration 023: Eventos cartograficos e base oficial
-- Promotion audit trail + preparação de migração do fallback local.
-- =================================================================

ALTER TABLE arquivos_projeto
    ADD COLUMN IF NOT EXISTS base_oficial BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS promovido_em TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS promovido_por TEXT,
    ADD COLUMN IF NOT EXISTS promocao_observacao TEXT;

CREATE TABLE IF NOT EXISTS eventos_cartograficos (
    id                      UUID        DEFAULT gen_random_uuid() PRIMARY KEY,
    projeto_id              UUID        NOT NULL REFERENCES projetos(id) ON DELETE CASCADE,
    arquivo_id              UUID        REFERENCES arquivos_projeto(id) ON DELETE SET NULL,
    area_id                 UUID        REFERENCES areas_projeto(id) ON DELETE SET NULL,
    cliente_id              UUID        REFERENCES clientes(id) ON DELETE SET NULL,
    tipo_evento             TEXT        NOT NULL
                            CHECK (tipo_evento IN (
                                'upload',
                                'migracao_storage',
                                'promocao_base_oficial',
                                'reclassificacao',
                                'exportacao'
                            )),
    origem                  TEXT,
    classificacao_anterior  TEXT,
    classificacao_nova      TEXT,
    storage_path_anterior   TEXT,
    storage_path_novo       TEXT,
    autor                   TEXT,
    observacao              TEXT,
    payload_json            JSONB       NOT NULL DEFAULT '{}'::jsonb,
    criado_em               TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at              TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_eventos_cartograficos_projeto
    ON eventos_cartograficos (projeto_id, criado_em DESC)
    WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_eventos_cartograficos_arquivo
    ON eventos_cartograficos (arquivo_id, criado_em DESC)
    WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_eventos_cartograficos_area
    ON eventos_cartograficos (area_id, criado_em DESC)
    WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_arquivos_projeto_base_oficial
    ON arquivos_projeto (projeto_id, base_oficial, criado_em DESC)
    WHERE deleted_at IS NULL;

ALTER TABLE eventos_cartograficos ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "topografo_acesso_total_eventos_cartograficos" ON eventos_cartograficos;
CREATE POLICY "topografo_acesso_total_eventos_cartograficos" ON eventos_cartograficos
    FOR ALL TO authenticated USING (true);
