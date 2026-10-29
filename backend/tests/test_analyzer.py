from app.analyzer import classify_failure, summarize_failures


def test_timeout_classification():
    result = classify_failure(error="ReadTimeout: request timed out")
    assert result["category"] == "Timeout / availability"
    assert "timeout" in result["recommendation"].lower()


def test_server_error_classification():
    result = classify_failure(expected_status=200, actual_status=500)
    assert result["category"] == "Server error"


def test_performance_regression_classification():
    result = classify_failure(duration_ms=1400, performance_budget_ms=1000)
    assert result["category"] == "Performance regression"


def test_summary_when_no_failures():
    assert "All checks passed" in summarize_failures([{"status": "passed"}])
