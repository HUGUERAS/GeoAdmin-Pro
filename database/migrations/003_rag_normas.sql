-- =================================================================
-- GeoAdmin Pro — Migration 003: RAG Normas INCRA
-- Cria tabela para armazenar chunks das normas INCRA com embeddings
-- vetoriais (pgvector) para busca semântica.
-- =================================================================

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS normas_chunks (
    id         UUID    DEFAULT gen_random_uuid() PRIMARY KEY,
    fonte      TEXT    NOT NULL,   -- ex: "Norma Técnica 3ª Ed., Art. 12"
    documento  TEXT    NOT NULL,   -- ex: "norma_tecnica_3ed" | "lei_13465" | "manual_sigef"
    pagina     INTEGER,
    texto      TEXT    NOT NULL,
    embedding  VECTOR(1024),       -- dimensão do voyage-3 (Anthropic)
    criado_em  TIMESTAMPTZ DEFAULT NOW()
);

-- Índice IVFFlat para busca por similaridade coseno
-- lists=100 é adequado para corpus pequeno (~200-400 chunks)
CREATE INDEX IF NOT EXISTS idx_normas_embedding
    ON normas_chunks USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

COMMENT ON TABLE normas_chunks IS
    'Chunks das normas INCRA indexados com embeddings voyage-3. '
    'Alimentado pelo script backend/scripts/indexar_normas.py.';

-- Verificação
SELECT COUNT(*) AS total_chunks FROM normas_chunks;
