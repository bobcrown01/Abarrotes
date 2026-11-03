-- Agrega los turnos de caja a una base que ya existe.
-- Uso: docker compose exec -T db psql -U app_user -d abarrotes < migrations/002_cash_sessions.sql

CREATE TABLE IF NOT EXISTS cash_sessions (
    id              SERIAL PRIMARY KEY,
    opened_by       INTEGER REFERENCES users(id),
    opened_at       TIMESTAMP NOT NULL DEFAULT NOW(),
    opening_amount  NUMERIC(12,2) NOT NULL,
    closed_by       INTEGER REFERENCES users(id),
    closed_at       TIMESTAMP,
    counted_amount  NUMERIC(12,2),
    expected_cash   NUMERIC(12,2),
    sales_total     NUMERIC(12,2),
    notes           VARCHAR(200)
);

-- Solo puede haber una caja abierta
CREATE UNIQUE INDEX IF NOT EXISTS cash_sessions_one_open
    ON cash_sessions ((closed_at IS NULL)) WHERE closed_at IS NULL;
