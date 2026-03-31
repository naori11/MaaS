import os


IDENTITY_SERVICE_URL = os.getenv("IDENTITY_SERVICE_URL", "http://localhost:8010")

# For docker compose, route to the service name within the docker network instead of localhost
MATH_ADD_SERVICE_URL = os.getenv("MATH_ADD_SERVICE_URL", "http://math-add:8000")
MATH_SUBTRACT_SERVICE_URL = os.getenv("MATH_SUBTRACT_SERVICE_URL", "http://math-subtract:8000")
MATH_MULTIPLY_SERVICE_URL = os.getenv("MATH_MULTIPLY_SERVICE_URL", "http://math-multiply:8000")
MATH_DIVIDE_SERVICE_URL = os.getenv("MATH_DIVIDE_SERVICE_URL", "http://math-divide:8000")

RATE_LIMIT_REQUESTS = int(os.getenv("RATE_LIMIT_REQUESTS", "60"))
RATE_LIMIT_WINDOW_SECONDS = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))
UPSTREAM_TIMEOUT_SECONDS = float(os.getenv("UPSTREAM_TIMEOUT_SECONDS", "5"))
