-- =============================================================================
-- Sports Concierge Agent — Database Schema
-- =============================================================================
-- Run this in your Supabase project's SQL Editor BEFORE using the agent's
-- audit-logging feature.
--
--   supabase-db  →  SQL Editor  →  paste & run
-- =============================================================================

-- -------------------------------------------------------------------------
-- security_logs — immutable audit trail of Guard Agent decisions
-- -------------------------------------------------------------------------
-- Every file-scan verdict (proceed / halt) is logged here so you can:
--   * Prove that every file was evaluated before plan generation.
--   * Investigate security incidents post-mortem.
--   * Aggregate scores & reasons to tune YARA rules over time.
--   * Satisfy compliance requirements (SOC 2, ISO 27001).
-- -------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS security_logs (
    id          BIGINT          GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    created_at  TIMESTAMPTZ     NOT NULL DEFAULT now(),
    filename    TEXT            NOT NULL,
    status      TEXT            NOT NULL,   -- 'safe' | 'threat' | 'error'
    score       INTEGER         NOT NULL,   -- 0 (benign) … 100 (malicious)
    reason      TEXT            NOT NULL    -- human-readable verdict explanation
);

-- Speed up queries that filter by status or sort by recency.
CREATE INDEX IF NOT EXISTS idx_security_logs_status    ON security_logs (status);
CREATE INDEX IF NOT EXISTS idx_security_logs_created_at ON security_logs (created_at DESC);

COMMENT ON TABLE  security_logs IS 'Immutable audit trail of Guard Agent security-scan verdicts.';
COMMENT ON COLUMN security_logs.status  IS 'safe | threat | error';
COMMENT ON COLUMN security_logs.score   IS '0 = benign, 100 = malicious';
COMMENT ON COLUMN security_logs.reason  IS 'Human-readable explanation from SecurityScanner';
