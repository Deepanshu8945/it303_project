import secrets
from datetime import timedelta

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError

from ..database import get_db
from ..mail import send_link
from ..models import ActionToken, Session, User, now
from ..security import (
    access_token,
    check_password,
    current_session,
    current_user,
    digest,
    hash_password,
    start_session,
    user_view,
)

router = APIRouter(prefix="/auth", tags=["User management"])


class Credentials(BaseModel):
    email: EmailStr
    password: str = Field(max_length=256)


class Registration(Credentials):
    name: str = Field(min_length=1, max_length=100)


class EmailRequest(BaseModel):
    email: EmailStr


class TokenRequest(BaseModel):
    token: str = Field(min_length=10, max_length=512)


class ResetRequest(TokenRequest):
    password: str = Field(max_length=256)


def issue_action(db, user, purpose, tasks):
    token = secrets.token_urlsafe(40)
    db.execute(
        delete(ActionToken).where(ActionToken.user_id == user.id, ActionToken.purpose == purpose)
    )
    db.add(
        ActionToken(
            token_hash=digest(token),
            user_id=user.id,
            purpose=purpose,
            expires_at=now() + timedelta(hours=1),
        )
    )
    db.commit()
    tasks.add_task(send_link, user.id, user.email, purpose, token)


@router.post("/register", status_code=201)
def register(body: Registration, tasks: BackgroundTasks, db=Depends(get_db)):
    if not body.name.strip():
        raise HTTPException(400, "Enter your name.")
    user = User(
        name=body.name.strip(),
        email=str(body.email).lower(),
        password_hash=hash_password(body.password),
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(400, "This email is already registered.")
    issue_action(db, user, "verify", tasks)
    return {"message": "Account created. Check your email for a verification link."}


@router.post("/verify")
def verify(body: TokenRequest, db=Depends(get_db)):
    token = valid_action(db, body.token, "verify")
    user = db.get(User, token.user_id)
    user.verified = True
    db.delete(token)
    db.commit()
    return {"message": "Email verified. You can now sign in."}


def valid_action(db, raw, purpose):
    token = db.scalar(
        select(ActionToken).where(ActionToken.token_hash == digest(raw)).with_for_update()
    )
    if not token or token.purpose != purpose or token.expires_at < now():
        raise HTTPException(400, "This link is invalid or expired. Request a new link.")
    return token


@router.post("/resend-verification")
def resend(body: EmailRequest, tasks: BackgroundTasks, db=Depends(get_db)):
    user = db.scalar(select(User).where(User.email == str(body.email).lower()))
    if user and not user.verified:
        issue_action(db, user, "verify", tasks)
    return {"message": "If verification is needed, a new link has been sent."}


@router.post("/forgot-password")
def forgot(body: EmailRequest, tasks: BackgroundTasks, db=Depends(get_db)):
    user = db.scalar(select(User).where(User.email == str(body.email).lower()))
    if user and user.active:
        issue_action(db, user, "reset", tasks)
    return {"message": "If this account exists, a password reset link has been sent."}


@router.post("/reset-password")
def reset(body: ResetRequest, db=Depends(get_db)):
    token = valid_action(db, body.token, "reset")
    user = db.get(User, token.user_id)
    user.password_hash = hash_password(body.password)
    user.failed_attempts, user.locked_until = 0, None
    db.execute(delete(Session).where(Session.user_id == user.id))
    db.execute(
        delete(ActionToken).where(ActionToken.user_id == user.id, ActionToken.purpose == "reset")
    )
    db.commit()
    return {"message": "Password reset. Sign in with your new password."}


@router.post("/login")
def login(body: Credentials, db=Depends(get_db)):
    user = db.scalar(select(User).where(User.email == str(body.email).lower()).with_for_update())
    if user and user.locked_until and user.locked_until > now():
        raise HTTPException(429, "Account temporarily locked. Try again in 15 minutes.")
    if not user or not check_password(body.password, user.password_hash):
        if user:
            user.failed_attempts += 1
            if user.failed_attempts >= 5:
                user.locked_until = now() + timedelta(minutes=15)
                user.failed_attempts = 0
            db.commit()
        raise HTTPException(401, "Email or password is incorrect.")
    if not user.active:
        raise HTTPException(403, "This account is suspended. Contact your administrator.")
    if not user.verified:
        raise HTTPException(403, "Verify your email before signing in.")
    user.failed_attempts, user.locked_until = 0, None
    return {**start_session(db, user), "user": user_view(user)}


@router.post("/refresh")
def refresh(body: TokenRequest, db=Depends(get_db)):
    session = db.scalar(
        select(Session).where(Session.refresh_hash == digest(body.token)).with_for_update()
    )
    from ..config import settings

    if not session or session.last_seen < now() - timedelta(hours=settings().session_hours):
        raise HTTPException(401, "Session expired. Sign in again.")
    user = db.get(User, session.user_id)
    if not user.active or not user.verified:
        raise HTTPException(401, "Account is unavailable.")
    refresh_token = secrets.token_urlsafe(48)
    session.refresh_hash, session.last_seen = digest(refresh_token), now()
    db.commit()
    return {
        "access_token": access_token(session),
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


@router.post("/logout")
def logout(session=Depends(current_session), db=Depends(get_db)):
    db.delete(session)
    db.commit()
    return {"message": "Signed out."}


@router.get("/me")
def me(user=Depends(current_user)):
    return user_view(user)
