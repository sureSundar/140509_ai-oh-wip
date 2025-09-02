from __future__ import annotations

import math
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Dict, List

from common.models import TransactionRequest


class InMemoryFeatureStore:
    """Very small in-memory feature store for demo purposes.

    Maintains rolling aggregates per customer for velocity and average amounts.
    """

    def __init__(self) -> None:
        self._tx_times: dict[str, List[datetime]] = defaultdict(list)
        self._amounts_7d: dict[str, List[float]] = defaultdict(list)

    def observe(self, tx: TransactionRequest) -> None:
        self._tx_times[tx.customerId].append(tx.timestamp)
        # Keep only last 7 days amounts
        self._amounts_7d[tx.customerId].append(float(tx.amount))
        cutoff = datetime.now(timezone.utc) - timedelta(days=7)
        self._tx_times[tx.customerId] = [t for t in self._tx_times[tx.customerId] if t >= cutoff]
        self._amounts_7d[tx.customerId] = self._amounts_7d[tx.customerId][-1000:]

    def get_features(self, customer_id: str) -> Dict[str, float]:
        now = datetime.now(timezone.utc)
        last_hour = now - timedelta(hours=1)
        txs_last_hour = [t for t in self._tx_times[customer_id] if t >= last_hour]
        velocity_1h = len(txs_last_hour)

        amounts = self._amounts_7d[customer_id]
        avg_amount_7d = sum(amounts) / len(amounts) if amounts else 0.0
        std_amount_7d = math.sqrt(
            sum((a - avg_amount_7d) ** 2 for a in amounts) / len(amounts)
        ) if amounts else 0.0

        return {
            "velocity_score_1h": float(velocity_1h),
            "avg_transaction_amount_7d": float(avg_amount_7d),
            "std_transaction_amount_7d": float(std_amount_7d),
        }
