from __future__ import annotations

import math
from typing import Dict, Tuple

from common.config import WEIGHTS


def _sigmoid(x: float) -> float:
    try:
        return 1 / (1 + math.exp(-x))
    except OverflowError:
        return 0.0 if x < 0 else 1.0


class EnsembleModel:
    """Simple heuristic-based ensemble to avoid external deps.

    Inputs: minimal feature dict {'amount', 'avg_transaction_amount_7d', 'velocity_score_1h', 'std_transaction_amount_7d'}
    Outputs: weighted probability and per-model components.
    """

    def predict(self, features: Dict[str, float]) -> Tuple[float, Dict[str, float]]:
        amount = float(features.get("amount", 0.0))
        avg_amt = float(features.get("avg_transaction_amount_7d", 0.0))
        std_amt = float(features.get("std_transaction_amount_7d", 0.0))
        velocity = float(features.get("velocity_score_1h", 0.0))

        # Normalize: compare against avg and std
        z = 0.0
        if std_amt > 0:
            z = (amount - avg_amt) / max(std_amt, 1e-6)
        elif avg_amt > 0:
            z = (amount - avg_amt) / max(avg_amt, 1e-6)

        # RandomForest heuristic: high z-score => higher fraud prob
        rf = _sigmoid(z)

        # IsolationForest heuristic: higher velocity => higher anomaly
        iso = _sigmoid((velocity - 5) / 2.0)

        # Neural network heuristic: nonlinear mix
        nn = _sigmoid(0.6 * z + 0.4 * (iso - 0.5) * 2)

        # XGBoost heuristic: emphasize amount spikes with small reg
        xgb = _sigmoid(0.9 * z + 0.1 * (velocity / 10.0))

        weighted = (
            WEIGHTS.random_forest * rf
            + WEIGHTS.isolation_forest * iso
            + WEIGHTS.neural_network * nn
            + WEIGHTS.xgboost * xgb
        )

        per_model = {
            "random_forest": rf,
            "isolation_forest": iso,
            "neural_network": nn,
            "xgboost": xgb,
        }
        return float(weighted), per_model
