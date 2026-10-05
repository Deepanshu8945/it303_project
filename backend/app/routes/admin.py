from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import delete, func, select

from ..database import get_db
from ..models import Conversion, Event, Session, SystemConfig, User
from ..security import admin_user, user_view
from ..storage import remove_user_files
from .conversions import history_view

router = APIRouter(prefix="/admin", tags=["Administration"])


def audit(db, user, message):
    db.add(Event(user_id=user.id, kind="admin", message=message))
    db.commit()


@router.get("")
def dashboard(q: str = "", user=Depends(admin_user), db=Depends(get_db)):
    audit(db, user, "Viewed administrative dashboard")
    accounts = select(User).order_by(User.created_at.desc())
    if q:
        accounts = accounts.where(
            User.email.contains(q, autoescape=True) | User.name.contains(q, autoescape=True)
        )
    config = db.get(SystemConfig, 1)
    return {
        "users": [user_view(u) for u in db.scalars(accounts.limit(500))],
        "stats": {
            "users": db.scalar(select(func.count()).select_from(User)),
            "conversions": db.scalar(select(func.count()).select_from(Conversion)),
            "validation_errors": db.scalar(
                select(func.count()).select_from(Event).where(Event.kind == "validation")
            ),
        },
        "config": {
            k: getattr(config, k) for k in ["max_upload_mb", "nominal_threshold", "retention_hours"]
        },
        "activity": [
            history_view(c)
            for c in db.scalars(select(Conversion).order_by(Conversion.created_at.desc()).limit(50))
        ],
        "logs": [
            {k: getattr(e, k) for k in ["id", "kind", "message", "details", "created_at"]}
            for e in db.scalars(select(Event).order_by(Event.created_at.desc()).limit(100))
        ],
    }


class AccountUpdate(BaseModel):
    active: bool


@router.patch("/users/{key}")
def update(key: str, body: AccountUpdate, user=Depends(admin_user), db=Depends(get_db)):
    target = db.get(User, key)
    if not target:
        raise HTTPException(404, "Account not found.")
    if target.role == "admin":
        raise HTTPException(400, "Administrator accounts cannot be suspended here.")
    target.active = body.active
    if not body.active:
        db.execute(delete(Session).where(Session.user_id == target.id))
    audit(
        db,
        user,
        f"Account {target.id}: " + ("activated" if body.active else "suspended"),
    )
    return user_view(target)


@router.delete("/users/{key}")
def remove(key: str, user=Depends(admin_user), db=Depends(get_db)):
    target = db.get(User, key)
    if not target:
        raise HTTPException(404, "Account not found.")
    if target.role == "admin":
        raise HTTPException(400, "Administrator accounts cannot be deleted here.")
    remove_user_files(db, target.id)
    db.delete(target)
    audit(db, user, f"Deleted account {key}")
    return {"message": "Account and related records deleted."}


class LimitsUpdate(BaseModel):
    max_upload_mb: int = Field(ge=1, le=50)
    nominal_threshold: int = Field(ge=1, le=1000)
    retention_hours: int = Field(ge=1, le=168)


@router.put("/config")
def configure(body: LimitsUpdate, user=Depends(admin_user), db=Depends(get_db)):
    from datetime import timedelta

    from ..models import Upload, now

    config = db.get(SystemConfig, 1)
    for key, value in body.model_dump().items():
        setattr(config, key, value)
    cutoff = now() + timedelta(hours=body.retention_hours)
    for model in (Upload, Conversion):
        from sqlalchemy import update

        db.execute(update(model).where(model.expires_at > cutoff).values(expires_at=cutoff))
    audit(db, user, "Updated system limits")
    return body
