-- Agrega los abonos de clientes a una base que ya existe.
-- Uso: docker compose exec -T db psql -U app_user -d abarrotes < migrations/003_customer_payments.sql

CREATE TABLE IF NOT EXISTS customer_payments (
    id           SERIAL PRIMARY KEY,
    customer_id  INTEGER NOT NULL REFERENCES customers(id),
    amount       NUMERIC(12,2) NOT NULL,
    method       VARCHAR(30) NOT NULL,
    user_id      INTEGER REFERENCES users(id),
    created_at   TIMESTAMP NOT NULL DEFAULT NOW()
);
