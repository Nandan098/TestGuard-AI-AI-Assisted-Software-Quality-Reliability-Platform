from unittest.mock import AsyncMock, patch


def test_health_and_catalog(client):
    health = client.get("/api/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"

    cases = client.get("/api/test-cases")
    assert cases.status_code == 200
    assert len(cases.json()) >= 5


def test_run_history_and_detail(client):
    payload = {
        "total": 2,
        "passed": 1,
        "failed": 1,
        "avg_duration_ms": 12.5,
        "summary": "One check failed.",
        "results": [
            {"test_name": "Health endpoint", "description": "Health test", "endpoint": "GET /health", "status": "passed", "duration_ms": 5.0, "expected": "200", "actual": "200", "category": "", "diagnosis": "", "recommendation": ""},
            {"test_name": "Checkout calculation", "description": "Totals match", "endpoint": "POST /checkout", "status": "failed", "duration_ms": 20.0, "expected": "9.98", "actual": "10.98", "category": "Response contract / data mismatch", "diagnosis": "Unexpected total", "recommendation": "Review price calculation."},
        ],
    }
    with patch("app.main.execute_suite", new=AsyncMock(return_value=payload)):
        response = client.post("/api/runs")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert body["pass_rate"] == 50.0
    assert len(body["results"]) == 2

    history = client.get("/api/runs")
    assert history.status_code == 200
    assert len(history.json()) == 1

    detail = client.get(f"/api/runs/{body['id']}")
    assert detail.status_code == 200
    assert detail.json()["results"][1]["category"] == "Response contract / data mismatch"


def test_missing_run_is_404(client):
    response = client.get("/api/runs/12345")
    assert response.status_code == 404
