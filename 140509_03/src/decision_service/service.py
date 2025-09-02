from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

from common.config import THRESHOLDS
from common.models import Decision, ModelPredictions, RuleResult, TransactionRequest
from feature_store.service import InMemoryFeatureStore
from ml_serving.service import EnsembleModel
from rule_engine.engine import RuleEngine


@dataclass
class DecisionArtifacts:
    features: Dict[str, float]
    per_model: Dict[str, float]
    rule_result: RuleResult


class DecisionService:
    def __init__(self) -> None:
        # Optional Redis-backed feature store if REDIS_URL is set
        import os
        redis_url = os.getenv("REDIS_URL")
        if redis_url:
            try:
                from .feature_store_redis import RedisFeatureStore  # type: ignore
            except Exception:
                self.feature_store = InMemoryFeatureStore()
            else:
                self.feature_store = RedisFeatureStore(redis_url)
        else:
            self.feature_store = InMemoryFeatureStore()
        self.model = EnsembleModel()
        self.rule_engine = RuleEngine()

    def decide(self, tx: TransactionRequest) -> tuple[Decision, int, Dict, DecisionArtifacts]:
        # Observe into feature store to update rolling aggregates
        self.feature_store.observe(tx)
        features = self.feature_store.get_features(tx.customerId)
        features["amount"] = float(tx.amount)

        # Derive z-score for rules context
        avg = features.get("avg_transaction_amount_7d", 0.0)
        std = features.get("std_transaction_amount_7d", 0.0)
        if std > 0:
            z = (features["amount"] - avg) / max(std, 1e-6)
        elif avg > 0:
            z = (features["amount"] - avg) / max(avg, 1e-6)
        else:
            z = 0.0
        features["z_score"] = float(z)

        # ML prediction
        weighted_prob, per_model = self.model.predict(features)

        # Rules
        rule_score, flags = self.rule_engine.evaluate(features)
        rule_result = RuleResult(ruleScore=int(rule_score), flags=flags)

        # Composite risk score: combine ML probability (0-1) to 0-800 and add rule points (0-200)
        ml_component = int(max(0.0, min(1.0, weighted_prob)) * 800)
        risk_score = int(min(1000, ml_component + rule_result.ruleScore))

        # Decision
        if risk_score <= THRESHOLDS.approve_max:
            decision = Decision.APPROVE
        elif risk_score >= THRESHOLDS.decline_min:
            decision = Decision.DECLINE
        else:
            decision = Decision.REVIEW

        explanation = {
            "ml": {
                "weightedProb": weighted_prob,
                "perModel": per_model,
            },
            "rules": {
                "flags": rule_result.flags,
                "ruleScore": rule_result.ruleScore,
            },
            "features": features,
        }

        artifacts = DecisionArtifacts(features=features, per_model=per_model, rule_result=rule_result)
        return decision, risk_score, explanation, artifacts
