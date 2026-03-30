-- =================================================================
-- GeoAdmin Pro — Migration 019: Participantes do projeto
-- Permite multiplos clientes por projeto com magic link por vinculo.
-- =================================================================

CREATE TABLE IF NOT EXISTS projeto_clientes (
    id                 UUID        DEFAULT gen_random_uuid() PRIMARY KEY,
    projeto_id         UUID        NOT NULL REFERENCES projetos(id) ON DELETE CASCADE,
    cliente_id         UUID        NOT NULL REFERENCES clientes(id) ON DELETE CASCADE,
    area_id            UUID        REFERENCES areas_projeto(id) ON DELETE SET NULL,
    papel              TEXT        NOT NULL DEFAULT 'outro'
                       CHECK (papel IN (
                           'principal','coproprietario','possuidor',
                           'herdeiro','representante','outro'
                       )),
    principal          BOOLEAN     NOT NULL DEFAULT FALSE,
    recebe_magic_link  BOOLEAN     NOT NULL DEFAULT FALSE,
    ordem              INTEGER     NOT NULL DEFAULT 0,
    magic_link_token   TEXT,
    magic_link_expira  TIMESTAMPTZ,
    criado_em          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    atualizado_em      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at         TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_projeto_clientes_projeto
    ON projeto_clientes (projeto_id, ordem)
    WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_projeto_clientes_cliente
    ON projeto_clientes (cliente_id)
    WHERE deleted_at IS NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uq_projeto_clientes_ativo
    ON projeto_clientes (projeto_id, cliente_id)
    WHERE deleted_at IS NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uq_projeto_clientes_principal
    ON projeto_clientes (projeto_id)
    WHERE deleted_at IS NULL AND principal = TRUE;

CREATE UNIQUE INDEX IF NOT EXISTS uq_projeto_clientes_magic_link
    ON projeto_clientes (magic_link_token)
    WHERE deleted_at IS NULL AND magic_link_token IS NOT NULL;

CREATE OR REPLACE FUNCTION public.set_projeto_clientes_atualizado_em()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    NEW.atualizado_em = NOW();
    RETURN NEW;
END; $$;

DROP TRIGGER IF EXISTS trg_projeto_clientes_atualizado_em ON projeto_clientes;
CREATE TRIGGER trg_projeto_clientes_atualizado_em
    BEFORE UPDATE ON projeto_clientes
    FOR EACH ROW
    EXECUTE FUNCTION public.set_projeto_clientes_atualizado_em();

ALTER TABLE projeto_clientes ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "topografo_acesso_total_projeto_clientes" ON projeto_clientes;
CREATE POLICY "topografo_acesso_total_projeto_clientes" ON projeto_clientes
    FOR ALL TO authenticated USING (true);

CREATE OR REPLACE VIEW vw_projeto_clientes AS
SELECT DISTINCT
    p.id AS projeto_id,
    p.nome AS projeto_nome,
    c.id AS cliente_id,
    c.nome AS cliente_nome,
    COALESCE(c.cpf, c.cpf_cnpj) AS cliente_cpf,
    c.telefone,
    c.email,
    pc.papel AS vinculo,
    pc.principal,
    pc.recebe_magic_link,
    pc.ordem,
    pc.area_id
FROM projeto_clientes pc
JOIN clientes c ON c.id = pc.cliente_id
JOIN projetos p ON p.id = pc.projeto_id
WHERE pc.deleted_at IS NULL
  AND p.deleted_at IS NULL
UNION
SELECT DISTINCT
    p.id AS projeto_id,
    p.nome AS projeto_nome,
    c.id AS cliente_id,
    c.nome AS cliente_nome,
    COALESCE(c.cpf, c.cpf_cnpj) AS cliente_cpf,
    c.telefone,
    c.email,
    'principal' AS vinculo,
    TRUE AS principal,
    COALESCE(c.magic_link_token IS NOT NULL, FALSE) AS recebe_magic_link,
    0 AS ordem,
    NULL::UUID AS area_id
FROM projetos p
JOIN clientes c ON c.id = p.cliente_id
WHERE p.deleted_at IS NULL
  AND NOT EXISTS (
      SELECT 1
      FROM projeto_clientes pc
      WHERE pc.projeto_id = p.id
        AND pc.deleted_at IS NULL
  );
