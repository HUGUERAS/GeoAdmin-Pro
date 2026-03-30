-- ================================================================
-- GeoAdmin Pro — Migration 018: enderecos residencial e do imovel
-- Separa endereco do cliente da localizacao/endereco do imovel.
-- ================================================================

ALTER TABLE projetos
    ADD COLUMN IF NOT EXISTS endereco_imovel TEXT,
    ADD COLUMN IF NOT EXISTS endereco_imovel_numero TEXT,
    ADD COLUMN IF NOT EXISTS cep_imovel TEXT;

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
    c.estado                   AS cliente_estado,
    p.endereco_imovel,
    p.endereco_imovel_numero,
    p.cep_imovel
FROM projetos p
LEFT JOIN clientes c ON c.id = p.cliente_id
LEFT JOIN (
    SELECT pontos.projeto_id, count(*) AS total_pontos
    FROM pontos
    WHERE pontos.coordenada IS NOT NULL
    GROUP BY pontos.projeto_id
) pt ON pt.projeto_id = p.id
WHERE p.deleted_at IS NULL;

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
    COALESCE(c.cpf, c.cpf_cnpj) AS cliente_cpf,
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
    c.magic_link_expira,
    p.endereco_imovel,
    p.endereco_imovel_numero,
    p.cep_imovel
FROM projetos p
JOIN clientes c ON c.id = p.cliente_id
WHERE p.deleted_at IS NULL;
