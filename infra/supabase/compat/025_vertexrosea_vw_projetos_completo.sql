-- Compatibility view for GeoAdmin-Pro backend running against the current
-- Vertex-style Supabase schema.

CREATE OR REPLACE VIEW public.vw_projetos_completo
WITH (security_invoker = true)
AS
SELECT
    p.id,
    pc.cliente_id,
    p.nome,
    p.nome AS projeto_nome,
    NULLIF(p.metadados ->> 'numero_job', '') AS numero_job,
    COALESCE(
        NULLIF(p.metadados ->> 'nome_imovel', ''),
        NULLIF(c.endereco_imovel_rural ->> 'nome_imovel', '')
    ) AS nome_imovel,
    p.municipio,
    p.uf::text AS estado,
    p.uf::text AS uf,
    COALESCE(NULLIF(p.metadados ->> 'zona_utm', ''), '23S') AS zona_utm,
    p.status::text AS status,
    NULLIF(p.metadados ->> 'tipo_processo', '') AS tipo_processo,
    p.progresso,
    p.proxima_etapa,
    p.owner_id,
    p.metadados,
    p.criado_em,
    p.atualizado_em,
    c.nome_razao AS cliente_nome,
    c.cpf_cnpj AS cliente_cpf,
    c.contato ->> 'telefone' AS cliente_telefone,
    c.contato ->> 'email' AS cliente_email,
    c.tipo_pessoa AS cliente_tipo_pessoa,
    c.contato AS cliente_contato,
    c.endereco_correspondencia AS cliente_endereco_correspondencia,
    c.endereco_imovel_rural AS cliente_endereco_imovel_rural,
    c.metadados AS cliente_metadados
FROM public.projetos p
LEFT JOIN LATERAL (
    SELECT pc_inner.*
    FROM public.projeto_clientes pc_inner
    WHERE pc_inner.projeto_id = p.id
    ORDER BY
        pc_inner.principal DESC NULLS LAST,
        (pc_inner.papel::text = 'principal') DESC,
        pc_inner.criado_em ASC
    LIMIT 1
) pc ON true
LEFT JOIN public.clientes c ON c.id = pc.cliente_id;

COMMENT ON VIEW public.vw_projetos_completo IS
    'Compatibility view used by GeoAdmin-Pro endpoints over the Vertex-style schema.';

GRANT SELECT ON public.vw_projetos_completo TO anon, authenticated, service_role;

NOTIFY pgrst, 'reload schema';
