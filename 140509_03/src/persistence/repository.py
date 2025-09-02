from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy.orm import Session

from common.models import Decision, TransactionRequest
from .models import TransactionORM, DecisionORM, Base


def init_db(session: Session) -> None:
    # Create tables if they don't exist
    engine = session.get_bind()
    Base.metadata.create_all(bind=engine)


def persist_transaction_and_decision(
    session: Session,
    tx: TransactionRequest,
    decision: Decision,
    risk_score: int,
    explanation: dict | None = None,
) -> str:
    tx_id = tx.transactionId or str(uuid.uuid4())

    tx_row = TransactionORM(
        transaction_id=uuid.UUID(tx_id),
        customer_id=tx.customerId,
        amount=tx.amount,
        currency=tx.currency,
        merchant_id=tx.merchantId,
        timestamp=tx.timestamp,
        channel=tx.channel.value,
        latitude=tx.location.latitude if tx.location else None,
        longitude=tx.location.longitude if tx.location else None,
        device_fingerprint=tx.deviceFingerprint,
    )
    # Upsert transaction first and flush to satisfy FK constraint ordering
    session.merge(tx_row)
    session.flush()

    dec_row = DecisionORM(
        transaction_id=uuid.UUID(tx_id),
        decision=decision.value,
        risk_score=risk_score,
        explanation=explanation,
    )
    session.merge(dec_row)
    session.flush()

    return tx_id
def get_recent_decisions(session: Session, limit: int = 20):
    q = (
        session.query(DecisionORM, TransactionORM)
        .join(TransactionORM, DecisionORM.transaction_id == TransactionORM.transaction_id)
        .order_by(DecisionORM.created_at.desc())
        .limit(limit)
    )
    rows = []
    for dec, tx in q.all():
        rows.append(
            {
                "decision": dec.decision,
                "riskScore": int(dec.risk_score),
                "explanation": dec.explanation or {},
                "customerId": tx.customer_id,
                "amount": float(tx.amount),
                "currency": tx.currency,
                "merchantId": tx.merchant_id,
                "timestamp": tx.timestamp.isoformat(),
            }
        )
    return rows
