from __future__ import annotations

import os

APP_NAME = "TestGuard AI"
APP_VERSION = "1.0.0"
TARGET_BASE_URL = os.getenv("TARGET_BASE_URL", "http://127.0.0.1:8001").rstrip("/")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./testguard.db")
REQUEST_TIMEOUT_SECONDS = float(os.getenv("REQUEST_TIMEOUT_SECONDS", "4"))
PERFORMANCE_BUDGET_MS = float(os.getenv("PERFORMANCE_BUDGET_MS", "1000"))
