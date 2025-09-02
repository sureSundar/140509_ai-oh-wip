from __future__ import annotations

import time
from sqlalchemy import text
from fastapi import FastAPI

from common.models import DecisionResponse, TransactionRequest
from common.timing import timed_ms
from decision_service.service import DecisionService
from common.db import is_db_enabled, get_session
from persistence.repository import (
    persist_transaction_and_decision,
    init_db,
    get_recent_decisions,
)
from common.metrics import http_requests_total, decisions_total, latency_seconds, metrics_endpoint
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from common.recent_cache import RecentCache, DecisionRecord

app = FastAPI(title="Fraud Detection Ingestion API (MVP)", version="0.1.0")
svc = DecisionService()
_start_time = time.time()
recent_cache = RecentCache(capacity=200)

# Serve static demo dashboard
app.mount(
    "/demo",
    StaticFiles(directory=str(__file__).rsplit("/", 1)[0] + "/static", html=True),
    name="demo",
)


@app.get("/healthz")
def healthz() -> JSONResponse:
    status = "ok"
    db_status = "disabled"
    if is_db_enabled():
        try:
            with get_session() as s:
                s.execute(text("SELECT 1"))
            db_status = "connected"
        except Exception as e:
            db_status = f"error: {e}"
            status = "degraded"
    uptime = time.time() - _start_time
    return JSONResponse({
        "status": status,
        "db": db_status,
        "uptimeSec": round(uptime, 3),
        "version": app.version,
    })


@app.get("/metrics")
def metrics():
    return metrics_endpoint()


@app.post("/api/v1/transactions", response_model=DecisionResponse)
def ingest(tx: TransactionRequest) -> DecisionResponse:
    http_requests_total.inc()
    start = time.perf_counter()
    (decision, risk_score, explanation, _), ms = timed_ms(svc.decide)(tx)
    if ms > 100:
        # Not raising an error; this is informational in MVP
        explanation["performanceWarning"] = f"Processing exceeded 100ms: {ms}ms"
    # Add to recent cache for demo
    recent_cache.add(
        DecisionRecord(
            decision=decision.value,
            riskScore=int(risk_score),
            explanation=explanation,
            customerId=tx.customerId,
            amount=float(tx.amount),
            currency=tx.currency,
            merchantId=tx.merchantId,
            timestamp=tx.timestamp.isoformat(),
        )
    )

    # Optional persistence if DATABASE_URL configured
    if is_db_enabled():
        try:
            with get_session() as session:
                init_db(session)  # idempotent
                persist_transaction_and_decision(
                    session, tx, decision, int(risk_score), explanation
                )
        except Exception as e:
            explanation["persistenceWarning"] = f"DB error: {e}"
    latency_seconds.observe(time.perf_counter() - start)
    decisions_total.labels(decision.value).inc()
    return DecisionResponse(
        decision=decision,
        riskScore=int(risk_score),
        explanation=explanation,
        processingMs=int(ms),
    )


# Run: uvicorn ingestion_service.main:app --reload


@app.get("/decisions/recent")
def recent(limit: int = 20) -> JSONResponse:
    if is_db_enabled():
        try:
            with get_session() as session:
                data = get_recent_decisions(session, limit=limit)
                return JSONResponse(data)
        except Exception:
            pass
    # Fallback to in-memory cache
    return JSONResponse(recent_cache.list(limit=limit))


@app.get("/stats/summary")
def stats_summary() -> JSONResponse:
    items = recent_cache.list(limit=200)
    total = len(items)
    by_decision = {"APPROVE": 0, "REVIEW": 0, "DECLINE": 0}
    for it in items:
        key = it.get("decision")
        if key in by_decision:
            by_decision[key] += 1
        else:
            by_decision[key] = 1
    return JSONResponse({"totalRecent": total, "byDecision": by_decision})


# ---- Rule management API ----
@app.get("/rules")
def list_rules() -> JSONResponse:
    return JSONResponse({
        "version": svc.rule_engine.version,
        "rules": svc.rule_engine.list_rules(),
    })


class RulePayload(TransactionRequest.__class__):
    pass


@app.post("/rules")
def add_rule(payload: dict) -> JSONResponse:
    category = payload.get("category")
    name = payload.get("name")
    condition = payload.get("condition")
    points = int(payload.get("points", 0))
    if category not in ("aml", "fraud"):
        return JSONResponse({"error": "invalid category"}, status_code=400)
    if not all([name, condition]):
        return JSONResponse({"error": "name and condition required"}, status_code=400)
    svc.rule_engine.add_rule(category, name, condition, points)
    return JSONResponse({"status": "ok", "version": svc.rule_engine.version})


@app.put("/rules/{category}/{name}")
def update_rule(category: str, name: str, payload: dict) -> JSONResponse:
    updated = svc.rule_engine.update_rule(category, name, payload.get("condition"), payload.get("points"))
    if not updated:
        return JSONResponse({"error": "rule not found"}, status_code=404)
    return JSONResponse({"status": "ok", "version": svc.rule_engine.version})


@app.delete("/rules/{category}/{name}")
def delete_rule(category: str, name: str) -> JSONResponse:
    removed = svc.rule_engine.delete_rule(category, name)
    if not removed:
        return JSONResponse({"error": "rule not found"}, status_code=404)
    return JSONResponse({"status": "ok", "version": svc.rule_engine.version})


@app.get("/rules/metrics")
def rule_metrics() -> JSONResponse:
    return JSONResponse({"metrics": svc.rule_engine.get_metrics()})


@app.post("/rules/metrics/reset")
def reset_rule_metrics() -> JSONResponse:
    svc.rule_engine.reset_metrics()
    return JSONResponse({"status": "ok"})
