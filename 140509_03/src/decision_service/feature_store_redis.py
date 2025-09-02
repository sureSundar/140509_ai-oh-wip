from __future__ import annotations

import json
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List

from redis import Redis
from common.models import TransactionRequest


class RedisFeatureStore:
    def __init__(self, redis_url: str) -> None:
        self.r = Redis.from_url(redis_url, decode_responses=True)

    def observe(self, tx: TransactionRequest) -> None:
        cid = tx.customerId
        ts = int(tx.timestamp.timestamp())
        # Store event time in sorted set (score = epoch seconds), keep last 7 days
        zkey = f"tx_times:{cid}"
        self.r.zadd(zkey, {str(ts): ts})
        cutoff = int((datetime.now(timezone.utc) - timedelta(days=7)).timestamp())
        self.r.zremrangebyscore(zkey, 0, cutoff)

        # Maintain last N amounts in a list (cap to 1000)
        lkey = f"amounts:{cid}"
        self.r.lpush(lkey, str(float(tx.amount)))
        self.r.ltrim(lkey, 0, 999)

    def get_features(self, customer_id: str) -> Dict[str, float]:
        now = int(time.time())
        last_hour = now - 3600
        zkey = f"tx_times:{customer_id}"
        velocity_1h = int(self.r.zcount(zkey, last_hour, now) or 0)

        lkey = f"amounts:{customer_id}"
        raw = self.r.lrange(lkey, 0, 999)
        amounts = [float(x) for x in raw] if raw else []
        if amounts:
            avg = sum(amounts) / len(amounts)
            var = sum((a - avg) ** 2 for a in amounts) / len(amounts)
            std = var ** 0.5
        else:
            avg = 0.0
            std = 0.0

        return {
            "velocity_score_1h": float(velocity_1h),
            "avg_transaction_amount_7d": float(avg),
            "std_transaction_amount_7d": float(std),
        }

