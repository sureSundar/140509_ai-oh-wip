from __future__ import annotations

from collections import deque
from dataclasses import dataclass, asdict
from typing import Deque, Dict, Any, List


@dataclass
class DecisionRecord:
    decision: str
    riskScore: int
    explanation: Dict[str, Any]
    customerId: str
    amount: float
    currency: str
    merchantId: str
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class RecentCache:
    def __init__(self, capacity: int = 100) -> None:
        self.capacity = capacity
        self._dq: Deque[DecisionRecord] = deque(maxlen=capacity)

    def add(self, rec: DecisionRecord) -> None:
        self._dq.append(rec)

    def list(self, limit: int = 20) -> List[Dict[str, Any]]:
        out = list(self._dq)[-limit:]
        return [r.to_dict() for r in reversed(out)]

