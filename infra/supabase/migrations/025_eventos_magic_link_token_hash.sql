-- =================================================================
-- GeoAdmin Pro — Migration 025: hash para historico de magic links
-- Evita persistir token bruto em eventos_magic_link.
-- =================================================================

CREATE SCHEMA IF NOT EXISTS extensions;
CREATE EXTENSION IF NOT EXISTS pgcrypto WITH SCHEMA extensions;

ALTER TABLE IF EXISTS public.eventos_magic_link
    ADD COLUMN IF NOT EXISTS token_hash text;

CREATE OR REPLACE FUNCTION public.geoadmin_magic_link_token_sha256(valor text)
RETURNS text
LANGUAGE sql
STABLE
SET search_path = public, extensions
AS $$
    SELECT CASE
        WHEN valor IS NULL OR valor = '' THEN NULL
        ELSE encode(digest(valor, 'sha256'), 'hex')
    END
$$;

DO $$
BEGIN
    IF to_regclass('public.eventos_magic_link') IS NOT NULL THEN
        EXECUTE 'CREATE INDEX IF NOT EXISTS idx_eventos_magic_link_token_hash
            ON public.eventos_magic_link (token_hash)
            WHERE deleted_at IS NULL AND token_hash IS NOT NULL';
    END IF;
END $$;

DO $$
BEGIN
    IF to_regclass('public.eventos_magic_link') IS NOT NULL
       AND EXISTS (
           SELECT 1
           FROM information_schema.columns
           WHERE table_schema = 'public'
             AND table_name = 'eventos_magic_link'
             AND column_name = 'token'
       )
    THEN
        EXECUTE $cleanup$
            UPDATE public.eventos_magic_link
               SET token_hash = COALESCE(token_hash, public.geoadmin_magic_link_token_sha256(token)),
                   token = NULL
             WHERE token IS NOT NULL
        $cleanup$;
    END IF;
END $$;

UPDATE public.eventos_magic_link
   SET payload_json = payload_json - 'link' - 'magic_link' - 'magic_link_url' - 'url'
 WHERE (
           payload_json ? 'link'
        OR payload_json ? 'magic_link'
        OR payload_json ? 'magic_link_url'
        OR payload_json ? 'url'
       )
   AND (
           COALESCE(payload_json->>'link', '') ILIKE '%token=%'
        OR COALESCE(payload_json->>'magic_link', '') ILIKE '%token=%'
        OR COALESCE(payload_json->>'magic_link_url', '') ILIKE '%token=%'
        OR COALESCE(payload_json->>'url', '') ILIKE '%token=%'
       );

CREATE OR REPLACE FUNCTION public.geoadmin_eventos_magic_link_strip_token()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = public, extensions
AS $$
BEGIN
    IF NEW.token_hash IS NULL AND NEW.token IS NOT NULL THEN
        NEW.token_hash := public.geoadmin_magic_link_token_sha256(NEW.token);
    END IF;

    NEW.token := NULL;
    RETURN NEW;
END;
$$;

DO $$
BEGIN
    IF to_regclass('public.eventos_magic_link') IS NOT NULL
       AND EXISTS (
           SELECT 1
           FROM information_schema.columns
           WHERE table_schema = 'public'
             AND table_name = 'eventos_magic_link'
             AND column_name = 'token'
       )
    THEN
        DROP TRIGGER IF EXISTS trg_eventos_magic_link_strip_token ON public.eventos_magic_link;
        CREATE TRIGGER trg_eventos_magic_link_strip_token
            BEFORE INSERT OR UPDATE OF token, token_hash ON public.eventos_magic_link
            FOR EACH ROW
            EXECUTE FUNCTION public.geoadmin_eventos_magic_link_strip_token();
    END IF;
END $$;

COMMENT ON COLUMN public.eventos_magic_link.token_hash
    IS 'SHA-256 do token de magic link. Nao persistir token bruto no historico.';
