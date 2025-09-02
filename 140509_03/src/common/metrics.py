from __future__ import annotations

from fastapi import Response
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

# Metrics
http_requests_total = Counter(
    "fraud_api_requests_total",
    "Total number of requests to the ingestion endpoint",
)

decisions_total = Counter(
    "fraud_decisions_total",
    "Total decisions made by type",
    labelnames=("decision",),
)

latency_seconds = Histogram(
    "fraud_request_latency_seconds",
    "End-to-end request latency in seconds",
    buckets=(0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0),
)


def metrics_endpoint() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

