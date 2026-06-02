-- DDL SQL: GeoAdmin Pro - Tabela de Rastreabilidade de Jobs CAD (VERTEXROSEA)
-- =========================================================================
-- Execute este script no SQL Editor do seu dashboard Supabase.

CREATE TABLE IF NOT EXISTS public.jobs_cad (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    projeto_id UUID REFERENCES public.projetos(id) ON DELETE CASCADE,
    vertex_job_id VARCHAR(255) NOT NULL UNIQUE,
    status VARCHAR(50) NOT NULL DEFAULT 'pending', -- pending, running, done, failed
    formato_saida VARCHAR(50)[] DEFAULT ARRAY['dxf', 'fcstd'],
    warnings TEXT[],
    criado_em TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    atualizado_em TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Indexação para polling e auditoria de alta performance
CREATE INDEX IF NOT EXISTS idx_jobs_cad_status ON public.jobs_cad(status);
CREATE INDEX IF NOT EXISTS idx_jobs_cad_projeto ON public.jobs_cad(projeto_id);
