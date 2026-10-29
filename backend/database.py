"""Optional MySQL persistence for VaultGuard.

Configure MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD and MYSQL_DATABASE.
For Aiven TLS verification, set MYSQL_SSL_CA to the PEM certificate contents.
Without database settings the API continues to run in demo-only mode.
"""
import os
import ssl
from typing import Any, Dict, Iterable, Optional

import pymysql
from pymysql.cursors import DictCursor


def is_configured() -> bool:
    required = ("MYSQL_HOST", "MYSQL_PORT", "MYSQL_USER", "MYSQL_PASSWORD", "MYSQL_DATABASE")
    return all(os.getenv(name) for name in required)


def _connect():
    if not is_configured():
        raise RuntimeError("MySQL environment variables are not fully configured")

    ca_pem = os.getenv("MYSQL_SSL_CA", "").strip()
    tls_context = ssl.create_default_context(cadata=ca_pem) if ca_pem else ssl.create_default_context()
    tls_context.check_hostname = True
    tls_context.verify_mode = ssl.CERT_REQUIRED

    return pymysql.connect(
        host=os.environ["MYSQL_HOST"],
        port=int(os.environ["MYSQL_PORT"]),
        user=os.environ["MYSQL_USER"],
        password=os.environ["MYSQL_PASSWORD"],
        database=os.environ["MYSQL_DATABASE"],
        charset="utf8mb4",
        cursorclass=DictCursor,
        connect_timeout=8,
        read_timeout=10,
        write_timeout=10,
        autocommit=False,
        ssl=tls_context,
    )


def ensure_schema() -> None:
    """Create the transaction table if it does not exist."""
    with _connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute("""
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
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)
        connection.commit()


def persist_transactions(rows: Iterable[Dict[str, Any]]) -> int:
    """Idempotently upsert synthetic/demo transaction rows."""
    batch = []
    for row in rows:
        stamp = row.get("timestamp")
        if isinstance(stamp, str):
            stamp = stamp.strip() or None
        batch.append((
            str(row.get("transaction_id") or row.get("id")),
            float(row.get("amount_inr", row.get("amount", 0)) or 0),
            row.get("sender_id"),
            row.get("beneficiary_id") or row.get("receiver_id"),
            row.get("channel"),
            row.get("segment"),
            row.get("risk_score"),
            row.get("risk_category"),
            row.get("decision"),
            row.get("status"),
            stamp,
            __import__("json").dumps(row.get("reasons", []), ensure_ascii=False),
        ))
    if not batch:
        return 0

    with _connect() as connection:
        with connection.cursor() as cursor:
            cursor.executemany("""
                INSERT INTO transactions
                    (transaction_id, amount_inr, sender_id, receiver_id, channel, segment,
                     risk_score, risk_category, decision, transaction_status,
                     transaction_timestamp, reasons)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    amount_inr=VALUES(amount_inr), sender_id=VALUES(sender_id),
                    receiver_id=VALUES(receiver_id), channel=VALUES(channel),
                    segment=VALUES(segment), risk_score=VALUES(risk_score),
                    risk_category=VALUES(risk_category), decision=VALUES(decision),
                    transaction_status=VALUES(transaction_status),
                    transaction_timestamp=VALUES(transaction_timestamp), reasons=VALUES(reasons)
            """, batch)
        connection.commit()
    return len(batch)


def get_status() -> Dict[str, Any]:
    if not is_configured():
        return {"configured": False, "connected": False, "message": "MySQL environment variables are not configured"}
    try:
        with _connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT DATABASE() AS database_name, COUNT(*) AS transaction_count FROM transactions")
                row = cursor.fetchone()
        return {
            "configured": True,
            "connected": True,
            "database": row["database_name"],
            "transaction_count": int(row["transaction_count"]),
        }
    except Exception as exc:
        # Return a useful error class, never credentials or connection strings.
        return {"configured": True, "connected": False, "error": type(exc).__name__, "message": str(exc)[:240]}
