from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone

from sqlalchemy import create_engine, text


def main() -> int:
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("DATABASE_URL not set; nothing to seed.")
        return 0
    engine = create_engine(db_url)
    tx_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO transactions (
                    transaction_id, customer_id, amount, currency, merchant_id,
                    timestamp, channel, created_at
                ) VALUES (
                    :transaction_id, :customer_id, :amount, :currency, :merchant_id,
                    :timestamp, :channel, :created_at
                ) ON CONFLICT (transaction_id) DO NOTHING
                """
            ),
            dict(
                transaction_id=tx_id,
                customer_id="SEED_CUST",
                amount=42.00,
                currency="USD",
                merchant_id="SEED_MERCHANT",
                timestamp=now,
                channel="CARD",
                created_at=now,
            ),
        )
        conn.execute(
            text(
                """
                INSERT INTO decisions (transaction_id, decision, risk_score, created_at)
                VALUES (:transaction_id, :decision, :risk_score, :created_at)
                ON CONFLICT (transaction_id) DO NOTHING
                """
            ),
            dict(
                transaction_id=tx_id,
                decision="APPROVE",
                risk_score=123,
                created_at=now,
            ),
        )
    print("Seed data inserted.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

