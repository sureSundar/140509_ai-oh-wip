from datetime import datetime, timezone
import sys
from pathlib import Path

# Add src to import path
sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from common.models import TransactionRequest, TransactionChannel  # type: ignore
from decision_service.service import DecisionService  # type: ignore


def _tx(amount: float, customer: str = "C1") -> TransactionRequest:
    return TransactionRequest(
        customerId=customer,
        amount=amount,
        currency="USD",
        merchantId="M1",
        timestamp=datetime.now(timezone.utc),
        channel=TransactionChannel.CARD,
    )


def test_low_amount_approves():
    svc = DecisionService()
    d, score, _, _ = svc.decide(_tx(10.0))
    assert d.value in ("APPROVE", "REVIEW")
    assert 0 <= score <= 1000


def test_high_velocity_increases_risk():
    svc = DecisionService()
    # generate many small tx quickly to drive velocity rule
    for _ in range(12):
        svc.decide(_tx(5.0, customer="C2"))
    d, score, _, _ = svc.decide(_tx(5.0, customer="C2"))
    assert score >= 350
