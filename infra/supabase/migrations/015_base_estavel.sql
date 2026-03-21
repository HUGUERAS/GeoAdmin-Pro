-- =================================================================
-- GeoAdmin Pro — Migration: Base estável
-- Corrige estruturas e contratos usados hoje por backend/mobile.
-- =================================================================

CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- -----------------------------------------------------------------
-- 1. Normalizar colunas base de projetos / clientes / pontos
-- -----------------------------------------------------------------

ALTER TABLE projetos
    ADD COLUMN IF NOT EXISTS numero_job              TEXT,
    ADD COLUMN IF NOT EXISTS municipio               TEXT,
    ADD COLUMN IF NOT EXISTS estado                  TEXT,
    ADD COLUMN IF NOT EXISTS nome_imovel             TEXT,
    ADD COLUMN IF NOT EXISTS comarca                 TEXT,
    ADD COLUMN IF NOT EXISTS matricula               TEXT,
    ADD COLUMN IF NOT EXISTS area_ha                 NUMERIC(12,4),
    ADD COLUMN IF NOT EXISTS classe_imovel           TEXT,
    ADD COLUMN IF NOT EXISTS distancia_sede_km       NUMERIC(8,2),
    ADD COLUMN IF NOT EXISTS distancia_asfalto_km    NUMERIC(8,2),
    ADD COLUMN IF NOT EXISTS tempo_posse_anos        INTEGER,
    ADD COLUMN IF NOT EXISTS renda_familiar          NUMERIC(12,2),
    ADD COLUMN IF NOT EXISTS funcao_publica          BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS possui_imovel_rural     BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS deleted_at              TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS criado_em               TIMESTAMPTZ DEFAULT NOW();

UPDATE projetos
SET criado_em = COALESCE(criado_em, created_at, NOW())
WHERE criado_em IS NULL;

ALTER TABLE projetos
    ALTER COLUMN criado_em SET DEFAULT NOW();

ALTER TABLE clientes
    ADD COLUMN IF NOT EXISTS cpf                     TEXT,
    ADD COLUMN IF NOT EXISTS rg                      TEXT,
    ADD COLUMN IF NOT EXISTS estado_civil            TEXT,
    ADD COLUMN IF NOT EXISTS profissao               TEXT,
    ADD COLUMN IF NOT EXISTS endereco                TEXT,
    ADD COLUMN IF NOT EXISTS endereco_numero         TEXT,
    ADD COLUMN IF NOT EXISTS municipio               TEXT,
    ADD COLUMN IF NOT EXISTS estado                  TEXT,
    ADD COLUMN IF NOT EXISTS setor                   TEXT,
    ADD COLUMN IF NOT EXISTS cep                     TEXT,
    ADD COLUMN IF NOT EXISTS conjuge_nome            TEXT,
    ADD COLUMN IF NOT EXISTS conjuge_cpf             TEXT,
    ADD COLUMN IF NOT EXISTS formulario_ok           BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS formulario_em           TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS magic_link_expira       TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS criado_em               TIMESTAMPTZ DEFAULT NOW();

UPDATE clientes
SET cpf = COALESCE(cpf, cpf_cnpj)
WHERE cpf IS NULL
  AND cpf_cnpj IS NOT NULL;

UPDATE clientes
SET criado_em = COALESCE(criado_em, created_at, NOW())
WHERE criado_em IS NULL;

ALTER TABLE clientes
    ALTER COLUMN criado_em SET DEFAULT NOW();

ALTER TABLE pontos
    ADD COLUMN IF NOT EXISTS deleted_at              TIMESTAMPTZ;

ALTER TABLE pontos
    ALTER COLUMN coordenada DROP NOT NULL;

UPDATE pontos
SET criado_em = COALESCE(criado_em, created_at, NOW())
WHERE criado_em IS NULL;

UPDATE pontos
SET altitude_m = COALESCE(altitude_m, cota)
WHERE altitude_m IS NULL
  AND cota IS NOT NULL;

UPDATE pontos
SET lat = COALESCE(lat, ST_Y(coordenada)),
    lon = COALESCE(lon, ST_X(coordenada))
WHERE coordenada IS NOT NULL
  AND (lat IS NULL OR lon IS NULL);

ALTER TABLE pontos
    ALTER COLUMN criado_em SET DEFAULT NOW();

-- -----------------------------------------------------------------
-- 2. Estrutura de perímetros
-- -----------------------------------------------------------------

CREATE TABLE IF NOT EXISTS perimetros (
    id           UUID        DEFAULT gen_random_uuid() PRIMARY KEY,
    projeto_id   UUID        NOT NULL REFERENCES projetos(id) ON DELETE CASCADE,
    nome         TEXT        NOT NULL,
    tipo         TEXT        NOT NULL
                 CHECK (tipo IN ('original', 'editado', 'definitivo')),
    vertices_json JSONB      NOT NULL DEFAULT '[]'::jsonb,
    criado_em    TIMESTAMPTZ DEFAULT NOW(),
    deleted_at   TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_perimetros_projeto
    ON perimetros (projeto_id, tipo, criado_em DESC);

-- -----------------------------------------------------------------
-- 3. Views compatíveis com backend atual
-- -----------------------------------------------------------------

CREATE OR REPLACE VIEW vw_projetos_completo AS
SELECT
    p.id,
    p.nome,
    p.nome                     AS projeto_nome,
    p.cliente_id,
    p.status,
    p.zona_utm,
    p.srid,
    p.numero_job,
    p.municipio,
    p.estado,
    p.nome_imovel,
    p.comarca,
    p.matricula,
    p.area_ha,
    p.classe_imovel,
    p.distancia_sede_km,
    p.distancia_asfalto_km,
    p.tempo_posse_anos,
    p.renda_familiar,
    p.funcao_publica,
    p.possui_imovel_rural,
    p.created_at,
    p.criado_em,
    p.deleted_at,
    c.nome                     AS cliente_nome,
    c.telefone                 AS cliente_telefone,
    c.email                    AS cliente_email,
    c.municipio                AS cliente_municipio,
    c.estado                   AS cliente_estado
FROM projetos p
LEFT JOIN clientes c ON c.id = p.cliente_id
WHERE p.deleted_at IS NULL;

CREATE OR REPLACE VIEW vw_formulario_cliente AS
SELECT
    p.id                       AS projeto_id,
    p.nome                     AS projeto_nome,
    p.nome_imovel,
    p.municipio                AS imovel_municipio,
    p.estado                   AS imovel_estado,
    p.comarca,
    p.matricula,
    p.area_ha,
    c.id                       AS cliente_id,
    c.nome                     AS cliente_nome,
    COALESCE(c.cpf, c.cpf_cnpj) AS cliente_cpf,
    c.rg                       AS cliente_rg,
    c.estado_civil,
    c.profissao,
    c.telefone,
    c.email,
    c.endereco,
    c.endereco_numero,
    c.municipio                AS cliente_municipio,
    c.estado                   AS cliente_estado,
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

CREATE OR REPLACE VIEW vw_pontos_geo AS
SELECT
    p.id,
    p.projeto_id,
    p.nome,
    COALESCE(p.altitude_m, p.cota) AS altitude_m,
    p.descricao,
    p.codigo,
    COALESCE(p.lon, ST_X(p.coordenada)) AS lon,
    COALESCE(p.lat, ST_Y(p.coordenada)) AS lat,
    p.deleted_at,
    p.criado_em
FROM pontos p
WHERE p.deleted_at IS NULL;

CREATE OR REPLACE VIEW vw_pontos_utm AS
SELECT
    p.id,
    p.projeto_id,
    p.nome,
    p.norte                    AS norte_utm,
    p.este                     AS este_utm,
    COALESCE(p.altitude_m, p.cota) AS altitude_m,
    p.codigo,
    p.descricao,
    COALESCE(p.lat, ST_Y(p.coordenada)) AS latitude,
    COALESCE(p.lon, ST_X(p.coordenada)) AS longitude,
    p.deleted_at,
    p.criado_em,
    pr.zona_utm
FROM pontos p
JOIN projetos pr ON pr.id = p.projeto_id
WHERE p.deleted_at IS NULL
  AND pr.deleted_at IS NULL;
