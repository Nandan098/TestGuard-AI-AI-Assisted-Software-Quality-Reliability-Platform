from __future__ import annotations

from typing import Any


def classify_failure(
    *,
    expected_status: int | None = None,
    actual_status: int | None = None,
    duration_ms: float = 0,
    performance_budget_ms: float = 1000,
    error: str | None = None,
    expected_text: str = "",
    actual_text: str = "",
) -> dict[str, str]:
    """Rule-based failure triage; deterministic and safe to run without an LLM."""
    if error:
        lower = error.lower()
        if "timeout" in lower or "timed out" in lower:
            return {
                "category": "Timeout / availability",
                "diagnosis": "The target service did not respond within the configured timeout.",
                "recommendation": "Check target availability, network connectivity, and service logs; increase the timeout only if the endpoint is expected to be slow.",
            }
        return {
            "category": "Connectivity / infrastructure",
            "diagnosis": "The test runner could not complete the request to the target service.",
            "recommendation": "Confirm the target app is running and TARGET_BASE_URL points to the correct host and port.",
        }

    if duration_ms > performance_budget_ms:
        return {
            "category": "Performance regression",
            "diagnosis": f"Response time ({duration_ms:.1f} ms) exceeded the configured budget ({performance_budget_ms:.0f} ms).",
            "recommendation": "Repeat the test to rule out transient noise, then inspect database calls, external dependencies, payload sizes, and recent changes.",
        }

    if actual_status is not None and expected_status is not None and actual_status != expected_status:
        if actual_status >= 500:
            category = "Server error"
            diagnosis = f"The endpoint returned HTTP {actual_status}, indicating an unexpected server-side failure."
            recommendation = "Inspect application logs and reproduce the request with the same payload; check exception handling and upstream dependencies."
        elif actual_status in (400, 401, 403, 404, 409, 422):
            category = "Unexpected HTTP status / validation"
            diagnosis = f"Expected HTTP {expected_status}, but received HTTP {actual_status}."
            recommendation = "Check request payload, validation rules, route behavior, and the expected response contract."
        else:
            category = "Unexpected HTTP status"
            diagnosis = f"Expected HTTP {expected_status}, but received HTTP {actual_status}."
            recommendation = "Review the endpoint contract and verify the status code for this scenario."
        return {"category": category, "diagnosis": diagnosis, "recommendation": recommendation}

    return {
        "category": "Response contract / data mismatch",
        "diagnosis": "The response status was acceptable, but one or more response assertions did not match the expected contract.",
        "recommendation": f"Compare expected behavior ({expected_text}) with actual behavior ({actual_text}); inspect serialization, business rules, and test assumptions.",
    }


def summarize_failures(results: list[dict[str, Any]]) -> str:
    failures = [r for r in results if r.get("status") == "failed"]
    if not failures:
        return "All checks passed. Continue monitoring response time and rerun the suite after code changes."
    counts: dict[str, int] = {}
    for item in failures:
        category = item.get("category") or "Unclassified"
        counts[category] = counts.get(category, 0) + 1
    most_common = sorted(counts.items(), key=lambda item: (-item[1], item[0]))[0]
    return f"{len(failures)} of {len(results)} checks failed. Most common category: {most_common[0]} ({most_common[1]}). Review the individual diagnosis and recommendations below."
