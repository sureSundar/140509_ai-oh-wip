from dataclasses import dataclass


@dataclass
class Weights:
    random_forest: float = 0.3
    isolation_forest: float = 0.2
    neural_network: float = 0.3
    xgboost: float = 0.2


@dataclass
class Thresholds:
    approve_max: int = 350  # <= approve
    review_min: int = 351   # 351..699 review
    decline_min: int = 700  # >= decline


WEIGHTS = Weights()
THRESHOLDS = Thresholds()

