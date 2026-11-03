-- Agrega la tabla del login a una base que ya existe.
-- schema.sql solo corre con el volumen vacío; una instalación nueva no necesita esto.
-- Uso: docker compose exec -T db psql -U app_user -d abarrotes < migrations/001_user_sessions.sql

CREATE TABLE IF NOT EXISTS user_sessions (
    token_hash  VARCHAR(64) PRIMARY KEY,
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    expires_at  TIMESTAMP NOT NULL
);
