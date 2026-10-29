-- VaultGuard transaction schema for Aiven MySQL.
-- The backend can create this table automatically at /api/database/status
-- when all MYSQL_* environment variables are configured.

CREATE TABLE IF NOT EXISTS transactions (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    transaction_id VARCHAR(100) NOT NULL UNIQUE,
    amount_inr DECIMAL(15,2) NOT NULL DEFAULT 0,
    sender_id VARCHAR(100),
    receiver_id VARCHAR(100),
    channel VARCHAR(50),
    segment VARCHAR(100),
    risk_score DECIMAL(6,2),
    risk_category VARCHAR(50),
    decision VARCHAR(50),
    transaction_status VARCHAR(50),
    transaction_timestamp DATETIME,
    reasons JSON NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_txn_timestamp (transaction_timestamp),
    INDEX idx_txn_risk_category (risk_category)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
