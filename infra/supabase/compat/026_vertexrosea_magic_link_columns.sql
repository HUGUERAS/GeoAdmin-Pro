-- GeoAdmin Pro compat: magic link columns on the current Vertex-style schema.
-- Safe to rerun. Only adds nullable/defaulted columns and indexes.

ALTER TABLE IF EXISTS public.projeto_clientes
    ADD COLUMN IF NOT EXISTS recebe_magic_link boolean NOT NULL DEFAULT true,
    ADD COLUMN IF NOT EXISTS ordem integer NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS magic_link_token text,
    ADD COLUMN IF NOT EXISTS magic_link_expira timestamptz,
    ADD COLUMN IF NOT EXISTS atualizado_em timestamptz NOT NULL DEFAULT now(),
    ADD COLUMN IF NOT EXISTS deleted_at timestamptz;

UPDATE public.projeto_clientes
SET recebe_magic_link = true
WHERE recebe_magic_link IS DISTINCT FROM true;

CREATE UNIQUE INDEX IF NOT EXISTS uq_projeto_clientes_magic_link
    ON public.projeto_clientes (magic_link_token)
    WHERE deleted_at IS NULL AND magic_link_token IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_projeto_clientes_projeto_compat
    ON public.projeto_clientes (projeto_id, ordem)
    WHERE deleted_at IS NULL;

ALTER TABLE IF EXISTS public.clientes
    ADD COLUMN IF NOT EXISTS nome text,
    ADD COLUMN IF NOT EXISTS cpf text,
    ADD COLUMN IF NOT EXISTS rg text,
    ADD COLUMN IF NOT EXISTS estado_civil text,
    ADD COLUMN IF NOT EXISTS profissao text,
    ADD COLUMN IF NOT EXISTS telefone text,
    ADD COLUMN IF NOT EXISTS email text,
    ADD COLUMN IF NOT EXISTS conjuge_nome text,
    ADD COLUMN IF NOT EXISTS conjuge_cpf text,
    ADD COLUMN IF NOT EXISTS endereco text,
    ADD COLUMN IF NOT EXISTS endereco_numero text,
    ADD COLUMN IF NOT EXISTS municipio text,
    ADD COLUMN IF NOT EXISTS cep text,
    ADD COLUMN IF NOT EXISTS formulario_ok boolean NOT NULL DEFAULT false,
    ADD COLUMN IF NOT EXISTS formulario_em timestamptz,
    ADD COLUMN IF NOT EXISTS magic_link_token text,
    ADD COLUMN IF NOT EXISTS magic_link_expira timestamptz,
    ADD COLUMN IF NOT EXISTS deleted_at timestamptz;

UPDATE public.clientes
SET
    nome = COALESCE(nome, nome_razao),
    cpf = COALESCE(cpf, cpf_cnpj),
    telefone = COALESCE(telefone, contato->>'telefone'),
    email = COALESCE(email, contato->>'email')
WHERE nome IS NULL
   OR cpf IS NULL
   OR telefone IS NULL
   OR email IS NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uq_clientes_magic_link
    ON public.clientes (magic_link_token)
    WHERE deleted_at IS NULL AND magic_link_token IS NOT NULL;

ALTER TABLE IF EXISTS public.eventos_magic_link
    ADD COLUMN IF NOT EXISTS projeto_cliente_id uuid,
    ADD COLUMN IF NOT EXISTS area_id uuid,
    ADD COLUMN IF NOT EXISTS cliente_id uuid,
    ADD COLUMN IF NOT EXISTS tipo_evento text NOT NULL DEFAULT 'gerado',
    ADD COLUMN IF NOT EXISTS canal text NOT NULL DEFAULT 'whatsapp',
    ADD COLUMN IF NOT EXISTS token text,
    ADD COLUMN IF NOT EXISTS autor text,
    ADD COLUMN IF NOT EXISTS expira_em timestamptz,
    ADD COLUMN IF NOT EXISTS payload_json jsonb NOT NULL DEFAULT '{}'::jsonb,
    ADD COLUMN IF NOT EXISTS criado_em timestamptz NOT NULL DEFAULT now(),
    ADD COLUMN IF NOT EXISTS deleted_at timestamptz;

CREATE INDEX IF NOT EXISTS idx_eventos_magic_link_projeto_compat
    ON public.eventos_magic_link (projeto_id, criado_em DESC)
    WHERE deleted_at IS NULL;

ALTER TABLE IF EXISTS public.projetos
    ADD COLUMN IF NOT EXISTS nome_imovel text,
    ADD COLUMN IF NOT EXISTS comarca text,
    ADD COLUMN IF NOT EXISTS matricula text,
    ADD COLUMN IF NOT EXISTS tempo_posse_anos integer,
    ADD COLUMN IF NOT EXISTS endereco_imovel text,
    ADD COLUMN IF NOT EXISTS endereco_imovel_numero text,
    ADD COLUMN IF NOT EXISTS cep_imovel text;

ALTER TABLE IF EXISTS public.confrontantes
    ADD COLUMN IF NOT EXISTS lado text,
    ADD COLUMN IF NOT EXISTS nome text,
    ADD COLUMN IF NOT EXISTS cpf text,
    ADD COLUMN IF NOT EXISTS nome_imovel text,
    ADD COLUMN IF NOT EXISTS matricula text,
    ADD COLUMN IF NOT EXISTS tipo text,
    ADD COLUMN IF NOT EXISTS origem text,
    ADD COLUMN IF NOT EXISTS deleted_at timestamptz;

CREATE INDEX IF NOT EXISTS idx_confrontantes_projeto_compat
    ON public.confrontantes (projeto_id)
    WHERE deleted_at IS NULL;
