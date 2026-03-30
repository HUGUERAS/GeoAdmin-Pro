-- =================================================================
-- GeoAdmin Pro — Migration 017: Areas de projeto no Supabase
-- Substitui o areas_projeto.json local por tabela persistente.
-- =================================================================

CREATE TABLE IF NOT EXISTS areas_projeto (
    id                UUID        DEFAULT gen_random_uuid() PRIMARY KEY,
    projeto_id        UUID        NOT NULL REFERENCES projetos(id) ON DELETE CASCADE,
    cliente_id        UUID        REFERENCES clientes(id) ON DELETE SET NULL,
    nome              TEXT        NOT NULL DEFAULT 'Area sem nome',
    proprietario_nome TEXT,
    municipio         TEXT,
    estado            TEXT,
    comarca           TEXT,
    matricula         TEXT,
    ccir              TEXT,
    car               TEXT,
    observacoes       TEXT,
    origem_tipo       TEXT        NOT NULL DEFAULT 'manual'
                      CHECK (origem_tipo IN (
                          'manual','formulario','formulario_cliente','importacao',
                          'referencia_cliente','perimetro_tecnico'
                      )),
    geometria_esboco  JSONB       DEFAULT '[]'::jsonb,
    geometria_final   JSONB       DEFAULT '[]'::jsonb,
    resumo_esboco     JSONB,
    resumo_final      JSONB,
    anexos            JSONB       DEFAULT '[]'::jsonb,
    criado_em         TIMESTAMPTZ DEFAULT NOW(),
    atualizado_em     TIMESTAMPTZ DEFAULT NOW(),
    deleted_at        TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_areas_projeto_projeto
    ON areas_projeto (projeto_id, atualizado_em DESC)
    WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_areas_projeto_cliente
    ON areas_projeto (cliente_id)
    WHERE deleted_at IS NULL;

CREATE OR REPLACE FUNCTION public.set_areas_projeto_atualizado_em()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    NEW.atualizado_em = NOW();
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_areas_projeto_atualizado_em ON areas_projeto;
CREATE TRIGGER trg_areas_projeto_atualizado_em
    BEFORE UPDATE ON areas_projeto
    FOR EACH ROW
    EXECUTE FUNCTION public.set_areas_projeto_atualizado_em();

ALTER TABLE areas_projeto ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "topografo_acesso_total" ON areas_projeto;
CREATE POLICY "topografo_acesso_total" ON areas_projeto
    FOR ALL TO authenticated USING (true);

ALTER TABLE projetos
    ADD COLUMN IF NOT EXISTS tipo_processo TEXT DEFAULT 'INCRA_SIGEF'
        CHECK (tipo_processo IN ('INCRA_SIGEF', 'SEAPA', 'AMBOS'));

ALTER TABLE clientes
    ADD COLUMN IF NOT EXISTS cpf TEXT;

UPDATE clientes
SET cpf = COALESCE(cpf, cpf_cnpj)
WHERE cpf IS NULL
  AND cpf_cnpj IS NOT NULL;

CREATE OR REPLACE VIEW vw_projetos_completo AS
SELECT
    p.id,
    p.cliente_id,
    p.nome,
    p.numero_job,
    p.descricao,
    p.municipio,
    p.estado,
    p.matricula,
    p.comarca,
    p.zona_utm,
    p.srid,
    p.status,
    p.data_medicao,
    p.data_protocolo,
    p.data_aprovacao,
    p.data_entrega,
    p.prazo_estimado,
    p.valor_servico,
    p.valor_pago,
    p.criado_em,
    p.atualizado_em,
    p.deleted_at,
    p.nome_imovel,
    p.area_ha,
    p.classe_imovel,
    p.distancia_sede_km,
    p.distancia_asfalto_km,
    p.tempo_posse_anos,
    p.renda_familiar,
    p.funcao_publica,
    p.possui_imovel_rural,
    c.nome                     AS cliente_nome,
    c.telefone                 AS cliente_telefone,
    c.email                    AS cliente_email,
    p.nome                     AS projeto_nome,
    COALESCE(pt.total_pontos, 0::bigint) AS total_pontos,
    p.tipo_processo,
    c.municipio                AS cliente_municipio,
    c.estado                   AS cliente_estado
FROM projetos p
LEFT JOIN clientes c ON c.id = p.cliente_id
LEFT JOIN (
    SELECT pontos.projeto_id, count(*) AS total_pontos
    FROM pontos
    WHERE pontos.coordenada IS NOT NULL
    GROUP BY pontos.projeto_id
) pt ON pt.projeto_id = p.id
WHERE p.deleted_at IS NULL;

CREATE OR REPLACE VIEW vw_projeto_clientes AS
SELECT DISTINCT
    p.id AS projeto_id,
    p.nome AS projeto_nome,
    c.id AS cliente_id,
    c.nome AS cliente_nome,
    COALESCE(c.cpf, c.cpf_cnpj) AS cliente_cpf,
    c.telefone,
    c.email,
    CASE WHEN p.cliente_id = c.id THEN 'principal' ELSE 'area' END AS vinculo
FROM projetos p
JOIN clientes c ON c.id = p.cliente_id
WHERE p.deleted_at IS NULL
UNION
SELECT DISTINCT
    ap.projeto_id,
    p.nome AS projeto_nome,
    c.id AS cliente_id,
    c.nome AS cliente_nome,
    COALESCE(c.cpf, c.cpf_cnpj) AS cliente_cpf,
    c.telefone,
    c.email,
    'area' AS vinculo
FROM areas_projeto ap
JOIN clientes c ON c.id = ap.cliente_id
JOIN projetos p ON p.id = ap.projeto_id
WHERE ap.deleted_at IS NULL
  AND p.deleted_at IS NULL;
