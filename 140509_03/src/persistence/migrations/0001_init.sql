-- Initial schema for MVP
CREATE TABLE IF NOT EXISTS transactions (
    transaction_id UUID PRIMARY KEY,
    customer_id VARCHAR(50) NOT NULL,
    amount NUMERIC(15,2) NOT NULL,
    currency CHAR(3) NOT NULL,
    merchant_id VARCHAR(50) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    channel VARCHAR(20) NOT NULL,
    latitude NUMERIC(10,8),
    longitude NUMERIC(11,8),
    device_fingerprint VARCHAR(256),
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_transactions_customer_id ON transactions (customer_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_transactions_merchant_id ON transactions (merchant_id, timestamp DESC);

CREATE TABLE IF NOT EXISTS decisions (
    transaction_id UUID PRIMARY KEY,
    decision VARCHAR(20) NOT NULL,
    risk_score INTEGER NOT NULL,
    explanation JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    CONSTRAINT fk_decisions_tx FOREIGN KEY (transaction_id) REFERENCES transactions(transaction_id)
);

-- Ensure explanation column exists if table already created
ALTER TABLE decisions ADD COLUMN IF NOT EXISTS explanation JSONB;
