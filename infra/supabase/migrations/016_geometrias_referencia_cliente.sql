-- =================================================================
-- GeoAdmin Pro -- Geometrias de referencia do cliente
-- Guarda o croqui/importacao informal do cliente para comparacao
-- com o perimetro tecnico levantado em campo.
-- =================================================================

CREATE TABLE IF NOT EXISTS geometrias_referencia_cliente (
    id              UUID        DEFAULT gen_random_uuid() PRIMARY KEY,
    cliente_id       UUID        NOT NULL REFERENCES clientes(id) ON DELETE CASCADE,
    projeto_id       UUID        REFERENCES projetos(id) ON DELETE SET NULL,
    nome            TEXT        NOT NULL DEFAULT 'Referencia do cliente',
    origem_tipo     TEXT        NOT NULL
                    CHECK (origem_tipo IN ('manual','importacao_texto','arquivo','formulario_cliente')),
    arquivo_nome    TEXT,
    formato         TEXT        NOT NULL,
    vertices_json   JSONB       NOT NULL DEFAULT '[]'::jsonb,
    resumo_json     JSONB       NOT NULL DEFAULT '{}'::jsonb,
    comparativo_json JSONB,
    atualizado_em   TIMESTAMPTZ DEFAULT NOW(),
    deleted_at      TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_geometrias_referencia_cliente_cliente
    ON geometrias_referencia_cliente (cliente_id, atualizado_em DESC);

CREATE INDEX IF NOT EXISTS idx_geometrias_referencia_cliente_projeto
    ON geometrias_referencia_cliente (projeto_id, atualizado_em DESC);

CREATE OR REPLACE FUNCTION public.set_geometrias_referencia_cliente_atualizado_em()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.atualizado_em = NOW();
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_geometrias_referencia_cliente_atualizado_em
    ON geometrias_referencia_cliente;

CREATE TRIGGER trg_geometrias_referencia_cliente_atualizado_em
    BEFORE UPDATE ON geometrias_referencia_cliente
    FOR EACH ROW
    EXECUTE FUNCTION public.set_geometrias_referencia_cliente_atualizado_em();

ALTER TABLE geometrias_referencia_cliente ENABLE ROW LEVEL SECURITY;

CREATE POLICY "topografo_acesso_total" ON geometrias_referencia_cliente
    FOR ALL TO authenticated USING (true);
