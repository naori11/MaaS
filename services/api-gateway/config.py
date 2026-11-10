import os

IDENTITY_SERVICE_URL = os.getenv("IDENTITY_SERVICE_URL", "http://localhost:8010")
BILLING_SERVICE_URL = os.getenv("BILLING_SERVICE_URL", "http://localhost:8031")
MATH_ADD_SERVICE_URL = os.getenv("MATH_ADD_SERVICE_URL", "http://localhost:8011")
MATH_SUBTRACT_SERVICE_URL = os.getenv("MATH_SUBTRACT_SERVICE_URL", "http://localhost:8012")
MATH_MULTIPLY_SERVICE_URL = os.getenv("MATH_MULTIPLY_SERVICE_URL", "http://localhost:8013")
MATH_DIVIDE_SERVICE_URL = os.getenv("MATH_DIVIDE_SERVICE_URL", "http://localhost:8014")

RATE_LIMIT_REQUESTS = int(os.getenv("RATE_LIMIT_REQUESTS", "60"))
RATE_LIMIT_WINDOW_SECONDS = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))
UPSTREAM_TIMEOUT_SECONDS = float(os.getenv("UPSTREAM_TIMEOUT_SECONDS", "5"))

LEDGER_SERVICE_URL = os.getenv("LEDGER_SERVICE_URL", "http://localhost:8021")
LEDGER_PUBLISH_TIMEOUT_SECONDS = float(os.getenv("LEDGER_PUBLISH_TIMEOUT_SECONDS", "0.5"))
JWT_SECRET = os.getenv("JWT_SECRET", "")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
CORS_ORIGINS = os.getenv("CORS_ORIGINS", os.getenv("CORS_ALLOWED_ORIGINS", ""))


def get_cors_origins() -> list[str]:
    raw = os.getenv("CORS_ALLOWED_ORIGINS") or os.getenv("CORS_ORIGINS")
    if raw is not None and raw.strip():
        return [origin.strip() for origin in raw.split(",") if origin.strip()]
    return [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://localhost:3000",
        "https://127.0.0.1:3000",
        "http://localhost",
        "https://localhost",
        "http://127.0.0.1",
        "https://127.0.0.1",
    ]
