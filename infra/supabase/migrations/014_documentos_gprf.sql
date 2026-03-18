-- =================================================================
-- GeoAdmin Pro — Migration: Documentos GPRF
-- infra/supabase/migrations/014_documentos_gprf.sql
-- =================================================================
-- Adiciona as tabelas e colunas necessárias para gerar
-- automaticamente os 7 documentos do processo GPRF:
--   01 Requerimento de Titulação
--   02 Requerimento de Ordem de Serviço
--   03 Declaração de Respeito de Limites
--   05 Declaração de Função Pública
--   06 Declaração de Imóvel Rural
--   07 Declaração de Residência
--   03 Requerimento Diverso
-- =================================================================

-- -----------------------------------------------------------------
-- 1. Ampliar tabela clientes com dados pessoais do formulário
-- -----------------------------------------------------------------

ALTER TABLE clientes
    ADD COLUMN IF NOT EXISTS rg               TEXT,
    ADD COLUMN IF NOT EXISTS estado_civil     TEXT
        CHECK (estado_civil IN (
            'solteiro','casado','divorciado','viuvo','uniao_estavel'
        )),
    ADD COLUMN IF NOT EXISTS profissao        TEXT,
    ADD COLUMN IF NOT EXISTS endereco         TEXT,
    ADD COLUMN IF NOT EXISTS endereco_numero  TEXT,
    ADD COLUMN IF NOT EXISTS setor            TEXT,
    ADD COLUMN IF NOT EXISTS cep              TEXT,
    ADD COLUMN IF NOT EXISTS conjuge_nome     TEXT,
    ADD COLUMN IF NOT EXISTS conjuge_cpf      TEXT,
    ADD COLUMN IF NOT EXISTS formulario_ok    BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS formulario_em    TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS magic_link_expira TIMESTAMPTZ;

COMMENT ON COLUMN clientes.formulario_ok IS
    'TRUE quando o cliente concluiu o preenchimento via Magic Link.';
COMMENT ON COLUMN clientes.magic_link_expira IS
    'Data/hora de expiração do Magic Link enviado ao cliente.';

-- -----------------------------------------------------------------
-- 2. Ampliar tabela projetos com dados do imóvel
-- -----------------------------------------------------------------

ALTER TABLE projetos
    ADD COLUMN IF NOT EXISTS nome_imovel      TEXT,
    ADD COLUMN IF NOT EXISTS comarca          TEXT,
    ADD COLUMN IF NOT EXISTS matricula        TEXT,
    ADD COLUMN IF NOT EXISTS area_ha          NUMERIC(12,4),
    ADD COLUMN IF NOT EXISTS classe_imovel    TEXT,
    ADD COLUMN IF NOT EXISTS distancia_sede_km NUMERIC(8,2),
    ADD COLUMN IF NOT EXISTS distancia_asfalto_km NUMERIC(8,2),
    ADD COLUMN IF NOT EXISTS tempo_posse_anos INTEGER,
    ADD COLUMN IF NOT EXISTS renda_familiar   NUMERIC(12,2),
    ADD COLUMN IF NOT EXISTS funcao_publica   BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS possui_imovel_rural BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS deleted_at       TIMESTAMPTZ;

COMMENT ON COLUMN projetos.area_ha IS
    'Área calculada do levantamento GNSS em hectares.';
COMMENT ON COLUMN projetos.funcao_publica IS
    'FALSE = cliente declarou não exercer função pública (Doc 05).';
COMMENT ON COLUMN projetos.deleted_at IS
    'Soft-delete: preenchido quando o projeto é removido.';

-- -----------------------------------------------------------------
-- 3. Tabela de confrontantes
-- -----------------------------------------------------------------

CREATE TABLE IF NOT EXISTS confrontantes (
    id          UUID    DEFAULT gen_random_uuid() PRIMARY KEY,
    projeto_id  UUID    NOT NULL REFERENCES projetos(id) ON DELETE CASCADE,

    lado        TEXT    NOT NULL
                CHECK (lado IN ('Norte','Sul','Leste','Oeste','Outros')),
    tipo        TEXT    DEFAULT 'particular'
                CHECK (tipo IN ('particular','uniao','estado','municipio','rio','estrada')),

    nome        TEXT    NOT NULL,
    cpf         TEXT,
    nome_imovel TEXT,
    matricula   TEXT,
    origem      TEXT,

    -- Vértices do trecho confrontante (gerado pelo calculo_geodesico.py)
    vertices_json JSONB,
    -- Formato esperado:
    -- [{"codigo":"V01","longitude":-47.929722,"latitude":-15.779167,
    --   "altitude":1172.0,"prox_codigo":"V02","azimute":"36°52'11\"",
    --   "distancia":500.000}]

    criado_em   TIMESTAMPTZ DEFAULT NOW(),
    deleted_at  TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_confrontantes_projeto
    ON confrontantes (projeto_id);

COMMENT ON TABLE confrontantes IS
    'Confrontantes de cada lado do imóvel. '
    'vertices_json contém o trecho técnico para a Declaração de Respeito de Limites.';

-- RLS
ALTER TABLE confrontantes ENABLE ROW LEVEL SECURITY;
CREATE POLICY "topografo_acesso_total" ON confrontantes
    FOR ALL TO authenticated USING (true);

-- -----------------------------------------------------------------
-- 4. Tabela do técnico responsável (configuração única)
-- -----------------------------------------------------------------

CREATE TABLE IF NOT EXISTS tecnico (
    id              UUID    DEFAULT gen_random_uuid() PRIMARY KEY,
    nome            TEXT    NOT NULL,
    cpf             TEXT,
    rg              TEXT,
    crt             TEXT,       -- Registro no CFTO
    crea            TEXT,       -- Registro no CREA
    codigo_incra    TEXT,       -- Código cadastrado no INCRA
    email           TEXT,
    telefone        TEXT,
    municipio       TEXT,
    estado          TEXT    DEFAULT 'GO',
    ativo           BOOLEAN DEFAULT TRUE,
    criado_em       TIMESTAMPTZ DEFAULT NOW()
);

-- Inserir dados do Hugo (atualizar com os valores reais)
INSERT INTO tecnico (nome, cpf, crt, codigo_incra, email, municipio, estado)
VALUES (
    'Hugo',          -- substituir pelo nome completo
    '',              -- CPF do técnico
    '',              -- número CRT
    '',              -- código INCRA
    '',              -- e-mail
    'Brasília',
    'DF'
)
ON CONFLICT DO NOTHING;

COMMENT ON TABLE tecnico IS
    'Dados do técnico responsável. Preencher uma vez, '
    'usado em todos os documentos gerados automaticamente.';

-- -----------------------------------------------------------------
-- 5. Tabela de documentos gerados
-- -----------------------------------------------------------------

CREATE TABLE IF NOT EXISTS documentos_gerados (
    id          UUID    DEFAULT gen_random_uuid() PRIMARY KEY,
    projeto_id  UUID    NOT NULL REFERENCES projetos(id) ON DELETE CASCADE,
    tipo        TEXT    NOT NULL
                CHECK (tipo IN (
                    'req_titulacao',
                    'req_ordem_servico',
                    'decl_respeito_limites',
                    'decl_funcao_publica',
                    'decl_imovel_rural',
                    'decl_residencia',
                    'req_diverso',
                    'memorial_descritivo',
                    'roteiro_perimetrico',
                    'planilha_ods',
                    'planta_dxf',
                    'kml'
                )),
    storage_path TEXT,          -- caminho no Supabase Storage
    versao      INTEGER DEFAULT 1,
    gerado_em   TIMESTAMPTZ DEFAULT NOW(),
    deleted_at  TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_docs_gerados_projeto
    ON documentos_gerados (projeto_id);

ALTER TABLE documentos_gerados ENABLE ROW LEVEL SECURITY;
CREATE POLICY "topografo_acesso_total" ON documentos_gerados
    FOR ALL TO authenticated USING (true);

-- -----------------------------------------------------------------
-- 6. View vw_projetos_completo (usada pelo endpoint magic-link)
-- -----------------------------------------------------------------

CREATE OR REPLACE VIEW vw_projetos_completo AS
SELECT
    p.*,
    c.nome  AS cliente_nome,
    c.telefone AS cliente_telefone,
    c.email AS cliente_email
FROM projetos p
LEFT JOIN clientes c ON c.id = p.cliente_id
WHERE p.deleted_at IS NULL;

COMMENT ON VIEW vw_projetos_completo IS
    'Projetos com dados básicos do cliente. Usada pelo endpoint magic-link.';

-- -----------------------------------------------------------------
-- 7. View para o formulário do cliente (Magic Link)
-- -----------------------------------------------------------------

CREATE OR REPLACE VIEW vw_formulario_cliente AS
SELECT
    p.id                        AS projeto_id,
    p.nome                      AS projeto_nome,
    p.nome_imovel,
    p.municipio                 AS imovel_municipio,
    p.estado                    AS imovel_estado,
    p.comarca,
    p.matricula,
    p.area_ha,
    c.id                        AS cliente_id,
    c.nome                      AS cliente_nome,
    c.cpf                       AS cliente_cpf,
    c.rg                        AS cliente_rg,
    c.estado_civil,
    c.profissao,
    c.telefone,
    c.email,
    c.endereco,
    c.endereco_numero,
    c.municipio                 AS cliente_municipio,
    c.estado                    AS cliente_estado,
    c.cep,
    c.conjuge_nome,
    c.conjuge_cpf,
    c.formulario_ok,
    c.formulario_em,
    c.magic_link_token,
    c.magic_link_expira
FROM projetos p
JOIN clientes c ON c.id = p.cliente_id
WHERE p.deleted_at IS NULL;

COMMENT ON VIEW vw_formulario_cliente IS
    'Dados completos para o formulário Magic Link do cliente.';

-- -----------------------------------------------------------------
-- 8. Verificação
-- -----------------------------------------------------------------

SELECT
    (SELECT COUNT(*) FROM confrontantes)        AS confrontantes,
    (SELECT COUNT(*) FROM tecnico)              AS tecnicos,
    (SELECT COUNT(*) FROM documentos_gerados)   AS docs_gerados;

-- Verificar novas colunas
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'clientes'
  AND column_name IN ('rg','estado_civil','formulario_ok','magic_link_expira')
ORDER BY column_name;
