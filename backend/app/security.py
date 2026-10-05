import hashlib
import secrets
from datetime import timedelta

import bcrypt
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .config import settings
from .database import get_db
from .models import Session, User, now

bearer = HTTPBearer(auto_error=False)


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def strong_password(password):
    if (
        len(password) < 10
        or len(password.encode()) > 72
        or not any(c.isupper() for c in password)
        or not any(c.islower() for c in password)
        or not any(c.isdigit() for c in password)
    ):
        raise HTTPException(400, "Use 10–72 bytes, including uppercase, lowercase, and a number.")


def hash_password(password):
    strong_password(password)
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def check_password(password, hashed):
    return len(password.encode()) <= 72 and bcrypt.checkpw(password.encode(), hashed.encode())


def access_token(session):
    return jwt.encode(
        {
            "sub": session.user_id,
            "sid": session.id,
            "iat": now(),
            "exp": now() + timedelta(minutes=15),
        },
        settings().jwt_secret,
        algorithm="HS256",
    )


def start_session(db, user):
    refresh = secrets.token_urlsafe(48)
    session = Session(user_id=user.id, refresh_hash=digest(refresh))
    db.add(session)
    db.commit()
    return {
        "access_token": access_token(session),
        "refresh_token": refresh,
        "token_type": "bearer",
    }


def current_session(
    credentials: HTTPAuthorizationCredentials = Depends(bearer), db=Depends(get_db)
):
    error = HTTPException(401, "Your session has expired. Please sign in again.")
    if not credentials:
        raise error
    try:
        claims = jwt.decode(credentials.credentials, settings().jwt_secret, algorithms=["HS256"])
        session = db.get(Session, claims["sid"])
        if not session or claims["sub"] != session.user_id:
            raise error
    except (jwt.PyJWTError, KeyError):
        raise error
    user = db.get(User, session.user_id)
    if (
        not user
        or not user.active
        or not user.verified
        or session.last_seen < now() - timedelta(hours=settings().session_hours)
    ):
        raise error
    session.last_seen = now()
    db.commit()
    return session


def current_user(session=Depends(current_session), db=Depends(get_db)):
    return db.get(User, session.user_id)


def admin_user(user=Depends(current_user)):
    if user.role != "admin":
        raise HTTPException(403, "Administrator access is required.")
    return user


def user_view(user):
    return {
        k: getattr(user, k)
        for k in ["id", "name", "email", "role", "verified", "active", "created_at"]
    }
