-- =================================================================
-- GeoAdmin Pro — Migration 022: Historico de magic links por vinculo
-- Registra geracao, reenvio e consumo por participante/lote do projeto.
-- =================================================================

CREATE TABLE IF NOT EXISTS eventos_magic_link (
    id                  UUID        DEFAULT gen_random_uuid() PRIMARY KEY,
    projeto_id          UUID        NOT NULL REFERENCES projetos(id) ON DELETE CASCADE,
    projeto_cliente_id  UUID        REFERENCES projeto_clientes(id) ON DELETE SET NULL,
    area_id             UUID        REFERENCES areas_projeto(id) ON DELETE SET NULL,
    cliente_id          UUID        REFERENCES clientes(id) ON DELETE SET NULL,
    tipo_evento         TEXT        NOT NULL DEFAULT 'gerado'
                        CHECK (tipo_evento IN ('gerado', 'reenviado', 'revogado', 'consumido', 'legado')),
    canal               TEXT        NOT NULL DEFAULT 'whatsapp'
                        CHECK (canal IN ('whatsapp', 'email', 'sms', 'manual', 'interno')),
    token               TEXT,
    autor               TEXT,
    expira_em           TIMESTAMPTZ,
    payload_json        JSONB       NOT NULL DEFAULT '{}'::jsonb,
    criado_em           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at          TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_eventos_magic_link_projeto
    ON eventos_magic_link (projeto_id, criado_em DESC)
    WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_eventos_magic_link_participante
    ON eventos_magic_link (projeto_cliente_id, criado_em DESC)
    WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_eventos_magic_link_area
    ON eventos_magic_link (area_id, criado_em DESC)
    WHERE deleted_at IS NULL;

ALTER TABLE eventos_magic_link ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "topografo_acesso_total_eventos_magic_link" ON eventos_magic_link;
CREATE POLICY "topografo_acesso_total_eventos_magic_link" ON eventos_magic_link
    FOR ALL TO authenticated USING (true);
