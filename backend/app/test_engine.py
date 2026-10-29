from __future__ import annotations

import time
from typing import Any, Awaitable, Callable

import httpx

from .analyzer import classify_failure, summarize_failures
from .config import PERFORMANCE_BUDGET_MS, REQUEST_TIMEOUT_SECONDS, TARGET_BASE_URL

Validator = Callable[[httpx.Response], tuple[bool, str, str]]


def _json_summary(response: httpx.Response) -> str:
    try:
        return str(response.json())[:700]
    except ValueError:
        return response.text[:700]


def _is_health_ok(response: httpx.Response) -> tuple[bool, str, str]:
    body = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
    ok = response.status_code == 200 and body.get("status") == "ok"
    return ok, "HTTP 200 with body.status='ok'", _json_summary(response)


def _is_product_list_ok(response: httpx.Response) -> tuple[bool, str, str]:
    body = response.json() if response.headers.get("content-type", "").startswith("application/json") else None
    product_one = next((item for item in body if isinstance(item, dict) and item.get("id") == 1), None) if isinstance(body, list) else None
    ok = response.status_code == 200 and isinstance(body, list) and len(body) >= 3 and product_one is not None and isinstance(product_one.get("price"), (int, float)) and abs(float(product_one["price"]) - 4.99) < 0.01
    return ok, "HTTP 200 with at least 3 products and product 1 price=4.99", _json_summary(response)


def _is_product_details_ok(response: httpx.Response) -> tuple[bool, str, str]:
    body = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
    ok = response.status_code == 200 and body.get("id") == 1 and isinstance(body.get("price"), (int, float)) and abs(float(body.get("price", 0)) - 4.99) < 0.01
    return ok, "HTTP 200, product id=1 and price=4.99", _json_summary(response)


def _is_unknown_product_404(response: httpx.Response) -> tuple[bool, str, str]:
    ok = response.status_code == 404
    return ok, "HTTP 404 for an unknown product", f"HTTP {response.status_code}: {_json_summary(response)}"


def _is_checkout_total_ok(response: httpx.Response) -> tuple[bool, str, str]:
    body = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
    total = body.get("total")
    ok = response.status_code == 201 and body.get("product_id") == 1 and body.get("quantity") == 2 and isinstance(total, (int, float)) and abs(float(total) - 9.98) < 0.01
    return ok, "HTTP 201 with total=9.98 for 2 units of product 1", _json_summary(response)


def _is_invalid_checkout_rejected(response: httpx.Response) -> tuple[bool, str, str]:
    ok = response.status_code == 422
    return ok, "HTTP 422 for quantity=0", f"HTTP {response.status_code}: {_json_summary(response)}"


def _is_unknown_route_404(response: httpx.Response) -> tuple[bool, str, str]:
    ok = response.status_code == 404
    return ok, "HTTP 404 for an unknown route", f"HTTP {response.status_code}: {_json_summary(response)}"


TEST_CASES: list[dict[str, Any]] = [
    {"name": "Health endpoint", "description": "Service health returns a healthy status.", "method": "GET", "path": "/health", "validator": _is_health_ok},
    {"name": "Product list contract", "description": "Product list returns at least three products.", "method": "GET", "path": "/products", "validator": _is_product_list_ok},
    {"name": "Product detail contract", "description": "Known product has an id and a positive price.", "method": "GET", "path": "/products/1", "validator": _is_product_details_ok},
    {"name": "Unknown product handling", "description": "Unknown product IDs return HTTP 404.", "method": "GET", "path": "/products/9999", "validator": _is_unknown_product_404},
    {"name": "Checkout calculation", "description": "Checkout correctly calculates a 2-item total.", "method": "POST", "path": "/checkout", "json": {"product_id": 1, "quantity": 2}, "validator": _is_checkout_total_ok},
    {"name": "Invalid checkout validation", "description": "Invalid quantity is rejected by request validation.", "method": "POST", "path": "/checkout", "json": {"product_id": 1, "quantity": 0}, "validator": _is_invalid_checkout_rejected},
    {"name": "Unknown route handling", "description": "Unknown routes return HTTP 404 rather than silently succeeding.", "method": "GET", "path": "/route-that-does-not-exist", "validator": _is_unknown_route_404},
]


def get_test_catalog() -> list[dict[str, str]]:
    return [{"name": c["name"], "description": c["description"], "method": c["method"], "path": c["path"]} for c in TEST_CASES]


async def execute_suite() -> dict[str, Any]:
    """Execute the built-in API contract suite against TARGET_BASE_URL."""
    results: list[dict[str, Any]] = []
    async with httpx.AsyncClient(base_url=TARGET_BASE_URL, timeout=REQUEST_TIMEOUT_SECONDS) as client:
        for case in TEST_CASES:
            started = time.perf_counter()
            result: dict[str, Any] = {
                "test_name": case["name"],
                "description": case["description"],
                "endpoint": f"{case['method']} {case['path']}",
                "status": "failed",
                "duration_ms": 0.0,
                "expected": "",
                "actual": "",
                "category": "",
                "diagnosis": "",
                "recommendation": "",
            }
            try:
                response = await client.request(case["method"], case["path"], json=case.get("json"))
                duration_ms = (time.perf_counter() - started) * 1000
                passed, expected, actual = case["validator"](response)
                result.update({
                    "status": "passed" if passed and duration_ms <= PERFORMANCE_BUDGET_MS else "failed",
                    "duration_ms": round(duration_ms, 2),
                    "expected": expected,
                    "actual": actual,
                })
                if result["status"] == "failed":
                    triage = classify_failure(
                        expected_status=200 if "HTTP 200" in expected else 201 if "HTTP 201" in expected else 422 if "HTTP 422" in expected else 404 if "HTTP 404" in expected else None,
                        actual_status=response.status_code,
                        duration_ms=duration_ms,
                        performance_budget_ms=PERFORMANCE_BUDGET_MS,
                        expected_text=expected,
                        actual_text=actual,
                    )
                    result.update(triage)
                    if duration_ms <= PERFORMANCE_BUDGET_MS and response.status_code in (200, 201, 404, 422):
                        # The HTTP status may be correct while the response body violates the contract.
                        if ("total=9.98" in expected and response.status_code == 201) or (expected.startswith("HTTP 200") and response.status_code == 200):
                            result["category"] = "Response contract / data mismatch"
                            result["diagnosis"] = "The endpoint returned an expected status but its response body failed a content assertion."
                            result["recommendation"] = "Compare the returned schema and business calculation with the API contract; add a focused unit test for the failing field."
            except (httpx.TimeoutException, httpx.ConnectError, httpx.RequestError) as exc:
                duration_ms = (time.perf_counter() - started) * 1000
                error_text = f"{type(exc).__name__}: {exc}"
                triage = classify_failure(error=error_text, duration_ms=duration_ms, performance_budget_ms=PERFORMANCE_BUDGET_MS)
                result.update({
                    "status": "failed",
                    "duration_ms": round(duration_ms, 2),
                    "expected": f"Reach target service at {TARGET_BASE_URL}",
                    "actual": error_text[:700],
                    **triage,
                })
            except Exception as exc:  # Keep a single malformed response from aborting the suite.
                duration_ms = (time.perf_counter() - started) * 1000
                triage = classify_failure(error=f"Unexpected runner error: {type(exc).__name__}: {exc}")
                result.update({"status": "failed", "duration_ms": round(duration_ms, 2), "expected": "Test completes without runner exceptions", "actual": str(exc)[:700], **triage})
            results.append(result)

    passed_count = sum(r["status"] == "passed" for r in results)
    total = len(results)
    return {
        "total": total,
        "passed": passed_count,
        "failed": total - passed_count,
        "avg_duration_ms": round(sum(r["duration_ms"] for r in results) / total, 2) if total else 0,
        "summary": summarize_failures(results),
        "results": results,
    }
