# Real-Time Outage Communication System — Phase 1 POC

A proof-of-concept platform that ingests planned-outage data for a utility, identifies the
customers affected by each outage, and dispatches multi-channel (SMS / Email) notifications —
prioritising **Medical Baseline** customers. The flow is orchestrated with a small,
deterministic **LangGraph** agent and surfaced through a **FastAPI** backend, a **React**
operations dashboard, and a **Streamlit** analytics dashboard.

> ⚠️ **POC scope.** Notification delivery runs in a sandbox by default (attempts are written to
> the database and logged). Business-critical decisions stay deterministic and auditable;
> LangGraph is used only for step orchestration, not for autonomous decision-making.

---

## Use Case

Utilities need to warn customers before a **planned** power outage. This POC demonstrates the
end-to-end loop:

1. **Ingest** mock outage data from an Excel/CSV workbook (customers, service points, outage
   events and their mappings).
2. **Validate** that an outage exists and is of type `Planned`.
3. **Map** the outage to its affected customers via the service-point / circuit mappings, and
   flag Medical Baseline customers for priority.
4. **Notify** each affected customer over their preferred channel (SMS / Email) and record
   every delivery attempt.
5. **Monitor** ingestion status, active outages, notification history, and KPIs from the
   dashboards.

A built-in **APScheduler** batch job can run the planned-outage workflow automatically for all
outages that are due.

---

## Architecture

```text
        React Dashboard            Streamlit Dashboard
        (operations UI)            (analytics / KPIs)
               \                        /
                \                      /
                 v                    v
            ┌───────────────────────────────┐
            │     FastAPI API Layer (/api/v1)│
            └───────────────────────────────┘
                          │
        ┌─────────────────┼──────────────────────────────┐
        │                 │                               │
        v                 v                               v
  LangGraph Agent     Services                        SQLite DB
  validate_outage     FileIngestionService            (Alembic-managed)
        │             PlannedOutageService
        v             CustomerMappingService
  identify_customers  NotificationService
        │             DashboardService
        v
  dispatch_notifications  ──►  SMS / Email (sandbox or SMTP)
```

**LangGraph workflow** (`app/agents/graph.py`):
`START → validate_outage → identify_customers → dispatch_notifications → END`

---

## Tech Stack

| Layer            | Technology                                                |
| ---------------- | --------------------------------------------------------- |
| Backend API      | FastAPI, Uvicorn, Pydantic / pydantic-settings            |
| Orchestration    | LangGraph, langchain-core                                 |
| Persistence      | SQLAlchemy + SQLite, Alembic migrations                   |
| Scheduling       | APScheduler (background batch job)                         |
| Data ingestion   | pandas, openpyxl (Excel/CSV)                               |
| Notifications    | Sandbox notifier / SMTP email backend                     |
| Ops dashboard    | React 18 + TypeScript + Vite                              |
| Analytics UI     | Streamlit                                                 |
| Tests            | pytest, httpx                                             |

---

## Repository Layout

```text
outage_poc/
├── backend/                       FastAPI service (see backend/README.md)
│   ├── app/
│   │   ├── api/v1/endpoints/      Route handlers (uploads, outages, notifications, dashboard, health)
│   │   ├── agents/                LangGraph graph, nodes, state
│   │   ├── core/                  config, database, logging, telemetry, exceptions, response envelope
│   │   ├── models/                SQLAlchemy models (customer, outage, notification, reference)
│   │   ├── repositories/          DB access layer
│   │   ├── schemas/               Pydantic request/response models
│   │   ├── services/              Business services
│   │   └── jobs/                  APScheduler planned-outage batch job
│   ├── alembic/                   Database migrations
│   ├── dashboard/                 Streamlit dashboard (streamlit_app.py)
│   ├── sample_data/               Mock .xlsx / .csv workbooks for local testing
│   ├── scripts/                   seed_from_excel.py
│   ├── tests/                     pytest suite
│   └── requirements.txt
├── frontend/react-dashboard/      React + Vite operations dashboard
└── postman/                       Postman collection + local environment
```

---

## Prerequisites

- Python 3.11+
- Node.js 18+ (for the React dashboard)

---

## Quick Start

### 1. Backend (FastAPI)

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# create your .env (see Configuration below), then run migrations
alembic upgrade head

# start the API
uvicorn app.main:app --reload --port 8000
```

- API docs (Swagger): http://localhost:8000/docs
- Health check: http://localhost:8000/health

### 2. Load mock data & run the workflow

```powershell
# upload a mock workbook
curl -X POST "http://localhost:8000/api/v1/uploads/outage-mock-data" `
  -F "file=@sample_data/mock_data_outage_system_demo.xlsx"

# process a single planned outage
curl -X POST "http://localhost:8000/api/v1/outages/OTG00002/process-planned?notification_type=Advance%20Notice"
```

### 3. Streamlit dashboard

```powershell
cd backend
streamlit run dashboard/streamlit_app.py
```

### 4. React dashboard

```powershell
cd frontend/react-dashboard
npm install
npm run dev
```

The React app reads its API base URL from `frontend/react-dashboard/.env`
(`VITE_API_BASE_URL=http://localhost:8000/api/v1`) and serves on http://localhost:5173.

---

## API Reference (`/api/v1`)

| Method | Path                                       | Description                                                        |
| ------ | ------------------------------------------ | ------------------------------------------------------------------ |
| GET    | `/health`                                  | Liveness check                                                     |
| POST   | `/uploads/outage-mock-data`                | Upload & import an Excel/CSV mock workbook                         |
| GET    | `/uploads/ingestion-status`                | Backend-owned ingestion status for dashboards                      |
| GET    | `/outages/active`                          | List active / scheduled outages                                    |
| GET    | `/outages/{outage_id}/affected-customers`  | Identify affected customers (Medical Baseline prioritised)         |
| POST   | `/outages/{outage_id}/process-planned`     | Run the LangGraph workflow for one outage (`?notification_type=`)  |
| POST   | `/outages/batch/process-planned`           | Run the planned-outage batch job on demand                         |
| GET    | `/notifications`                           | List notifications (`?outage_id=`, `?limit=`)                      |
| GET    | `/dashboard/summary`                       | KPI summary                                                        |
| GET    | `/dashboard/active-outages`                | Active outage rows for tables/maps                                 |

A Postman collection and local environment are provided under [postman/](postman/).

### Response envelope

Every successful response:

```json
{ "status_code": 200, "message": "Success message", "data": {} }
```

Every handled error:

```json
{ "status_code": 400, "message": "Human-readable error", "error_code": "DOMAIN_ERROR", "details": {} }
```

---

## Configuration

Backend settings load from `backend/.env`. Key variables:

| Variable                   | Default                          | Purpose                                            |
| -------------------------- | -------------------------------- | -------------------------------------------------- |
| `APP_ENV`                  | `local`                          | Environment name                                   |
| `DEBUG`                    | `false`                          | Debug mode (also accepts `dev`/`prod`)             |
| `API_V1_PREFIX`            | `/api/v1`                        | API route prefix                                   |
| `DATABASE_URL`             | `sqlite:///./outage_poc.db`      | SQLAlchemy connection string                       |
| `LOG_LEVEL` / `LOG_JSON`   | `INFO` / `true`                  | Logging level & structured JSON logging            |
| `NOTIFICATION_MODE`        | `sandbox`                        | `sandbox` or `provider`                            |
| `EMAIL_BACKEND`            | `sandbox`                        | `sandbox` or `smtp`                                |
| `SMTP_HOST`/`PORT`/`USER`/`PASSWORD`/`FROM_EMAIL`/`TLS` | —    | SMTP settings when `EMAIL_BACKEND=smtp`            |
| `BATCH_SCHEDULER_ENABLED`  | `false`                          | Enable the APScheduler batch job on startup        |
| `BATCH_INTERVAL_MINUTES`   | `5`                              | Batch interval                                     |

> 🔐 **Security note:** do not commit real SMTP credentials. Use app-specific passwords and keep
> secrets out of version control.

---

## Mock Data Format

Uploaded workbooks are imported sheet-by-sheet. Expected sheet names:

`CUSTOMER`, `SERVICE_POINT`, `OUTAGE_EVENT`, `CUSTOMER_SERVICE_POINT`, `CUSTOMER_TYPE`,
`CHANNEL_MASTER`, `OUTAGE_CIRCUIT_MAP`, `OUTAGE_CUSTOMER_MAP`.

Ready-to-use samples live in [backend/sample_data/](backend/sample_data/).

---

## Tests

```powershell
cd backend
pytest
```

---

## POC Limitations

- Notification delivery is sandboxed by default — delivery attempts are persisted and logged but
  no real provider is called unless you configure the SMTP backend or extend the notifier adapters.
- Phase 1 focuses on **SMS** and **Email**. IVR and App-Push preferences are recorded but
  simulated.
- Only `Planned` outages are supported by the workflow.
- SQLite is used for simplicity; swap `DATABASE_URL` for a production-grade database when needed.

---

See [backend/README.md](backend/README.md) for backend-specific details.
