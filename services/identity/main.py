from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from typing import Annotated, Literal
from uuid import uuid4

import base64
import hashlib
import hmac
import secrets

import jwt
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from jwt import InvalidTokenError
from pydantic import BaseModel, StringConstraints
from sqlalchemy import DateTime, String, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from config import DATABASE_URL, JWT_ALGORITHM, JWT_EXPIRES_SECONDS, JWT_SECRET


Password = Annotated[str, StringConstraints(min_length=8)]


class RegisterRequest(BaseModel):
    email: str
    password: Password


class LoginRequest(BaseModel):
    email: str
    password: Password


class AuthResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"]
    expires_in: int


class MeResponse(BaseModel):
    id: str
    email: str
    created_at: str


class RegisterResponse(BaseModel):
    id: str
    email: str
    created_at: str


class Base(DeclarativeBase):
    pass


class UserORM(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)


_SESSION_FACTORY: async_sessionmaker[AsyncSession] | None = None


def _database_url() -> str:
    if DATABASE_URL.startswith("postgresql://"):
        return DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
    return DATABASE_URL


def _to_iso_z(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 600_000)
    return f"pbkdf2_sha256$600000${base64.b64encode(salt).decode('ascii')}${base64.b64encode(derived).decode('ascii')}"


def _verify_password(password: str, password_hash: str) -> bool:
    try:
        algorithm, iterations_raw, salt_raw, expected_raw = password_hash.split("$", 3)
    except ValueError:
        return False

    if algorithm != "pbkdf2_sha256":
        return False

    try:
        iterations = int(iterations_raw)
        salt = base64.b64decode(salt_raw.encode("ascii"), validate=True)
        expected = base64.b64decode(expected_raw.encode("ascii"), validate=True)
    except Exception:
        return False

    derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return hmac.compare_digest(derived, expected)


def _issue_access_token(user_id: str) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": user_id,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=JWT_EXPIRES_SECONDS)).timestamp()),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def _extract_bearer_token(request: Request) -> str:
    authorization = request.headers.get("Authorization", "")
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    return token


def _user_id_from_token(token: str) -> str:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except InvalidTokenError as exc:
        raise HTTPException(status_code=401, detail="Invalid credentials") from exc

    user_id = payload.get("sub")
    if not isinstance(user_id, str) or not user_id:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return user_id


def _make_engine():
    url = _database_url()
    if ":memory:" in url:
        return create_async_engine(
            url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    return create_async_engine(url)


@asynccontextmanager
async def lifespan(_: FastAPI):
    global _SESSION_FACTORY

    engine = _make_engine()
    _SESSION_FACTORY = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    try:
        yield
    finally:
        _SESSION_FACTORY = None
        await engine.dispose()


app = FastAPI(lifespan=lifespan)


@app.exception_handler(RequestValidationError)
async def request_validation_exception_handler(_, __):
    return JSONResponse(status_code=400, content={"detail": "Malformed payload"})


@app.post("/api/v1/auth/register", response_model=RegisterResponse, status_code=201)
async def register(payload: RegisterRequest) -> RegisterResponse:
    if _SESSION_FACTORY is None:
        raise HTTPException(status_code=500, detail="Identity database unavailable")

    created_at = datetime.now(UTC)
    user = UserORM(
        email=payload.email,
        password_hash=_hash_password(payload.password),
        created_at=created_at,
    )

    async with _SESSION_FACTORY() as session:
        session.add(user)
        try:
            await session.commit()
        except IntegrityError as exc:
            await session.rollback()
            raise HTTPException(status_code=409, detail="Email already registered") from exc

    return RegisterResponse(id=user.id, email=user.email, created_at=_to_iso_z(user.created_at))


@app.post("/api/v1/auth/login", response_model=AuthResponse)
async def login(payload: LoginRequest) -> AuthResponse:
    if _SESSION_FACTORY is None:
        raise HTTPException(status_code=500, detail="Identity database unavailable")

    async with _SESSION_FACTORY() as session:
        result = await session.execute(select(UserORM).where(UserORM.email == payload.email))
        user = result.scalar_one_or_none()

    if user is None or not _verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = _issue_access_token(user.id)
    return AuthResponse(access_token=token, token_type="bearer", expires_in=JWT_EXPIRES_SECONDS)


@app.get("/api/v1/auth/me", response_model=MeResponse)
async def me(request: Request) -> MeResponse:
    if _SESSION_FACTORY is None:
        raise HTTPException(status_code=500, detail="Identity database unavailable")

    token = _extract_bearer_token(request)
    user_id = _user_id_from_token(token)

    async with _SESSION_FACTORY() as session:
        result = await session.execute(select(UserORM).where(UserORM.id == user_id))
        user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    return MeResponse(id=user.id, email=user.email, created_at=_to_iso_z(user.created_at))
