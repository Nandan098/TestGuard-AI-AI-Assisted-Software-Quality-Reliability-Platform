# TestGuard AI — Automated API Testing & Reliability Platform

TestGuard AI is a portfolio-ready full-stack project that runs a repeatable API contract test suite against a sample service, measures response time, stores run history, and offers rule-based AI-assisted failure triage. It is designed to demonstrate Quality Engineering, Software Development, automation, API design, and reliability concepts.

> **Important:** The failure explanations are deterministic, rule-based recommendations—not an LLM and not guaranteed root-cause analysis. The included commerce API is a demo service. `DEMO_BUG_MODE` and `DEMO_LATENCY_MS` deliberately introduce faults so you can show the tests detecting problems. Do not describe the demo's seed product data as production data.

## Features

- **Seven automated checks:** health response, product-list contract (including a known price), product detail (including a known price), unknown product handling, checkout total, invalid checkout validation, and unknown-route handling.
- **Assertions and regression checks:** verifies HTTP status, expected JSON fields and values, and a configurable response-time budget.
- **Failure triage:** labels issues such as server error, timeout/connectivity, performance regression, unexpected status, or response-contract mismatch, then suggests useful debugging steps.
- **Run history:** persists test runs and per-test results in SQLite by default; PostgreSQL can be configured using `DATABASE_URL` and the suitable PostgreSQL driver.
- **Dashboard:** React + Vite UI with pass rate metrics, a run trend chart, per-test details, failure diagnosis, catalog, and historical runs.
- **Demo fault injection:** enable a wrong product price or added latency to prove your suite catches faults.
- **API documentation:** FastAPI's interactive OpenAPI documentation.
- **Tests:** pytest coverage for triage logic and backend endpoints.

## Architecture

```text
React + Vite dashboard (5173)
          |
          | HTTP /api/*
          v
FastAPI TestGuard backend (8000) ---- SQLAlchemy ---- SQLite database
          |
          | HTTP requests / assertions
          v
Demo Commerce API (8001)
  /health, /products, /products/{id}, /checkout
```

The TestGuard backend is the **test runner**. The Demo Commerce API is the **system under test**. Keep these as separate services when presenting the project.

## Requirements

- Python 3.10+ (Python 3.11 or 3.12 recommended)
- Node.js 18+ and npm
- Git (for version control)
- Optional: Docker Desktop and Docker Compose

## Option A — Run locally (recommended while learning)

Open three terminals from the project root. Run each service in its own terminal so you can see the logs.

### 1. Install Python dependencies

Create and activate a virtual environment from the project root:

**Windows PowerShell**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r target_app\requirements.txt -r backend\requirements.txt
```

**macOS / Linux**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r target_app/requirements.txt -r backend/requirements.txt
```

### 2. Start the demo API (Terminal 1)

From the project root:

```bash
cd target_app
python -m uvicorn app.main:app --reload --port 8001
```

Verify it by opening <http://localhost:8001/health>. Interactive docs: <http://localhost:8001/docs>.

### 3. Start the TestGuard backend (Terminal 2)

From the project root, activate the same virtual environment if this is a new terminal:

```bash
# Windows PowerShell
.\.venv\Scripts\Activate.ps1

# macOS / Linux
source .venv/bin/activate
```

Then run:

```bash
cd backend
# Windows PowerShell: $env:TARGET_BASE_URL = "http://127.0.0.1:8001"
# macOS / Linux: export TARGET_BASE_URL="http://127.0.0.1:8001"
python -m uvicorn app.main:app --reload --port 8000
```

Verify at <http://localhost:8000/api/health>. API docs: <http://localhost:8000/docs>.

The local SQLite database file will be created as `backend/testguard.db` on first app start.

### 4. Start the frontend (Terminal 3)

From the project root:

```bash
cd frontend
npm install
npm run dev
```

Open <http://localhost:5173>. The dashboard should show the backend as connected. Click **Run test suite** to run all seven API checks and save the results.

### 5. Run backend tests

From the project root, activate `.venv`, then:

```bash
cd backend
python -m pytest -v
```

## Option B — Run everything with Docker Compose

Install Docker Desktop, then from the project root:

```bash
docker compose up --build
```

Open:
- Dashboard: <http://localhost:5173>
- TestGuard API docs: <http://localhost:8000/docs>
- Demo target API docs: <http://localhost:8001/docs>

To shut down:

```bash
docker compose down
```

Run history is stored in a named Docker volume (`testguard-data`). To remove the volume and its stored history too, use `docker compose down -v`.

## Demonstrate a detected regression

The sample target app includes a fault-injection setting. It is intentionally off by default.

### Demonstration 1 — Wrong product price

Stop the local target API, then start it with the fault switch enabled:

**Windows PowerShell**

```powershell
cd target_app
$env:DEMO_BUG_MODE = "true"
python -m uvicorn app.main:app --reload --port 8001
```

**macOS / Linux**

```bash
cd target_app
DEMO_BUG_MODE=true python -m uvicorn app.main:app --reload --port 8001
```

Rerun the TestGuard test suite. Product-detail and checkout assertions should detect the changed price/total. The dashboard will classify the issue as a response-contract/data mismatch and show the expected-versus-actual output.

Turn fault injection off by stopping the service and starting it again without `DEMO_BUG_MODE=true`.

### Demonstration 2 — Added latency

Start the target with `DEMO_LATENCY_MS=1200`. Endpoints that include the delay should breach the default 1000 ms performance budget. Adjust `PERFORMANCE_BUDGET_MS` if you want to show a different baseline. Added latency is a controlled demo signal, not a statistically robust load test.

## API endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/api/health` | Backend status and target URL |
| `GET` | `/api/test-cases` | Built-in test catalog |
| `POST` | `/api/runs` | Execute tests and persist a report |
| `GET` | `/api/runs` | List recent runs (optional `limit`, maximum 100) |
| `GET` | `/api/runs/{run_id}` | Detailed report and per-test assertions |
| `GET` | `/api/overview` | Summary metrics and last 10-run trend |
| `DELETE` | `/api/runs` | Clear saved history (demo reset) |

## Configuration

Set environment variables before starting the backend:

| Variable | Default | Meaning |
|---|---|---|
| `TARGET_BASE_URL` | `http://127.0.0.1:8001` | Base URL of the service under test |
| `DATABASE_URL` | `sqlite:///./testguard.db` | SQLAlchemy database URL |
| `REQUEST_TIMEOUT_SECONDS` | `4` | HTTP timeout per assertion |
| `PERFORMANCE_BUDGET_MS` | `1000` | Max response time allowed by the suite |

For local PostgreSQL, install a compatible driver such as `psycopg[binary]` and set a PostgreSQL SQLAlchemy URL. The included Docker Compose setup uses SQLite persisted to a named volume.

The target service has separate demo variables:

| Variable | Default | Meaning |
|---|---|---|
| `DEMO_BUG_MODE` | `false` | Deliberately return an incorrect price for product 1 |
| `DEMO_LATENCY_MS` | `0` | Add a delay to target API handlers that simulate work |

## Project structure

```text
TestGuardAI/
├── backend/
│   ├── app/
│   │   ├── analyzer.py       # Failure triage and summary
│   │   ├── config.py         # Environment-driven settings
│   │   ├── database.py       # SQLAlchemy engine/session
│   │   ├── main.py           # REST endpoints and persistence
│   │   ├── models.py         # Test run and result schema
│   │   └── test_engine.py    # HTTP suite, validators, timing
│   ├── tests/
│   │   ├── conftest.py
│   │   ├── test_analyzer.py
│   │   └── test_api.py
│   ├── Dockerfile
│   └── requirements.txt
├── target_app/
│   ├── app/main.py           # Sample API and safe fault injection
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/App.jsx           # Dashboard components and interactions
│   ├── src/api.js            # Backend API client
│   ├── src/main.jsx
│   ├── src/style.css
│   ├── Dockerfile
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
├── scripts/
│   ├── run_local.sh
│   └── run_local.ps1
├── .env.example
├── .gitignore
├── docker-compose.yml
└── README.md
```

## How to extend it

Good next enhancements after the baseline works:

1. Add tests driven from a YAML/JSON test-spec file so endpoint contracts can be changed without editing Python.
2. Add a JSON/CSV export of each run for attaching reports to issues.
3. Add configurable per-endpoint performance budgets and repeat runs to reduce transient timing noise.
4. Add authentication and role-based access before deploying outside a local portfolio demo.
5. Integrate an LLM behind an explicit opt-in setting to summarize sanitized logs. Do not send tokens, secrets, or personal data to a model; do not treat generated suggestions as verified fixes.
6. Add coverage, linting, type checking, and CI tests for the backend and frontend.

## Portfolio and resume guidance

Only claim results you can reproduce. After running the tests, record real measurements such as the number of test assertions, detected fault types, suite execution time, and CI pass/fail behavior. Be ready to explain:

- How the test runner separates assertions from report persistence.
- Why a response can return HTTP 200 and still fail a contract test.
- How you distinguish response contract failures from latency and connectivity failures.
- Why performance timings can be noisy and why one threshold is not a substitute for load testing.
- How the fault-injection demo proves the tests actually detect defects.

This project is a learning/demo system, not a production-certified quality platform.
