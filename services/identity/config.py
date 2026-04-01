import os


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"{name} environment variable is required")
    return value


def _parse_int_env(name: str, default: str) -> int:
    raw_value = os.getenv(name, default)
    try:
        return int(raw_value)
    except ValueError as exc:
        raise RuntimeError(
            f"{name} environment variable must be an integer, got {raw_value!r}"
        ) from exc


DATABASE_URL = _require_env("DATABASE_URL")
JWT_SECRET = _require_env("JWT_SECRET")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRES_SECONDS = _parse_int_env("JWT_EXPIRES_SECONDS", "3600")
