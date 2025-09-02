from enum import Enum
from typing import Optional
from datetime import datetime

from pydantic import BaseModel, Field, condecimal, validator


class TransactionChannel(str, Enum):
    CARD = "CARD"
    ACH = "ACH"
    WIRE = "WIRE"
    MOBILE = "MOBILE"


class GeoLocation(BaseModel):
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    country: Optional[str] = None
    city: Optional[str] = None


class TransactionRequest(BaseModel):
    transactionId: Optional[str] = None
    customerId: str = Field(..., min_length=1)
    amount: condecimal(gt=0)  # type: ignore
    currency: str = Field(..., min_length=3, max_length=3)
    merchantId: str = Field(..., min_length=1)
    timestamp: datetime
    channel: TransactionChannel
    location: Optional[GeoLocation] = None
    deviceFingerprint: Optional[str] = None

    @validator("currency")
    def uppercase_currency(cls, v: str) -> str:
        return v.upper()


class ModelPredictions(BaseModel):
    random_forest: float
    isolation_forest: float
    neural_network: float
    xgboost: float


class RuleResult(BaseModel):
    ruleScore: int
    flags: list[str]


class Decision(str, Enum):
    APPROVE = "APPROVE"
    DECLINE = "DECLINE"
    REVIEW = "REVIEW"


class DecisionResponse(BaseModel):
    decision: Decision
    riskScore: int
    explanation: dict
    processingMs: int

