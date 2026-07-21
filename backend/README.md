# Real-Time Outage Communication System - Phase 1 POC Backend

Production-style FastAPI backend skeleton for the Phase 1:

- Upload Excel/CSV data
- PostgreSQL schema with Alembic migrations
- Planned outage batch processing
- Basic customer-to-service-point-to-outage mapping
- SMS/Email sandbox notifications
- Smart, personalised, **multilingual** message generation via Google Gemini (Vertex AI),
  with a deterministic template fallback
- Streamlit monitoring dashboard
- Basic LangGraph agent orchestration (step orchestration only — not autonomous/agentic)
- Structured JSON logging and standard API response envelope

## Architecture

```text
React / Streamlit Dashboard
        |
        v
FastAPI API Layer
        |
        +--> LangGraph Agent Orchestration
        |       Outage Validation -> Customer Mapping -> Notification Dispatch
        |
        +--> Services
        |       FileIngestionService
        |       PlannedOutageService
        |       CustomerMappingService
        |       NotificationService --> LlmMessageService --> Gemini (Vertex AI)
        |       DashboardService                  (template fallback on failure)
        |
        +--> PostgreSQL
        |
```

## Quick Start - Local

### 1. Create environment

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

### 2. Run DB migrations

```bash
alembic upgrade head
```

### 3. Run FastAPI

```bash
uvicorn app.main:app --reload --port 8000
```

Open:

- API: http://localhost:8000/docs
- Health: http://localhost:8000/health

### 4. Upload data

```bash
curl -X POST "http://localhost:8000/api/v1/uploads/outage-data" \
  -F "file=@sample_data/data_outage_system.xlsx"
```

### 5. Process one planned outage

```bash
curl -X POST "http://localhost:8000/api/v1/outages/OTG00002/process-planned?notification_type=Advance%20Notice"
```

### 6. Start Streamlit dashboard

```bash
streamlit run dashboard/streamlit_app.py
```

## API Response Standard

Every successful endpoint returns:

```json
{
  "status_code": 200,
  "message": "Success message",
  "data": {}
}
```

Every handled error returns:

```json
{
  "status_code": 400,
  "message": "Human-readable error",
  "error_code": "DOMAIN_ERROR",
  "details": {}
}
```

8.frontend run
cd frontend/react-dashboard
npm install
npm run dev
## Important POC Notes

- Notification delivery is sandboxed by default. It writes delivery attempts to DB and logs them; it does not call real Twilio/SendGrid unless you extend the notifier adapters.
- IVR and App Push customer preferences are recorded, but POC dispatch simulates delivery. Phase 1 focuses on SMS and Email.
- LangGraph is used for basic orchestration, but business-critical decisions remain deterministic and auditable. Gemini only generates the message *text* (no routing/timing decisions); it is not an autonomous agent.
- Message generation uses Gemini on Vertex AI (auth via the service-account `auth.json`). Supports English and Spanish via the `CUSTOMER.preferred_language` column. Set `LLM_ENABLED=false` to disable and use deterministic English templates only; the same fallback triggers on any LLM error or guardrail rejection.
- This POC imports data from Excel sheets matching the uploaded workbook names: `CUSTOMER`, `SERVICE_POINT`, `OUTAGE_EVENT`, `CUSTOMER_SERVICE_POINT`, `CUSTOMER_TYPE`, `CHANNEL_MASTER`, `OUTAGE_CIRCUIT_MAP`, and `OUTAGE_CUSTOMER_MAP`. The `CUSTOMER` sheet now carries a `preferred_language` column.

## Project Structure

```text
app/
  api/v1/endpoints/       FastAPI route handlers
  agents/                 LangGraph orchestration graph
  core/                   config, db, logging, telemetry, errors
  integrations/notifiers/ notification adapters (SMS/Email)
  integrations/llm/       Gemini (Vertex AI) client for message generation
  models/                 SQLAlchemy models
  repositories/           DB access layer
  schemas/                Pydantic request/response models
  services/               business services
  jobs/                   APScheduler planned outage job
alembic/                  migrations
dashboard/                Streamlit dashboard
sample_data/              uploaded xlsx copied for local testing
```
