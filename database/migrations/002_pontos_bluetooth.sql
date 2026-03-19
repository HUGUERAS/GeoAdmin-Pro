-- =================================================================
-- GeoAdmin Pro — Migration 002: Pontos Bluetooth
-- Adiciona colunas necessárias para coleta GNSS via Bluetooth
-- e sincronização offline.
-- =================================================================

ALTER TABLE pontos
    ADD COLUMN IF NOT EXISTS lat         NUMERIC(11,8),
    ADD COLUMN IF NOT EXISTS lon         NUMERIC(11,8),
    ADD COLUMN IF NOT EXISTS norte       NUMERIC(12,4),
    ADD COLUMN IF NOT EXISTS este        NUMERIC(12,4),
    ADD COLUMN IF NOT EXISTS cota        NUMERIC(10,4),
    ADD COLUMN IF NOT EXISTS altitude_m  NUMERIC(10,4),
    ADD COLUMN IF NOT EXISTS codigo      TEXT DEFAULT 'TP',
    ADD COLUMN IF NOT EXISTS status_gnss TEXT DEFAULT 'Fixo',
    ADD COLUMN IF NOT EXISTS satelites   SMALLINT DEFAULT 0,
    ADD COLUMN IF NOT EXISTS pdop        NUMERIC(5,2),
    ADD COLUMN IF NOT EXISTS sigma_e     NUMERIC(7,4),
    ADD COLUMN IF NOT EXISTS sigma_n     NUMERIC(7,4),
    ADD COLUMN IF NOT EXISTS sigma_u     NUMERIC(7,4),
    ADD COLUMN IF NOT EXISTS origem      TEXT DEFAULT 'gnss',
    ADD COLUMN IF NOT EXISTS local_id    UUID,
    ADD COLUMN IF NOT EXISTS coletado_em TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS criado_em   TIMESTAMPTZ DEFAULT NOW();

-- Índice único para dedup no sync offline
CREATE UNIQUE INDEX IF NOT EXISTS idx_pontos_local_id
    ON pontos (local_id)
    WHERE local_id IS NOT NULL;

-- Verificação
SELECT COUNT(*) AS total_pontos FROM pontos;
