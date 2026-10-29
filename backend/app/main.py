from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import desc, select
from sqlalchemy.orm import Session, selectinload

from .config import APP_NAME, APP_VERSION, TARGET_BASE_URL
from .database import Base, engine, get_db
from .models import TestResult, TestRun
from .test_engine import execute_suite, get_test_catalog

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    description="Automated API contract testing, regression monitoring, and AI-assisted failure triage.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:4173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()


def _result_dict(item: TestResult) -> dict[str, Any]:
    return {
        "id": item.id,
        "test_name": item.test_name,
        "description": item.description,
        "endpoint": item.endpoint,
        "status": item.status,
        "duration_ms": item.duration_ms,
        "expected": item.expected,
        "actual": item.actual,
        "category": item.category,
        "diagnosis": item.diagnosis,
        "recommendation": item.recommendation,
    }


def _run_dict(run: TestRun, include_results: bool = False) -> dict[str, Any]:
    total = run.total or 0
    output: dict[str, Any] = {
        "id": run.id,
        "started_at": _iso(run.started_at),
        "finished_at": _iso(run.finished_at),
        "total": total,
        "passed": run.passed,
        "failed": run.failed,
        "pass_rate": round((run.passed / total) * 100, 1) if total else 0,
        "avg_duration_ms": round(run.avg_duration_ms, 2),
    }
    if include_results:
        output["results"] = [_result_dict(item) for item in run.results]
        failures = [r for r in output["results"] if r["status"] == "failed"]
        if not failures:
            output["summary"] = "All checks passed. Continue monitoring response time and rerun the suite after code changes."
        else:
            categories: dict[str, int] = {}
            for failure in failures:
                category = failure["category"] or "Unclassified"
                categories[category] = categories.get(category, 0) + 1
            top = max(categories.items(), key=lambda item: item[1])
            output["summary"] = f"{len(failures)} of {total} checks failed. Most common category: {top[0]} ({top[1]}). Review the individual diagnosis and recommendations below."
    return output


@app.get("/", tags=["system"])
def root():
    return {"name": APP_NAME, "version": APP_VERSION, "docs": "/docs"}


@app.get("/api/health", tags=["system"])
def health():
    return {"status": "ok", "service": APP_NAME, "version": APP_VERSION, "target_base_url": TARGET_BASE_URL}


@app.get("/api/test-cases", tags=["testing"])
def test_cases():
    return get_test_catalog()


@app.post("/api/runs", tags=["testing"])
async def create_run(db: Session = Depends(get_db)):
    started_at = datetime.now(timezone.utc)
    payload = await execute_suite()
    finished_at = datetime.now(timezone.utc)
    run = TestRun(
        started_at=started_at,
        finished_at=finished_at,
        total=payload["total"],
        passed=payload["passed"],
        failed=payload["failed"],
        avg_duration_ms=payload["avg_duration_ms"],
    )
    db.add(run)
    db.flush()
    for result in payload["results"]:
        db.add(TestResult(
            run_id=run.id,
            test_name=result["test_name"],
            description=result.get("description", ""),
            endpoint=result.get("endpoint", ""),
            status=result["status"],
            duration_ms=result["duration_ms"],
            expected=result.get("expected", ""),
            actual=result.get("actual", ""),
            category=result.get("category", ""),
            diagnosis=result.get("diagnosis", ""),
            recommendation=result.get("recommendation", ""),
        ))
    db.commit()
    db.refresh(run)
    run = db.scalar(select(TestRun).options(selectinload(TestRun.results)).where(TestRun.id == run.id))
    assert run is not None
    return _run_dict(run, include_results=True)


@app.get("/api/runs", tags=["testing"])
def list_runs(limit: int = 20, db: Session = Depends(get_db)):
    limit = max(1, min(limit, 100))
    runs = db.scalars(select(TestRun).order_by(desc(TestRun.id)).limit(limit)).all()
    return [_run_dict(run) for run in runs]


@app.get("/api/runs/{run_id}", tags=["testing"])
def get_run(run_id: int, db: Session = Depends(get_db)):
    run = db.scalar(select(TestRun).options(selectinload(TestRun.results)).where(TestRun.id == run_id))
    if run is None:
        raise HTTPException(status_code=404, detail="Test run not found")
    return _run_dict(run, include_results=True)


@app.get("/api/overview", tags=["analytics"])
def overview(db: Session = Depends(get_db)):
    runs = db.scalars(select(TestRun).order_by(desc(TestRun.id)).limit(10)).all()
    latest = runs[0] if runs else None
    total_runs = db.query(TestRun).count()
    all_time_failed = db.query(TestResult).filter(TestResult.status == "failed").count()
    return {
        "total_runs": total_runs,
        "all_time_failed_tests": all_time_failed,
        "latest_run": _run_dict(latest) if latest else None,
        "trend": [
            {"id": run.id, "started_at": _iso(run.started_at), "pass_rate": round(run.passed / run.total * 100, 1) if run.total else 0,
             "passed": run.passed, "failed": run.failed, "avg_duration_ms": round(run.avg_duration_ms, 2)}
            for run in reversed(runs)
        ],
    }


@app.delete("/api/runs", tags=["testing"])
def clear_runs(db: Session = Depends(get_db)):
    """Clear run history; useful for a clean demo reset."""
    db.query(TestResult).delete()
    db.query(TestRun).delete()
    db.commit()
    return {"deleted": True}
