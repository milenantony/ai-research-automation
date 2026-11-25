from datetime import datetime, timezone
from hashlib import scrypt, sha256
from hmac import compare_digest
from secrets import token_bytes
from typing import Annotated
from uuid import UUID

from fastapi import Cookie, Depends, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.models.account import Account, AccountSession
from app.models.research_job import ResearchJob


SESSION_COOKIE = "paperx_session"


def _derive_password(password: str, salt: bytes) -> bytes:
    return scrypt(password.encode("utf-8"), salt=salt, n=2**17, r=8, p=1, maxmem=256 * 1024 * 1024)


def hash_password(password: str) -> str:
    salt = token_bytes(16)
    return f"{salt.hex()}:{_derive_password(password, salt).hex()}"


def verify_password(password: str, password_hash: str | None) -> bool:
    if password_hash is None:
        _derive_password(password, bytes(16))
        return False
    salt, expected = password_hash.split(":", 1)
    return compare_digest(_derive_password(password, bytes.fromhex(salt)), bytes.fromhex(expected))


def digest_token(token: str) -> str:
    return sha256(token.encode("utf-8")).hexdigest()


def current_account(
    db: Annotated[Session, Depends(get_db)],
    token: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None,
) -> Account:
    if token:
        account = db.scalar(
            select(Account)
            .join(AccountSession)
            .where(
                AccountSession.token_hash == digest_token(token),
                AccountSession.expires_at > datetime.now(timezone.utc),
            )
        )
        if account:
            return account
    raise HTTPException(401, "Sign in to continue")


def require_job_access(
    request: Request,
    response: Response,
    account: Annotated[Account, Depends(current_account)],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    response.headers["Cache-Control"] = "no-store"
    job_id = request.path_params.get("job_id")
    if job_id is None:
        return
    try:
        job_id = UUID(job_id)
    except ValueError as exc:
        raise HTTPException(422, "Invalid research job ID") from exc

    if db.scalar(select(ResearchJob.id).where(
        ResearchJob.id == job_id, ResearchJob.owner_id == account.id
    )) is None:
        raise HTTPException(404, "Research job not found")
