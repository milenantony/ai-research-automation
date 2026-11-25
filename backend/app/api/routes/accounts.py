from datetime import datetime, timedelta, timezone
from secrets import token_urlsafe
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field, SecretStr, field_validator
from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.models.account import Account, AccountSession
from app.services.account_security import (
    SESSION_COOKIE,
    current_account,
    digest_token,
    hash_password,
    verify_password,
)


router = APIRouter(prefix="/auth", tags=["Accounts"])
SESSION_LIFETIME = timedelta(days=7)


class Credentials(BaseModel):
    email: str = Field(max_length=254, pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
    password: SecretStr

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value):
        return value.strip().casefold() if isinstance(value, str) else value


class AccountResponse(BaseModel):
    id: UUID
    email: str


def start_session(
    db: Session, account: Account, request: Request, response: Response
) -> AccountResponse:
    previous = request.cookies.get(SESSION_COOKIE)
    if previous:
        db.execute(delete(AccountSession).where(AccountSession.token_hash == digest_token(previous)))
    now = datetime.now(timezone.utc)
    db.execute(delete(AccountSession).where(
        AccountSession.account_id == account.id, AccountSession.expires_at <= now
    ))
    token = token_urlsafe(32)
    db.add(AccountSession(
        token_hash=digest_token(token), account_id=account.id, expires_at=now + SESSION_LIFETIME
    ))
    result = AccountResponse(id=account.id, email=account.email)
    db.commit()
    loopback = request.url.hostname in {"localhost", "127.0.0.1", "::1"}
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=int(SESSION_LIFETIME.total_seconds()),
        httponly=True,
        secure=request.url.scheme == "https" or not loopback,
        samesite="strict",
    )
    response.headers["Cache-Control"] = "no-store"
    return result


@router.post("/register", status_code=201)
def register(
    credentials: Credentials, request: Request, response: Response,
    db: Annotated[Session, Depends(get_db)],
) -> AccountResponse:
    password = credentials.password.get_secret_value()
    if not 12 <= len(password) <= 128:
        raise HTTPException(422, "Password must be between 12 and 128 characters")
    account = db.scalar(
        insert(Account)
        .values(email=credentials.email, password_hash=hash_password(password))
        .on_conflict_do_nothing(index_elements=[Account.email])
        .returning(Account)
    )
    if account is None:
        raise HTTPException(409, "An account already exists for this email")
    return start_session(db, account, request, response)


@router.post("/session")
def sign_in(
    credentials: Credentials, request: Request, response: Response,
    db: Annotated[Session, Depends(get_db)],
) -> AccountResponse:
    password = credentials.password.get_secret_value()
    if not 12 <= len(password) <= 128:
        raise HTTPException(401, "Invalid email or password")
    account = db.scalar(select(Account).where(Account.email == credentials.email))
    if not verify_password(password, account.password_hash if account else None):
        raise HTTPException(401, "Invalid email or password")
    return start_session(db, account, request, response)


@router.get("/session")
def get_session(
    response: Response, account: Annotated[Account, Depends(current_account)],
) -> AccountResponse:
    response.headers["Cache-Control"] = "no-store"
    return AccountResponse(id=account.id, email=account.email)


@router.delete("/session", status_code=204)
def sign_out(
    response: Response,
    db: Annotated[Session, Depends(get_db)],
    token: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None,
) -> None:
    if token:
        db.execute(delete(AccountSession).where(AccountSession.token_hash == digest_token(token)))
        db.commit()
    response.delete_cookie(SESSION_COOKIE)
    response.headers["Cache-Control"] = "no-store"
