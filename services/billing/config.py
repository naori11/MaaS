import os


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if value is None or not value.strip():
        raise RuntimeError(f"{name} environment variable is required")
    return value.strip()


def _optional_env(name: str) -> str | None:
    value = os.getenv(name)
    if value is None or not value.strip():
        return None
    return value.strip()


def get_database_url() -> str | None:
    raw_database_url = _optional_env("DATABASE_URL")
    if raw_database_url is None:
        return None
    if raw_database_url.startswith("postgresql://"):
        return raw_database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return raw_database_url


def get_jwt_secret() -> str:
    return _require_env("JWT_SECRET")


def get_jwt_algorithm() -> str:
    return os.getenv("JWT_ALGORITHM", "HS256")


def get_xendit_secret_key() -> str:
    return _require_env("XENDIT_SECRET_KEY")


def get_xendit_callback_token() -> str:
    return _require_env("XENDIT_CALLBACK_TOKEN")


def get_xendit_components_origins() -> list[str]:
    raw_origins = _optional_env("XENDIT_COMPONENTS_ORIGINS")
    if raw_origins is None:
        return ["https://localhost:3000"]

    origins = [origin.strip().rstrip("/") for origin in raw_origins.split(",") if origin.strip()]
    if not origins:
        return ["https://localhost:3000"]

    normalized_origins: list[str] = []
    for origin in origins:
        if origin.startswith("https://"):
            normalized_origins.append(origin)
            continue

        if origin.startswith("http://"):
            normalized_origins.append(f"https://{origin[len('http://'):]}")
            continue

        normalized_origins.append(f"https://{origin}")

    return normalized_origins
