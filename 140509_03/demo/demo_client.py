from __future__ import annotations

import json
import time
import uuid
from datetime import datetime, timezone
from urllib.request import Request, urlopen


API = "http://127.0.0.1:8000/api/v1/transactions"


def post(tx: dict) -> dict:
    data = json.dumps(tx).encode("utf-8")
    req = Request(API, data=data, headers={"Content-Type": "application/json"})
    with urlopen(req, timeout=5) as r:
        return json.loads(r.read().decode("utf-8"))


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def scenario_baseline(customer: str = "C_BASE") -> None:
    print("-- Baseline normal transactions")
    for amt in (20, 25, 19, 22, 21):
        body = {
            "transactionId": str(uuid.uuid4()),
            "customerId": customer,
            "amount": amt,
            "currency": "USD",
            "merchantId": "M_GENERAL",
            "timestamp": now_iso(),
            "channel": "CARD",
        }
        print(post(body))
        time.sleep(0.2)


def scenario_amount_spike(customer: str = "C_SPIKE") -> None:
    print("-- Amount spike to trigger z-score and rules")
    for amt in (15, 16, 14, 15, 5000):
        body = {
            "transactionId": str(uuid.uuid4()),
            "customerId": customer,
            "amount": amt,
            "currency": "USD",
            "merchantId": "M_ELECTRONICS",
            "timestamp": now_iso(),
            "channel": "CARD",
        }
        print(post(body))
        time.sleep(0.2)


def scenario_high_velocity(customer: str = "C_VEL") -> None:
    print("-- High velocity burst to trigger velocity rule")
    for _ in range(12):
        body = {
            "transactionId": str(uuid.uuid4()),
            "customerId": customer,
            "amount": 5.0,
            "currency": "USD",
            "merchantId": "M_MICRO",
            "timestamp": now_iso(),
            "channel": "CARD",
        }
        print(post(body))
        time.sleep(0.05)


def scenario_large_cash(customer: str = "C_CASH") -> None:
    print("-- Large cash transaction to trigger AML rule")
    body = {
        "transactionId": str(uuid.uuid4()),
        "customerId": customer,
        "amount": 15000.0,
        "currency": "USD",
        "merchantId": "ATM001",
        "timestamp": now_iso(),
        "channel": "CARD",
    }
    print(post(body))


def main() -> int:
    scenario_baseline()
    scenario_amount_spike()
    scenario_high_velocity()
    scenario_large_cash()
    print("Done. Open http://127.0.0.1:8000/demo")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

