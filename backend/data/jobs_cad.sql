-- DDL SQL: GeoAdmin Pro - Tabela de Rastreabilidade de Jobs CAD (VERTEXROSEA)
-- =========================================================================
-- Execute este script no SQL Editor do seu dashboard Supabase.

CREATE TABLE IF NOT EXISTS public.jobs_cad (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    projeto_id UUID REFERENCES public.projetos(id) ON DELETE CASCADE,
    arquivo_id_origem UUID REFERENCES public.arquivos_projeto(id) ON DELETE SET NULL,
    vertex_job_id VARCHAR(255) NOT NULL UNIQUE,
    tipo_job VARCHAR(50) NOT NULL, -- 'validar_dxf', 'extrair_pontos', 'parse_txt', 'freecad'
    status VARCHAR(50) NOT NULL DEFAULT 'pending', -- pending, running, done, failed
    warnings TEXT[],
    erro TEXT,
    payload_json JSONB,
    artefatos_json JSONB,
    criado_em TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    atualizado_em TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    concluido_em TIMESTAMP WITH TIME ZONE
);

-- Indexação para polling e auditoria de alta performance
CREATE INDEX IF NOT EXISTS idx_jobs_cad_status ON public.jobs_cad(status);
CREATE INDEX IF NOT EXISTS idx_jobs_cad_projeto ON public.jobs_cad(projeto_id);
CREATE INDEX IF NOT EXISTS idx_jobs_cad_arquivo_origem ON public.jobs_cad(arquivo_id_origem);
