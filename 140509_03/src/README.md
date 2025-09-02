Fraud Detection MVP (Problem 140509_03)

Overview
- Implements a minimal end-to-end path described in docs (PRD/FRD/NFRD/AD/HLD/LLD).
- Services: ingestion (FastAPI), decision service, simple ML ensemble, in-memory feature store, rules engine.

Run (local)
1) Create venv and install deps:
   python3 -m venv .venv && source .venv/bin/activate
   pip install -r src/requirements.txt

2) Start API:
   uvicorn ingestion_service.main:app --reload --app-dir src

3) Test request:
   curl -s -X POST http://127.0.0.1:8000/api/v1/transactions \
     -H 'Content-Type: application/json' \
     -d '{
           "customerId": "CUST123",
           "amount": 150.00,
           "currency": "USD",
           "merchantId": "M001",
           "timestamp": "2024-01-01T12:00:00Z",
           "channel": "CARD",
           "location": {"latitude": 40.7, "longitude": -74.0}
         }' | jq

Notes
- This MVP uses in-memory state; no external Kafka/Redis/Postgres are required.
- Rules are loaded from src/rule_engine/rules.yaml (falls back if PyYAML unavailable).
- Risk score combines ML prob (0..800) and rules (0..200) into 0..1000.

Docker
- Build and run with Postgres via docker-compose (even though the API is in-memory for now):
  docker compose -f 140509_03/docker-compose.yml up --build -d

- API will be available at:
  http://localhost:8000/docs
  Health check: http://localhost:8000/healthz
  Prometheus metrics: http://localhost:8000/metrics
  Demo dashboard: http://localhost:8000/demo

- Stop and remove containers:
  docker compose -f 140509_03/docker-compose.yml down -v

Persistence
- If `DATABASE_URL` is set (compose sets it for you), the API will:
  - auto-create tables `transactions` and `decisions` (SQLAlchemy) on first request
  - persist each transaction and its decision
  - continue to function if the DB is unavailable (adds a `persistenceWarning` in response)

Migrations and Seed
- Apply migrations (SQL):
  docker compose -f 140509_03/docker-compose.yml exec api \
    python persistence/run_migrations.py

- Seed example data:
  docker compose -f 140509_03/docker-compose.yml exec api \
    python persistence/seed.py

Alembic (optional)
- Run Alembic migrations instead of raw SQL:
  docker compose -f 140509_03/docker-compose.yml exec api \
    alembic upgrade head

Rule Management API
- List rules:
  GET /rules
- Add rule:
  POST /rules {"category":"fraud","name":"NewRule","condition":"amount>5000","points":25}
- Update rule:
  PUT /rules/{category}/{name} {"condition":"velocity_score_1h>=5","points":30}
- Delete rule:
  DELETE /rules/{category}/{name}
- Rule metrics:
  GET /rules/metrics
  POST /rules/metrics/reset

Redis Feature Store (optional)
- Set REDIS_URL env var to enable Redis-backed features. Without it, the service uses in-memory features.

Live Demo (local)
- In one terminal, start API locally:
  source .venv/bin/activate  # if created earlier
  uvicorn ingestion_service.main:app --reload --app-dir 140509_03/src

- In another terminal, run the demo client to generate scenarios:
  python 140509_03/demo/demo_client.py

- Open the live dashboard:
  http://127.0.0.1:8000/demo

- Explore API docs and recent decisions:
  http://127.0.0.1:8000/docs
  http://127.0.0.1:8000/decisions/recent?limit=25
