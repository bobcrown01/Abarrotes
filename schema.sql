-- =========================
-- CATEGORÍAS Y PRODUCTOS
-- =========================

CREATE TABLE categories (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(100) NOT NULL
);

CREATE TABLE products (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(150) NOT NULL,
    barcode     VARCHAR(50),
    sku         VARCHAR(50),
    category_id INTEGER REFERENCES categories(id),
    price       NUMERIC(12,2) NOT NULL,
    cost        NUMERIC(12,2),
    unit        VARCHAR(20),
    is_active   BOOLEAN DEFAULT TRUE
);

-- Un código de barras no se puede repetir (los productos sin código sí)
CREATE UNIQUE INDEX products_barcode_key ON products (barcode) WHERE barcode IS NOT NULL;

-- =========================
-- INVENTARIO
-- =========================

CREATE TABLE inventory (
    id          SERIAL PRIMARY KEY,
    product_id  INTEGER NOT NULL UNIQUE REFERENCES products(id),
    quantity    NUMERIC(14,3) DEFAULT 0,
    min_stock   NUMERIC(14,3) DEFAULT 0,
    max_stock   NUMERIC(14,3)
);

CREATE TABLE inventory_movements (
    id          SERIAL PRIMARY KEY,
    product_id  INTEGER NOT NULL REFERENCES products(id),
    type        VARCHAR(20) NOT NULL, -- entrada / salida / ajuste
    quantity    NUMERIC(14,3) NOT NULL,
    reason      VARCHAR(100),
    created_at  TIMESTAMP NOT NULL DEFAULT NOW(),
    user_id     INTEGER
);

-- =========================
-- CLIENTES
-- =========================

CREATE TABLE customers (
    id            SERIAL PRIMARY KEY,
    name          VARCHAR(150) NOT NULL,
    phone         VARCHAR(30),
    email         VARCHAR(100),
    credit_limit  NUMERIC(12,2) DEFAULT 0,
    balance       NUMERIC(12,2) DEFAULT 0,
    created_at    TIMESTAMP NOT NULL DEFAULT NOW()
);

-- =========================
-- VENTAS
-- =========================

CREATE TABLE sales (
    id           SERIAL PRIMARY KEY,
    folio        VARCHAR(50) UNIQUE,
    customer_id  INTEGER REFERENCES customers(id),
    subtotal     NUMERIC(12,2) NOT NULL DEFAULT 0,
    discount     NUMERIC(12,2) NOT NULL DEFAULT 0,
    total        NUMERIC(12,2) NOT NULL DEFAULT 0,
    status       VARCHAR(20) NOT NULL DEFAULT 'pagada', -- pagada / pendiente / cancelada
    created_at   TIMESTAMP NOT NULL DEFAULT NOW(),
    user_id      INTEGER
);

CREATE TABLE sale_items (
    id           SERIAL PRIMARY KEY,
    sale_id      INTEGER NOT NULL REFERENCES sales(id) ON DELETE CASCADE,
    product_id   INTEGER NOT NULL REFERENCES products(id),
    qty          NUMERIC(14,3) NOT NULL,
    price        NUMERIC(12,2) NOT NULL,
    discount     NUMERIC(12,2) NOT NULL DEFAULT 0,
    subtotal     NUMERIC(12,2) NOT NULL
);

-- =========================
-- PAGOS
-- =========================

CREATE TABLE payments (
    id           SERIAL PRIMARY KEY,
    sale_id      INTEGER NOT NULL REFERENCES sales(id) ON DELETE CASCADE,
    method       VARCHAR(30) NOT NULL, -- efectivo, tarjeta, transferencia, crédito, monedero
    amount       NUMERIC(12,2) NOT NULL,
    received     NUMERIC(12,2),
    change       NUMERIC(12,2),
    reference    VARCHAR(100),
    created_at   TIMESTAMP NOT NULL DEFAULT NOW()
);

-- =========================
-- PROVEEDORES Y COMPRAS
-- =========================

CREATE TABLE suppliers (
    id        SERIAL PRIMARY KEY,
    name      VARCHAR(150) NOT NULL,
    phone     VARCHAR(30),
    email     VARCHAR(100)
);

CREATE TABLE purchases (
    id           SERIAL PRIMARY KEY,
    supplier_id  INTEGER REFERENCES suppliers(id),
    total        NUMERIC(12,2) NOT NULL DEFAULT 0,
    created_at   TIMESTAMP NOT NULL DEFAULT NOW(),
    user_id      INTEGER
);

CREATE TABLE purchase_items (
    id           SERIAL PRIMARY KEY,
    purchase_id  INTEGER NOT NULL REFERENCES purchases(id) ON DELETE CASCADE,
    product_id   INTEGER NOT NULL REFERENCES products(id),
    qty          NUMERIC(14,3) NOT NULL,
    cost         NUMERIC(12,2) NOT NULL
);

-- =========================
-- USUARIOS Y ROLES
-- =========================

CREATE TABLE roles (
    id        SERIAL PRIMARY KEY,
    name      VARCHAR(50) NOT NULL UNIQUE -- admin, cajero, supervisor
);

CREATE TABLE users (
    id             SERIAL PRIMARY KEY,
    username       VARCHAR(50) NOT NULL UNIQUE,
    password_hash  VARCHAR(255) NOT NULL,
    role_id        INTEGER REFERENCES roles(id),
    is_active      BOOLEAN DEFAULT TRUE
);

ALTER TABLE inventory_movements
    ADD CONSTRAINT inventory_movements_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id);

ALTER TABLE sales
    ADD CONSTRAINT sales_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id);

ALTER TABLE purchases
    ADD CONSTRAINT purchases_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id);

-- =========================
-- AUDITORÍA
-- =========================

CREATE TABLE audit_logs (
    id          SERIAL PRIMARY KEY,
    user_id     INTEGER REFERENCES users(id),
    action      VARCHAR(100) NOT NULL,
    description TEXT,
    created_at  TIMESTAMP NOT NULL DEFAULT NOW()
);
