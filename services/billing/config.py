import os


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if value is None or not value.strip():
        raise RuntimeError(f"{name} environment variable is required")
    return value.strip()


def get_database_url() -> str:
    raw_database_url = _require_env("DATABASE_URL")
    if raw_database_url.startswith("postgresql://"):
        return raw_database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return raw_database_url


def get_jwt_secret() -> str:
    return _require_env("JWT_SECRET")


def get_jwt_algorithm() -> str:
    return os.getenv("JWT_ALGORITHM", "HS256")


def get_xendit_secret_key() -> str:
    return _require_env("XENDIT_SECRET_KEY")
